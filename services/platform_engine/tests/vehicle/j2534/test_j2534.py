import pytest
from vehicle.devices.models import DeviceDescriptor, DeviceCapabilities
from vehicle.adapters.j2534 import J2534Adapter

class Fake:
    def __init__(self): self.opened=False
    def open(self): self.opened=True
    def close(self): self.opened=False
    def connect(self,*a): pass
    def disconnect(self): pass
    def send(self,*a,**k): return []
    def receive(self,*a,**k): return []

@pytest.mark.asyncio
async def test_j2534_adapter_lifecycle():
    d=DeviceDescriptor('j','Test','J2534',capabilities=DeviceCapabilities(j2534=True))
    a=J2534Adapter(d,Fake()); await a.connect(); assert d.status.value=='connected'
    h=await a.health_check(); assert h['j2534'] is True
    await a.disconnect(); assert d.status.value=='disconnected'
