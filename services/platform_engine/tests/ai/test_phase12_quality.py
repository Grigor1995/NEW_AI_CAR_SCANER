from ai.rag.evaluation import RetrievalCase, RetrievalEvaluator, RetrievalQualityGate, ndcg_at_k, reciprocal_rank
from ai.rag.quality import RetrievalQualityRunner


def test_reciprocal_rank_and_ndcg():
    assert reciprocal_rank({'doc2'}, ['doc1', 'doc2']) == 0.5
    assert ndcg_at_k({'doc1': 3.0, 'doc2': 1.0}, ['doc1', 'doc2'], 2) == 1.0


def test_evaluator_exposes_mrr_and_ndcg_and_applies_gate():
    case = RetrievalCase('P0302 LPG', frozenset({'doc2'}), ('LPG',), {'doc2': 2.0})
    evaluator = RetrievalEvaluator(RetrievalQualityGate(min_recall_at_k=1.0, min_mrr=0.5, min_ndcg_at_k=0.6))
    result = evaluator.evaluate(case, ['doc1', 'doc2'], ['LPG procedure'])
    assert result.passed
    assert result.recall_at_k == 1.0
    assert result.mrr == 0.5
    assert round(result.ndcg_at_k, 3) == 0.631


def test_quality_runner_summarizes_corpus():
    cases = [
        RetrievalCase('q1', frozenset({'d1'})),
        RetrievalCase('q2', frozenset({'d2'})),
    ]
    result = RetrievalQualityRunner(RetrievalQualityGate(min_recall_at_k=1, min_mrr=1, min_ndcg_at_k=1)).evaluate_cases(
        cases, [['d1'], ['d2']], [['text'], ['text']]
    )
    assert result.cases == 2
    assert result.passed == 2
    assert result.failed == 0
    assert result.gate_passed
