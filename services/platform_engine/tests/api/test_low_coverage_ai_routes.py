from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import api.ai_routes as routes


def test_add_knowledge_indexes_document(monkeypatch):
    observed = []
    monkeypatch.setattr(routes.knowledge_store, "add", observed.append)
    response = routes.add_knowledge(routes.KnowledgeRequest(
        document_id="doc-1", title="Workshop", text="P0302 misfire", metadata={"make": "Mercedes"}
    ))
    assert response == {"status": "indexed", "document_id": "doc-1"}
    assert observed[0].document_id == "doc-1"
    assert observed[0].title == "Workshop"
    assert observed[0].metadata == {"make": "Mercedes"}


def test_search_knowledge_returns_reranked_hits(monkeypatch):
    hit = SimpleNamespace(document_id="doc-1", title="Misfire guide", text="Inspect ignition", metadata={"engine": "M272"})
    ranked = [SimpleNamespace(hit=hit, rerank_score=0.93)]
    monkeypatch.setattr(routes.knowledge_store, "search", lambda query, filters, top_k: [hit])
    monkeypatch.setattr(routes.pipeline.reranker, "rerank", lambda query, hits, top_k: ranked)

    result = routes.search_knowledge(routes.SearchRequest(
        query="misfire", filters={"engine": "M272"}, top_k=3
    ))
    assert result == [{
        "document_id": "doc-1", "title": "Misfire guide", "text": "Inspect ignition",
        "score": 0.93, "metadata": {"engine": "M272"},
    }]


def test_search_knowledge_returns_empty_list_when_no_hits(monkeypatch):
    monkeypatch.setattr(routes.knowledge_store, "search", lambda *_args: [])
    monkeypatch.setattr(routes.pipeline.reranker, "rerank", lambda _query, hits, _top_k: hits)
    assert routes.search_knowledge(routes.SearchRequest(query="not found")) == []


def test_build_ai_context_rejects_unknown_session(monkeypatch):
    monkeypatch.setattr(routes, "sessions", {})
    with pytest.raises(HTTPException) as error:
        routes.build_ai_context("missing", language="hy")
    assert error.value.status_code == 404
    assert error.value.detail == "Session not found"


def test_build_ai_context_runs_pipeline_with_requested_language(monkeypatch):
    session = SimpleNamespace(session_id="session-1")
    expected = SimpleNamespace(session=session, retrieved=[{"id": "doc"}], llm_prompt="prompt")
    calls = []
    monkeypatch.setattr(routes, "sessions", {"session-1": session})
    monkeypatch.setattr(routes.pipeline, "run", lambda value, language: calls.append((value, language)) or expected)

    result = routes.build_ai_context("session-1", language="ru")
    assert calls == [(session, "ru")]
    assert result == {"session": session, "retrieved": [{"id": "doc"}], "prompt": "prompt"}


def test_provider_info_includes_config_and_availability(monkeypatch):
    provider = SimpleNamespace(
        config=SimpleNamespace(model="demo-model"),
        availability=lambda: {"available": True, "endpoint": "http://local"},
    )
    monkeypatch.setattr(routes, "build_llm_provider", lambda: provider)
    assert routes.provider_info() == {
        "provider": "SimpleNamespace", "model": "demo-model",
        "available": True, "endpoint": "http://local",
    }


def test_provider_info_handles_provider_without_config_or_availability(monkeypatch):
    class MinimalProvider:
        pass
    monkeypatch.setattr(routes, "build_llm_provider", MinimalProvider)
    result = routes.provider_info()
    assert result["provider"] == "MinimalProvider"
    assert result["model"] == "unknown"
    assert result["available"] is False


def test_provider_info_ignores_non_callable_availability(monkeypatch):
    provider = SimpleNamespace(config=None, availability={"available": True})
    monkeypatch.setattr(routes, "build_llm_provider", lambda: provider)
    assert routes.provider_info()["available"] is False
