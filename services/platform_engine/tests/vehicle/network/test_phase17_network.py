import pytest
from uuid import uuid4
from vehicle.network.models import EcuNode, GatewayNode, VehicleNetworkTopology
from vehicle.network.runtime import MultiEcuRuntime

@pytest.mark.asyncio
async def test_concurrent_multi_ecu_identity_and_dtc_reads():
    topology = VehicleNetworkTopology(ecus=(
        EcuNode('engine', 'Engine ECU', 0x7E0, 0x7E8, metadata={'vin': 'VINENG1234567890', 'dtc_records': [(0x030200, 0x28)]}),
        EcuNode('transmission', 'Transmission ECU', 0x7E1, 0x7E9, metadata={'vin': 'VINENG1234567890', 'dtc_records': [(0x030200, 0x28)]}),
        EcuNode('abs', 'ABS ECU', 0x7E2, 0x7EA, metadata={'vin': 'VINENG1234567890', 'dtc_records': []}),
    ), gateways=(GatewayNode('gw1', 'Central Gateway'),))
    runtime = MultiEcuRuntime(session_id=uuid4(), topology=topology)
    await runtime.connect()
    identities = await runtime.identify_all()
    assert identities['engine'].vin == 'VINENG1234567890'
    assert identities['transmission'].vin == 'VINENG1234567890'
    dtcs = await runtime.read_all_dtcs()
    assert len(dtcs['engine']) == 1 and len(dtcs['transmission']) == 1
    assert dtcs['abs'] == []
    correlations = runtime.correlate_dtcs(dtcs)
    assert correlations[0]['type'] == 'SHARED_DTC'
    await runtime.disconnect()

@pytest.mark.asyncio
async def test_can_demux_prevents_response_cross_talk():
    topology = VehicleNetworkTopology(ecus=(
        EcuNode('a', 'ECU A', 0x700, 0x708, metadata={'vin': 'A1234567890123456'}),
        EcuNode('b', 'ECU B', 0x701, 0x709, metadata={'vin': 'B1234567890123456'}),
    ))
    runtime = MultiEcuRuntime(session_id=uuid4(), topology=topology)
    await runtime.connect()
    identities = await runtime.identify_all()
    assert identities['a'].vin == 'A1234567890123456'
    assert identities['b'].vin == 'B1234567890123456'
    await runtime.disconnect()
