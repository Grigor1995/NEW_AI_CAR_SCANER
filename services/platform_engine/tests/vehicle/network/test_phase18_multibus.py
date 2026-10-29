import pytest
from uuid import uuid4
from vehicle.network.models import EcuNode, GatewayNode, GatewayRoute, VehicleNetworkTopology
from vehicle.network.multibus import CanBusConfig
from backend.multi_ecu.multibus_runtime import MultiBusDiagnosticRuntime

@pytest.mark.asyncio
async def test_direct_multi_bus_identity_and_dtc_reads():
    topology = VehicleNetworkTopology(ecus=(
        EcuNode('engine', 'Engine ECU', 0x7E0, 0x7E8, bus='CAN0', metadata={'vin': 'ENGINEVIN1234567', 'dtc_records': [(0x030200, 0x28)]}),
        EcuNode('abs', 'ABS ECU', 0x740, 0x748, bus='CAN1', metadata={'vin': 'ABSVIN1234567890', 'dtc_records': []}),
    ))
    rt = MultiBusDiagnosticRuntime(session_id=uuid4(), topology=topology,
        buses=(CanBusConfig('CAN0'), CanBusConfig('CAN1')))
    await rt.connect()
    ids = await rt.identify_all()
    assert ids['engine'].vin == 'ENGINEVIN1234567'
    assert ids['abs'].vin == 'ABSVIN1234567890'
    dtcs = await rt.read_all_dtcs()
    assert len(dtcs['engine']) == 1 and dtcs['abs'] == []

@pytest.mark.asyncio
async def test_gateway_routes_engine_request_across_buses():
    topology = VehicleNetworkTopology(
        ecus=(EcuNode('engine', 'Engine ECU', 0x7E0, 0x7E8, bus='CAN1', gateway_id='gw', metadata={'vin': 'GATEWAYVIN123456'}),),
        gateways=(GatewayNode('gw', 'Central Gateway', bus='CAN0'),),
        routes=(GatewayRoute('gw', 'CAN0', 'CAN1', 'engine'),),
    )
    rt = MultiBusDiagnosticRuntime(session_id=uuid4(), topology=topology,
        buses=(CanBusConfig('CAN0'), CanBusConfig('CAN1')))
    await rt.connect()
    ids = await rt.identify_all()
    assert ids['engine'].vin == 'GATEWAYVIN123456'
    assert rt.gateway.stats()['forwarded_frames'] >= 1
