from dataclasses import dataclass, field
from collections import deque
from vehicle.interfaces import DeviceCapabilities
@dataclass
class SimulatedVehicle:
    vin:str="WDB21100000000001"; dtcs:list[str]=field(default_factory=list); pids:dict[int,float]=field(default_factory=lambda:{0x0C:850.0,0x05:90.0,0x06:1.2,0x07:0.8}); can_rx:deque=field(default_factory=deque); connected:bool=False
    def connect(self): self.connected=True
    def disconnect(self): self.connected=False
    def read_vin(self): return self.vin
    def read_dtcs(self): return list(self.dtcs)
    def read_pid(self,pid): return self.pids.get(pid)
class SimulatedAdapter:
    def __init__(self,vehicle:SimulatedVehicle): self.vehicle=vehicle
    async def connect(self): self.vehicle.connect()
    async def disconnect(self): self.vehicle.disconnect()
    def capabilities(self): return DeviceCapabilities(obd=True,can=True,can_fd=True,uds=True)
    async def read_vin(self): return self.vehicle.read_vin()
    async def read_dtcs(self): return self.vehicle.read_dtcs()
    async def read_pid(self,pid): return self.vehicle.read_pid(pid)
    async def send(self,arbitration_id,data): self.vehicle.can_rx.append((arbitration_id,data))
    async def receive(self,timeout_ms=1000): return self.vehicle.can_rx.popleft() if self.vehicle.can_rx else None
    async def diagnostic_session_control(self,session_type): return bytes([0x50,session_type])
