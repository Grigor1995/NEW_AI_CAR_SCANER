from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expected_document_ids: frozenset[str]
    required_terms: tuple[str, ...] = ()
    graded_relevance: dict[str, float] | None = None


@dataclass(frozen=True)
class RetrievalEvaluation:
    passed: bool
    recall_at_k: float
    mrr: float
    ndcg_at_k: float
    relevant_found: int
    expected_relevant: int
    missing_terms: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalQualityGate:
    min_recall_at_k: float = 1.0
    min_mrr: float = 1.0
    min_ndcg_at_k: float = 1.0

    def validate(self, result: RetrievalEvaluation) -> bool:
        return (
            result.recall_at_k >= self.min_recall_at_k
            and result.mrr >= self.min_mrr
            and result.ndcg_at_k >= self.min_ndcg_at_k
            and not result.missing_terms
        )


def reciprocal_rank(expected: set[str], ranked_ids: Sequence[str]) -> float:
    for index, document_id in enumerate(ranked_ids, start=1):
        if document_id in expected:
            return 1.0 / index
    return 0.0


def ndcg_at_k(relevance: dict[str, float], ranked_ids: Sequence[str], k: int) -> float:
    def dcg(values: Sequence[float]) -> float:
        return sum((2.0**score - 1.0) / math.log2(i + 2.0) for i, score in enumerate(values))

    predicted = [float(relevance.get(doc_id, 0.0)) for doc_id in ranked_ids[:k]]
    ideal = sorted((float(score) for score in relevance.values()), reverse=True)[:k]
    ideal_dcg = dcg(ideal)
    return 0.0 if ideal_dcg == 0 else dcg(predicted) / ideal_dcg


class RetrievalEvaluator:
    def __init__(self, quality_gate: RetrievalQualityGate | None = None):
        self.quality_gate = quality_gate or RetrievalQualityGate()

    def evaluate(self, case: RetrievalCase, document_ids: Iterable[str], texts: Iterable[str]) -> RetrievalEvaluation:
        ids = list(document_ids)
        text = " ".join(texts).lower()
        found = len(case.expected_document_ids.intersection(ids))
        recall = found / max(1, len(case.expected_document_ids))
        mrr = reciprocal_rank(set(case.expected_document_ids), ids)
        relevance = case.graded_relevance or {doc_id: 1.0 for doc_id in case.expected_document_ids}
        ndcg = ndcg_at_k(relevance, ids, len(ids))
        missing = tuple(term for term in case.required_terms if term.lower() not in text)
        result = RetrievalEvaluation(
            passed=False,
            recall_at_k=recall,
            mrr=mrr,
            ndcg_at_k=ndcg,
            relevant_found=found,
            expected_relevant=len(case.expected_document_ids),
            missing_terms=missing,
        )
        return RetrievalEvaluation(**{**result.__dict__, "passed": self.quality_gate.validate(result)})
