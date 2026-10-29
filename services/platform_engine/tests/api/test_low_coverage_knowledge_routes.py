from io import BytesIO
from types import SimpleNamespace

import pytest
from fastapi import HTTPException, UploadFile

import api.knowledge_routes as routes


def ingestion_result():
    return SimpleNamespace(
        document=SimpleNamespace(document_id="doc-1", title="Workshop notes"),
        chunks=[SimpleNamespace(chunk_id="chunk-1", text="misfire inspection")],
        warnings=["sample warning"],
    )


def test_ingest_text_writes_text_and_serializes_pipeline_result(monkeypatch):
    observed = {}

    def fake_ingest(path, metadata, title):
        from pathlib import Path
        observed["text"] = Path(path).read_text(encoding="utf-8")
        observed["title"] = title
        observed["metadata"] = metadata
        return ingestion_result()

    monkeypatch.setattr(routes.pipeline, "ingest_file", fake_ingest)
    response = routes.ingest_text(routes.IngestTextRequest(
        title="Workshop notes",
        text="misfire inspection",
        metadata={},
    ))

    assert observed["text"] == "misfire inspection"
    assert observed["title"] == "Workshop notes"
    assert response["document"]["document_id"] == "doc-1"
    assert response["chunks"][0]["text"] == "misfire inspection"
    assert response["warnings"] == ["sample warning"]


def test_ingest_text_passes_metadata_to_document_model(monkeypatch):
    observed = {}
    monkeypatch.setattr(
        routes.pipeline,
        "ingest_file",
        lambda _path, metadata, title: (
            observed.update(metadata=metadata, title=title) or ingestion_result()
        ),
    )
    routes.ingest_text(routes.IngestTextRequest(
        title="Case",
        text="symptom",
        metadata={"source": "manual"},
    ))
    assert observed["metadata"].source == "manual"
    assert observed["title"] == "Case"


@pytest.mark.asyncio
async def test_ingest_file_uses_upload_suffix_and_filename_stem(monkeypatch):
    observed = {}

    def fake_ingest(path, metadata, title):
        from pathlib import Path
        observed.update(
            suffix=Path(path).suffix,
            bytes=Path(path).read_bytes(),
            title=title,
            metadata=metadata,
        )
        return ingestion_result()

    monkeypatch.setattr(routes.pipeline, "ingest_file", fake_ingest)
    upload = UploadFile(filename="engine_notes.md", file=BytesIO(b"note body"))
    response = await routes.ingest_file(upload, metadata_json="{}", title=None)

    assert observed["suffix"] == ".md"
    assert observed["bytes"] == b"note body"
    assert observed["title"] == "engine_notes"
    assert response["document"]["title"] == "Workshop notes"


@pytest.mark.asyncio
async def test_ingest_file_prefers_explicit_title(monkeypatch):
    titles = []
    monkeypatch.setattr(
        routes.pipeline,
        "ingest_file",
        lambda _path, _metadata, title: (
            titles.append(title) or ingestion_result()
        ),
    )
    upload = UploadFile(filename="engine_notes.txt", file=BytesIO(b"note"))
    await routes.ingest_file(upload, metadata_json="{}", title="Curated vehicle case")
    assert titles == ["Curated vehicle case"]


@pytest.mark.asyncio
async def test_ingest_file_defaults_suffix_and_title_for_missing_filename(monkeypatch):
    observed = {}
    def fake_ingest(path, _metadata, title):
        from pathlib import Path
        observed["suffix"] = Path(path).suffix
        observed["title"] = title
        return ingestion_result()

    monkeypatch.setattr(routes.pipeline, "ingest_file", fake_ingest)
    upload = UploadFile(filename=None, file=BytesIO(b"fallback"))
    await routes.ingest_file(upload, metadata_json="{}", title=None)
    assert observed == {"suffix": ".txt", "title": "upload"}


@pytest.mark.asyncio
async def test_ingest_file_rejects_invalid_metadata_json(monkeypatch):
    monkeypatch.setattr(
        routes.pipeline, "ingest_file",
        lambda *_args: pytest.fail("pipeline must not run for invalid metadata"),
    )
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"note"))
    with pytest.raises(HTTPException) as error:
        await routes.ingest_file(upload, metadata_json="{not-json")
    assert error.value.status_code == 400
    assert "Invalid metadata JSON" in error.value.detail


@pytest.mark.asyncio
async def test_ingest_file_rejects_invalid_metadata_shape(monkeypatch):
    monkeypatch.setattr(
        routes.pipeline, "ingest_file",
        lambda *_args: pytest.fail("pipeline must not run for invalid metadata"),
    )
    upload = UploadFile(filename="notes.txt", file=BytesIO(b"note"))
    with pytest.raises(HTTPException) as error:
        await routes.ingest_file(upload, metadata_json='{"unknown_field_for_test": true}')
    assert error.value.status_code == 400
