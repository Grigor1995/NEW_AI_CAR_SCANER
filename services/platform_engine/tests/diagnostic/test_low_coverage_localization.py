import pytest

from diagnostic.localization import (
    _localized_evidence_fact,
    _localized_evidence_status,
    _localized_event,
    _localized_hypothesis_targets,
    _localized_prerequisite,
    _localized_question,
    _localized_safety_note,
    _localized_status,
    _localized_test_result_fact,
    localize_session_analysis,
    normalize_language,
)
from diagnostic.models import (
    DiagnosticSession,
    DiagnosticTest,
    Evidence,
    EvidenceSource,
    EvidenceStatus,
    Hypothesis,
    TestResult,
)


def test_language_aliases_and_localization_helpers_preserve_unknown_values():
    assert normalize_language(None) == "en"
    assert normalize_language(" ARM ") == "hy"
    assert normalize_language("am") == "hy"
    assert normalize_language("RU") == "ru"
    assert normalize_language("fr") == "en"

    assert _localized_evidence_status("measured", "hy") != "measured"
    assert _localized_evidence_status("custom-state", "hy") == "custom-state"
    assert _localized_event("SYMPTOM_ADDED", "hy") != "SYMPTOM_ADDED"
    assert _localized_event("CUSTOM_EVENT", "ru") == "CUSTOM_EVENT"
    assert _localized_hypothesis_targets(["LPG injection", "custom category"], "hy")[1] == "custom category"
    assert _localized_prerequisite("misfire", "hy") != "misfire"
    assert _localized_prerequisite("custom", "ru") == "custom"
    assert _localized_safety_note("Follow LPG system manufacturer procedures.", "hy") != "Follow LPG system manufacturer procedures."
    assert _localized_safety_note("unmapped safety note", "hy") == "unmapped safety note"
    assert _localized_safety_note("unmapped safety note", "en") == "unmapped safety note"
    assert _localized_status("possible:0.75", "hy") != "possible:0.75"
    assert _localized_status("custom:0.1", "ru") == "custom:0.1"
    assert _localized_status("possible:0.75", "en") == "possible:0.75"
    question = "What is LPG gas pressure at idle and during the reported load/RPM window?"
    assert _localized_question(question, "hy") != question
    assert _localized_question("custom question", "ru") == "custom question"


def test_test_result_evidence_supports_legacy_detailed_id_and_unmatched_shapes():
    legacy = _localized_test_result_fact("Test T12 result: PASS", "hy")
    assert "T12" in legacy and "ԱՆՑԱՎ" in legacy

    detailed = _localized_test_result_fact(
        "Completed diagnostic test: Measure LPG pressure; result: FAIL; technician notes: below spec",
        "ru",
    )
    assert "Measure LPG pressure" in detailed
    assert "НЕ ПРОЙДЕН" in detailed
    assert "technician notes: below spec" in detailed

    id_form = _localized_test_result_fact(
        "Completed diagnostic test ID: abc-123; result: INCOMPLETE",
        "hy",
    )
    assert "abc-123" in id_form and "ԱՆԱՎԱՐՏ" in id_form
    plain = "P0302 was reported by the driver"
    assert _localized_test_result_fact(plain, "ru") == plain
    compact = _localized_evidence_fact("Test abcdef12-3456 result: INCOMPLETE", "ru")
    assert "НЕ ЗАВЕРШЁН" in compact
    assert _localized_evidence_fact("not a test-result record", "hy") == "not a test-result record"
    assert _localized_evidence_fact("Test abcdef12 result: PASS", "en") == "Test abcdef12 result: PASS"


def test_localize_session_analysis_translates_nested_fields_without_mutating_source():
    session = DiagnosticSession()
    session.hypotheses = [
        Hypothesis(category="LPG injection", statement="Check injectors", status="possible:0.85")
    ]
    session.recommendations = [
        DiagnosticTest(
            name="Measure LPG pressure at idle and under load",
            purpose="Check pressure",
            safety_notes=[
                "Follow LPG system manufacturer procedures.",
                "unknown note",
            ],
            prerequisites=["misfire", "custom prerequisite"],
            target_hypotheses=["LPG injection", "custom hypothesis"],
        )
    ]
    session.test_results = [
        TestResult(
            test_id=session.recommendations[0].id,
            result="PASS",
            test_name="Measure LPG pressure at idle and under load",
        )
    ]
    session.evidence = [
        Evidence(
            fact="Completed diagnostic test: Measure LPG pressure at idle and under load; result: PASS; technician notes: stable",
            source=EvidenceSource.TECHNICIAN_OBSERVED,
            status=EvidenceStatus.MEASURED,
        ),
        Evidence(
            fact=f"Test {session.recommendations[0].id} result: INCOMPLETE",
            source=EvidenceSource.TECHNICIAN_OBSERVED,
            status=EvidenceStatus.MEASURED,
        ),
    ]
    session.audit_log = [
        {
            "event": "SYMPTOM_ADDED",
            "questions": ["What is LPG gas pressure at idle and during the reported load/RPM window?", "custom question"],
        },
        {"event": "CUSTOM_EVENT"},
    ]

    localized = localize_session_analysis(session, "arm")
    assert localized is not session
    assert localized.hypotheses[0].category != session.hypotheses[0].category
    assert localized.hypotheses[0].status != session.hypotheses[0].status
    assert localized.recommendations[0].name != session.recommendations[0].name
    assert localized.recommendations[0].safety_notes[1] == "unknown note"
    assert localized.recommendations[0].prerequisites[1] == "custom prerequisite"
    assert localized.recommendations[0].target_hypotheses[1] == "custom hypothesis"
    assert localized.test_results[0].result == "PASS"
    assert localized.test_results[0].result_label == "ԱՆՑԱՎ"
    assert "stable" in localized.evidence[0].fact
    assert "ԱՆԱՎԱՐՏ" in localized.evidence[1].fact
    assert localized.audit_log[0]["event"] != "SYMPTOM_ADDED"
    assert localized.audit_log[0]["questions"][1] == "custom question"
    assert localized.audit_log[1]["event"] == "CUSTOM_EVENT"

    # English is intentionally a deep-copied identity result.
    english = localize_session_analysis(session, "en")
    assert english is not session
    assert english.hypotheses[0].category == session.hypotheses[0].category


@pytest.mark.parametrize("language", ["hy", "ru"])
def test_localized_dtc_and_structured_facts_keep_source_session_unchanged(language):
    from diagnostic.models import DTC, DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus
    from diagnostic.localization import localize_session_analysis
    session = DiagnosticSession(dtcs=[DTC(code="P0302"), DTC(code="P0171", description="Technician original note")])
    session.evidence.append(Evidence(fact="fuel_mode_lpg", source=EvidenceSource.USER_REPORTED, status=EvidenceStatus.REPORTED, metadata={"derived_from": "on LPG"}))
    localized = localize_session_analysis(session, language)
    assert localized.dtcs[0].description
    assert localized.dtcs[1].description == "Technician original note"
    assert localized.evidence[0].fact != "fuel_mode_lpg"
    assert localized.evidence[0].source == EvidenceSource.USER_REPORTED
    assert session.dtcs[0].description is None
    assert session.evidence[0].fact == "fuel_mode_lpg"


@pytest.mark.parametrize("language", ["hy", "ru"])
def test_entire_decision_plan_presentation_is_localized(language):
    from diagnostic.decision import CATALOG, DecisionCandidate, DiagnosticDecisionPlan
    from diagnostic.localization import localize_decision_plan
    from uuid import uuid4
    candidates = [DecisionCandidate(test_id=uuid4(), name=spec.name, purpose=spec.purpose, priority_score=.5, information_gain=.5, evidence_fit=.5, cost_penalty=.1, risk_penalty=.1, safety_notes=list(spec.safety_notes), rationale=["Required evidence is present.", "Estimated information gain: 0.50.", "Targets ignition."]) for spec in CATALOG]
    plan = DiagnosticDecisionPlan(session_id=uuid4(), state="TESTING", candidates=candidates)
    localized = localize_decision_plan(plan, language)
    for original, translated in zip(plan.candidates, localized.candidates):
        assert original.test_id == translated.test_id
        assert original.name != translated.name
        assert original.purpose != translated.purpose
        assert original.rationale != translated.rationale
        assert original.safety_notes != translated.safety_notes
