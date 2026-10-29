from __future__ import annotations

import asyncio
import json
from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from urllib.error import URLError

from backend.ai.llm import ollama
from backend.ai.rag import vector_store


class FakeHttpResponse:
    def __init__(self, body: bytes):
        self.body = body
        self.status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self): return self.body


def test_ollama_provider_posts_payload_and_maps_response(monkeypatch):
    captured = {}
    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeHttpResponse(b'{"response":"Check LPG pressure","done":true}')
    monkeypatch.setattr(ollama, "urlopen", fake_urlopen)
    provider = ollama.OllamaLLMProvider(
        ollama.OllamaConfig(base_url="http://localhost:11434/", model="test-model", timeout_s=7, temperature=0.25)
    )
    result = asyncio.run(provider.generate("diagnose", {"fuel": "LPG"}))
    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["timeout"] == 7
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["stream"] is False
    assert captured["payload"]["options"]["temperature"] == 0.25
    assert json.loads(captured["payload"]["prompt"]) == {"task": "diagnose", "context": {"fuel": "LPG"}}
    assert result.text == "Check LPG pressure"
    assert result.model == "test-model"
    assert result.provider == "ollama"
    assert result.raw["done"] is True


@pytest.mark.parametrize("failure", [URLError("offline"), TimeoutError("timed out")])
def test_ollama_provider_wraps_transport_failures(monkeypatch, failure):
    monkeypatch.setattr(ollama, "urlopen", Mock(side_effect=failure))
    provider = ollama.OllamaLLMProvider()
    with pytest.raises(RuntimeError, match="Ollama inference failed"):
        asyncio.run(provider.generate("prompt", {}))


def test_ollama_provider_wraps_invalid_json(monkeypatch):
    monkeypatch.setattr(ollama, "urlopen", lambda *args, **kwargs: FakeHttpResponse(b"not-json"))
    with pytest.raises(RuntimeError, match="Ollama inference failed"):
        asyncio.run(ollama.OllamaLLMProvider().generate("prompt", {}))


def test_ollama_provider_uses_empty_text_if_response_key_is_missing(monkeypatch):
    monkeypatch.setattr(ollama, "urlopen", lambda *args, **kwargs: FakeHttpResponse(b'{"model":"other"}'))
    result = asyncio.run(ollama.OllamaLLMProvider().generate("prompt", {}))
    assert result.text == ""


class FakeConnection:
    def __init__(self):
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return FakeResult()


class FakeResult:
    def mappings(self):
        return self
    def all(self):
        return [{
            "chunk_id": "chunk-1",
            "document_id": "doc-1",
            "content": "LPG misfire",
            "metadata": {"source": "manual"},
            "score": 0.91,
        }]


class FakeEngine:
    def __init__(self):
        self.connection = FakeConnection()
    @contextmanager
    def begin(self):
        yield self.connection


def test_pgvector_repository_schema_upsert_and_search_without_database(monkeypatch):
    engine = FakeEngine()
    monkeypatch.setattr(vector_store, "create_engine", Mock(return_value=engine))
    repository = vector_store.PgVectorKnowledgeRepository("postgresql://unused")
    repository.ensure_schema(dimensions=384)
    repository.upsert(
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
        "LPG misfire",
        {"source": "manual"},
        [0.1, 0.2, 0.3],
    )
    hits = repository.search([0.1, 0.2, 0.3], top_k=4)
    assert len(engine.connection.calls) == 4
    assert "CREATE EXTENSION IF NOT EXISTS vector" in engine.connection.calls[0][0]
    assert "vector(384)" in engine.connection.calls[1][0]
    assert engine.connection.calls[2][1]["metadata"] == '{"source": "manual"}'
    assert engine.connection.calls[2][1]["embedding"] == "[0.1,0.2,0.3]"
    assert engine.connection.calls[3][1]["top_k"] == 4
    assert hits == [vector_store.VectorHit("chunk-1", "doc-1", "LPG misfire", {"source": "manual"}, 0.91)]
