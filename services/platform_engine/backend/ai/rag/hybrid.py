from __future__ import annotations

from dataclasses import dataclass
import re
from collections import Counter
from typing import Any, Sequence


TOKEN_RE = re.compile(r"[a-zA-Z0-9_\-\.]+")

@dataclass(frozen=True)
class RetrievedChunk:
    chunk_id: str
    document_id: str
    content: str
    metadata: dict[str, Any]
    vector_score: float = 0.0
    lexical_score: float = 0.0
    fused_score: float = 0.0
    rank: int = 0


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_RE.findall(text) if len(t) > 1]


class QueryRewriter:
    """Deterministic query expansion for automotive diagnostic terminology.

    This is deliberately transparent: it adds aliases/canonical terms without
    inventing vehicle-specific facts.
    """
    ALIASES = {
        "misfire": ["misfire", "combustion", "cylinder"],
        "shaking": ["rough running", "rough idle", "vibration"],
        "lpg": ["LPG", "autogas", "gas injection", "gas fuel"],
        "maf": ["MAF", "mass air flow", "air mass"],
        "o2": ["O2", "oxygen sensor", "lambda"],
        "trim": ["fuel trim", "STFT", "LTFT"],
    }

    def rewrite(self, query: str) -> list[str]:
        base = query.strip()
        terms = set(tokenize(base))
        expansions: list[str] = []
        for token, aliases in self.ALIASES.items():
            if token in terms or any(a.lower() in base.lower() for a in aliases):
                expansions.extend(aliases)
        expanded = " ".join(dict.fromkeys([base, *expansions]))
        return [base] if expanded == base else [base, expanded]


class HybridFusion:
    """Rank-fusion utility independent of a particular database/vector engine."""
    def __init__(self, vector_weight: float = 0.65, lexical_weight: float = 0.35):
        if vector_weight < 0 or lexical_weight < 0 or vector_weight + lexical_weight <= 0:
            raise ValueError("weights must be non-negative and not both zero")
        total = vector_weight + lexical_weight
        self.vector_weight = vector_weight / total
        self.lexical_weight = lexical_weight / total

    def fuse(self, vector_hits: Sequence[RetrievedChunk], lexical_hits: Sequence[RetrievedChunk], top_k: int = 5) -> list[RetrievedChunk]:
        by_key: dict[str, RetrievedChunk] = {}
        max_v = max((h.vector_score for h in vector_hits), default=1.0) or 1.0
        max_l = max((h.lexical_score for h in lexical_hits), default=1.0) or 1.0
        for h in vector_hits:
            by_key[h.chunk_id] = RetrievedChunk(**{**h.__dict__, "vector_score": h.vector_score / max_v})
        for h in lexical_hits:
            current = by_key.get(h.chunk_id)
            if current is None:
                current = RetrievedChunk(**{**h.__dict__, "lexical_score": h.lexical_score / max_l})
            else:
                current = RetrievedChunk(**{**current.__dict__, "lexical_score": h.lexical_score / max_l})
            by_key[h.chunk_id] = current
        ranked = []
        for h in by_key.values():
            fused = self.vector_weight * h.vector_score + self.lexical_weight * h.lexical_score
            ranked.append(RetrievedChunk(**{**h.__dict__, "fused_score": fused}))
        ranked.sort(key=lambda x: (x.fused_score, x.vector_score, x.lexical_score), reverse=True)
        return [RetrievedChunk(**{**h.__dict__, "rank": i + 1}) for i, h in enumerate(ranked[:top_k])]


def lexical_score(query: str, content: str) -> float:
    q = Counter(tokenize(query))
    d = Counter(tokenize(content))
    if not q or not d:
        return 0.0
    overlap = sum(min(freq, d.get(token, 0)) for token, freq in q.items())
    coverage = overlap / max(1, sum(q.values()))
    phrase = 0.25 if query.strip().lower() in content.lower() else 0.0
    return min(1.0, coverage + phrase)


def metadata_matches(metadata: dict[str, Any], filters: dict[str, Any] | None) -> bool:
    for key, expected in (filters or {}).items():
        if expected is None:
            continue
        actual = metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True
