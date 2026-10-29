from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ai.embeddings import create_embedding_provider
from ai.rag.pgvector_hybrid import PgVectorConfig, PgVectorHybridRepository
from ai.rag.retrieval import DiagnosticRAGRetriever
from ai.rag.reranker import create_reranker

router = APIRouter(prefix="/api/v1/rag", tags=["rag-retrieval"])


class RAGSearchRequest(BaseModel):
    query: str = Field(min_length=2)
    filters: dict = Field(default_factory=dict)
    top_k: int = Field(default=5, ge=1, le=50)


@router.get("/config")
def rag_config():
    cfg = PgVectorConfig.from_env()
    return {
        "dimensions": cfg.dimensions,
        "vector_index": "hnsw" if cfg.use_hnsw else "ivfflat",
        "embedding_provider": os.getenv("RAG_EMBEDDING_PROVIDER", "hash"),
        "embedding_model": os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
        "reranker_provider": os.getenv("RAG_RERANKER_PROVIDER", "lexical"),
        "reranker_model": os.getenv("RAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        "quality_gate": {
            "min_recall_at_k": float(os.getenv("RAG_GATE_MIN_RECALL", "0.90")),
            "min_mrr": float(os.getenv("RAG_GATE_MIN_MRR", "0.80")),
            "min_ndcg_at_k": float(os.getenv("RAG_GATE_MIN_NDCG", "0.80")),
        },
    }


@router.post("/search")
async def rag_search(request: RAGSearchRequest):
    cfg = PgVectorConfig.from_env()
    try:
        repo = PgVectorHybridRepository(cfg)
        provider = create_embedding_provider(dimensions=cfg.dimensions)
        retriever = DiagnosticRAGRetriever(repo, provider, reranker=create_reranker())
        result = await retriever.retrieve(request.query, request.filters, request.top_k)
        return {
            "query": result.query,
            "rewritten_queries": result.rewritten_queries,
            "diagnostics": result.diagnostics,
            "hits": [h.__dict__ for h in result.hits],
        }
    except Exception as exc:
        raise HTTPException(503, f"RAG backend unavailable: {type(exc).__name__}: {exc}") from exc
