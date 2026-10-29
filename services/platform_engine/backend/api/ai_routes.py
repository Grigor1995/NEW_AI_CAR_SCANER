from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from api.state import sessions
from ai.llm.factory import build_llm_provider
from ai.rag.store import HybridKnowledgeStore, KnowledgeDocument
from ai.reasoning.pipeline import DiagnosticIntelligencePipeline

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
knowledge_store = HybridKnowledgeStore()
pipeline = DiagnosticIntelligencePipeline(knowledge_store)


class KnowledgeRequest(BaseModel):
    document_id: str
    title: str
    text: str
    metadata: dict = {}


class SearchRequest(BaseModel):
    query: str
    filters: dict = {}
    top_k: int = 5


@router.post("/knowledge")
def add_knowledge(request: KnowledgeRequest):
    knowledge_store.add(KnowledgeDocument(request.document_id, request.title, request.text, request.metadata))
    return {"status": "indexed", "document_id": request.document_id}


@router.post("/knowledge/search")
def search_knowledge(request: SearchRequest):
    hits = knowledge_store.search(request.query, request.filters, request.top_k)
    reranked = pipeline.reranker.rerank(request.query, hits, request.top_k)
    return [{"document_id": x.hit.document_id, "title": x.hit.title, "text": x.hit.text, "score": x.rerank_score, "metadata": x.hit.metadata} for x in reranked]


@router.post("/sessions/{session_id}/context")
def build_ai_context(session_id: str, language: str = Query("en")):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    result = pipeline.run(sessions[session_id], language=language)
    return {"session": result.session, "retrieved": result.retrieved, "prompt": result.llm_prompt}


@router.get("/provider")
def provider_info():
    provider = build_llm_provider()
    info = {
        "provider": provider.__class__.__name__,
        "model": getattr(getattr(provider, "config", None), "model", "unknown"),
        "available": False,
    }
    availability = getattr(provider, "availability", None)
    if callable(availability):
        info.update(availability())
    return info
