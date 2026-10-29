from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import median
from typing import Iterable

from vehicle.can.models import CanFrame


@dataclass(frozen=True)
class CanIdObservation:
    bus: str
    arbitration_id: int
    timestamp_ns: int
    dlc: int
    data_hex: str
    direction: str = "RX"
    extended: bool = False
    fd: bool = False


@dataclass(frozen=True)
class CanIdProfile:
    bus: str
    arbitration_id: int
    frame_count: int
    dlc_values: tuple[int, ...]
    periodicity_ms: float | None
    extended: bool
    fd: bool
    sample_payloads: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "bus": self.bus,
            "arbitration_id": self.arbitration_id,
            "arbitration_id_hex": f"0x{self.arbitration_id:X}",
            "frame_count": self.frame_count,
            "dlc_values": list(self.dlc_values),
            "periodicity_ms": self.periodicity_ms,
            "extended": self.extended,
            "fd": self.fd,
            "sample_payloads": list(self.sample_payloads),
        }


@dataclass(frozen=True)
class InferredUdsPair:
    bus: str
    request_id: int
    response_id: int
    confidence: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict:
        return {
            "bus": self.bus,
            "request_id": self.request_id,
            "response_id": self.response_id,
            "request_id_hex": f"0x{self.request_id:X}",
            "response_id_hex": f"0x{self.response_id:X}",
            "confidence": round(self.confidence, 4),
            "evidence": list(self.evidence),
        }


@dataclass(frozen=True)
class DiscoveredEcuCandidate:
    candidate_id: str
    bus: str
    request_id: int | None
    response_id: int | None
    confidence: float
    classification: str
    evidence: tuple[str, ...]
    observed_ids: tuple[int, ...] = ()

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "bus": self.bus,
            "request_id": self.request_id,
            "response_id": self.response_id,
            "request_id_hex": f"0x{self.request_id:X}" if self.request_id is not None else None,
            "response_id_hex": f"0x{self.response_id:X}" if self.response_id is not None else None,
            "confidence": round(self.confidence, 4),
            "classification": self.classification,
            "evidence": list(self.evidence),
            "observed_ids": list(self.observed_ids),
            "observed_ids_hex": [f"0x{x:X}" for x in self.observed_ids],
        }


@dataclass
class VehicleNetworkDiscoveryResult:
    profiles: list[CanIdProfile] = field(default_factory=list)
    uds_pairs: list[InferredUdsPair] = field(default_factory=list)
    ecu_candidates: list[DiscoveredEcuCandidate] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "profiles": [p.to_dict() for p in self.profiles],
            "uds_pairs": [p.to_dict() for p in self.uds_pairs],
            "ecu_candidates": [c.to_dict() for c in self.ecu_candidates],
            "summary": {
                "bus_count": len({p.bus for p in self.profiles}),
                "observed_can_ids": len(self.profiles),
                "inferred_uds_pairs": len(self.uds_pairs),
                "ecu_candidates": len(self.ecu_candidates),
            },
        }


class VehicleNetworkDiscoveryEngine:
    """Passive discovery from observed CAN traffic.

    Discovery is intentionally inferential. It never promotes an observed
    arbitration ID into a confirmed ECU identity unless corroborating evidence
    is available from a higher-level diagnostic operation.
    """

    def __init__(self, *, uds_pair_offsets: tuple[int, ...] = (8,), min_pair_evidence: int = 2):
        self.uds_pair_offsets = uds_pair_offsets
        self.min_pair_evidence = min_pair_evidence

    def analyze(self, frames: Iterable[CanFrame], *, bus: str = "CAN0") -> VehicleNetworkDiscoveryResult:
        observations = [
            CanIdObservation(
                bus=bus,
                arbitration_id=f.arbitration_id,
                timestamp_ns=f.timestamp_ns or 0,
                dlc=f.dlc,
                data_hex=f.data.hex().upper(),
                extended=f.is_extended,
                fd=f.is_fd,
            )
            for f in frames
        ]
        return self.analyze_observations(observations)

    def analyze_observations(self, observations: Iterable[CanIdObservation]) -> VehicleNetworkDiscoveryResult:
        by_key: dict[tuple[str, int], list[CanIdObservation]] = defaultdict(list)
        for obs in observations:
            by_key[(obs.bus, obs.arbitration_id)].append(obs)

        profiles: list[CanIdProfile] = []
        for (bus, arbitration_id), values in sorted(by_key.items()):
            values.sort(key=lambda x: x.timestamp_ns)
            deltas_ms = [
                (b.timestamp_ns - a.timestamp_ns) / 1_000_000
                for a, b in zip(values, values[1:])
                if b.timestamp_ns > a.timestamp_ns
            ]
            periodicity = median(deltas_ms) if deltas_ms else None
            profiles.append(
                CanIdProfile(
                    bus=bus,
                    arbitration_id=arbitration_id,
                    frame_count=len(values),
                    dlc_values=tuple(sorted({v.dlc for v in values})),
                    periodicity_ms=round(periodicity, 3) if periodicity is not None else None,
                    extended=any(v.extended for v in values),
                    fd=any(v.fd for v in values),
                    sample_payloads=tuple(dict.fromkeys(v.data_hex for v in values[:5])),
                )
            )

        ids_by_bus = defaultdict(set)
        counts_by_bus = Counter()
        for (bus, arbitration_id), values in by_key.items():
            ids_by_bus[bus].add(arbitration_id)
            counts_by_bus[(bus, arbitration_id)] = len(values)

        pairs: list[InferredUdsPair] = []
        for bus, ids in sorted(ids_by_bus.items()):
            for request_id in sorted(ids):
                for offset in self.uds_pair_offsets:
                    response_id = request_id + offset
                    if response_id not in ids or response_id > 0x7FF:
                        continue
                    req_count = counts_by_bus[(bus, request_id)]
                    res_count = counts_by_bus[(bus, response_id)]
                    evidence_count = min(req_count, res_count)
                    if evidence_count < self.min_pair_evidence:
                        continue
                    confidence = min(0.95, 0.55 + 0.10 * min(evidence_count, 4))
                    pairs.append(
                        InferredUdsPair(
                            bus=bus,
                            request_id=request_id,
                            response_id=response_id,
                            confidence=confidence,
                            evidence=(
                                f"both IDs observed on {bus}",
                                f"request/response offset +{offset}",
                                f"paired observations={evidence_count}",
                            ),
                        )
                    )

        candidates: list[DiscoveredEcuCandidate] = []
        used_ids = set()
        for idx, pair in enumerate(pairs, start=1):
            used_ids.add((pair.bus, pair.request_id))
            used_ids.add((pair.bus, pair.response_id))
            candidates.append(
                DiscoveredEcuCandidate(
                    candidate_id=f"DISC_ECU_{idx:03d}",
                    bus=pair.bus,
                    request_id=pair.request_id,
                    response_id=pair.response_id,
                    confidence=pair.confidence,
                    classification="UDS_REQUEST_RESPONSE_INFERRED",
                    evidence=pair.evidence,
                    observed_ids=(pair.request_id, pair.response_id),
                )
            )

        # IDs that are active but cannot be paired are surfaced as unknown nodes.
        next_idx = len(candidates) + 1
        for profile in profiles:
            key = (profile.bus, profile.arbitration_id)
            if key in used_ids:
                continue
            # Only classify low-volume unknown IDs as candidates when there is
            # enough traffic to make the observation useful.
            if profile.frame_count >= self.min_pair_evidence:
                candidates.append(
                    DiscoveredEcuCandidate(
                        candidate_id=f"DISC_ECU_{next_idx:03d}",
                        bus=profile.bus,
                        request_id=profile.arbitration_id if profile.arbitration_id >= 0x700 else None,
                        response_id=profile.arbitration_id if profile.arbitration_id >= 0x700 else None,
                        confidence=0.30,
                        classification="OBSERVED_CAN_NODE",
                        evidence=(
                            f"observed {profile.frame_count} frames",
                            "no corroborated UDS request/response pair",
                        ),
                        observed_ids=(profile.arbitration_id,),
                    )
                )
                next_idx += 1

        return VehicleNetworkDiscoveryResult(
            profiles=profiles,
            uds_pairs=pairs,
            ecu_candidates=candidates,
        )
