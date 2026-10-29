from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .evaluation import RetrievalCase, RetrievalEvaluator, RetrievalQualityGate


@dataclass(frozen=True)
class CorpusQualitySummary:
    cases: int
    passed: int
    failed: int
    mean_recall_at_k: float
    mean_mrr: float
    mean_ndcg_at_k: float
    gate_passed: bool


class RetrievalQualityRunner:
    """Runs a deterministic retrieval evaluation set and applies release gates."""

    def __init__(self, gate: RetrievalQualityGate | None = None):
        self.evaluator = RetrievalEvaluator(gate)
        self.gate = gate or RetrievalQualityGate()

    def evaluate_cases(self, cases: Iterable[RetrievalCase], ranked_ids: Sequence[Sequence[str]], texts: Sequence[Sequence[str]]) -> CorpusQualitySummary:
        cases_list = list(cases)
        if len(cases_list) != len(ranked_ids) or len(cases_list) != len(texts):
            raise ValueError("cases, ranked_ids, and texts must have equal length")
        results = [
            self.evaluator.evaluate(case, ids, body)
            for case, ids, body in zip(cases_list, ranked_ids, texts)
        ]
        count = len(results)
        passed = sum(1 for result in results if result.passed)
        return CorpusQualitySummary(
            cases=count,
            passed=passed,
            failed=count - passed,
            mean_recall_at_k=sum(r.recall_at_k for r in results) / max(1, count),
            mean_mrr=sum(r.mrr for r in results) / max(1, count),
            mean_ndcg_at_k=sum(r.ndcg_at_k for r in results) / max(1, count),
            gate_passed=passed == count,
        )
