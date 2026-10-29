import pytest
from vehicle.obd.client import GenericObdClient
from vehicle.obd.adapters.simulator import SimulatorTransport

@pytest.mark.asyncio
async def test_generic_obd_client():
    t=SimulatorTransport({'0100':'41 00 08 18 80 00','ATZ':'ELM327 v2.2','ATE0':'OK','ATL0':'OK','ATS0':'OK','ATSP0':'OK','0902':'49 02 01 ' + ' '.join(f'{b:02X}' for b in b'WDB21100000000001'),'03':'43 03 02 00 00','010C':'41 0C 0B B8','0105':'41 05 5A','010D':'41 0D 28','0111':'41 11 80'})
    c=GenericObdClient(t); await c.connect()
    assert (await c.read_vin()) == 'WDB21100000000001'
    assert await c.read_dtcs() == ['P0302']
    data=await c.read_standard_live_data()
    assert data['rpm'] == 750.0 and data['coolant_c'] == 50.0 and data['speed_kmh'] == 40.0
