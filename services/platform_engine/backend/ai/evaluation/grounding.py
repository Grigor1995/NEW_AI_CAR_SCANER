from __future__ import annotations
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class GroundingResult:
    grounded: bool
    supported_claims: int
    unsupported_claims: int
    citation_coverage: float
    reasons: list[str]

class GroundingEvaluator:
    """Heuristic evaluation gate for generated diagnostic explanations."""
    def evaluate(self, text: str, allowed_sources: list[str], required_terms: set[str] | None = None) -> GroundingResult:
        lower = text.lower()
        reasons: list[str] = []
        required_terms = required_terms or set()
        missing = [term for term in required_terms if term.lower() not in lower]
        if missing:
            reasons.append(f"Missing required terms: {', '.join(sorted(missing))}")
        explicit_confirmations = re.findall(r"confirmed\s+([a-z0-9_ -]+)", lower)
        forbidden_confirmations = [x for x in explicit_confirmations if not any(x.strip() in s.lower() for s in allowed_sources)]
        unsupported = len(forbidden_confirmations)
        coverage = 0.0 if not allowed_sources else min(1.0, len([s for s in allowed_sources if s.lower() in lower]) / len(allowed_sources))
        if unsupported:
            reasons.append("Generated text contains confirmation language that is not traceable to supplied sources.")
        grounded = not missing and unsupported == 0
        return GroundingResult(grounded, max(0, len(required_terms) - len(missing)), unsupported, coverage, reasons)
