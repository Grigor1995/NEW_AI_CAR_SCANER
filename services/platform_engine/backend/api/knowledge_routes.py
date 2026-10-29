from __future__ import annotations
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ai.ingestion.models import DocumentMetadata
from ai.ingestion.pipeline import KnowledgeIngestionPipeline

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge-ingestion"])
pipeline = KnowledgeIngestionPipeline()

class IngestTextRequest(BaseModel):
    title: str
    text: str
    metadata: dict = {}

@router.post("/ingest/text")
def ingest_text(request: IngestTextRequest):
    metadata = DocumentMetadata(**request.metadata)
    # Close the file before handing its path to the ingestion pipeline. On
    # Windows, reopening a still-open NamedTemporaryFile can fail with
    # PermissionError, so use a temporary directory and a normal closed file.
    with TemporaryDirectory(prefix="ai-car-ingest-") as temp_dir:
        temp_path = Path(temp_dir) / "input.txt"
        temp_path.write_text(request.text, encoding="utf-8")
        result = pipeline.ingest_file(str(temp_path), metadata, request.title)
    return {
        "document": result.document.__dict__,
        "chunks": [c.__dict__ for c in result.chunks],
        "warnings": list(result.warnings),
    }

@router.post("/ingest/file")
async def ingest_file(file: UploadFile = File(...), metadata_json: str = Form("{}"), title: str | None = Form(None)):
    try:
        metadata = DocumentMetadata(**json.loads(metadata_json))
    except Exception as exc:
        raise HTTPException(400, f"Invalid metadata JSON: {exc}") from exc
    suffix = Path(file.filename or "upload.txt").suffix or ".txt"
    data = await file.read()
    with TemporaryDirectory(prefix="ai-car-ingest-") as temp_dir:
        temp_path = Path(temp_dir) / f"upload{suffix}"
        temp_path.write_bytes(data)
        result = pipeline.ingest_file(
            str(temp_path), metadata, title or Path(file.filename or "upload").stem
        )
    return {"document": result.document.__dict__, "chunks": [c.__dict__ for c in result.chunks], "warnings": list(result.warnings)}
