import pytest
from vehicle.uds.client import UdsClient, UdsError

class LoopbackIsoTp:
    def __init__(self): self.sent=[]; self.responses=[]
    async def send(self,p): self.sent.append(p)
    async def receive(self): return self.responses.pop(0)

@pytest.mark.asyncio
async def test_uds_positive_response():
    t=LoopbackIsoTp(); t.responses=[b'\x50\x03']; c=UdsClient(t)
    assert await c.diagnostic_session_control(3)==b'\x03'
    assert t.sent==[b'\x10\x03']

@pytest.mark.asyncio
async def test_uds_negative_response():
    t=LoopbackIsoTp(); t.responses=[b'\x7f\x22\x31']; c=UdsClient(t)
    with pytest.raises(UdsError) as e: await c.read_data_by_identifier(0xF190)
    assert e.value.nrc==0x31
