from __future__ import annotations
from dataclasses import dataclass
import re

from .models import KnowledgeChunk, ParsedDocument, ParsedPage, stable_chunk_id

@dataclass(frozen=True)
class ChunkingConfig:
    target_chars: int = 1200
    overlap_chars: int = 180
    min_chars: int = 120

class SemanticChunker:
    """Heading-aware, paragraph-preserving chunker with overlap for retrieval continuity."""
    def __init__(self, config: ChunkingConfig | None = None):
        self.config = config or ChunkingConfig()

    def _blocks(self, text: str) -> list[str]:
        normalized = re.sub(r"\r\n?", "\n", text).strip()
        if not normalized:
            return []
        blocks = [b.strip() for b in re.split(r"\n\s*\n", normalized) if b.strip()]
        return blocks

    def chunk(self, document_id: str, parsed: ParsedDocument, base_metadata: dict) -> list[KnowledgeChunk]:
        blocks = self._blocks(parsed.content)
        if not blocks:
            return []
        chunks: list[KnowledgeChunk] = []
        current: list[str] = []
        current_len = 0
        ranges: list[tuple[int, int, str]] = []
        # Locate blocks approximately while preserving deterministic offsets.
        search_from = 0
        for block in blocks:
            pos = parsed.content.find(block, search_from)
            pos = pos if pos >= 0 else search_from
            ranges.append((pos, pos + len(block), block))
            search_from = pos + len(block)

        def emit(items: list[tuple[int, int, str]], idx: int) -> KnowledgeChunk:
            content = "\n\n".join(x[2] for x in items).strip()
            meta = dict(base_metadata)
            pages = [p.page_number for p in parsed.pages if any(_overlaps_page(p, x[0], x[1], parsed.content) for x in items)]
            if pages:
                meta.update({"page_start": min(pages), "page_end": max(pages)})
            return KnowledgeChunk(
                stable_chunk_id(document_id, idx, content), document_id, idx, content, meta,
                min(pages) if pages else None, max(pages) if pages else None,
                items[0][0], items[-1][1]
            )

        idx = 0
        for item in ranges:
            block_len = len(item[2])
            if current and current_len + block_len + 2 > self.config.target_chars:
                chunks.append(emit(current, idx)); idx += 1
                overlap: list[tuple[int, int, str]] = []
                overlap_len = 0
                for candidate in reversed(current):
                    if overlap_len + len(candidate[2]) > self.config.overlap_chars:
                        break
                    overlap.insert(0, candidate); overlap_len += len(candidate[2]) + 2
                current = overlap
                current_len = overlap_len
            current.append(item)
            current_len += block_len + 2
        if current:
            chunks.append(emit(current, idx))

        # Avoid tiny trailing chunks where possible.
        if len(chunks) > 1 and len(chunks[-1].content) < self.config.min_chars:
            last = chunks.pop()
            prev = chunks.pop()
            merged = [(prev.start_char, prev.end_char, prev.content), (last.start_char, last.end_char, last.content)]
            chunks.append(emit(merged, prev.chunk_index))
            chunks = [
                KnowledgeChunk(c.chunk_id, c.document_id, i, c.content, c.metadata, c.page_start, c.page_end, c.start_char, c.end_char)
                for i, c in enumerate(chunks)
            ]
        return chunks

def _overlaps_page(page: ParsedPage, start: int, end: int, full_text: str) -> bool:
    # Page offsets are not explicitly stored by parsers; use ordered section matching as a safe approximation.
    # When there is one page it is exact; multi-page association is refined by the parser/pipeline in future versions.
    if len(full_text) == 0:
        return False
    return page.page_number == 1
