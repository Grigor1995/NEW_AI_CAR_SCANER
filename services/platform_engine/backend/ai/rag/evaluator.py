from __future__ import annotations
from dataclasses import dataclass
from .store import HybridKnowledgeStore

@dataclass(frozen=True)
class RagEvalCase:
    query: str
    expected_document_ids: set[str]

@dataclass(frozen=True)
class RagEvalResult:
    hit: bool
    retrieved_ids: list[str]

class RagEvaluator:
    def evaluate(self, store: HybridKnowledgeStore, case: RagEvalCase, top_k: int = 5) -> RagEvalResult:
        hits = store.search(case.query, top_k=top_k)
        ids = [h.document_id for h in hits]
        return RagEvalResult(bool(case.expected_document_ids.intersection(ids)), ids)
