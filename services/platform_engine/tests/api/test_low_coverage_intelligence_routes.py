from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from diagnostic.models import DiagnosticSession, EvidenceSource
from api import intelligence_routes as routes


class FakeEngine:
    def __init__(self):
        self.ingest_calls = []
        self.analyze_calls = []
        self.result_calls = []

    def ingest_text(self, session, text, source):
        self.ingest_calls.append((session, text, source))
        return session

    def analyze(self, session):
        self.analyze_calls.append(session)
        return session

    def record_test_result(self, session, test_id, result, measurements, notes):
        self.result_calls.append((session, test_id, result, measurements, notes))
        return session


def _setup(monkeypatch, session=None):
    session = session or DiagnosticSession()
    sessions = {"session-1": session}
    engine = FakeEngine()
    localized = []
    monkeypatch.setattr(routes, "sessions", sessions)
    monkeypatch.setattr(routes, "engine", engine)
    monkeypatch.setattr(
        routes,
        "localize_session_analysis",
        lambda result, language: localized.append((result, language)) or {"localized": language},
    )
    return session, engine, localized


def test_ingest_text_404_and_success(monkeypatch):
    session, engine, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.ingest_text("missing", routes.IngestTextRequest(text="misfire"))
    assert exc.value.status_code == 404

    response = routes.ingest_text(
        "session-1",
        routes.IngestTextRequest(text="P0302 misfire", source=EvidenceSource.TECHNICIAN_OBSERVED),
    )
    assert response is session
    assert engine.ingest_calls == [(session, "P0302 misfire", EvidenceSource.TECHNICIAN_OBSERVED)]


def test_analyze_404_and_localizes_requested_language(monkeypatch):
    session, engine, localized = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.analyze("missing", language="ru")
    assert exc.value.status_code == 404

    assert routes.analyze("session-1", language="hy") == {"localized": "hy"}
    assert engine.analyze_calls == [session]
    assert localized == [(session, "hy")]


def test_test_result_unknown_maps_to_incomplete_and_success_is_localized(monkeypatch):
    session, engine, localized = _setup(monkeypatch)
    test_id = uuid4()
    request = routes.TestResultRequest(
        test_id=test_id,
        result=" unknown ",
        measurements={"pressure_kpa": 180},
        notes="Measured during load",
    )

    assert routes.add_test_result("session-1", request, language="ru") == {"localized": "ru"}
    assert engine.result_calls == [(session, test_id, "INCOMPLETE", {"pressure_kpa": 180}, "Measured during load")]
    assert localized == [(session, "ru")]


def test_test_result_accepts_normalized_status_and_rejects_invalid(monkeypatch):
    session, engine, _ = _setup(monkeypatch)
    test_id = uuid4()
    routes.add_test_result(
        "session-1",
        routes.TestResultRequest(test_id=test_id, result=" pass "),
    )
    assert engine.result_calls[-1][2] == "PASS"

    with pytest.raises(HTTPException) as exc:
        routes.add_test_result(
            "session-1",
            routes.TestResultRequest(test_id=test_id, result="success"),
        )
    assert exc.value.status_code == 422
    assert "PASS, FAIL, or INCOMPLETE" in exc.value.detail


def test_test_result_404_does_not_call_engine(monkeypatch):
    _, engine, _ = _setup(monkeypatch)
    with pytest.raises(HTTPException) as exc:
        routes.add_test_result(
            "missing",
            routes.TestResultRequest(test_id=uuid4(), result="FAIL"),
        )
    assert exc.value.status_code == 404
    assert engine.result_calls == []
