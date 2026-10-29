from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass(frozen=True)
class GatewayRoute:
    gateway_id: str
    source_bus: str
    target_bus: str
    target_ecu_id: str
    addressing: str = 'NORMAL'

@dataclass(frozen=True)
class GatewayNode:
    gateway_id: str
    name: str
    bus: str = 'CAN0'
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class EcuNode:
    ecu_id: str
    name: str
    request_id: int
    response_id: int
    bus: str = 'CAN0'
    gateway_id: str | None = None
    address_type: str = 'NORMAL'
    capabilities: frozenset[str] = frozenset({'IDENTITY', 'DTC_READ'})
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'ecu_id': self.ecu_id, 'name': self.name,
            'request_id': self.request_id, 'response_id': self.response_id,
            'bus': self.bus, 'gateway_id': self.gateway_id,
            'address_type': self.address_type,
            'capabilities': sorted(self.capabilities), 'metadata': self.metadata,
        }

@dataclass(frozen=True)
class VehicleNetworkTopology:
    ecus: tuple[EcuNode, ...] = ()
    gateways: tuple[GatewayNode, ...] = ()
    routes: tuple[GatewayRoute, ...] = ()

    def ecu(self, ecu_id: str) -> EcuNode:
        for node in self.ecus:
            if node.ecu_id == ecu_id:
                return node
        raise KeyError(ecu_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            'ecus': [e.to_dict() for e in self.ecus],
            'gateways': [g.__dict__ for g in self.gateways],
            'routes': [r.__dict__ for r in self.routes],
        }
