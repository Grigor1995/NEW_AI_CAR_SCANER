from types import SimpleNamespace

import pytest

from ai.rag.hybrid import RetrievedChunk
from ai.rag.retrieval import DiagnosticRAGRetriever


def make_chunk(chunk_id, content, score, title="Guide"):
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-" + chunk_id,
        content=content,
        metadata={"title": title},
        vector_score=score,
        fused_score=score,
    )


class FakeEmbeddingProvider:
    async def embed(self, texts):
        return [[float(len(text))] for text in texts]


class FakeRepository:
    def __init__(self):
        self.calls = []

    def hybrid_search(self, embedding, query, filters=None, top_k=5):
        self.calls.append((embedding, query, filters, top_k))
        if query == "LPG misfire":
            return [make_chunk("a", "LPG injector balance", 0.7), make_chunk("shared", "cylinder misfire", 0.4)], {"source": "first"}
        return [make_chunk("shared", "cylinder misfire", 0.9), make_chunk("b", "fuel pressure under load", 0.6)], {"source": "expanded"}


class MatchingReranker:
    def rerank(self, query, hits, top_k=5):
        assert query == "LPG misfire"
        assert hits
        # Ensure a hit returned by the reranker is mapped back to its source chunk.
        selected = next(hit for hit in hits if hit.text == "cylinder misfire")
        return [SimpleNamespace(hit=SimpleNamespace(text=selected.text, title=selected.title), rerank_score=0.99)]


class IncompatibleReranker:
    def rerank(self, query, hits, top_k=5):
        return [SimpleNamespace(hit=SimpleNamespace(text="not in candidate list", title="unknown"), rerank_score=1.0)]


@pytest.mark.asyncio
async def test_retriever_rewrites_deduplicates_filters_and_maps_reranker_result():
    repository = FakeRepository()
    retriever = DiagnosticRAGRetriever(
        repository,
        FakeEmbeddingProvider(),
        reranker=MatchingReranker(),
        candidate_k_multiplier=2,
    )

    response = await retriever.retrieve("LPG misfire", filters={"make": "Mercedes"}, top_k=1)

    assert response.query == "LPG misfire"
    assert len(response.rewritten_queries) == 2
    assert len(repository.calls) == 2
    assert all(call[2] == {"make": "Mercedes"} for call in repository.calls)
    assert all(call[3] == 2 for call in repository.calls)
    assert response.diagnostics["candidate_count"] == 2
    assert response.diagnostics["result_count"] == 1
    assert response.diagnostics["reranker"] == "MatchingReranker"
    assert response.hits[0].chunk_id == "shared"
    assert response.hits[0].rank == 1
    assert response.hits[0].fused_score == 0.99


@pytest.mark.asyncio
async def test_retriever_uses_best_duplicate_score_before_reranking():
    repository = FakeRepository()
    retriever = DiagnosticRAGRetriever(repository, FakeEmbeddingProvider(), reranker=IncompatibleReranker())
    response = await retriever.retrieve("LPG misfire", top_k=3)

    shared = next(hit for hit in response.hits if hit.chunk_id == "shared")
    assert shared.fused_score == 0.9
    # A custom reranker with incompatible output must not erase usable retrieval results.
    assert [hit.chunk_id for hit in response.hits] == ["shared", "a", "b"]
    assert response.diagnostics["candidate_count"] == 3


@pytest.mark.asyncio
async def test_retriever_handles_no_results():
    class EmptyRepository:
        def hybrid_search(self, embedding, query, filters=None, top_k=5):
            return [], {"source": "empty"}

    retriever = DiagnosticRAGRetriever(EmptyRepository(), FakeEmbeddingProvider())
    response = await retriever.retrieve("battery", top_k=4)
    assert response.hits == []
    assert response.diagnostics["candidate_count"] == 0
    assert response.diagnostics["result_count"] == 0


def test_candidate_multiplier_is_clamped_to_at_least_one():
    retriever = DiagnosticRAGRetriever(FakeRepository(), FakeEmbeddingProvider(), candidate_k_multiplier=0)
    assert retriever.candidate_k_multiplier == 1
