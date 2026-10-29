from pathlib import Path
from backend.ai.ingestion.chunker import ChunkingConfig, SemanticChunker
from backend.ai.ingestion.dataset import RetrievalDatasetBuilder
from backend.ai.ingestion.models import DocumentMetadata
from backend.ai.ingestion.parsers import DocumentParserRegistry
from backend.ai.ingestion.pipeline import KnowledgeIngestionPipeline


def test_registry_parses_markdown(tmp_path: Path):
    p = tmp_path / "manual.md"
    p.write_text("# DTC P0302\n\nCylinder 2 misfire diagnostics.", encoding="utf-8")
    parsed = DocumentParserRegistry().parse(p)
    assert parsed.content_type == "text/plain"
    assert "P0302" in parsed.content


def test_ingestion_is_content_hashed_and_chunked(tmp_path: Path):
    p = tmp_path / "mb_manual.txt"
    p.write_text("P0302 Cylinder 2 misfire.\n\n" + ("Check ignition and LPG injection. " * 80), encoding="utf-8")
    result = KnowledgeIngestionPipeline().ingest_file(
        p, DocumentMetadata(manufacturer="Mercedes-Benz", model="W211", year=2006, engine="M272 3.5", fuel="LPG", source="test")
    )
    assert len(result.document.content_hash) == 64
    assert result.document.document_id
    assert len(result.chunks) > 1
    assert all(c.metadata["manufacturer"] == "Mercedes-Benz" for c in result.chunks)


def test_chunker_has_deterministic_ids():
    from backend.ai.ingestion.models import ParsedDocument
    parsed = ParsedDocument("x", "P0302 information.\n\nA second paragraph.", ())
    c = SemanticChunker(ChunkingConfig(target_chars=100)).chunk("doc", parsed, {"manufacturer": "Mercedes-Benz"})
    c2 = SemanticChunker(ChunkingConfig(target_chars=100)).chunk("doc", parsed, {"manufacturer": "Mercedes-Benz"})
    assert [x.chunk_id for x in c] == [x.chunk_id for x in c2]


def test_retrieval_dataset_builder_finds_dtc_queries(tmp_path: Path):
    p = tmp_path / "dtc.txt"
    p.write_text("P0302 means cylinder 2 misfire.\n\nPossible causes include ignition and fuel delivery.", encoding="utf-8")
    result = KnowledgeIngestionPipeline().ingest_file(p, DocumentMetadata(manufacturer="Mercedes-Benz", model="W211", year=2006, source="oem"))
    examples = RetrievalDatasetBuilder().from_results([result])
    assert examples
    assert examples[0].query == "P0302"
    assert result.document.document_id in examples[0].source_case
