from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Iterable

from .chunker import ChunkingConfig, SemanticChunker
from .models import DocumentMetadata, IngestedDocument, IngestionResult, stable_document_id
from .parsers import DocumentParserRegistry

@dataclass(frozen=True)
class IngestionConfig:
    source: str = "unknown"
    default_language: str = "en"
    fail_on_empty: bool = True
    chunking: ChunkingConfig = ChunkingConfig()

class KnowledgeIngestionPipeline:
    """Production-oriented ingestion pipeline independent from a particular embedding vendor."""
    def __init__(self, config: IngestionConfig | None = None, registry: DocumentParserRegistry | None = None, chunker: SemanticChunker | None = None):
        self.config = config or IngestionConfig()
        self.registry = registry or DocumentParserRegistry()
        self.chunker = chunker or SemanticChunker(self.config.chunking)

    def ingest_file(self, path: str | Path, metadata: DocumentMetadata, title: str | None = None) -> IngestionResult:
        p = Path(path)
        parsed = self.registry.parse(p)
        normalized = re.sub(r"\s+", " ", parsed.content).strip()
        warnings: list[str] = []
        if not normalized:
            message = f"Document has no extractable text: {p}"
            if self.config.fail_on_empty:
                raise ValueError(message)
            warnings.append(message)
        content_hash = sha256(parsed.content.encode("utf-8")).hexdigest()
        document_id = stable_document_id(str(p.resolve()), content_hash)
        effective_metadata = metadata
        if not effective_metadata.source or effective_metadata.source == "unknown":
            effective_metadata = DocumentMetadata(**{**metadata.to_dict(), "source": self.config.source})
        base_metadata = effective_metadata.to_dict()
        base_metadata.update({"content_type": parsed.content_type, "source_path": str(p), "content_hash": content_hash})
        chunks = self.chunker.chunk(document_id, parsed, base_metadata)
        if not chunks and normalized:
            warnings.append("No chunks were generated")
        doc = IngestedDocument(document_id, title or p.stem, effective_metadata, str(p), content_hash, parsed.content_type, len(parsed.pages), len(parsed.content))
        return IngestionResult(doc, tuple(chunks), tuple(warnings), skipped=False)

    def ingest_directory(self, root: str | Path, metadata_by_suffix: dict[str, DocumentMetadata] | None = None) -> list[IngestionResult]:
        root_path = Path(root)
        results: list[IngestionResult] = []
        suffixes = set(self.registry._by_ext)
        for path in sorted(p for p in root_path.rglob("*") if p.is_file() and p.suffix.lower() in suffixes):
            metadata = (metadata_by_suffix or {}).get(path.suffix.lower(), DocumentMetadata(source=self.config.source, language=self.config.default_language))
            results.append(self.ingest_file(path, metadata))
        return results

    @staticmethod
    def manifest(results: Iterable[IngestionResult]) -> list[dict]:
        rows = []
        for result in results:
            rows.append({
                "document_id": result.document.document_id,
                "title": result.document.title,
                "source_path": result.document.source_path,
                "content_hash": result.document.content_hash,
                "content_type": result.document.content_type,
                "page_count": result.document.page_count,
                "char_count": result.document.char_count,
                "chunk_count": len(result.chunks),
                "metadata": result.document.metadata.to_dict(),
                "warnings": list(result.warnings),
                "skipped": result.skipped,
            })
        return rows

    @staticmethod
    def save_manifest(results: Iterable[IngestionResult], path: str | Path) -> None:
        Path(path).write_text(json.dumps(KnowledgeIngestionPipeline.manifest(results), indent=2, ensure_ascii=False), encoding="utf-8")
