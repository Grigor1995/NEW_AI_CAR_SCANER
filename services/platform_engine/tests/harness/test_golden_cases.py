from diagnostic.models import DiagnosticSession, DTC, Symptom, Vehicle
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from global_data import global_data


def _session(case: dict) -> DiagnosticSession:
    return DiagnosticSession(
        vehicle=Vehicle(**case["vehicle"]),
        symptoms=[Symptom(raw_text=case["symptoms"][0])],
        dtcs=[DTC(code=case["dtcs"][0])],
    )


def test_golden_lpg_misfire_case():
    case = global_data.case("LPG_MISFIRE_001")
    assert case is not None
    session = DiagnosticIntelligenceEngine().analyze(_session(case))
    categories = {h.category for h in session.hypotheses}
    for expected in case["expected_hypothesis_domains"]:
        assert expected in categories
    statements = " ".join(h.statement.lower() for h in session.hypotheses)
    for forbidden in case["forbidden_conclusions"]:
        assert forbidden not in statements


def test_golden_lean_mixture_case():
    case = global_data.case("LEAN_MIXTURE_001")
    assert case is not None
    session = DiagnosticIntelligenceEngine().analyze(_session(case))
    categories = {h.category.lower() for h in session.hypotheses}
    assert "lean mixture" in categories
    assert session.recommendations


def test_golden_cases_have_testable_contracts():
    cases = global_data.snapshot().diagnostic_cases
    assert len(cases) >= 2
    for case in cases:
        assert case["case_id"]
        assert case["vehicle"]["make"]
        assert case["dtcs"]
        assert case["symptoms"]
        assert case["expected_hypothesis_domains"]
        assert case["forbidden_conclusions"]
