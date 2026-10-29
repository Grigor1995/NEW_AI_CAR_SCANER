
from ai.ml.anomaly import NumericAnomalyDetector
from ai.rag.evaluator import RagEvalCase, RagEvaluator
from ai.rag.store import HybridKnowledgeStore, KnowledgeDocument
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from diagnostic.models import DTC, DiagnosticSession, EvidenceSource, Vehicle


def build_case():
    session = DiagnosticSession(vehicle=Vehicle(make="Mercedes-Benz", model="W211", year=2006, engine="M272 3.5", fuel=["petrol", "LPG"]))
    session.dtcs.append(DTC(code="P0302", source=EvidenceSource.ECU_REPORTED))
    return session


def test_structured_evidence_and_questions():
    session = build_case()
    engine = DiagnosticIntelligenceEngine()
    engine.ingest_text(session, "Engine is shaking during acceleration below 2000 RPM on LPG; petrol is normal.")
    out = engine.analyze(session)
    facts = {e.fact for e in out.evidence}
    assert "fuel_mode_lpg" in facts
    assert "misfire" in facts
    assert any(x.get("event") == "QUESTIONS_IDENTIFIED" for x in out.audit_log)
    assert {h.category for h in out.hypotheses} >= {"ignition", "intake"}


def test_test_result_loops_back_into_reasoning():
    session = build_case()
    engine = DiagnosticIntelligenceEngine()
    engine.ingest_text(session, "Misfire occurs only on LPG during acceleration below 2000 RPM.")
    engine.analyze(session)
    test = engine.next_test(session)
    assert test is not None
    engine.record_test_result(session, test.id, "LPG pressure drops", {"pressure_bar": 0.65})
    assert session.test_results[-1].test_id == test.id
    assert session.state.value in {"HYPOTHESIS_VALIDATION", "QUESTIONS_PENDING", "INITIAL_ANALYSIS"}
    assert any(e.status.value == "measured" for e in session.evidence)


def test_anomaly_detector():
    result = NumericAnomalyDetector().score("fuel_trim", 25.0, [1.0, 1.5, 1.0, 0.5, 1.0])
    assert result.anomalous is True
    assert result.z_score > 3


def test_rag_retrieval_and_eval():
    store = HybridKnowledgeStore([
        KnowledgeDocument("dtc-p0302", "P0302 Misfire", "Cylinder 2 misfire diagnostic information", {"manufacturer": "Mercedes-Benz"}),
        KnowledgeDocument("unrelated", "ABS", "Wheel speed sensor information", {"manufacturer": "Other"}),
    ])
    result = RagEvaluator().evaluate(store, RagEvalCase("P0302 cylinder 2 misfire", {"dtc-p0302"}))
    assert result.hit
    assert result.retrieved_ids[0] == "dtc-p0302"
