from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence
from sqlalchemy import create_engine, text

@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    document_id: str
    content: str
    metadata: dict
    score: float

class PgVectorKnowledgeRepository:
    """PostgreSQL/pgvector persistence adapter. Schema creation is handled separately."""
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, future=True)

    def ensure_schema(self, dimensions: int = 256) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS ai_knowledge_chunks (
                    chunk_id uuid PRIMARY KEY,
                    document_id uuid NOT NULL,
                    content text NOT NULL,
                    metadata jsonb NOT NULL DEFAULT '{{}}'::jsonb,
                    embedding vector({dimensions}) NOT NULL
                )
            """))

    def upsert(self, chunk_id: str, document_id: str, content: str, metadata: dict, embedding: Sequence[float]) -> None:
        with self.engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO ai_knowledge_chunks (chunk_id, document_id, content, metadata, embedding)
                VALUES (:chunk_id::uuid, :document_id::uuid, :content, CAST(:metadata AS jsonb), CAST(:embedding AS vector))
                ON CONFLICT (chunk_id) DO UPDATE SET content=EXCLUDED.content, metadata=EXCLUDED.metadata, embedding=EXCLUDED.embedding
            """), {"chunk_id": chunk_id, "document_id": document_id, "content": content, "metadata": __import__('json').dumps(metadata), "embedding": "[" + ",".join(map(str, embedding)) + "]"})

    def search(self, embedding: Sequence[float], top_k: int = 5) -> list[VectorHit]:
        vector = "[" + ",".join(map(str, embedding)) + "]"
        with self.engine.begin() as conn:
            rows = conn.execute(text("""
                SELECT chunk_id::text, document_id::text, content, metadata, 1 - (embedding <=> CAST(:embedding AS vector)) AS score
                FROM ai_knowledge_chunks ORDER BY embedding <=> CAST(:embedding AS vector) LIMIT :top_k
            """), {"embedding": vector, "top_k": top_k}).mappings().all()
        return [VectorHit(r["chunk_id"], r["document_id"], r["content"], dict(r["metadata"]), float(r["score"])) for r in rows]
