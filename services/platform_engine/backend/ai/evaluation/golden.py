from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


def _normalize_claim_text(value: str) -> str:
    """Normalize token-like and natural-language claims for robust matching."""
    return re.sub(r"\s+", " ", re.sub(r"[\W_]+", " ", value.casefold())).strip()

@dataclass(frozen=True)
class GoldenCase:
    case_id: str
    expected_categories: set[str]
    forbidden_claims: set[str]

    @classmethod
    def load(cls, path: str | Path) -> "GoldenCase":
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        return cls(
            raw["case_id"],
            set(raw.get("expected_categories", [])),
            set(raw.get("forbidden_claims", [])),
        )


@dataclass(frozen=True)
class GoldenResult:
    category_coverage: float
    forbidden_claims_present: list[str]
    passed: bool


class GoldenCaseEvaluator:
    def evaluate(self, categories: set[str], generated_text: str, case: GoldenCase) -> GoldenResult:
        coverage = len(categories & case.expected_categories) / max(1, len(case.expected_categories))
        normalized_text = f" {_normalize_claim_text(generated_text)} "
        forbidden: list[str] = []
        for claim in case.forbidden_claims:
            normalized_claim = _normalize_claim_text(claim)
            if normalized_claim and f" {normalized_claim} " in normalized_text:
                forbidden.append(claim)
        return GoldenResult(coverage, forbidden, coverage >= 0.5 and not forbidden)
