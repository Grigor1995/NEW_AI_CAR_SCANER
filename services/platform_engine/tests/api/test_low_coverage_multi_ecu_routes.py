from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import api.multi_ecu_routes as routes
from diagnostic.models import DiagnosticSession, EvidenceSource
from multi_ecu.models import MultiEcuConnectRequest, EcuNodeRequest


@pytest.fixture
def session_map(monkeypatch):
    session = DiagnosticSession()
    monkeypatch.setattr(routes, "sessions", {"s1": session})
    return session


def request():
    return MultiEcuConnectRequest(ecus=[
        EcuNodeRequest(ecu_id="engine", name="Engine ECU", request_id=0x7E0, response_id=0x7E8,
                       dtc_records=[(0x030200, 0x28)]),
    ])


def runtime(session_id=None):
    return SimpleNamespace(
        session_id=session_id or uuid4(),
        connected=True,
        topology=SimpleNamespace(ecus=[object(), object()], gateways=[object()]),
        trace_snapshot=lambda limit=500: [{"event": "CONNECTED"}][:limit],
    )


@pytest.mark.asyncio
async def test_connect_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        await routes.connect("missing", request())
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_connect_maps_invalid_topology_to_400(monkeypatch, session_map):
    async def fail(*_args):
        raise ValueError("duplicate CAN arbitration id")
    monkeypatch.setattr(routes.service, "connect", fail)
    with pytest.raises(HTTPException) as error:
        await routes.connect("s1", request())
    assert error.value.status_code == 400
    assert error.value.detail == "duplicate CAN arbitration id"


@pytest.mark.asyncio
async def test_connect_returns_status_counts(monkeypatch, session_map):
    expected_runtime = runtime(session_map.session_id)
    async def fake_connect(session_id, payload):
        assert session_id == session_map.session_id
        assert payload.ecus[0].ecu_id == "engine"
        return expected_runtime
    monkeypatch.setattr(routes.service, "connect", fake_connect)

    result = await routes.connect("s1", request())
    assert result.connected is True
    assert result.ecu_count == 2
    assert result.gateway_count == 1
    assert result.trace_events == 1


@pytest.mark.asyncio
async def test_disconnect_rejects_unknown_session_and_missing_runtime(monkeypatch, session_map):
    monkeypatch.setattr(routes.service, "disconnect", lambda *_args: None)
    with pytest.raises(HTTPException) as missing_session:
        await routes.disconnect("missing")
    assert missing_session.value.status_code == 404

    async def fail(_session_id):
        raise KeyError("runtime")
    monkeypatch.setattr(routes.service, "disconnect", fail)
    with pytest.raises(HTTPException) as missing_runtime:
        await routes.disconnect("s1")
    assert missing_runtime.value.status_code == 404
    assert missing_runtime.value.detail == "Multi-ECU runtime not found"


@pytest.mark.asyncio
async def test_disconnect_returns_runtime_status(monkeypatch, session_map):
    current = runtime(session_map.session_id)
    current.connected = False
    async def fake_disconnect(session_id):
        assert session_id == session_map.session_id
        return current
    monkeypatch.setattr(routes.service, "disconnect", fake_disconnect)
    result = await routes.disconnect("s1")
    assert result.connected is False


def test_topology_returns_discovered_topology_and_handles_missing_runtime(monkeypatch, session_map):
    topology = SimpleNamespace(to_dict=lambda: {"ecus": [{"ecu_id": "engine"}], "gateways": []})
    connected_runtime = SimpleNamespace(discover=lambda: topology)
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)
    assert routes.topology("s1") == {"ecus": [{"ecu_id": "engine"}], "gateways": []}

    monkeypatch.setattr(routes.service, "require", lambda _sid: (_ for _ in ()).throw(KeyError("runtime")))
    with pytest.raises(HTTPException) as error:
        routes.topology("s1")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_identify_all_serializes_identities(monkeypatch, session_map):
    expected = {"engine": SimpleNamespace(to_dict=lambda: {"vin": "VIN1"})}
    connected_runtime = SimpleNamespace(identify_all=lambda: None)
    async def fake_identify_all():
        return expected
    connected_runtime.identify_all = fake_identify_all
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)
    result = await routes.identify_all("s1")
    assert result == {"session_id": "s1", "ecus": {"engine": {"vin": "VIN1"}}}


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [KeyError("runtime"), RuntimeError("not connected")])
async def test_identify_all_maps_runtime_errors(monkeypatch, session_map, failure):
    connected_runtime = SimpleNamespace()
    async def fail():
        raise failure
    connected_runtime.identify_all = fail
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)
    with pytest.raises(HTTPException) as error:
        await routes.identify_all("s1")
    assert error.value.status_code == 409


@pytest.mark.asyncio
async def test_read_all_dtcs_adds_session_evidence_and_correlations(monkeypatch, session_map):
    record = SimpleNamespace(code="P0302", raw_dtc=0x030200, status_byte=0x28, confirmed=True)
    dtcs = {"engine": [record], "transmission": [record]}
    connected_runtime = SimpleNamespace(
        read_all_dtcs=None,
        correlate_dtcs=lambda value: [{"type": "SHARED_DTC", "code": "P0302", "ecu_ids": list(value)}],
    )
    async def fake_read_all():
        return dtcs
    connected_runtime.read_all_dtcs = fake_read_all
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)

    result = await routes.read_all_dtcs("s1")
    assert result["dtcs_by_ecu"]["engine"][0]["confirmed"] is True
    assert result["correlations"][0]["type"] == "SHARED_DTC"
    assert [dtc.code for dtc in session_map.dtcs] == ["P0302", "P0302"]
    assert len(session_map.evidence) == 2
    assert all(event.source == EvidenceSource.ECU_REPORTED for event in session_map.evidence)
    assert session_map.evidence[0].metadata["ecu_id"] == "engine"


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", [KeyError("runtime"), RuntimeError("not connected")])
async def test_read_all_dtcs_maps_runtime_errors(monkeypatch, session_map, failure):
    connected_runtime = SimpleNamespace(correlate_dtcs=lambda _dtcs: [])
    async def fail():
        raise failure
    connected_runtime.read_all_dtcs = fail
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)
    with pytest.raises(HTTPException) as error:
        await routes.read_all_dtcs("s1")
    assert error.value.status_code == 409


def test_trace_validates_session_limit_and_missing_runtime(monkeypatch, session_map):
    with pytest.raises(HTTPException) as missing_session:
        routes.trace("missing")
    assert missing_session.value.status_code == 404
    with pytest.raises(HTTPException) as invalid_low:
        routes.trace("s1", limit=0)
    assert invalid_low.value.status_code == 400
    with pytest.raises(HTTPException) as invalid_high:
        routes.trace("s1", limit=5001)
    assert invalid_high.value.status_code == 400

    monkeypatch.setattr(routes.service, "require", lambda _sid: (_ for _ in ()).throw(KeyError("runtime")))
    with pytest.raises(HTTPException) as missing_runtime:
        routes.trace("s1")
    assert missing_runtime.value.status_code == 404


def test_trace_serializes_snapshot_events(monkeypatch, session_map):
    event = SimpleNamespace(to_dict=lambda: {"event": "CONNECTED", "ecu_count": 1})
    connected_runtime = SimpleNamespace(trace_snapshot=lambda limit: [event])
    monkeypatch.setattr(routes.service, "require", lambda _sid: connected_runtime)
    assert routes.trace("s1", limit=10) == {"events": [{"event": "CONNECTED", "ecu_count": 1}]}
