from __future__ import annotations

import hashlib
import math
import os
import re
from typing import Any

from ai.interfaces import EmbeddingProvider


class HashEmbeddingProvider(EmbeddingProvider):
    """Offline deterministic embedding fallback.

    Python's built-in hash() is intentionally randomized between processes, so
    this implementation uses SHA-256 buckets to keep embeddings reproducible.
    """

    def __init__(self, dimensions: int = 256):
        if dimensions < 8:
            raise ValueError("dimensions must be >= 8")
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dimensions
            tokens = re.findall(r"[a-zA-Z0-9_]+", text.lower())
            for token in tokens:
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                idx = int.from_bytes(digest[:8], "big") % self.dimensions
                vec[idx] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            vectors.append([v / norm for v in vec])
        return vectors


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Local sentence-transformers embedding provider.

    The dependency and model are loaded lazily so the base project stays
    installable without ML packages or model downloads.
    """

    def __init__(self, model_name: str | None = None, device: str | None = None, normalize: bool = True):
        self.model_name = model_name or os.getenv("RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        self.device = device or os.getenv("RAG_EMBEDDING_DEVICE", "cpu")
        self.normalize = normalize
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError(
                    "sentence-transformers is not installed. Install backend/requirements-ai.txt "
                    "or use RAG_EMBEDDING_PROVIDER=hash."
                ) from exc
            self._model = SentenceTransformer(self.model_name, device=self.device)
        return self._model

    @property
    def dimensions(self) -> int:
        model = self._load()
        return int(model.get_sentence_embedding_dimension())

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        encoded = model.encode(
            texts,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return encoded.tolist()


class FastEmbedEmbeddingProvider(EmbeddingProvider):
    """Optional ONNX/CPU embedding provider via fastembed."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or os.getenv("RAG_FASTEMBED_MODEL", "BAAI/bge-small-en-v1.5")
        self._model: Any | None = None

    def _load(self) -> Any:
        if self._model is None:
            try:
                from fastembed import TextEmbedding
            except ImportError as exc:
                raise RuntimeError(
                    "fastembed is not installed. Install backend/requirements-ai.txt "
                    "or use another embedding provider."
                ) from exc
            self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        model = self._load()
        return [vector.tolist() if hasattr(vector, "tolist") else list(vector) for vector in model.embed(texts)]


def create_embedding_provider(provider: str | None = None, dimensions: int = 256) -> EmbeddingProvider:
    name = (provider or os.getenv("RAG_EMBEDDING_PROVIDER", "hash")).lower()
    if name == "hash":
        return HashEmbeddingProvider(dimensions)
    if name in {"sentence_transformers", "sentence-transformers", "st"}:
        return SentenceTransformerEmbeddingProvider()
    if name == "fastembed":
        return FastEmbedEmbeddingProvider()
    raise ValueError(f"unsupported embedding provider: {name}")
