from uuid import uuid4

import pytest

from vehicle.network.models import EcuNode, GatewayRoute, VehicleNetworkTopology
from vehicle.network.multibus import CanBusConfig
from multi_ecu.multibus_runtime import MultiBusDiagnosticRuntime


def _topology():
    return VehicleNetworkTopology(
        ecus=(
            EcuNode(
                ecu_id="engine", name="Engine ECU", request_id=0x7E0, response_id=0x7E8,
                bus="CAN0", metadata={
                    "vin": "ENGINEVIN12345678", "software_version": "ENG-SW",
                    "hardware_version": "ENG-HW", "dtc_records": [(0x030200, 0x28)],
                },
            ),
            EcuNode(
                ecu_id="transmission", name="Transmission ECU", request_id=0x7E1, response_id=0x7E9,
                bus="CAN1", gateway_id="GW1", metadata={
                    "vin": "TRANSVIN12345678", "software_version": "TCM-SW",
                    "hardware_version": "TCM-HW", "dtc_records": [(0x010203, 0x01)],
                },
            ),
        ),
        routes=(GatewayRoute(
            gateway_id="GW1", source_bus="CAN0", target_bus="CAN1",
            target_ecu_id="transmission",
        ),),
    )


def test_multibus_runtime_validates_bus_configuration_and_ecu_references():
    with pytest.raises(ValueError, match="at least one CAN bus"):
        MultiBusDiagnosticRuntime(
            session_id=uuid4(), topology=VehicleNetworkTopology(),
            buses=(),
        )

    with pytest.raises(ValueError, match="unknown bus"):
        MultiBusDiagnosticRuntime(
            session_id=uuid4(),
            topology=VehicleNetworkTopology(ecus=(
                EcuNode("engine", "Engine", 0x7E0, 0x7E8, bus="CAN9"),
            )),
            buses=(CanBusConfig("CAN0"),),
        )


@pytest.mark.asyncio
async def test_multibus_runtime_connects_routes_gateway_and_runs_read_only_operations():
    runtime = MultiBusDiagnosticRuntime(
        session_id=uuid4(),
        topology=_topology(),
        buses=(CanBusConfig("CAN0"), CanBusConfig("CAN1", bitrate=250_000, can_fd=True, data_bitrate=2_000_000)),
    )
    try:
        await runtime.connect()
        await runtime.connect()  # reconnecting an active runtime is idempotent
        assert runtime.connected is True
        assert runtime.ecus["engine"].direct is True
        assert runtime.ecus["engine"].access_bus == "CAN0"
        assert runtime.ecus["transmission"].direct is False
        assert runtime.ecus["transmission"].access_bus == "CAN0"

        view = runtime.topology_view()
        assert [bus["name"] for bus in view["buses"]] == ["CAN0", "CAN1"]
        assert view["buses"][1]["data_bitrate"] == 2_000_000
        assert view["network"]["routes"][0]["gateway_id"] == "GW1"
        assert runtime.gateway.route_for_ecu("transmission").gateway_id == "GW1"
        assert runtime.gateway.route_for_ecu("transmission", source_bus="CAN9") is None

        identities = await runtime.identify_all()
        assert set(identities) == {"engine", "transmission"}
        assert identities["engine"].vin == "ENGINEVIN12345678"
        assert identities["transmission"].vin == "TRANSVIN12345678"

        dtcs = await runtime.read_all_dtcs()
        assert set(dtcs) == {"engine", "transmission"}
        assert dtcs["engine"][0].code == "P030200"
        assert dtcs["transmission"][0].code == "P010203"
    finally:
        await runtime.disconnect()

    assert runtime.connected is False
    assert runtime.ecus == {}
    with pytest.raises(RuntimeError, match="disconnected"):
        await runtime.identify_all()
    with pytest.raises(RuntimeError, match="disconnected"):
        await runtime.read_all_dtcs()
