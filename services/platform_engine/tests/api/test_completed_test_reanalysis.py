"""A normal Analyze must not resurrect a test already completed by the technician."""
from api import main, intelligence_routes
from diagnostic.models import DiagnosticSession, DTC, Vehicle


def test_normal_analysis_does_not_reintroduce_a_completed_rule_test(monkeypatch):
    session = DiagnosticSession(vehicle=Vehicle(make="Toyota", model="Corolla"), dtcs=[DTC(code="P0171")])
    sid = str(session.session_id)
    monkeypatch.setattr(main, "sessions", {sid: session})
    monkeypatch.setattr(intelligence_routes, "sessions", {sid: session})
    first = main.analyze(sid, language="en")
    assert first.recommendations
    selected = first.recommendations[0]
    intelligence_routes.add_test_result(sid, intelligence_routes.TestResultRequest(test_id=selected.id, result="PASS"), language="en")
    repeated = main.analyze(sid, language="en")
    assert selected.name not in {test.name for test in repeated.recommendations}
    assert repeated.test_results[-1].test_name == selected.name
