from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Sequence

from .store import RetrievalHit


@dataclass(frozen=True)
class RerankedHit:
    hit: RetrievalHit
    rerank_score: float


class LexicalReranker:
    """Deterministic reranker for offline/dev use."""

    def rerank(self, query: str, hits: Sequence[RetrievalHit], top_k: int = 5) -> list[RerankedHit]:
        q = [t for t in re.findall(r"[a-zA-Z0-9_]+", query.lower()) if len(t) > 1]
        qset = set(q)
        out: list[RerankedHit] = []
        for h in hits:
            text = f"{h.title} {h.text}".lower()
            matched = sum(1 for t in qset if t in text)
            phrase_bonus = 0.15 if query.lower() in text else 0.0
            score = min(1.0, 0.65 * h.score + 0.35 * (matched / max(1, len(qset))) + phrase_bonus)
            out.append(RerankedHit(h, score))
        return sorted(out, key=lambda x: x.rerank_score, reverse=True)[:top_k]


class CrossEncoderReranker:
    """Optional local cross-encoder reranker.

    Model loading is lazy; production deployments can select a domain-tuned
    cross-encoder without forcing the base test environment to download it.
    """

    def __init__(self, model_name: str | None = None, device: str | None = None, batch_size: int = 16):
        self.model_name = model_name or os.getenv("RAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        self.device = device or os.getenv("RAG_RERANKER_DEVICE", "cpu")
        self.batch_size = batch_size
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            # PyTorch/sentence-transformers can trigger a native DLL access
            # violation on some Windows environments. Keep the optional
            # cross-encoder opt-in there; the deterministic lexical path remains
            # the safe default. Set RAG_RERANKER_ALLOW_NATIVE=1 to enable it.
            if os.name == "nt" and os.getenv("RAG_RERANKER_ALLOW_NATIVE", "").lower() not in {"1", "true", "yes"}:
                raise RuntimeError(
                    "sentence-transformers is not installed or unavailable. Install backend/requirements-ai.txt "
                    "or use the lexical reranker."
                )
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name, device=self.device)
            except Exception as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed or unavailable. Install backend/requirements-ai.txt "
                    "or use the lexical reranker."
                ) from exc
        return self._model

    def rerank(self, query: str, hits: Sequence[RetrievalHit], top_k: int = 5) -> list[RerankedHit]:
        if not hits:
            return []
        model = self._load()
        pairs = [[query, f"{h.title}\n{h.text}"] for h in hits]
        scores = model.predict(pairs, batch_size=self.batch_size, show_progress_bar=False)
        scored = [RerankedHit(hit=h, rerank_score=float(score)) for h, score in zip(hits, scores)]
        scored.sort(key=lambda x: x.rerank_score, reverse=True)
        return scored[:top_k]


def create_reranker(name: str | None = None) -> Any:
    provider = (name or os.getenv("RAG_RERANKER_PROVIDER", "lexical")).lower()
    if provider in {"lexical", "baseline"}:
        return LexicalReranker()
    if provider in {"cross_encoder", "cross-encoder", "ce"}:
        return CrossEncoderReranker()
    raise ValueError(f"unsupported reranker provider: {provider}")
