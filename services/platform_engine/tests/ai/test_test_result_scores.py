from diagnostic.models import DiagnosticSession, Evidence, EvidenceSource, EvidenceStatus
from ai.reasoning.engine import DiagnosticIntelligenceEngine


def case():
    engine = DiagnosticIntelligenceEngine()
    session = DiagnosticSession(evidence=[
        Evidence(fact="misfire on LPG, petrol normal", source=EvidenceSource.USER_REPORTED,
                 status=EvidenceStatus.REPORTED),
    ])
    engine.analyze(session)
    return engine, session


def scores(session):
    return {h.category: h.confidence_score for h in session.hypotheses}


def test_outcomes_change_scores_and_survive_repeat_analysis_and_persistence():
    for outcome, direction in [("FAIL", 1), ("PASS", -1)]:
        engine, session = case()
        baseline = scores(session)
        test = session.recommendations[0]
        engine.record_test_result(session, test.id, outcome)
        changed = scores(session)
        for target in test.target_hypotheses:
            if target in baseline:
                assert (changed[target] - baseline[target]) * direction > 0
        assert changed != baseline
        restored = DiagnosticSession.model_validate_json(session.model_dump_json())
        engine.analyze(restored)
        assert scores(restored) == changed
        assert list(scores(restored).values()) == sorted(scores(restored).values(), reverse=True)


def test_correcting_same_test_replaces_effect_and_incomplete_withdraws_it():
    engine, session = case()
    baseline = scores(session)
    test = session.recommendations[0]
    engine.record_test_result(session, test.id, "FAIL")
    engine.record_test_result(session, test.id, "FAIL")
    failed = scores(session)
    engine.analyze(session)
    assert scores(session) == failed
    engine.record_test_result(session, test.id, "PASS")
    passed = scores(session)
    assert any(passed[k] < baseline[k] for k in baseline)
    engine.record_test_result(session, test.id, "INCOMPLETE", notes="pressure drops")
    assert scores(session) == baseline


def test_two_distinct_results_accumulate_and_first_survives_second():
    engine, session = case()
    first = session.recommendations[0]
    engine.record_test_result(session, first.id, "FAIL")
    after_first = scores(session)
    second = next(x for x in session.recommendations if set(x.target_hypotheses) & set(first.target_hypotheses))
    engine.record_test_result(session, second.id, "FAIL")
    after_second = scores(session)
    common = set(first.target_hypotheses) & set(second.target_hypotheses)
    assert any(after_second[x] > after_first[x] for x in common if x in after_first)
    engine.analyze(session)
    assert scores(session) == after_second


def test_localized_result_and_normal_analysis_keep_recalculated_scores(monkeypatch):
    from api import intelligence_routes, main
    from diagnostic.localization import localize_session_analysis

    engine, session = case()
    sid = str(session.session_id)
    monkeypatch.setattr(intelligence_routes, "sessions", {sid: session})
    monkeypatch.setattr(main, "sessions", {sid: session})
    test = session.recommendations[0]
    baseline = scores(session)
    response = intelligence_routes.add_test_result(
        sid, intelligence_routes.TestResultRequest(test_id=test.id, result="FAIL"), language="hy")
    assert scores(session) != baseline
    assert sorted(h.confidence_score for h in response.hypotheses) == sorted(scores(session).values())
    changed = scores(session)
    main.analyze(sid, language="ru")
    assert scores(session) == changed
    for language in ("en", "ru", "hy"):
        localized = localize_session_analysis(session, language)
        assert [h.confidence_score for h in localized.hypotheses] == list(changed.values())
