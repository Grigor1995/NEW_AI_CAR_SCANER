from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class CanBusConfig:
    name: str
    bitrate: int = 500_000
    can_fd: bool = False
    data_bitrate: int | None = None
    def to_dict(self): return self.__dict__.copy()

class GatewayRoutingEngine:
    def __init__(self, buses, topology):
        self.buses=buses; self.topology=topology; self._installed=False
    def install(self): self._installed=True
    async def start(self): return None
    async def stop(self): return None
    def route_for_ecu(self, ecu_id):
        for r in self.topology.routes:
            if r.target_ecu_id == ecu_id: return r
        return None
    def stats(self): return {"installed":self._installed,"buses":len(self.buses),"routes":len(self.topology.routes)}

class MultiBusDemultiplexer:
    def __init__(self, bus, response_ids):
        self.bus=bus; self.response_ids=response_ids; self.queues={}
    async def start(self): return None
    async def stop(self): return None
