from __future__ import annotations
from dataclasses import dataclass, field

@dataclass
class CanIdObservation:
    bus: str
    arbitration_id: int
    timestamp_ns: int
    dlc: int
    data_hex: str
    extended: bool
    fd: bool

@dataclass
class DiscoveredEcuCandidate:
    candidate_id: str
    bus: str
    request_id: int|None
    response_id: int|None
    classification: str = "CAN_NODE"
    confidence: float = 0.5
    def to_dict(self): return self.__dict__.copy()

@dataclass
class VehicleNetworkDiscoveryResult:
    ecu_candidates: list[DiscoveredEcuCandidate] = field(default_factory=list)
    observations: int = 0
    def to_dict(self): return {"ecu_candidates":[c.to_dict() for c in self.ecu_candidates],"observations":self.observations}

class VehicleNetworkDiscoveryEngine:
    def analyze_observations(self, observations):
        candidates={}
        for o in observations:
            if 0x7E0 <= o.arbitration_id <= 0x7E7:
                key=f"{o.bus}:{o.arbitration_id:03X}"
                candidates.setdefault(key,DiscoveredEcuCandidate(key,o.bus,o.arbitration_id,o.arbitration_id+8,"CAN_NODE",0.5))
        return VehicleNetworkDiscoveryResult(list(candidates.values()),len(observations))
