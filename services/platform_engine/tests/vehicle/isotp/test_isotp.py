import pytest
from vehicle.can.models import CanFrame
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.isotp.stack import IsoTpStack

@pytest.mark.asyncio
async def test_single_frame_send():
    bus=SimulatedCanBus(); stack=IsoTpStack(bus,0x700,0x708)
    await stack.send(b'ABC')
    f=bus.pop_tx(); assert f.data==b'\x03ABC'

@pytest.mark.asyncio
async def test_multi_frame_receive():
    bus=SimulatedCanBus(); stack=IsoTpStack(bus,0x700,0x708)
    payload=b'0123456789ABC'
    bus.inject(CanFrame(0x708,bytes([0x10,len(payload)])+payload[:6]))
    bus.inject(CanFrame(0x708,b'\x21'+payload[6:]))
    assert await stack.receive()==payload
    fc=bus.pop_tx(); assert fc.data==b'\x30\x00\x00'
