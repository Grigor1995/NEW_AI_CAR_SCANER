from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import api.vehicle_diagnostic_routes as routes
from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus, Vehicle
from device.manager import DeviceDescriptor, DeviceStatus


@pytest.fixture
def session():
    return DiagnosticSession()


@pytest.fixture
def session_map(monkeypatch, session):
    monkeypatch.setattr(routes, "sessions", {"s1": session})
    return session


@pytest.mark.asyncio
async def test_connect_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        await routes.connect("missing", routes.DiagnosticConnectRequest())
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_connect_passes_adapter_and_can_ids(monkeypatch, session_map):
    calls = []
    async def fake_connect(session_id, **kwargs):
        calls.append((session_id, kwargs))
        return SimpleNamespace(connected=True)
    monkeypatch.setattr(routes.service, "connect", fake_connect)
    request = routes.DiagnosticConnectRequest(adapter="simulator", request_id=0x700, response_id=0x708)
    result = await routes.connect("s1", request)
    assert result.connected is True
    assert calls == [(session_map.session_id, {"adapter": "simulator", "request_id": 0x700, "response_id": 0x708})]


@pytest.mark.asyncio
async def test_connect_maps_unimplemented_adapter_to_501(monkeypatch, session_map):
    async def fake_connect(*_args, **_kwargs):
        raise NotImplementedError("physical adapter unavailable")
    monkeypatch.setattr(routes.service, "connect", fake_connect)
    with pytest.raises(HTTPException) as error:
        await routes.connect("s1", routes.DiagnosticConnectRequest(adapter="ble"))
    assert error.value.status_code == 501
    assert "physical adapter unavailable" in error.value.detail


@pytest.mark.asyncio
async def test_disconnect_maps_missing_runtime_to_404(monkeypatch, session_map):
    async def fake_disconnect(_session_id):
        raise KeyError("runtime")
    monkeypatch.setattr(routes.service, "disconnect", fake_disconnect)
    with pytest.raises(HTTPException) as error:
        await routes.disconnect("s1")
    assert error.value.status_code == 404
    assert error.value.detail == "Diagnostic connection not found"


@pytest.mark.asyncio
async def test_disconnect_returns_service_status(monkeypatch, session_map):
    expected = SimpleNamespace(connected=False)
    async def fake_disconnect(session_id):
        assert session_id == session_map.session_id
        return expected
    monkeypatch.setattr(routes.service, "disconnect", fake_disconnect)
    assert await routes.disconnect("s1") is expected


def test_status_handles_unknown_session_and_missing_runtime(monkeypatch, session_map):
    with pytest.raises(HTTPException) as missing_session:
        routes.status("missing")
    assert missing_session.value.status_code == 404

    def fail(_session_id):
        raise KeyError("runtime")
    monkeypatch.setattr(routes.service, "status", fail)
    with pytest.raises(HTTPException) as missing_runtime:
        routes.status("s1")
    assert missing_runtime.value.status_code == 404
    assert missing_runtime.value.detail == "Diagnostic connection not found"


def test_status_returns_service_result(monkeypatch, session_map):
    expected = SimpleNamespace(connected=True)
    monkeypatch.setattr(routes.service, "status", lambda _session_id: expected)
    assert routes.status("s1") is expected


@pytest.mark.asyncio
async def test_identify_ecu_records_vin_as_measured_evidence(monkeypatch, session_map):
    identity = SimpleNamespace(vin="VINTEST1234567890", software_version="SIM-1", hardware_version="HW-1")
    async def fake_identify(session_id):
        assert session_id == session_map.session_id
        return identity
    monkeypatch.setattr(routes.service, "identify_ecu", fake_identify)

    result = await routes.identify_ecu("s1")
    assert result.vin == identity.vin
    assert result.software_version == "SIM-1"
    assert session_map.evidence[-1].source_ref == "UDS:DID:F190"
    assert session_map.evidence[-1].status == EvidenceStatus.MEASURED


@pytest.mark.asyncio
async def test_identify_ecu_without_vin_does_not_add_evidence(monkeypatch, session_map):
    monkeypatch.setattr(routes.service, "identify_ecu", lambda _sid: None)
    async def fake_identify(_sid):
        return SimpleNamespace(vin=None, software_version=None, hardware_version=None)
    monkeypatch.setattr(routes.service, "identify_ecu", fake_identify)
    result = await routes.identify_ecu("s1")
    assert result.vin is None
    assert session_map.evidence == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "status_code", "detail"),
    [
        (RuntimeError("adapter stopped"), 409, "adapter stopped"),
        (KeyError("runtime"), 404, "Diagnostic connection not found"),
    ],
)
async def test_identify_ecu_maps_service_errors(monkeypatch, session_map, failure, status_code, detail):
    async def fake_identify(_sid):
        raise failure
    monkeypatch.setattr(routes.service, "identify_ecu", fake_identify)
    with pytest.raises(HTTPException) as error:
        await routes.identify_ecu("s1")
    assert error.value.status_code == status_code
    assert error.value.detail == detail


@pytest.mark.asyncio
async def test_read_dtcs_adds_records_and_evidence(monkeypatch, session_map):
    records = [
        SimpleNamespace(code="P0102", raw_dtc=0x0102, status_byte=0x28, confirmed=True),
        SimpleNamespace(code="P0302", raw_dtc=0x0302, status_byte=0x08, confirmed=False),
    ]
    async def fake_read(session_id):
        assert session_id == session_map.session_id
        return records
    monkeypatch.setattr(routes.service, "read_dtcs", fake_read)

    result = await routes.read_dtcs("s1")
    assert [record["code"] for record in result.records] == ["P0102", "P0302"]
    assert [dtc.code for dtc in session_map.dtcs] == ["P0102", "P0302"]
    assert [item.source_ref for item in session_map.evidence] == ["UDS:SVC:19:02", "UDS:SVC:19:02"]
    assert session_map.evidence[0].metadata["status_byte"] == 0x28


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "status_code", "detail"),
    [
        (RuntimeError("UDS timeout"), 409, "UDS timeout"),
        (KeyError("runtime"), 404, "Diagnostic connection not found"),
    ],
)
async def test_read_dtcs_maps_service_errors(monkeypatch, session_map, failure, status_code, detail):
    async def fake_read(_sid):
        raise failure
    monkeypatch.setattr(routes.service, "read_dtcs", fake_read)
    with pytest.raises(HTTPException) as error:
        await routes.read_dtcs("s1")
    assert error.value.status_code == status_code
    assert error.value.detail == detail


def test_trace_validates_session_limit_and_runtime(monkeypatch, session_map):
    with pytest.raises(HTTPException) as missing:
        routes.trace("missing")
    assert missing.value.status_code == 404
    with pytest.raises(HTTPException) as low:
        routes.trace("s1", limit=0)
    assert low.value.status_code == 400
    with pytest.raises(HTTPException) as high:
        routes.trace("s1", limit=5001)
    assert high.value.status_code == 400

    monkeypatch.setattr(routes.service, "trace", lambda *_args: (_ for _ in ()).throw(KeyError("runtime")))
    with pytest.raises(HTTPException) as missing_runtime:
        routes.trace("s1")
    assert missing_runtime.value.status_code == 404


def test_trace_serializes_events(monkeypatch, session_map):
    event = SimpleNamespace(to_dict=lambda: {"event": "CONNECTED"})
    monkeypatch.setattr(routes.service, "trace", lambda _sid, limit: [event])
    assert routes.trace("s1", limit=10) == {"events": [{"event": "CONNECTED"}]}


@pytest.mark.asyncio
async def test_bind_device_rejects_unknown_session_and_missing_device(monkeypatch, session_map):
    with pytest.raises(HTTPException) as missing_session:
        await routes.bind_device("missing", routes.SessionDeviceBindRequest(device_id="vci-1"))
    assert missing_session.value.status_code == 404

    monkeypatch.setattr(routes.vci_manager, "status", lambda _device_id: (_ for _ in ()).throw(RuntimeError("missing")))
    with pytest.raises(HTTPException) as missing_device:
        await routes.bind_device("s1", routes.SessionDeviceBindRequest(device_id="vci-1"))
    assert missing_device.value.status_code == 404
    assert "Device not found: vci-1" in missing_device.value.detail


@pytest.mark.asyncio
async def test_bind_device_requires_connected_vci(monkeypatch, session_map):
    monkeypatch.setattr(
        routes.vci_manager, "status",
        lambda _device_id: DeviceDescriptor(device_id="vci-1", status=DeviceStatus.DISCONNECTED),
    )
    with pytest.raises(HTTPException) as error:
        await routes.bind_device("s1", routes.SessionDeviceBindRequest(device_id="vci-1"))
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_bind_device_stores_binding_and_audit_record(monkeypatch, session_map):
    device = DeviceDescriptor(
        device_id="vci-1", connection_type="usb", status=DeviceStatus.CONNECTED
    )
    monkeypatch.setattr(routes.vci_manager, "status", lambda _device_id: device)
    result = await routes.bind_device("s1", routes.SessionDeviceBindRequest(device_id="vci-1"))
    assert result.connected is True
    assert session_map.connected_device_id == "vci-1"
    assert session_map.connection_type == "usb"
    assert session_map.audit_log[-1] == {
        "event": "DEVICE_BOUND", "device_id": "vci-1", "connection_type": "usb"
    }


def test_device_binding_handles_unbound_connected_and_stale_devices(monkeypatch, session_map):
    unbound = routes.device_binding("s1")
    assert unbound.connected is False
    assert unbound.device_id is None

    session_map.connected_device_id = "vci-1"
    session_map.connection_type = "wifi"
    monkeypatch.setattr(
        routes.vci_manager, "status",
        lambda _device_id: DeviceDescriptor(device_id="vci-1", status=DeviceStatus.CONNECTED, connection_type="usb"),
    )
    connected = routes.device_binding("s1")
    assert connected.connected is True
    assert connected.connection_type == "usb"

    monkeypatch.setattr(routes.vci_manager, "status", lambda _device_id: (_ for _ in ()).throw(RuntimeError("gone")))
    stale = routes.device_binding("s1")
    assert stale.connected is False
    assert stale.device_id == "vci-1"
    assert stale.connection_type == "wifi"


def test_device_binding_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        routes.device_binding("missing")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_sync_obd_validates_session_binding_and_connection(monkeypatch, session_map):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as missing:
        await routes.sync_obd_to_session("s1")
    assert missing.value.status_code == 404

    monkeypatch.setattr(routes, "sessions", {"s1": session_map})
    session_map.connected_device_id = None
    with pytest.raises(HTTPException) as unbound:
        await routes.sync_obd_to_session("s1")
    assert unbound.value.status_code == 409

    session_map.connected_device_id = "vci-1"
    monkeypatch.setattr(
        routes.vci_manager, "status",
        lambda _device_id: DeviceDescriptor(device_id="vci-1", status=DeviceStatus.DISCONNECTED),
    )
    with pytest.raises(HTTPException) as disconnected:
        await routes.sync_obd_to_session("s1")
    assert disconnected.value.status_code == 409


@pytest.mark.asyncio
async def test_sync_obd_maps_device_failure_to_502(monkeypatch, session_map):
    session_map.connected_device_id = "vci-1"
    monkeypatch.setattr(routes.vci_manager, "status", lambda _device_id: (_ for _ in ()).throw(RuntimeError("offline")))
    with pytest.raises(HTTPException) as error:
        await routes.sync_obd_to_session("s1")
    assert error.value.status_code == 502
    assert "OBD synchronization failed" in error.value.detail


@pytest.mark.asyncio
async def test_sync_obd_imports_vin_dtcs_live_data_and_deduplicates(monkeypatch, session_map):
    device = DeviceDescriptor(device_id="vci-1", status=DeviceStatus.CONNECTED, connection_type="usb")
    session_map.connected_device_id = "vci-1"
    session_map.vehicle = Vehicle(make="Mercedes-Benz", model="E350")
    session_map.dtcs.append(routes.DTC(code="P0102", source=EvidenceSource.ECU_REPORTED))
    session_map.evidence.append(Evidence(
        fact="existing vin", source=EvidenceSource.ECU_REPORTED, status=EvidenceStatus.MEASURED,
        source_ref="OBD:MODE:09:02", metadata={},
    ))
    monkeypatch.setattr(routes.vci_manager, "status", lambda _device_id: device)

    async def read_vin(_device_id):
        return "WDD2110801A123456"
    async def read_dtcs(_device_id):
        return ["P0102", "P0302"]
    async def read_live_data(_device_id):
        return {"rpm": 1696.0, "unknown": None, "coolant_temp_c": 50.0}
    monkeypatch.setattr(routes.vci_manager, "read_vin", read_vin)
    monkeypatch.setattr(routes.vci_manager, "read_dtcs", read_dtcs)
    monkeypatch.setattr(routes.vci_manager, "read_live_data", read_live_data)

    result = await routes.sync_obd_to_session("s1")
    assert result.vin == "WDD2110801A123456"
    assert result.dtcs == ["P0102", "P0302"]
    assert result.telemetry_measurements_added == 2
    assert result.evidence_added >= 3
    assert session_map.vehicle.metadata["vin"] == "WDD2110801A123456"
    assert [dtc.code for dtc in session_map.dtcs].count("P0102") == 1
    assert any(dtc.code == "P0302" for dtc in session_map.dtcs)
    assert session_map.live_data[-1]["values"]["rpm"] == 1696.0
    assert session_map.audit_log[-1]["event"] == "OBD_SESSION_SYNC"


@pytest.mark.asyncio
async def test_sync_obd_handles_empty_live_data_and_missing_vehicle(monkeypatch, session_map):
    session_map.connected_device_id = "vci-2"
    monkeypatch.setattr(
        routes.vci_manager, "status",
        lambda _device_id: DeviceDescriptor(device_id="vci-2", status=DeviceStatus.CONNECTED),
    )
    async def read_vin(_device_id):
        return None
    async def read_dtcs(_device_id):
        return []
    async def read_live_data(_device_id):
        return {}
    monkeypatch.setattr(routes.vci_manager, "read_vin", read_vin)
    monkeypatch.setattr(routes.vci_manager, "read_dtcs", read_dtcs)
    monkeypatch.setattr(routes.vci_manager, "read_live_data", read_live_data)

    result = await routes.sync_obd_to_session("s1")
    assert result.vin is None
    assert result.evidence_added == 0
    assert result.telemetry_measurements_added == 0
    assert session_map.live_data == []
    assert session_map.audit_log[-1]["event"] == "OBD_SESSION_SYNC"
