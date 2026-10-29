from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession
from professional_platform.models import AuditEvent, Role
from acquisition.service import AcquisitionRecord, AcquisitionSourceType
from backend.acquisition.models import AcquisitionStartRequest, AcquisitionStatus
from api import acquisition_routes as acquisition_routes
from api import platform_routes


def test_platform_roles_and_audit_filter(monkeypatch):
    organization_id = uuid4()
    other_id = uuid4()
    event = AuditEvent(
        organization_id=organization_id,
        action="SESSION_CREATED",
        resource_type="diagnostic_session",
    )
    platform = SimpleNamespace(audit=[event])
    monkeypatch.setattr(platform_routes, "platform", platform)

    assert platform_routes.roles() == {"roles": [role.value for role in Role]}
    assert platform_routes.audit(organization_id) == [event.model_dump(mode="json")]
    assert platform_routes.audit(other_id) == []


def _status(session_id, state="RUNNING", buffered=1):
    return AcquisitionStatus(
        session_id=session_id, state=state, adapter="simulator",
        stats={"polls": 1, "records": buffered, "errors": 0, "reconnects": 0},
        buffered_records=buffered, offline_queue_items=0,
    )


def _setup_acquisition(monkeypatch):
    session = DiagnosticSession()
    fake = SimpleNamespace(
        start_simulator=AsyncMock(return_value=_status(session.session_id)),
        stop=AsyncMock(return_value=_status(session.session_id, "STOPPED")),
        status=lambda _sid: _status(session.session_id),
        snapshot=lambda _sid, limit: [
            AcquisitionRecord(
                session_id=session.session_id, timestamp_ms=123, channel="0x0C",
                numeric_value=750.0, unit="rpm", sequence=1, quality="GOOD",
                metadata={"pid": 12}, source_type=AcquisitionSourceType.OBD_ACQUISITION,
                raw=b"\x03\xE8",
            )
        ][:limit],
    )
    monkeypatch.setattr(acquisition_routes, "sessions", {"s1": session})
    monkeypatch.setattr(acquisition_routes, "service", fake)
    return session, fake


@pytest.mark.asyncio
async def test_acquisition_start_validates_session_adapter_and_service_errors(monkeypatch):
    _, fake = _setup_acquisition(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await acquisition_routes.start_acquisition("missing", AcquisitionStartRequest())
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await acquisition_routes.start_acquisition("s1", AcquisitionStartRequest(adapter="ble"))
    assert exc.value.status_code == 409
    assert "Bind a connected" in exc.value.detail

    request = AcquisitionStartRequest(adapter="simulator", pids=[12])
    assert await acquisition_routes.start_acquisition("s1", request) == _status(fake.start_simulator.await_args.args[0])
    fake.start_simulator.assert_awaited_once()

    async def fail(*_args):
        raise RuntimeError("simulator failure")
    fake.start_simulator = fail
    with pytest.raises(HTTPException) as exc:
        await acquisition_routes.start_acquisition("s1", request)
    assert exc.value.status_code == 502
    assert "simulator failure" in exc.value.detail


@pytest.mark.asyncio
async def test_acquisition_stop_status_and_records_cover_missing_resources(monkeypatch):
    session, fake = _setup_acquisition(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        await acquisition_routes.stop_acquisition("missing")
    assert exc.value.status_code == 404
    assert await acquisition_routes.stop_acquisition("s1") == _status(session.session_id, "STOPPED")
    fake.stop = AsyncMock(side_effect=KeyError(session.session_id))
    with pytest.raises(HTTPException) as exc:
        await acquisition_routes.stop_acquisition("s1")
    assert exc.value.status_code == 409

    with pytest.raises(HTTPException) as exc:
        acquisition_routes.acquisition_status("missing")
    assert exc.value.status_code == 404
    fake.status = lambda _sid: (_ for _ in ()).throw(KeyError(_sid))
    with pytest.raises(HTTPException) as exc:
        acquisition_routes.acquisition_status("s1")
    assert exc.value.status_code == 404
    fake.status = lambda _sid: _status(session.session_id)
    assert acquisition_routes.acquisition_status("s1") == _status(session.session_id)

    with pytest.raises(HTTPException) as exc:
        acquisition_routes.acquisition_records("s1", limit=0)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        acquisition_routes.acquisition_records("s1", limit=1001)
    assert exc.value.status_code == 400
    with pytest.raises(HTTPException) as exc:
        acquisition_routes.acquisition_records("missing", limit=10)
    assert exc.value.status_code == 404

    result = acquisition_routes.acquisition_records("s1", limit=10)
    record = result["records"][0]
    assert record["channel"] == "0x0C"
    assert record["source_type"] == "OBD_ACQUISITION"
    assert record["raw"] == "03e8"
