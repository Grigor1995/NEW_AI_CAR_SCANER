from __future__ import annotations
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Iterable

from .models import IngestionResult

@dataclass(frozen=True)
class RetrievalExample:
    query: str
    relevant_chunk_ids: tuple[str, ...]
    metadata_filters: dict
    source_case: str

class RetrievalDatasetBuilder:
    """Builds a simple, human-reviewable retrieval regression dataset from ingested chunks."""
    def from_results(self, results: Iterable[IngestionResult]) -> list[RetrievalExample]:
        out: list[RetrievalExample] = []
        for result in results:
            dtc_codes = set(re.findall(r"\bP\d{4}\b", " ".join(c.content for c in result.chunks), re.I))
            for code in sorted(dtc_codes):
                relevant = tuple(c.chunk_id for c in result.chunks if code.lower() in c.content.lower())
                if relevant:
                    filters = {k: v for k, v in result.document.metadata.to_dict().items() if k in {"manufacturer", "model", "year", "engine", "ecu"} and v is not None}
                    out.append(RetrievalExample(code, relevant, filters, result.document.document_id))
        return out

    @staticmethod
    def save(examples: Iterable[RetrievalExample], path: str | Path) -> None:
        payload = [e.__dict__ | {"relevant_chunk_ids": list(e.relevant_chunk_ids)} for e in examples]
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
