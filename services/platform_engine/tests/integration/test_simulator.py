import asyncio
from simulator.vehicle import SimulatedVehicle,SimulatedAdapter
def test_simulator():
    async def run():
        a=SimulatedAdapter(SimulatedVehicle(dtcs=['P0302'])); await a.connect(); assert await a.read_vin(); assert await a.read_dtcs()==['P0302']; assert await a.read_pid(0x0C)==850.0; assert await a.diagnostic_session_control(3)==b'P\x03'
    asyncio.run(run())
