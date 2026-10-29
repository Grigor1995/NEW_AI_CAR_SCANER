from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession
from api import network_discovery_routes as routes


class FakeDiscoveryService:
    def __init__(self):
        self.ingested = None
        self.reset_ids = []
        self.sid = None

    def ingest_frames(self, session_id, *, bus, frames):
        self.ingested = (session_id, bus, frames)
        return len(frames)

    def observation_count(self, session_id):
        self.sid = session_id
        return 7

    def analyze(self, session_id):
        self.sid = session_id
        return SimpleNamespace(to_dict=lambda: {"summary": {"ecu_candidates": 2}})

    def reset(self, session_id):
        self.reset_ids.append(session_id)


def _setup(monkeypatch):
    session = DiagnosticSession()
    service = FakeDiscoveryService()
    monkeypatch.setattr(routes, "sessions", {"session-1": session})
    monkeypatch.setattr(routes, "service", service)
    return session, service


def test_ingest_frames_404_invalid_hex_and_success(monkeypatch):
    session, service = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.ingest_frames("missing", routes.DiscoveryBatchRequest(
            frames=[routes.DiscoveredFrameRequest(arbitration_id=0x7E0, data_hex="0102")]
        ))
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        routes._frame(routes.DiscoveredFrameRequest(arbitration_id=0x7E0, data_hex="not-hex"))
    assert exc.value.status_code == 422
    assert "valid hexadecimal" in exc.value.detail

    response = routes.ingest_frames(
        "session-1",
        routes.DiscoveryBatchRequest(
            bus="CAN1",
            frames=[
                routes.DiscoveredFrameRequest(
                    arbitration_id=0x7E0, data_hex="0102", timestamp_ns=123,
                ),
                routes.DiscoveredFrameRequest(
                    arbitration_id=0x18DAF110, data_hex="AABB", is_extended=True,
                ),
            ],
        ),
    )
    assert response == {"accepted": 2, "observation_count": 7}
    sid, bus, frames = service.ingested
    assert sid == session.session_id
    assert bus == "CAN1"
    assert len(frames) == 2
    assert frames[0].data == b"\x01\x02"
    assert frames[0].timestamp_ns == 123
    assert frames[1].is_extended is True


def test_map_and_reset_validate_session_and_return_service_result(monkeypatch):
    session, service = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.discover_map("missing")
    assert exc.value.status_code == 404
    assert routes.discover_map("session-1") == {"summary": {"ecu_candidates": 2}}
    assert service.sid == session.session_id

    with pytest.raises(HTTPException) as exc:
        routes.reset_discovery("missing")
    assert exc.value.status_code == 404
    assert routes.reset_discovery("session-1") == {"status": "reset"}
    assert service.reset_ids == [session.session_id]
