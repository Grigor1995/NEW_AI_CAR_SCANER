from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest

import ai.rag.pgvector_hybrid as pgvector
from ai.rag.hybrid import RetrievedChunk


class FakeResult:
    def __init__(self, rows=()):
        self.rows = rows
    def mappings(self):
        return self
    def all(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows=()):
        self.rows = rows
        self.calls = []
    def execute(self, statement, params=None):
        self.calls.append((str(statement), params))
        return FakeResult(self.rows)


class FakeEngine:
    def __init__(self, connection):
        self.connection = connection
        self.transactions = 0
        self.disposed = False
    @contextmanager
    def begin(self):
        self.transactions += 1
        yield self.connection
    def dispose(self):
        self.disposed = True


def make_row():
    return {
        "chunk_id": str(uuid4()),
        "document_id": str(uuid4()),
        "content": "P0302 misfire under LPG load",
        "metadata": {"make": "Mercedes-Benz"},
        "score": 0.82,
    }


def build_repository(monkeypatch, rows=()):
    connection = FakeConnection(rows)
    engine = FakeEngine(connection)
    monkeypatch.setattr(pgvector, "create_engine", lambda *args, **kwargs: engine)
    repo = pgvector.PgVectorHybridRepository(pgvector.PgVectorConfig("postgresql://unused", dimensions=3))
    return repo, engine, connection


def test_pgvector_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://db/example")
    monkeypatch.setenv("RAG_EMBEDDING_DIMENSIONS", "384")
    monkeypatch.setenv("RAG_IVFFLAT_LISTS", "32")
    monkeypatch.setenv("RAG_HNSW_M", "12")
    monkeypatch.setenv("RAG_HNSW_EF_CONSTRUCTION", "80")
    monkeypatch.setenv("RAG_VECTOR_INDEX", "ivfflat")
    config = pgvector.PgVectorConfig.from_env()
    assert config.database_url == "postgresql://db/example"
    assert config.dimensions == 384
    assert config.index_lists == 32
    assert config.hnsw_m == 12
    assert config.hnsw_ef_construction == 80
    assert not config.use_hnsw


def test_vector_format_is_stable_and_length_mismatch_fails_before_connecting(monkeypatch):
    assert pgvector.PgVectorHybridRepository._vector([1, 2.5, -3]) == "[1,2.5,-3]"
    repo, engine, _ = build_repository(monkeypatch)
    with pytest.raises(ValueError, match="length must match"):
        repo.upsert_chunks([SimpleNamespace()], [])
    assert engine.transactions == 0


def test_upsert_validates_dimensions_and_executes_parameterized_upsert(monkeypatch):
    repo, engine, connection = build_repository(monkeypatch)
    chunk = SimpleNamespace(
        chunk_id=str(uuid4()),
        document_id=str(uuid4()),
        chunk_index=2,
        content="misfire",
        metadata={"make": "Mercedes-Benz"},
    )
    with pytest.raises(ValueError, match="embedding dimension 2 != configured 3"):
        repo.upsert_chunks([chunk], [[0.1, 0.2]])
    # The repository enters its transaction before validating individual embedding dimensions.
    # Validation must fail without executing any SQL statements.
    assert engine.transactions == 1
    assert connection.calls == []

    repo.upsert_chunks([chunk], [[0.1, 0.2, 0.3]])
    assert engine.transactions == 2
    sql, params = connection.calls[-1]
    assert "ON CONFLICT (chunk_id) DO UPDATE" in sql
    assert params["chunk_index"] == 2
    assert params["metadata"] == '{"make": "Mercedes-Benz"}'
    assert params["embedding"] == "[0.1,0.2,0.3]"


def test_vector_search_builds_metadata_filters_and_maps_rows(monkeypatch):
    repo, _, connection = build_repository(monkeypatch, [make_row()])
    hits = repo.vector_search([0.1, 0.2, 0.3], filters={"make": "Mercedes-Benz", "year": None}, top_k=4)
    assert len(hits) == 1
    assert isinstance(hits[0], RetrievedChunk)
    assert hits[0].metadata == {"make": "Mercedes-Benz"}
    sql, params = connection.calls[-1]
    assert "metadata ->>" in sql
    assert "filter_0" in params and "key_0" in params
    assert "filter_1" not in params


def test_lexical_search_uses_query_and_filters(monkeypatch):
    repo, _, connection = build_repository(monkeypatch, [make_row()])
    hits = repo.lexical_search("P0302 misfire", filters={"make": "Mercedes-Benz"}, top_k=7)
    assert len(hits) == 1
    assert hits[0].lexical_score == 0.82
    sql, params = connection.calls[-1]
    assert "plainto_tsquery" in sql
    assert params["query"] == "P0302 misfire"
    assert params["filter_0"] == "Mercedes-Benz"


def test_hybrid_search_fuses_vector_and_lexical_candidates(monkeypatch):
    repo, _, _ = build_repository(monkeypatch)
    vector = RetrievedChunk("a", "doc-a", "same", {}, vector_score=0.9)
    lexical = RetrievedChunk("a", "doc-a", "same", {}, lexical_score=0.8)
    monkeypatch.setattr(repo, "vector_search", lambda *args, **kwargs: [vector])
    monkeypatch.setattr(repo, "lexical_search", lambda *args, **kwargs: [lexical])
    hits, meta = repo.hybrid_search([0.1, 0.2, 0.3], "misfire", top_k=3)
    assert len(hits) == 1
    assert hits[0].chunk_id == "a"
    assert hits[0].rank == 1
    assert meta == {
        "vector_candidates": 1,
        "lexical_candidates": 1,
        "filters": {},
        "top_k": 3,
    }


@pytest.mark.parametrize(
    ("use_hnsw", "expected_index"),
    [(True, "USING hnsw"), (False, "USING ivfflat")],
)
def test_ensure_schema_creates_vector_and_text_indexes(monkeypatch, use_hnsw, expected_index):
    connection = FakeConnection()
    engine = FakeEngine(connection)
    monkeypatch.setattr(pgvector, "create_engine", lambda *args, **kwargs: engine)
    config = pgvector.PgVectorConfig(
        "postgresql://unused",
        dimensions=32,
        index_lists=8,
        hnsw_m=12,
        hnsw_ef_construction=40,
        use_hnsw=use_hnsw,
    )
    repo = pgvector.PgVectorHybridRepository(config)

    repo.ensure_schema()

    sql_calls = [sql for sql, _params in connection.calls]
    assert any("CREATE EXTENSION IF NOT EXISTS vector" in sql for sql in sql_calls)
    assert any("vector(32)" in sql for sql in sql_calls)
    assert any("ix_rag_chunks_metadata" in sql for sql in sql_calls)
    assert any("ix_rag_chunks_tsv" in sql for sql in sql_calls)
    assert any(expected_index in sql for sql in sql_calls)
    assert engine.transactions == 1
