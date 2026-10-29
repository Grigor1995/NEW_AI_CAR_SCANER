from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import api.rag_routes as routes


def test_rag_config_reports_environment_overrides(monkeypatch):
    cfg = SimpleNamespace(dimensions=384, use_hnsw=True)
    monkeypatch.setattr(routes.PgVectorConfig, "from_env", lambda: cfg)
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "test-embedder")
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "model-x")
    monkeypatch.setenv("RAG_RERANKER_PROVIDER", "test-reranker")
    monkeypatch.setenv("RAG_RERANKER_MODEL", "ranker-y")
    monkeypatch.setenv("RAG_GATE_MIN_RECALL", "0.95")
    monkeypatch.setenv("RAG_GATE_MIN_MRR", "0.85")
    monkeypatch.setenv("RAG_GATE_MIN_NDCG", "0.88")

    result = routes.rag_config()
    assert result["dimensions"] == 384
    assert result["vector_index"] == "hnsw"
    assert result["embedding_provider"] == "test-embedder"
    assert result["embedding_model"] == "model-x"
    assert result["reranker_provider"] == "test-reranker"
    assert result["reranker_model"] == "ranker-y"
    assert result["quality_gate"] == {
        "min_recall_at_k": 0.95, "min_mrr": 0.85, "min_ndcg_at_k": 0.88
    }


def test_rag_config_defaults_to_ivfflat_and_default_environment(monkeypatch):
    cfg = SimpleNamespace(dimensions=128, use_hnsw=False)
    monkeypatch.setattr(routes.PgVectorConfig, "from_env", lambda: cfg)
    for name in (
        "RAG_EMBEDDING_PROVIDER", "RAG_EMBEDDING_MODEL",
        "RAG_RERANKER_PROVIDER", "RAG_RERANKER_MODEL",
        "RAG_GATE_MIN_RECALL", "RAG_GATE_MIN_MRR", "RAG_GATE_MIN_NDCG",
    ):
        monkeypatch.delenv(name, raising=False)

    result = routes.rag_config()
    assert result["vector_index"] == "ivfflat"
    assert result["embedding_provider"] == "hash"
    assert result["reranker_provider"] == "lexical"
    assert result["quality_gate"] == {
        "min_recall_at_k": 0.90, "min_mrr": 0.80, "min_ndcg_at_k": 0.80
    }


@pytest.mark.parametrize("payload", [
    {"query": "x"},
    {"query": "valid query", "top_k": 0},
    {"query": "valid query", "top_k": 51},
])
def test_search_request_rejects_invalid_query_or_top_k(payload):
    with pytest.raises(ValidationError):
        routes.RAGSearchRequest(**payload)


@pytest.mark.asyncio
async def test_rag_search_returns_retrieval_payload(monkeypatch):
    cfg = SimpleNamespace(dimensions=3)
    monkeypatch.setattr(routes.PgVectorConfig, "from_env", lambda: cfg)
    monkeypatch.setattr(routes, "PgVectorHybridRepository", lambda _cfg: object())
    monkeypatch.setattr(routes, "create_embedding_provider", lambda **_kwargs: object())
    monkeypatch.setattr(routes, "create_reranker", lambda: "reranker")

    expected = SimpleNamespace(
        query="rough idle",
        rewritten_queries=["rough idle", "engine idle vibration"],
        diagnostics={"candidate_count": 2},
        hits=[SimpleNamespace(document_id="d1", score=0.9)],
    )

    class FakeRetriever:
        def __init__(self, repo, provider, reranker=None):
            assert reranker == "reranker"
        async def retrieve(self, query, filters, top_k):
            assert (query, filters, top_k) == ("rough idle", {"make": "Mercedes"}, 2)
            return expected

    monkeypatch.setattr(routes, "DiagnosticRAGRetriever", FakeRetriever)
    result = await routes.rag_search(routes.RAGSearchRequest(
        query="rough idle", filters={"make": "Mercedes"}, top_k=2
    ))
    assert result == {
        "query": "rough idle",
        "rewritten_queries": ["rough idle", "engine idle vibration"],
        "diagnostics": {"candidate_count": 2},
        "hits": [{"document_id": "d1", "score": 0.9}],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_site", ["repository", "provider", "retriever", "retrieve"])
async def test_rag_search_maps_backend_failures_to_503(monkeypatch, failure_site):
    cfg = SimpleNamespace(dimensions=8)
    monkeypatch.setattr(routes.PgVectorConfig, "from_env", lambda: cfg)

    if failure_site == "repository":
        monkeypatch.setattr(routes, "PgVectorHybridRepository", lambda _cfg: (_ for _ in ()).throw(OSError("db unavailable")))
    else:
        monkeypatch.setattr(routes, "PgVectorHybridRepository", lambda _cfg: object())

    if failure_site == "provider":
        monkeypatch.setattr(routes, "create_embedding_provider", lambda **_kwargs: (_ for _ in ()).throw(ValueError("bad provider")))
    else:
        monkeypatch.setattr(routes, "create_embedding_provider", lambda **_kwargs: object())

    class FakeRetriever:
        def __init__(self, *_args, **_kwargs):
            if failure_site == "retriever":
                raise RuntimeError("retriever init failed")
        async def retrieve(self, *_args):
            if failure_site == "retrieve":
                raise TimeoutError("retrieval timed out")
            return SimpleNamespace(query="test", rewritten_queries=[], diagnostics={}, hits=[])

    monkeypatch.setattr(routes, "DiagnosticRAGRetriever", FakeRetriever)
    monkeypatch.setattr(routes, "create_reranker", lambda: object())
    with pytest.raises(HTTPException) as error:
        await routes.rag_search(routes.RAGSearchRequest(query="test query"))
    assert error.value.status_code == 503
    assert "RAG backend unavailable" in error.value.detail
    assert type(error.value.__cause__).__name__ == {
        "repository": "OSError", "provider": "ValueError",
        "retriever": "RuntimeError", "retrieve": "TimeoutError",
    }[failure_site]
