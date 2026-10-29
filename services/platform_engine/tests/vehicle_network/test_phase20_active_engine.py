import pytest
from vehicle.adapters.can_simulator import SimulatedCanBus
from vehicle.adapters.uds_simulator import UdsEcuSimulator
from vehicle.network.active_discovery import ActiveEcuDiscoveryEngine, ActiveProbePolicy, ActiveProbeTarget

@pytest.mark.asyncio
async def test_active_probe_confirms_identity_read_only():
    bus = SimulatedCanBus()
    UdsEcuSimulator(bus, request_id=0x7E0, response_id=0x7E8, vin='ACTIVEVIN1234567', software_version='SW-9', hardware_version='HW-2')
    engine = ActiveEcuDiscoveryEngine(ActiveProbePolicy(timeout_ms=500, inter_probe_ms=0))
    out = await engine.probe_many([ActiveProbeTarget('DISC_ECU_001','CAN0',0x7E0,0x7E8)], {'CAN0': bus})
    assert out[0].classification == 'CONFIRMED_UDS_ECU'
    assert out[0].identity['vin'] == 'ACTIVEVIN1234567'
    assert out[0].successful_dids == ('0xF190','0xF187','0xF191')

@pytest.mark.asyncio
async def test_active_probe_no_response_is_not_confirmation():
    bus = SimulatedCanBus()
    engine = ActiveEcuDiscoveryEngine(ActiveProbePolicy(timeout_ms=150, inter_probe_ms=0))
    out = await engine.probe_many([ActiveProbeTarget('DISC_ECU_099','CAN0',0x700,0x708)], {'CAN0': bus})
    assert out[0].classification == 'NO_RESPONSE'
    assert not out[0].responded

@pytest.mark.asyncio
async def test_only_allowlisted_read_dids_are_sent():
    bus = SimulatedCanBus(); seen=[]
    def hook(frame):
        if frame.arbitration_id == 0x7E0 and frame.data:
            seen.append(bytes(frame.data))
    bus.add_tx_hook(hook)
    UdsEcuSimulator(bus, request_id=0x7E0, response_id=0x7E8, vin='VIN1234567890123')
    engine = ActiveEcuDiscoveryEngine(ActiveProbePolicy(allowed_dids=(0xF190,), timeout_ms=500, inter_probe_ms=0))
    out = await engine.probe_many([ActiveProbeTarget('DISC_ECU_002','CAN0',0x7E0,0x7E8)], {'CAN0': bus})
    assert out[0].classification == 'CONFIRMED_UDS_ECU'
    uds_payloads = [x[1:1+x[0]] for x in seen if (x[0] & 0xF0) == 0]
    assert uds_payloads and uds_payloads[0] == b'\x22\xF1\x90'


@pytest.mark.asyncio
async def test_active_probe_correlates_gateway_access_path():
    from vehicle.network.models import EcuNode, GatewayNode, GatewayRoute, VehicleNetworkTopology
    from vehicle.network.multibus import GatewayRoutingEngine
    can0, can1 = SimulatedCanBus(), SimulatedCanBus()
    topology = VehicleNetworkTopology(
        ecus=(EcuNode('engine','Engine ECU',0x7E0,0x7E8,bus='CAN1',gateway_id='gw',metadata={'vin':'GWACTIVE12345678'}),),
        gateways=(GatewayNode('gw','Central Gateway','CAN0'),),
        routes=(GatewayRoute('gw','CAN0','CAN1','engine'),),
    )
    gateway = GatewayRoutingEngine({'CAN0':can0,'CAN1':can1}, topology); gateway.install()
    UdsEcuSimulator(can1, request_id=0x7E0, response_id=0x7E8, vin='GWACTIVE12345678')
    engine = ActiveEcuDiscoveryEngine(ActiveProbePolicy(allowed_dids=(0xF190,), timeout_ms=500, inter_probe_ms=0))
    out = await engine.probe_many([ActiveProbeTarget('DISC_ECU_GW','CAN0',0x7E0,0x7E8,'gw')], {'CAN0':can0,'CAN1':can1})
    assert out[0].classification == 'CONFIRMED_UDS_ECU'
    assert out[0].gateway_id == 'gw'
    assert out[0].identity['vin'] == 'GWACTIVE12345678'
