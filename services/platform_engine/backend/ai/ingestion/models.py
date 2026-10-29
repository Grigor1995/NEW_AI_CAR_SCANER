from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

@dataclass(frozen=True)
class DocumentMetadata:
    manufacturer: str | None = None
    model: str | None = None
    year: int | None = None
    engine: str | None = None
    fuel: str | None = None
    ecu: str | None = None
    document_type: str = "technical_document"
    source: str = "unknown"
    version: str | None = None
    language: str = "en"
    license: str | None = None
    country: str | None = None
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        data = {
            "manufacturer": self.manufacturer,
            "model": self.model,
            "year": self.year,
            "engine": self.engine,
            "fuel": self.fuel,
            "ecu": self.ecu,
            "document_type": self.document_type,
            "source": self.source,
            "version": self.version,
            "language": self.language,
            "license": self.license,
            "country": self.country,
            "tags": list(self.tags),
        }
        return {k: v for k, v in data.items() if v is not None and v != []}

@dataclass(frozen=True)
class ParsedPage:
    page_number: int
    text: str

@dataclass(frozen=True)
class ParsedDocument:
    source_path: str
    content: str
    pages: tuple[ParsedPage, ...] = ()
    content_type: str = "text/plain"

@dataclass(frozen=True)
class IngestedDocument:
    document_id: str
    title: str
    metadata: DocumentMetadata
    source_path: str
    content_hash: str
    content_type: str
    page_count: int
    char_count: int
    indexed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    document_id: str
    chunk_index: int
    content: str
    metadata: dict[str, Any]
    page_start: int | None = None
    page_end: int | None = None
    start_char: int = 0
    end_char: int = 0

@dataclass(frozen=True)
class IngestionResult:
    document: IngestedDocument
    chunks: tuple[KnowledgeChunk, ...]
    warnings: tuple[str, ...] = ()
    skipped: bool = False


def stable_document_id(source_path: str, content_hash: str) -> str:
    return sha256(f"{source_path}\n{content_hash}".encode("utf-8")).hexdigest()[:32]


def stable_chunk_id(document_id: str, chunk_index: int, content: str) -> str:
    return sha256(f"{document_id}:{chunk_index}:{content}".encode("utf-8")).hexdigest()[:32]
