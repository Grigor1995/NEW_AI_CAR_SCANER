import pytest
from ai.rag.hybrid import QueryRewriter, HybridFusion, RetrievedChunk, lexical_score, metadata_matches
from ai.rag.evaluation import RetrievalCase, RetrievalEvaluator


def chunk(cid, vector=0.0, lexical=0.0, meta=None):
    return RetrievedChunk(cid, 'doc', f'content {cid}', meta or {}, vector_score=vector, lexical_score=lexical)


def test_query_rewriter_adds_automotive_aliases_without_dropping_original():
    queries = QueryRewriter().rewrite('LPG misfire below 2000 rpm')
    assert queries[0] == 'LPG misfire below 2000 rpm'
    assert 'gas injection' in queries[-1]


def test_hybrid_fusion_combines_candidates_from_both_retrievers():
    result = HybridFusion().fuse([chunk('a', vector=.9), chunk('b', vector=.7)], [chunk('b', lexical=.9), chunk('c', lexical=.8)], top_k=3)
    assert {r.chunk_id for r in result} == {'a', 'b', 'c'}
    assert result[0].rank == 1


def test_lexical_score_rewards_term_overlap():
    assert lexical_score('P0302 misfire', 'P0302 cylinder 2 misfire') > lexical_score('P0302 misfire', 'battery voltage')


def test_metadata_filter_requires_exact_scope():
    assert metadata_matches({'manufacturer': 'Mercedes-Benz', 'year': 2006}, {'manufacturer': 'Mercedes-Benz'})
    assert not metadata_matches({'manufacturer': 'BMW'}, {'manufacturer': 'Mercedes-Benz'})


def test_retrieval_evaluator_requires_expected_document_and_terms():
    case = RetrievalCase('P0302 misfire', frozenset({'doc1'}), ('LPG', 'misfire'))
    result = RetrievalEvaluator().evaluate(case, ['doc1', 'doc2'], ['LPG misfire diagnostic procedure'])
    assert result.passed
    assert result.recall_at_k == 1.0


def test_retrieval_evaluator_fails_missing_relevant_document():
    case = RetrievalCase('P0302 misfire', frozenset({'doc1'}), ('LPG',))
    result = RetrievalEvaluator().evaluate(case, ['doc2'], ['LPG misfire'])
    assert not result.passed
    assert result.relevant_found == 0

@pytest.mark.skipif(True, reason='Requires a running PostgreSQL/pgvector service')
def test_postgres_hybrid_integration_placeholder():
    pass
