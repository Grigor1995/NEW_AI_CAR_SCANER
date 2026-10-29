from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

import api.decision_routes as routes


@pytest.fixture
def sample_session():
    return SimpleNamespace(recommendations=[], audit_log=[])


def test_decision_plan_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        routes.decision_plan("missing")
    assert error.value.status_code == 404
    assert error.value.detail == "Session not found"


def test_refresh_plan_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        routes.refresh_decision_plan("missing")
    assert error.value.status_code == 404


def test_select_test_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        routes.select_test("missing", routes.ConfirmTestRequest(test_id="test-1"))
    assert error.value.status_code == 404


def test_select_test_rejects_candidate_not_in_plan(monkeypatch, sample_session):
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(routes.engine, "build_plan", lambda _session: SimpleNamespace(candidates=[]))
    with pytest.raises(HTTPException) as error:
        routes.select_test("session-1", routes.ConfirmTestRequest(test_id="test-1"))
    assert error.value.status_code == 404
    assert error.value.detail == "Test candidate not found"


def test_select_test_requires_confirmation_for_high_risk(monkeypatch, sample_session):
    test_id = uuid4()
    candidate = SimpleNamespace(test_id=test_id, name="Compression test", safety_notes=["Engine off"])
    sample_session.recommendations = [SimpleNamespace(name="Compression test", risk_level="HIGH")]
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(
        routes.engine,
        "build_plan",
        lambda _session: SimpleNamespace(candidates=[candidate]),
    )

    with pytest.raises(HTTPException) as error:
        routes.select_test("session-1", routes.ConfirmTestRequest(test_id=str(test_id)))
    assert error.value.status_code == 409
    assert "Safety confirmation required" in error.value.detail
    assert sample_session.audit_log == []


def test_select_test_records_audited_selection_after_confirmation(monkeypatch, sample_session):
    test_id = uuid4()
    candidate = SimpleNamespace(test_id=test_id, name="Compression test", safety_notes=["Engine off"])
    sample_session.recommendations = [SimpleNamespace(name="Compression test", risk_level="HIGH")]
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(
        routes.engine,
        "build_plan",
        lambda _session: SimpleNamespace(candidates=[candidate]),
    )

    response = routes.select_test(
        "session-1",
        routes.ConfirmTestRequest(test_id=str(test_id), safety_confirmed=True),
    )
    assert response == {
        "selected_test_id": str(test_id),
        "name": "Compression test",
        "risk_level": "HIGH",
        "safety_notes": ["Engine off"],
    }
    assert sample_session.audit_log == [{
        "event": "TEST_SELECTED",
        "test_id": str(test_id),
        "name": "Compression test",
        "risk_level": "HIGH",
    }]


def test_select_test_defaults_to_low_risk_when_test_record_is_missing(monkeypatch, sample_session):
    test_id = uuid4()
    candidate = SimpleNamespace(test_id=test_id, name="Visual inspection", safety_notes=[])
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(
        routes.engine,
        "build_plan",
        lambda _session: SimpleNamespace(candidates=[candidate]),
    )

    response = routes.select_test(
        "session-1",
        routes.ConfirmTestRequest(test_id=str(test_id)),
    )
    assert response["risk_level"] == "LOW"
    assert sample_session.audit_log[-1]["risk_level"] == "LOW"


def test_decision_plan_returns_engine_plan_for_existing_session(monkeypatch, sample_session):
    expected_plan = routes.DiagnosticDecisionPlan(session_id=uuid4(), state="CREATED")
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(routes.engine, "build_plan", lambda _session: expected_plan)

    assert routes.decision_plan("session-1") == expected_plan


def test_refresh_plan_returns_updated_engine_plan(monkeypatch, sample_session):
    expected_plan = routes.DiagnosticDecisionPlan(session_id=uuid4(), state="CREATED")
    monkeypatch.setattr(routes, "sessions", {"session-1": sample_session})
    monkeypatch.setattr(routes.engine, "refresh_recommendations", lambda _session: expected_plan)

    assert routes.refresh_decision_plan("session-1") is expected_plan
