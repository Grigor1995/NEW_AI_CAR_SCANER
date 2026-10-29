from ai.reasoning.engine import DiagnosticIntelligenceEngine
from diagnostic.decision import DiagnosticDecisionEngine
from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus, Vehicle


def build_case():
    s = DiagnosticSession(vehicle=Vehicle(make="Mercedes-Benz", model="W211", year=2006, engine="M272 3.5", fuel=["petrol", "LPG"]))
    s.evidence.extend([
        Evidence(fact="fuel_mode_lpg", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED),
        Evidence(fact="misfire", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED),
        Evidence(fact="petrol normal", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED),
        Evidence(fact="acceleration below 2000 RPM", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED),
    ])
    return s


def test_decision_plan_targets_hypotheses_and_scores_candidates():
    engine = DiagnosticIntelligenceEngine()
    session = build_case()
    engine.analyze(session)
    plan = DiagnosticDecisionEngine().build_plan(session)
    assert plan.candidates
    assert plan.selected_test_id == plan.candidates[0].test_id
    assert all(0 <= c.priority_score <= 1 for c in plan.candidates)
    assert any("LPG injection" in " ".join(c.rationale) for c in plan.candidates)


def test_refresh_recommendations_populates_ranked_tests():
    engine = DiagnosticIntelligenceEngine()
    session = build_case()
    engine.analyze(session)
    assert session.recommendations
    assert session.state.value == "TESTING"
    assert session.recommendations[0].priority_score >= session.recommendations[-1].priority_score


def test_test_result_changes_hypothesis_status_without_claiming_component_confirmation():
    engine = DiagnosticIntelligenceEngine()
    session = build_case()
    engine.analyze(session)
    test = session.recommendations[0]
    engine.record_test_result(session, test.id, "LPG pressure drops under load", {"pressure_bar": 0.65})
    assert any(h.status == "supported_by_test" for h in session.hypotheses)
    assert not any("confirmed component" in h.statement.lower() for h in session.hypotheses)
    assert any(x.get("event") == "TEST_RESULT_INTERPRETED" for x in session.audit_log)


def test_pass_and_fail_outcomes_change_target_hypothesis_status():
    engine = DiagnosticIntelligenceEngine()

    passing = build_case()
    engine.analyze(passing)
    passing_test = passing.recommendations[0]
    engine.record_test_result(passing, passing_test.id, "PASS")
    assert any(h.status == "disfavored_by_test" for h in passing.hypotheses)

    failing = build_case()
    engine.analyze(failing)
    failing_test = failing.recommendations[0]
    engine.record_test_result(failing, failing_test.id, "FAIL")
    assert any(h.status == "supported_by_test" for h in failing.hypotheses)


def test_technician_notes_can_drive_test_interpretation():
    engine = DiagnosticIntelligenceEngine()
    session = build_case()
    engine.analyze(session)
    test = session.recommendations[0]
    engine.record_test_result(session, test.id, "INCONCLUSIVE", notes="LPG pressure drops under load")
    assert any(h.status == "supported_by_test" for h in session.hypotheses)
