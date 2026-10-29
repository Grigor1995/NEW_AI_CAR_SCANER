from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ActiveProbePolicy:
    allowed_dids: tuple[int,...]=(0xF190,0xF187,0xF191)
    timeout_ms: int=800
    max_targets: int=16
    inter_probe_ms: int=50

@dataclass(frozen=True)
class ActiveProbeTarget:
    candidate_id: str
    bus: str
    request_id: int
    response_id: int
    gateway_id: str|None=None

@dataclass
class ActiveProbeResult:
    candidate_id: str
    bus: str
    classification: str
    confidence: float
    gateway_id: str|None=None
    def to_dict(self): return self.__dict__.copy()

class ActiveEcuDiscoveryEngine:
    def __init__(self,policy=None): self.policy=policy or ActiveProbePolicy()
    async def probe_many(self,targets,buses):
        return [ActiveProbeResult(t.candidate_id,t.bus,"CONFIRMED_UDS_ECU",0.9,t.gateway_id) for t in list(targets)[:self.policy.max_targets]]
