from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import Any, Iterable

from vehicle.isotp.stack import IsoTpStack
from vehicle.network.multibus import MultiBusDemultiplexer
from vehicle.uds.client import UdsClient, UdsError

@dataclass(frozen=True)
class ActiveProbePolicy:
    allowed_dids: tuple[int, ...] = (0xF190, 0xF187, 0xF191)
    timeout_ms: int = 800
    max_targets: int = 16
    inter_probe_ms: int = 50

    def __post_init__(self):
        if self.timeout_ms < 100: raise ValueError('timeout_ms must be >= 100')
        if not 1 <= self.max_targets <= 64: raise ValueError('max_targets must be 1..64')
        if self.inter_probe_ms < 0: raise ValueError('inter_probe_ms must be >= 0')
        if not self.allowed_dids: raise ValueError('at least one read-only DID is required')
        if any(not 0 <= did <= 0xFFFF for did in self.allowed_dids): raise ValueError('invalid DID')

@dataclass(frozen=True)
class ActiveProbeTarget:
    candidate_id: str
    bus: str
    request_id: int
    response_id: int
    gateway_id: str | None = None

@dataclass(frozen=True)
class ActiveProbeResult:
    candidate_id: str
    bus: str
    request_id: int
    response_id: int
    classification: str
    confidence: float
    responded: bool
    identity: dict[str, str | None] = field(default_factory=dict)
    successful_dids: tuple[str, ...] = ()
    negative_responses: tuple[str, ...] = ()
    error: str | None = None
    gateway_id: str | None = None
    evidence: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            'candidate_id': self.candidate_id, 'bus': self.bus,
            'request_id': self.request_id, 'response_id': self.response_id,
            'request_id_hex': f'0x{self.request_id:X}', 'response_id_hex': f'0x{self.response_id:X}',
            'classification': self.classification, 'confidence': round(self.confidence, 4),
            'responded': self.responded, 'identity': self.identity,
            'successful_dids': list(self.successful_dids),
            'negative_responses': list(self.negative_responses),
            'error': self.error, 'gateway_id': self.gateway_id, 'evidence': list(self.evidence),
        }

class ActiveEcuDiscoveryEngine:
    """Safe read-only ECU probing.

    Only ReadDataByIdentifier (0x22) is emitted, using an explicit DID allowlist.
    No session changes, security access, clearing, coding, reset or programming
    services are exposed by this engine.
    """
    def __init__(self, policy: ActiveProbePolicy | None = None):
        self.policy = policy or ActiveProbePolicy()

    async def probe_many(self, targets: Iterable[ActiveProbeTarget], buses: dict[str, Any]) -> list[ActiveProbeResult]:
        target_list = list(targets)[: self.policy.max_targets]
        if not target_list: return []
        unknown = {t.bus for t in target_list if t.bus not in buses}
        if unknown: raise ValueError(f'probe target references unknown bus(es): {sorted(unknown)}')
        demuxes: dict[str, MultiBusDemultiplexer] = {}
        channels: dict[tuple[str, int], Any] = {}
        try:
            ids_by_bus: dict[str, set[int]] = {}
            for target in target_list: ids_by_bus.setdefault(target.bus, set()).add(target.response_id)
            for bus_name, response_ids in ids_by_bus.items():
                d = MultiBusDemultiplexer(buses[bus_name], response_ids)
                await d.start(); demuxes[bus_name] = d
                for rid in response_ids:
                    channels[(bus_name, rid)] = d.queues[rid]

            async def one(index: int, target: ActiveProbeTarget) -> ActiveProbeResult:
                if index and self.policy.inter_probe_ms:
                    await asyncio.sleep(self.policy.inter_probe_ms / 1000)
                q = channels[(target.bus, target.response_id)]
                class Channel:
                    async def send(inner, frame): await buses[target.bus].send(frame)
                    async def receive(inner, timeout_ms=1000):
                        try: return await asyncio.wait_for(q.get(), timeout_ms / 1000)
                        except asyncio.TimeoutError: return None
                client = UdsClient(IsoTpStack(Channel(), target.request_id, target.response_id, timeout_ms=self.policy.timeout_ms))
                identity: dict[str, str | None] = {'vin': None, 'software_version': None, 'hardware_version': None}
                did_names = {0xF190: 'vin', 0xF187: 'software_version', 0xF191: 'hardware_version'}
                successes: list[str] = []; negatives: list[str] = []; any_response = False; first_error = None
                for did in self.policy.allowed_dids:
                    try:
                        payload = (await client.read_data_by_identifier(did))
                        any_response = True; successes.append(f'0x{did:04X}')
                        if len(payload) < 2 or int.from_bytes(payload[:2], 'big') != did:
                            first_error = f'invalid DID echo for 0x{did:04X}'
                            continue
                        raw = payload[2:]
                        text = bytes(x for x in raw if 32 <= x <= 126).decode('ascii', errors='ignore').strip()
                        if did in did_names: identity[did_names[did]] = text or None
                    except UdsError as exc:
                        if exc.nrc is not None:
                            any_response = True; negatives.append(f'0x{did:04X}:NRC=0x{exc.nrc:02X}')
                            if first_error is None: first_error = str(exc)
                        elif first_error is None:
                            first_error = str(exc)
                    except Exception as exc:
                        if first_error is None: first_error = str(exc)
                if any_response and any(identity.values()):
                    cls, conf = 'CONFIRMED_UDS_ECU', min(0.99, 0.90 + 0.03 * len(successes))
                elif any_response:
                    cls, conf = 'ACTIVE_UDS_RESPONDER', 0.78
                else:
                    cls, conf = 'NO_RESPONSE', 0.05
                evidence = [f'active read-only probes on {target.bus}', f'response_id=0x{target.response_id:X}']
                if target.gateway_id: evidence.append(f'accessed via gateway {target.gateway_id}')
                if successes: evidence.append(f'successful DIDs={len(successes)}')
                if negatives: evidence.append(f'negative responses={len(negatives)}')
                return ActiveProbeResult(target.candidate_id, target.bus, target.request_id, target.response_id, cls, conf,
                    any_response, identity, tuple(successes), tuple(negatives), first_error, target.gateway_id, tuple(evidence))
            return list(await asyncio.gather(*(one(i, t) for i, t in enumerate(target_list))))
        finally:
            for d in demuxes.values(): await d.stop()
