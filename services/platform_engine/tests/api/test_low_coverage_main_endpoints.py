from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import HTTPException

from diagnostic.models import (
    DiagnosticSession, DiagnosticTest, DTC, EvidenceSource,
    EvidenceStatus, Hypothesis, Symptom, Vehicle,
)
from api import main as api_main


def _setup(monkeypatch):
    store = {}
    monkeypatch.setattr(api_main, "sessions", store)
    return store


def test_create_list_and_get_session_bounds_and_missing_case(monkeypatch):
    store = _setup(monkeypatch)
    empty = api_main.create_session(None)
    assert empty.vehicle is None
    assert store[str(empty.session_id)] is empty

    created = api_main.create_session({"make": "Mercedes-Benz", "model": "W211", "year": 2006})
    assert created.vehicle.make == "Mercedes-Benz"
    assert len(api_main.list_sessions()) == 2
    assert api_main.list_sessions(limit=0)
    assert len(api_main.list_sessions(limit=500)) == 2
    assert api_main.get_session(str(created.session_id)) is created

    with pytest.raises(HTTPException) as exc:
        api_main.get_session("unknown")
    assert exc.value.status_code == 404


def test_vehicle_and_symptom_create_update_delete_lifecycle(monkeypatch):
    store = _setup(monkeypatch)
    session = DiagnosticSession()
    store["s1"] = session

    updated = api_main.update_vehicle("s1", Vehicle(make="Mercedes-Benz", model="W211", year=2006))
    assert updated.vehicle.model == "W211"
    assert updated.audit_log[-1]["event"] == "VEHICLE_UPDATED"

    with pytest.raises(HTTPException) as exc:
        api_main.add_symptom("s1", type("SymptomInput", (), {"raw_text": "  "})())
    assert exc.value.status_code == 422

    symptom = Symptom(raw_text="Engine shakes on LPG")
    result = api_main.add_symptom("s1", symptom)
    assert result.symptoms[0].id == symptom.id
    assert result.evidence[-1].fact == "Engine shakes on LPG"
    assert result.audit_log[-1]["event"] == "SYMPTOM_ADDED"

    changed = Symptom(raw_text="  Rough idle  ", normalized={"fuel_mode": "LPG"})
    result = api_main.update_symptom("s1", str(symptom.id), changed)
    assert result.symptoms[0].raw_text == "Rough idle"
    assert result.evidence[-1].fact == "Rough idle"
    assert result.audit_log[-1]["event"] == "SYMPTOM_UPDATED"

    with pytest.raises(HTTPException) as exc:
        api_main.update_symptom("s1", str(uuid4()), changed)
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        api_main.delete_symptom("s1", str(uuid4()))
    assert exc.value.status_code == 404

    result = api_main.delete_symptom("s1", str(symptom.id))
    assert result.symptoms == []
    assert not any(e.fact == "Rough idle" for e in result.evidence)
    assert result.audit_log[-1]["event"] == "SYMPTOM_DELETED"


def test_dtc_create_update_delete_normalizes_evidence_and_invalidates_analysis(monkeypatch):
    store = _setup(monkeypatch)
    session = DiagnosticSession(
        hypotheses=[Hypothesis(category="ignition", statement="possible coil")],
        recommendations=[DiagnosticTest(name="Check ignition", purpose="verify")],
    )
    store["s1"] = session

    with pytest.raises(HTTPException) as exc:
        api_main.add_dtc("s1", DTC(code="  "))
    assert exc.value.status_code == 422

    created = api_main.add_dtc("s1", DTC(code=" p0302 ", source=EvidenceSource.ECU_REPORTED))
    dtc = created.dtcs[0]
    assert dtc.code == "P0302"
    assert created.evidence[-1].status is EvidenceStatus.MEASURED
    assert created.hypotheses == [] and created.recommendations == []

    with pytest.raises(HTTPException) as exc:
        api_main.update_dtc("s1", str(uuid4()), DTC(code="P0171"))
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        api_main.update_dtc("s1", str(dtc.id), DTC(code=" "))
    assert exc.value.status_code == 422

    created.hypotheses = [Hypothesis(category="mixture", statement="possible lean")]
    created.recommendations = [DiagnosticTest(name="Check trims", purpose="measure")]
    updated = api_main.update_dtc("s1", str(dtc.id), DTC(code="p0171", source=EvidenceSource.USER_REPORTED))
    assert updated.dtcs[0].code == "P0171"
    assert updated.evidence[-1].fact == "P0171"
    assert updated.evidence[-1].status is EvidenceStatus.REPORTED
    assert updated.hypotheses == [] and updated.recommendations == []
    assert updated.audit_log[-1]["event"] == "DTC_UPDATED"

    with pytest.raises(HTTPException) as exc:
        api_main.delete_dtc("s1", str(uuid4()))
    assert exc.value.status_code == 404
    deleted = api_main.delete_dtc("s1", str(dtc.id))
    assert deleted.dtcs == []
    assert not any(item.fact == "P0171" for item in deleted.evidence)
    assert deleted.audit_log[-1]["event"] == "DTC_DELETED"


def test_analysis_compat_path_merges_rule_tests_and_enriches_missing_fields(monkeypatch):
    store = _setup(monkeypatch)
    session = DiagnosticSession()
    store["s1"] = session
    rule_test = DiagnosticTest(
        name="Check LPG pressure", purpose="rule test", risk_level="LOW",
        target_hypotheses=["engine"],
    )
    duplicate_test = DiagnosticTest(name="Decision test", purpose="duplicate")
    decision_test = DiagnosticTest(name="Decision test", purpose="decision")
    decision_test.estimated_cost = 3.0
    session.recommendations = [rule_test, duplicate_test]
    session.hypotheses = [
        Hypothesis(category="engine", statement="engine issue"),
        Hypothesis(category="mixture", statement="mixture issue"),
    ]

    class FakeEngine:
        def analyze(self, current):
            current.recommendations = [rule_test, duplicate_test]
            current.hypotheses = [
                Hypothesis(category="engine", statement="engine issue"),
                Hypothesis(category="mixture", statement="mixture issue"),
            ]
            return current

    class FakeIntelligence:
        def _apply_test_history(self, current):
            pass
        def _annotate_scores(self, current):
            current.audit_log.append({"event": "SCORES_ANNOTATED"})
        def _add_missing_questions(self, current):
            current.audit_log.append({"event": "QUESTIONS_ADDED"})

    class FakeDecision:
        def refresh_recommendations(self, current):
            current.recommendations = [decision_test]

    monkeypatch.setattr(api_main, "engine", FakeEngine())
    monkeypatch.setattr(api_main, "intelligence_engine", FakeIntelligence())
    monkeypatch.setattr(api_main, "decision_engine", FakeDecision())
    monkeypatch.setattr(api_main, "localize_session_analysis", lambda current, language: current)

    result = api_main.analyze_compat("s1", language="hy")
    assert result is session
    assert [item.name for item in result.recommendations] == [
        "Decision test", "Check LPG pressure",
    ]
    rule = result.recommendations[1]
    assert rule.expected_information_gain == 0.95
    assert rule.estimated_cost > 0
    assert rule.priority_score > 0
    assert result.audit_log[-2]["event"] == "SCORES_ANNOTATED" or any(
        item.get("event") == "SCORES_ANNOTATED" for item in result.audit_log
    )

    # Exact API path delegates to the same helper.
    assert api_main.analyze("s1", language="en") is session

@pytest.mark.asyncio
async def test_health_lifespan_and_request_middleware_always_persist(monkeypatch):
    calls = []
    monkeypatch.setattr(api_main, "load_persisted_sessions", lambda: calls.append("load"))
    monkeypatch.setattr(api_main, "persist_sessions", lambda: calls.append("persist"))

    assert api_main.health() == {
        "status": "ok", "service": "diagnostic-api", "version": "0.1.0"
    }

    async with api_main.lifespan(api_main.app):
        assert calls == ["load"]
    assert calls == ["load"]

    async def success(_request):
        return {"ok": True}
    assert await api_main.persist_diagnostic_sessions(object(), success) == {"ok": True}
    assert calls[-1] == "persist"

    async def fail(_request):
        raise RuntimeError("handler failed")
    with pytest.raises(RuntimeError, match="handler failed"):
        await api_main.persist_diagnostic_sessions(object(), fail)
    assert calls[-1] == "persist"


def test_analysis_enrichment_covers_unmatched_targets_and_default_risk_cost(monkeypatch):
    store = _setup(monkeypatch)
    session = DiagnosticSession(
        hypotheses=[Hypothesis(category="engine", statement="issue", status="possible")],
    )
    unmatched = DiagnosticTest(
        name="Unknown risk check", purpose="cover fallback cost", risk_level="CUSTOM",
        target_hypotheses=["not-a-hypothesis"],
    )
    full_match = DiagnosticTest(
        name="Full match check", purpose="cover full match", risk_level="HIGH",
        target_hypotheses=["engine"],
    )
    session.recommendations = [unmatched, full_match]
    store["s1"] = session

    class FakeEngine:
        def analyze(self, current):
            current.recommendations = [unmatched, full_match]
            current.hypotheses = [
                Hypothesis(category="engine", statement="issue", status="possible"),
            ]
            return current

    class FakeIntelligence:
        def _apply_test_history(self, current):
            pass
        def _annotate_scores(self, _current):
            pass
        def _add_missing_questions(self, _current):
            pass

    class EmptyDecision:
        def refresh_recommendations(self, current):
            current.recommendations = []

    monkeypatch.setattr(api_main, "engine", FakeEngine())
    monkeypatch.setattr(api_main, "intelligence_engine", FakeIntelligence())
    monkeypatch.setattr(api_main, "decision_engine", EmptyDecision())
    monkeypatch.setattr(api_main, "localize_session_analysis", lambda current, _language: current)

    result = api_main.analyze("s1", language="en")
    by_name = {item.name: item for item in result.recommendations}
    assert by_name["Unknown risk check"].expected_information_gain == 0.15
    assert by_name["Unknown risk check"].estimated_cost == 1.0
    assert by_name["Unknown risk check"].priority_score > 0
    assert by_name["Full match check"].expected_information_gain == 0.25
    assert by_name["Full match check"].estimated_cost == 4.0
    assert by_name["Full match check"].priority_score > 0
