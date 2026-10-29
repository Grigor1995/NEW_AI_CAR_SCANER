from __future__ import annotations
from dataclasses import dataclass
from ai.reasoning.engine import DiagnosticIntelligenceEngine
from ai.rag.store import HybridKnowledgeStore
from ai.rag.reranker import LexicalReranker
from ai.llm.interfaces_guard import SafePromptContext
from diagnostic.models import DiagnosticSession

@dataclass(frozen=True)
class DiagnosticIntelligenceResult:
    session: DiagnosticSession
    retrieved: list[dict]
    llm_prompt: str

class DiagnosticIntelligencePipeline:
    """Deterministic engine + retrieval + safe LLM context assembly."""
    def __init__(self, store: HybridKnowledgeStore | None = None):
        self.engine = DiagnosticIntelligenceEngine()
        self.store = store or HybridKnowledgeStore()
        self.reranker = LexicalReranker()

    def run(self, session: DiagnosticSession, query: str | None = None, language: str = "en") -> DiagnosticIntelligenceResult:
        session = self.engine.analyze(session)
        query = query or " ".join(e.fact for e in session.evidence)
        hits = self.reranker.rerank(query, self.store.search(query, top_k=10), top_k=5)
        retrieved = [{"document_id": x.hit.document_id, "title": x.hit.title, "text": x.hit.text, "score": x.rerank_score, "metadata": x.hit.metadata} for x in hits]
        safe = SafePromptContext.from_session(session, retrieved, language)
        prompt = safe.to_prompt()
        return DiagnosticIntelligenceResult(session, retrieved, prompt)
