from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .hybrid import QueryRewriter, RetrievedChunk
from .reranker import create_reranker
from .pgvector_hybrid import PgVectorHybridRepository

@dataclass(frozen=True)
class RetrievalResponse:
    query: str
    rewritten_queries: list[str]
    hits: list[RetrievedChunk]
    diagnostics: dict[str, Any]

class DiagnosticRAGRetriever:
    def __init__(self, repository: PgVectorHybridRepository, embedding_provider: Any, query_rewriter: QueryRewriter | None = None, reranker: Any | None = None, candidate_k_multiplier: int = 4):
        self.repository = repository
        self.embedding_provider = embedding_provider
        self.query_rewriter = query_rewriter or QueryRewriter()
        self.reranker = reranker or create_reranker()
        self.candidate_k_multiplier = max(1, candidate_k_multiplier)

    async def retrieve(self, query: str, filters: dict[str, Any] | None = None, top_k: int = 5) -> RetrievalResponse:
        queries = self.query_rewriter.rewrite(query)
        aggregate: dict[str, RetrievedChunk] = {}
        per_query = []
        for rewritten in queries:
            embedding = (await self.embedding_provider.embed([rewritten]))[0]
            hits, meta = self.repository.hybrid_search(embedding, rewritten, filters=filters, top_k=max(top_k, top_k * self.candidate_k_multiplier))
            per_query.append({"query": rewritten, **meta})
            for hit in hits:
                prior = aggregate.get(hit.chunk_id)
                if prior is None or hit.fused_score > prior.fused_score:
                    aggregate[hit.chunk_id] = hit
        candidates = sorted(aggregate.values(), key=lambda x: x.fused_score, reverse=True)[: max(top_k, top_k * self.candidate_k_multiplier)]
        rerank_hits = self.reranker.rerank(
            query,
            [type("RetrievalHitCompat", (), {"title": h.metadata.get("title", ""), "text": h.content, "score": h.fused_score})() for h in candidates],
            top_k=top_k,
        )
        ranked: list[RetrievedChunk] = []
        # Cross-reranker receives minimal RetrievalHit compatibility objects; match results by text.
        used: set[int] = set()
        for reranked in rerank_hits:
            for index, candidate in enumerate(candidates):
                if index in used:
                    continue
                if candidate.content == reranked.hit.text and candidate.metadata.get("title", "") == reranked.hit.title:
                    ranked.append(RetrievedChunk(**{**candidate.__dict__, "fused_score": reranked.rerank_score, "rank": len(ranked) + 1}))
                    used.add(index)
                    break
        # Defensive fallback if a custom reranker returned incompatible hits.
        if not ranked:
            ranked = [RetrievedChunk(**{**h.__dict__, "rank": i + 1}) for i, h in enumerate(candidates[:top_k])]
        return RetrievalResponse(query=query, rewritten_queries=queries, hits=ranked[:top_k], diagnostics={"queries": per_query, "candidate_count": len(candidates), "reranker": type(self.reranker).__name__, "result_count": min(len(ranked), top_k)})
