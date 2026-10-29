from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable

@dataclass(frozen=True)
class KnowledgeDocument:
    document_id: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)

@dataclass(frozen=True)
class RetrievalHit:
    document_id: str
    title: str
    text: str
    score: float
    metadata: dict

class HybridKnowledgeStore:
    """Small local RAG foundation. Uses lexical scoring now; embedding/reranker adapters can be added later."""
    def __init__(self, documents: Iterable[KnowledgeDocument] = ()):
        self.documents: dict[str, KnowledgeDocument] = {d.document_id: d for d in documents}

    def add(self, document: KnowledgeDocument) -> None:
        self.documents[document.document_id] = document

    def search(self, query: str, filters: dict | None = None, top_k: int = 5) -> list[RetrievalHit]:
        filters = filters or {}
        tokens = {t.lower() for t in query.split() if len(t) > 1}
        hits: list[RetrievalHit] = []
        for d in self.documents.values():
            if any(filters.get(k) is not None and d.metadata.get(k) != v for k, v in filters.items()):
                continue
            hay = f"{d.title} {d.text}".lower()
            matched = sum(1 for t in tokens if t in hay)
            if matched:
                score = matched / max(1, len(tokens))
                hits.append(RetrievalHit(d.document_id, d.title, d.text, score, d.metadata))
        return sorted(hits, key=lambda x: x.score, reverse=True)[:top_k]
