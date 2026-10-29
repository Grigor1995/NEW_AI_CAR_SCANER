from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from apps.desktop.models import Session, TestCandidate, Vehicle
from apps.desktop import storage as desktop_storage
from backend.vehicle.adapters.can_simulator import SimulatedCanBus
from backend.vehicle.adapters.uds_simulator import UdsEcuSimulator
from backend.vehicle.can.models import CanFrame
from backend.vehicle.isotp.stack import IsoTpStack
from backend.vehicle.network.active_discovery import (
    ActiveEcuDiscoveryEngine, ActiveProbePolicy, ActiveProbeTarget,
)
from backend.vehicle.network.discovery import (
    CanIdObservation, VehicleNetworkDiscoveryEngine,
)
from backend.vehicle.network.models import (
    EcuNode, GatewayNode, GatewayRoute, VehicleNetworkTopology,
)
from backend.vehicle.network.multibus import CanBusConfig, GatewayRoutingEngine
from backend.vehicle.obd.client import GenericObdClient as StubObdClient
from backend.vehicle.obd.service import ObdDiagnosticService
from backend.vehicle.protocol.trace import ProtocolTraceRecorder, TracedCanBus
from backend.vehicle.uds.client import UdsClient
from backend.vehicle.uds.diagnostics import UdsDiagnosticSession
from backend.professional_platform.analytics import summarize_events
from backend.professional_platform.audit import AuditLog
from backend.professional_platform.models import AuditEvent
from backend.professional_platform.reporting import build_session_report
from backend.security.audit_security import event as security_event
from vehicle.adapters.simulator import VciSimulatorAdapter
from vehicle.adapters.vendor import VendorSdkAdapter
from vehicle.can.bus import CanBus
from vehicle.can.models import CanFrame as NativeCanFrame
from vehicle.devices.models import DeviceCapabilities, DeviceDescriptor, DeviceStatus
from vehicle.obd.pid_catalog import STANDARD_PIDS


def test_desktop_models_round_trip_and_optional_values():
    vehicle = Vehicle.from_json({
        "make": "Mercedes-Benz", "model": "E350", "year": "2006",
        "fuel": ["petrol", "lpg"], "ecu": "ME9.7",
    })
    assert vehicle.to_json()["year"] == 2006
    assert Vehicle.from_json({}).make == "Unknown"
    assert Vehicle.from_json({"year": ""}).year is None
    candidate = TestCandidate.from_json({
        "id": "t1", "name": "Check pressure", "risk": "MEDIUM",
        "priority_score": "0.8", "expected_information_gain": "0.4",
        "safety_notes": ["Work outdoors"],
    })
    assert candidate.test_id == "t1"
    assert candidate.risk_level == "MEDIUM"
    assert candidate.expected_information_gain == 0.4
    assert candidate.safety_notes == ["Work outdoors"]
    assert Session("s1").state == "CREATED"


def test_desktop_storage_missing_corrupt_and_round_trip(tmp_path, monkeypatch):
    file_path = tmp_path / "vehicles.json"
    monkeypatch.setattr(desktop_storage, "APP_DIR", tmp_path)
    monkeypatch.setattr(desktop_storage, "VEHICLES_FILE", file_path)
    store = desktop_storage.VehicleStore()
    assert store.load() == []
    cars = [Vehicle("Mercedes-Benz", "E350", year=2006, fuel=["petrol", "lpg"])]
    store.save(cars)
    assert store.load()[0].model == "E350"
    file_path.write_text("{broken", encoding="utf-8")
    assert store.load() == []
    file_path.write_text('{"not":"a list"}', encoding="utf-8")
    assert store.load() == []


def test_can_frame_and_simulated_can_bus_send_receive_and_timeout():
    async def scenario():
        bus = SimulatedCanBus()
        frame = CanFrame(0x7E0, b"\x01\x02")
        await bus.send(frame)
        assert await bus.receive(100) == frame
        assert await bus.receive(1) is None
    asyncio.run(scenario())
    assert CanFrame(0x7E8, b"123").dlc == 3


def test_isotp_and_uds_clients_forward_requests():
    class Channel:
        async def receive(self, timeout_ms):
            return {"timeout_ms": timeout_ms, "payload": b"\x62\xF1\x90"}
    channel = Channel()
    stack = IsoTpStack(channel, 0x7E0, 0x7E8)
    transport = SimpleNamespace(request=Mock())
    async def request(payload):
        return payload + b"!"
    transport.request.side_effect = request
    async def scenario():
        assert await stack.request(b"\x22", 250) == {"timeout_ms": 250, "payload": b"\x62\xF1\x90"}
        assert await UdsClient(transport).request(b"\x22") == b"\x22!"
    asyncio.run(scenario())
    transport.request.assert_called_once_with(b"\x22")


def test_network_discovery_deduplicates_and_filters_can_ids():
    observations = [
        CanIdObservation("CAN0", 0x7E0, 1, 8, "0102", False, False),
        CanIdObservation("CAN0", 0x7E0, 2, 8, "0304", False, False),
        CanIdObservation("CAN0", 0x700, 3, 8, "0506", False, False),
    ]
    result = VehicleNetworkDiscoveryEngine().analyze_observations(observations)
    assert result.observations == 3
    assert len(result.ecu_candidates) == 1
    assert result.ecu_candidates[0].response_id == 0x7E8
    assert result.to_dict()["ecu_candidates"][0]["candidate_id"] == "CAN0:7E0"


def test_active_discovery_respects_policy_limit_and_maps_targets():
    targets = [
        ActiveProbeTarget(f"ecu-{i}", "CAN0", 0x700 + i, 0x708 + i, "gw-1")
        for i in range(3)
    ]
    async def scenario():
        engine = ActiveEcuDiscoveryEngine(ActiveProbePolicy(max_targets=2))
        return await engine.probe_many(targets, ["CAN0"])
    results = asyncio.run(scenario())
    assert len(results) == 2
    assert results[0].classification == "CONFIRMED_UDS_ECU"
    assert results[0].gateway_id == "gw-1"
    assert results[0].to_dict()["confidence"] == 0.9


def test_network_topology_serialization_and_routing():
    ecu = EcuNode("engine", "Engine ECU", 0x7E0, 0x7E8, capabilities=frozenset({"UDS", "DTC"}))
    gateway = GatewayNode("gw", "Gateway")
    route = GatewayRoute("gw", "CAN0", "CAN1", "engine")
    topology = VehicleNetworkTopology((ecu,), (gateway,), (route,))
    assert topology.ecu("engine") == ecu
    with pytest.raises(KeyError):
        topology.ecu("missing")
    encoded = topology.to_dict()
    assert encoded["ecus"][0]["capabilities"] == ["DTC", "UDS"]
    engine = GatewayRoutingEngine(["CAN0", "CAN1"], topology)
    assert engine.route_for_ecu("engine") == route
    assert engine.route_for_ecu("missing") is None
    assert engine.stats() == {"installed": False, "buses": 2, "routes": 1}
    engine.install()
    assert engine.stats()["installed"] is True
    assert CanBusConfig("CAN0").to_dict()["bitrate"] == 500_000


def test_stub_obd_service_and_uds_diagnostic_contracts():
    class Client:
        async def read_vin(self): return "SIMULATORVIN0000001"
        async def read_dtcs(self): return ["P0302"]
        async def read_standard_live_data(self): return {"rpm": 800.0}
    client = Client()
    async def scenario():
        service = ObdDiagnosticService(client)
        assert await service.identify_vehicle() == {
            "vin": "SIMULATORVIN0000001", "dtcs": ["P0302"]
        }
        assert await service.snapshot() == {"rpm": 800.0}
        uds = UdsDiagnosticSession(client)
        identity = await uds.identify_ecu()
        assert identity.vin == "SIMULATORVIN0000001"
        assert identity.software_version == "SIM-ECU-1.0"
        assert await uds.read_dtcs() == []
    asyncio.run(scenario())
    stub = StubObdClient()
    async def stub_scenario():
        assert await stub.read_vin() is None
        assert await stub.read_dtcs() == []
        assert (await stub.read_standard_live_data())["rpm"] == 750.0
    asyncio.run(stub_scenario())


def test_trace_recorder_and_traced_bus_capture_tx_rx():
    frame = NativeCanFrame(0x7E0, b"\x01\x02")
    class Bus:
        async def send(self, sent): self.sent = sent
        async def receive(self, timeout_ms=1000): return frame
    trace = ProtocolTraceRecorder("session-1")
    bus = TracedCanBus(Bus(), trace)
    async def scenario():
        await bus.send(frame)
        assert await bus.receive(50) == frame
    asyncio.run(scenario())
    assert [entry["event"] for entry in trace.events] == ["CAN_TX", "CAN_RX"]
    assert trace.events[0]["data"] == "0102"


def test_uds_simulator_and_standard_pid_catalog():
    sim = UdsEcuSimulator("bus", 0x7E0, 0x7E8, vin="VIN", dtc_records=[{"code": "P0302"}])
    assert (sim.request_id, sim.response_id, sim.vin) == (0x7E0, 0x7E8, "VIN")
    assert sim.dtc_records == [{"code": "P0302"}]
    assert [pid.pid for pid in STANDARD_PIDS] == [0x05, 0x0C, 0x0D, 0x11]
    assert DeviceCapabilities(obd=True).obd
    assert DeviceDescriptor("x", "m", "model").status == DeviceStatus.DISCONNECTED


def test_vci_simulator_and_vendor_adapter_lifecycle():
    async def scenario():
        sim = VciSimulatorAdapter("sim-test")
        assert sim.descriptor.status == DeviceStatus.DISCONNECTED
        await sim.connect()
        assert sim.descriptor.status == DeviceStatus.CONNECTED
        assert (await sim.health_check())["latency_ms"] == 1.0
        await sim.disconnect()
        assert sim.descriptor.status == DeviceStatus.DISCONNECTED

        descriptor = DeviceDescriptor("vendor-1", "OEM", "VCI")
        sdk = SimpleNamespace(connect=Mock(), disconnect=Mock(), health_check=Mock(return_value={"healthy": True}))
        vendor = VendorSdkAdapter(descriptor, sdk)
        await vendor.connect()
        assert descriptor.status == DeviceStatus.CONNECTED
        assert await vendor.health_check() == {"healthy": True}
        await vendor.disconnect()
        sdk.connect.assert_called_once()
        sdk.disconnect.assert_called_once()

        no_sdk = VendorSdkAdapter(DeviceDescriptor("vendor-2", "OEM", "Basic"))
        await no_sdk.connect()
        assert await no_sdk.health_check() == {"device_id": "vendor-2", "status": "connected"}
        await no_sdk.disconnect()
    asyncio.run(scenario())


def test_can_bus_request_uses_send_then_receive():
    class FakeBus(CanBus):
        def __init__(self): self.sent = None
        async def send(self, frame): self.sent = frame
        async def receive(self, timeout_ms=1000):
            return NativeCanFrame(0x7E8, b"\x41\x0C") if timeout_ms == 25 else None
    bus = FakeBus()
    request = NativeCanFrame(0x7E0, b"\x01\x0C")
    async def scenario():
        response = await bus.request(request, 25)
        assert bus.sent == request
        assert response.arbitration_id == 0x7E8
    asyncio.run(scenario())


def test_professional_analytics_audit_reporting_and_security_event():
    org = "00000000-0000-0000-0000-000000000001"
    snapshot = summarize_events(org, "2026-10", [
        {"action": "SESSION_CREATED", "actor_user_id": "00000000-0000-0000-0000-000000000011", "vehicle_id": "00000000-0000-0000-0000-000000000021"},
        {"action": "SESSION_CLOSED", "actor_user_id": "00000000-0000-0000-0000-000000000011", "vehicle_id": "00000000-0000-0000-0000-000000000021"},
        {"action": "DTC_READ", "actor_user_id": "00000000-0000-0000-0000-000000000012", "vehicle_id": "00000000-0000-0000-0000-000000000022"},
        {"action": "AI_ANALYSIS_STARTED", "actor_user_id": "00000000-0000-0000-0000-000000000012"},
        {"action": "SYNC_COMPLETED", "actor_user_id": None},
        {"action": "OTHER"},
    ])
    assert snapshot.active_technicians == 2
    assert snapshot.active_vehicles == 2
    assert snapshot.diagnostic_sessions == snapshot.completed_sessions == 1
    assert snapshot.dtcs_read == snapshot.ai_analyses == snapshot.offline_sync_operations == 1

    audit = AuditLog()
    first = AuditEvent(organization_id=org, action="SESSION_CREATED", resource_type="session")
    second = AuditEvent(organization_id="00000000-0000-0000-0000-000000000002", action="DTC_READ", resource_type="vehicle")
    assert audit.append(first) is first
    audit.append(second)
    assert audit.for_organization(first.organization_id) == [first]
    assert build_session_report({"id": "s1"}, [first.model_dump()])["audit"]
    report = build_session_report({"id": "s2"})
    assert report["audit"] == []
    assert report["report_version"] == "1.0"

    sec = security_event("u1", org, "LOGIN", "session", outcome="denied")
    assert sec.actor_id == "u1"
    assert sec.outcome == "denied"
    assert sec.timestamp.endswith("+00:00")

def test_diagnostic_intelligence_reexport_is_public():
    from backend.diagnostic.intelligence import DiagnosticIntelligenceEngine
    from ai.reasoning.engine import DiagnosticIntelligenceEngine as Engine
    assert DiagnosticIntelligenceEngine is Engine
