from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Sequence

from sqlalchemy import create_engine, text

from .hybrid import RetrievedChunk

@dataclass(frozen=True)
class PgVectorConfig:
    database_url: str
    dimensions: int = 256
    index_lists: int = 100
    hnsw_m: int = 16
    hnsw_ef_construction: int = 64
    use_hnsw: bool = True

    @classmethod
    def from_env(cls) -> "PgVectorConfig":
        return cls(
            database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://diagnostic:diagnostic@localhost:5432/diagnostic"),
            dimensions=int(os.getenv("RAG_EMBEDDING_DIMENSIONS", "256")),
            index_lists=int(os.getenv("RAG_IVFFLAT_LISTS", "100")),
            hnsw_m=int(os.getenv("RAG_HNSW_M", "16")),
            hnsw_ef_construction=int(os.getenv("RAG_HNSW_EF_CONSTRUCTION", "64")),
            use_hnsw=os.getenv("RAG_VECTOR_INDEX", "hnsw").lower() == "hnsw",
        )


class PgVectorHybridRepository:
    """Persistent vector + PostgreSQL full-text retrieval for RAG chunks."""

    def __init__(self, config: PgVectorConfig):
        self.config = config
        self.engine = create_engine(config.database_url, future=True, pool_pre_ping=True)

    @staticmethod
    def _vector(values: Sequence[float]) -> str:
        return "[" + ",".join(f"{float(v):.10g}" for v in values) + "]"

    def ensure_schema(self) -> None:
        d = self.config.dimensions
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS rag_chunks (
                    chunk_id uuid PRIMARY KEY,
                    document_id uuid NOT NULL,
                    chunk_index integer NOT NULL,
                    content text NOT NULL,
                    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({d}) NOT NULL,
                    content_tsv tsvector GENERATED ALWAYS AS (to_tsvector('simple', content)) STORED,
                    created_at timestamptz NOT NULL DEFAULT now()
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_document ON rag_chunks(document_id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_metadata ON rag_chunks USING gin(metadata)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_rag_chunks_tsv ON rag_chunks USING gin(content_tsv)"))
            if self.config.use_hnsw:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_hnsw "
                    "ON rag_chunks USING hnsw (embedding vector_cosine_ops) "
                    f"WITH (m = {self.config.hnsw_m}, ef_construction = {self.config.hnsw_ef_construction})"
                ))
            else:
                conn.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_rag_chunks_embedding_ivfflat "
                    "ON rag_chunks USING ivfflat (embedding vector_cosine_ops) "
                    f"WITH (lists = {self.config.index_lists})"
                ))

    def upsert_chunks(self, chunks: Sequence[Any], embeddings: Sequence[Sequence[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length must match")
        with self.engine.begin() as conn:
            for chunk, embedding in zip(chunks, embeddings):
                if len(embedding) != self.config.dimensions:
                    raise ValueError(f"embedding dimension {len(embedding)} != configured {self.config.dimensions}")
                conn.execute(text("""
                    INSERT INTO rag_chunks (chunk_id, document_id, chunk_index, content, metadata, embedding)
                    VALUES (CAST(:chunk_id AS uuid), CAST(:document_id AS uuid), :chunk_index, :content,
                            CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content=EXCLUDED.content,
                        metadata=EXCLUDED.metadata,
                        embedding=EXCLUDED.embedding,
                        chunk_index=EXCLUDED.chunk_index
                """), {
                    "chunk_id": chunk.chunk_id,
                    "document_id": chunk.document_id,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "metadata": json.dumps(chunk.metadata),
                    "embedding": self._vector(embedding),
                })

    def vector_search(self, embedding: Sequence[float], filters: dict[str, Any] | None = None, top_k: int = 20) -> list[RetrievedChunk]:
        vector = self._vector(embedding)
        conditions = []
        params: dict[str, Any] = {"embedding": vector, "top_k": top_k}
        for i, (key, value) in enumerate((filters or {}).items()):
            if value is None:
                continue
            param = f"filter_{i}"
            conditions.append(f"metadata ->> :key_{i} = :{param}")
            params[f"key_{i}"] = key
            params[param] = str(value)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        with self.engine.begin() as conn:
            rows = conn.execute(text(f"""
                SELECT chunk_id::text, document_id::text, content, metadata,
                       1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM rag_chunks
                {where}
                ORDER BY embedding <=> CAST(:embedding AS vector)
                LIMIT :top_k
            """), params).mappings().all()
        return [RetrievedChunk(r["chunk_id"], r["document_id"], r["content"], dict(r["metadata"]), vector_score=float(r["score"])) for r in rows]

    def lexical_search(self, query: str, filters: dict[str, Any] | None = None, top_k: int = 20) -> list[RetrievedChunk]:
        conditions = ["content_tsv @@ plainto_tsquery('simple', :query)"]
        params: dict[str, Any] = {"query": query, "top_k": top_k}
        for i, (key, value) in enumerate((filters or {}).items()):
            if value is None:
                continue
            conditions.append(f"metadata ->> :key_{i} = :filter_{i}")
            params[f"key_{i}"] = key
            params[f"filter_{i}"] = str(value)
        with self.engine.begin() as conn:
            rows = conn.execute(text(f"""
                SELECT chunk_id::text, document_id::text, content, metadata,
                       ts_rank_cd(content_tsv, plainto_tsquery('simple', :query)) AS score
                FROM rag_chunks
                WHERE {' AND '.join(conditions)}
                ORDER BY score DESC
                LIMIT :top_k
            """), params).mappings().all()
        return [RetrievedChunk(r["chunk_id"], r["document_id"], r["content"], dict(r["metadata"]), lexical_score=float(r["score"])) for r in rows]

    def hybrid_search(self, embedding: Sequence[float], query: str, filters: dict[str, Any] | None = None, top_k: int = 5) -> tuple[list[RetrievedChunk], dict[str, Any]]:
        from .hybrid import HybridFusion
        vector_hits = self.vector_search(embedding, filters=filters, top_k=max(20, top_k * 4))
        lexical_hits = self.lexical_search(query, filters=filters, top_k=max(20, top_k * 4))
        fused = HybridFusion().fuse(vector_hits, lexical_hits, top_k=top_k)
        return fused, {"vector_candidates": len(vector_hits), "lexical_candidates": len(lexical_hits), "filters": filters or {}, "top_k": top_k}
