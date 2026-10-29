from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class EcuNode:
    ecu_id: str
    name: str
    request_id: int
    response_id: int
    bus: str = "CAN0"
    gateway_id: str | None = None
    address_type: str = "NORMAL"
    capabilities: frozenset[str] = frozenset()
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class GatewayNode:
    gateway_id: str
    name: str
    bus: str = "CAN0"

@dataclass(frozen=True)
class GatewayRoute:
    gateway_id: str
    source_bus: str
    target_bus: str
    target_ecu_id: str
    addressing: str = "NORMAL"

@dataclass
class VehicleNetworkTopology:
    ecus: tuple[EcuNode, ...]
    gateways: tuple[GatewayNode, ...] = ()
    routes: tuple[GatewayRoute, ...] = ()
    def ecu(self, ecu_id: str) -> EcuNode:
        for e in self.ecus:
            if e.ecu_id == ecu_id: return e
        raise KeyError(ecu_id)
    def to_dict(self) -> dict:
        return {
            "ecus":[{**e.__dict__, "capabilities":sorted(e.capabilities)} for e in self.ecus],
            "gateways":[g.__dict__ for g in self.gateways],
            "routes":[r.__dict__ for r in self.routes],
        }
