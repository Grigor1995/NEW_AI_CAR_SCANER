from __future__ import annotations

import json

import pytest

from ai.ingestion.chunker import ChunkingConfig, SemanticChunker
from ai.ingestion.models import DocumentMetadata
from ai.ingestion.pipeline import IngestionConfig, KnowledgeIngestionPipeline


def test_ingest_file_normalizes_metadata_and_builds_chunks(tmp_path):
    path = tmp_path / "w211.txt"
    path.write_text(
        "P0302 misfire is reported under LPG load.\n\n"
        "Compare petrol and LPG behavior, then measure trims and gas pressure.",
        encoding="utf-8",
    )
    pipeline = KnowledgeIngestionPipeline(
        IngestionConfig(source="local-test", default_language="hy"),
        chunker=SemanticChunker(ChunkingConfig(target_chars=45, overlap_chars=0, min_chars=1)),
    )

    result = pipeline.ingest_file(path, DocumentMetadata(source="unknown", tags=("misfire",)))

    assert result.skipped is False
    assert result.document.title == "w211"
    assert result.document.metadata.source == "local-test"
    assert result.document.metadata.language == "en"  # explicit metadata stays authoritative
    assert result.document.content_hash
    assert result.document.char_count == len(path.read_text(encoding="utf-8"))
    assert result.chunks
    assert all(chunk.document_id == result.document.document_id for chunk in result.chunks)
    assert result.chunks[0].metadata["content_type"] == "text/plain"
    assert result.chunks[0].metadata["source_path"] == str(path)


def test_ingest_file_preserves_explicit_source_and_title(tmp_path):
    path = tmp_path / "guide.md"
    path.write_text("Useful diagnostic information with enough content to index.", encoding="utf-8")
    pipeline = KnowledgeIngestionPipeline()

    result = pipeline.ingest_file(path, DocumentMetadata(source="oem-manual", language="hy"), title="Workshop guide")

    assert result.document.title == "Workshop guide"
    assert result.document.metadata.source == "oem-manual"
    assert result.document.metadata.language == "hy"


def test_empty_document_can_fail_or_return_warning(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text(" \n\t ", encoding="utf-8")

    with pytest.raises(ValueError, match="no extractable text"):
        KnowledgeIngestionPipeline(IngestionConfig(fail_on_empty=True)).ingest_file(path, DocumentMetadata())

    result = KnowledgeIngestionPipeline(
        IngestionConfig(source="test", fail_on_empty=False)
    ).ingest_file(path, DocumentMetadata())

    assert result.chunks == ()
    assert result.warnings and "no extractable text" in result.warnings[0]


def test_nonempty_document_with_no_chunks_adds_warning(tmp_path):
    path = tmp_path / "content.txt"
    path.write_text("Readable content that a deliberately empty chunker will not emit.", encoding="utf-8")

    class EmptyChunker:
        def chunk(self, document_id, parsed, base_metadata):
            return []

    result = KnowledgeIngestionPipeline(chunker=EmptyChunker()).ingest_file(path, DocumentMetadata())
    assert result.chunks == ()
    assert result.warnings == ("No chunks were generated",)


def test_ingest_directory_filters_extensions_sorts_and_applies_suffix_metadata(tmp_path):
    (tmp_path / "b.md").write_text("Second diagnostic guide with useful text.", encoding="utf-8")
    (tmp_path / "a.txt").write_text("First diagnostic guide with useful text.", encoding="utf-8")
    (tmp_path / "ignore.bin").write_bytes(b"not a parser-supported document")
    pipeline = KnowledgeIngestionPipeline(IngestionConfig(source="directory", default_language="ru"))

    results = pipeline.ingest_directory(
        tmp_path,
        metadata_by_suffix={".md": DocumentMetadata(source="curated", language="hy")},
    )

    assert [result.document.title for result in results] == ["a", "b"]
    assert results[0].document.metadata.source == "directory"
    assert results[0].document.metadata.language == "ru"
    assert results[1].document.metadata.source == "curated"
    assert results[1].document.metadata.language == "hy"


def test_manifest_and_save_manifest_serialize_warnings_and_metadata(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("A short diagnostic document for manifest generation.", encoding="utf-8")
    pipeline = KnowledgeIngestionPipeline()
    result = pipeline.ingest_file(source, DocumentMetadata(source="test"))
    rows = pipeline.manifest([result])

    assert rows[0]["document_id"] == result.document.document_id
    assert rows[0]["chunk_count"] == len(result.chunks)
    assert rows[0]["metadata"]["source"] == "test"
    assert rows[0]["warnings"] == []
    assert rows[0]["skipped"] is False

    target = tmp_path / "manifest.json"
    pipeline.save_manifest([result], target)
    assert json.loads(target.read_text(encoding="utf-8")) == rows

    empty_target = tmp_path / "empty.json"
    pipeline.save_manifest([], empty_target)
    assert json.loads(empty_target.read_text(encoding="utf-8")) == []
