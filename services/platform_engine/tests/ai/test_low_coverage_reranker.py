from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import Mock

import pytest

from ai.rag.reranker import CrossEncoderReranker, LexicalReranker, create_reranker
from ai.rag.store import RetrievalHit


def _hit(doc_id, title, text, score=0.5, metadata=None):
    return RetrievalHit(doc_id, title, text, score, metadata or {})


def test_lexical_reranker_phrase_match_order_cap_and_top_k():
    phrase = _hit("phrase", "P0302", "misfire on LPG load", 0.3, {"type": "manual"})
    weak = _hit("weak", "brakes", "replace worn pads", 0.8)
    reranker = LexicalReranker()

    results = reranker.rerank("P0302 misfire", [weak, phrase], top_k=1)

    assert len(results) == 1
    assert results[0].hit.document_id == "phrase"
    assert 0 <= results[0].rerank_score <= 1
    assert results[0].hit.metadata == {"type": "manual"}
    assert reranker.rerank("P0302 misfire", [phrase], top_k=0) == []


def test_lexical_reranker_handles_no_query_tokens_and_empty_hits():
    reranker = LexicalReranker()
    assert reranker.rerank("x a _", [], top_k=3) == []
    results = reranker.rerank("x a", [_hit("one", "Generic", "document", 0.0)], top_k=2)
    assert len(results) == 1
    assert results[0].rerank_score >= 0


def test_cross_encoder_is_lazy_predicts_sorts_and_caches_model(monkeypatch):
    # The project intentionally requires an explicit opt-in for native model
    # loading on Windows; this test substitutes a fake model and performs no
    # native load, so authorize the code path explicitly.
    monkeypatch.setenv("RAG_RERANKER_ALLOW_NATIVE", "1")
    model = Mock()
    model.predict.return_value = [0.1, 0.9]
    module = ModuleType("sentence_transformers")
    constructor = Mock(return_value=model)
    module.CrossEncoder = constructor
    monkeypatch.setitem(sys.modules, "sentence_transformers", module)

    reranker = CrossEncoderReranker(model_name="local/test", device="cpu", batch_size=4)
    hits = [_hit("a", "A", "first"), _hit("b", "B", "second")]
    assert reranker._model is None

    results = reranker.rerank("query", hits, top_k=2)

    assert [item.hit.document_id for item in results] == ["b", "a"]
    constructor.assert_called_once_with("local/test", device="cpu")
    model.predict.assert_called_once_with(
        [["query", "A\nfirst"], ["query", "B\nsecond"]],
        batch_size=4,
        show_progress_bar=False,
    )
    reranker._load()
    constructor.assert_called_once()


def test_cross_encoder_empty_hits_do_not_load_optional_dependency():
    reranker = CrossEncoderReranker()
    assert reranker.rerank("query", [], top_k=5) == []
    assert reranker._model is None


def test_cross_encoder_import_failure_is_reported_as_runtime_error(monkeypatch):
    monkeypatch.setitem(sys.modules, "sentence_transformers", None)
    reranker = CrossEncoderReranker(model_name="unavailable")
    with pytest.raises(RuntimeError, match="sentence-transformers is not installed"):
        reranker.rerank("query", [_hit("a", "title", "text")])


def test_reranker_factory_aliases_and_unsupported_provider(monkeypatch):
    monkeypatch.delenv("RAG_RERANKER_PROVIDER", raising=False)
    assert isinstance(create_reranker(), LexicalReranker)
    assert isinstance(create_reranker("baseline"), LexicalReranker)
    assert isinstance(create_reranker("cross-encoder"), CrossEncoderReranker)
    assert isinstance(create_reranker("ce"), CrossEncoderReranker)
    with pytest.raises(ValueError, match="unsupported reranker provider"):
        create_reranker("unknown")
