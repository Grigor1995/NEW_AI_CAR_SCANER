from __future__ import annotations
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from typing import Protocol

from .models import ParsedDocument, ParsedPage

class SupportsParser(Protocol):
    extensions: tuple[str, ...]
    content_type: str
    def parse(self, path: Path) -> ParsedDocument: ...

class TextParser:
    extensions = (".txt", ".md", ".markdown", ".rst", ".csv", ".log")
    content_type = "text/plain"
    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8", errors="replace")
        pages = tuple(ParsedPage(i + 1, part) for i, part in enumerate(re.split(r"\f", text)))
        return ParsedDocument(str(path), text, pages, self.content_type)

class JsonParser:
    extensions = (".json",)
    content_type = "application/json"
    def parse(self, path: Path) -> ParsedDocument:
        obj = json.loads(path.read_text(encoding="utf-8"))
        text = json.dumps(obj, ensure_ascii=False, indent=2)
        return ParsedDocument(str(path), text, (ParsedPage(1, text),), self.content_type)

class YamlParser:
    extensions = (".yaml", ".yml")
    content_type = "application/yaml"
    def parse(self, path: Path) -> ParsedDocument:
        try:
            import yaml
            obj = yaml.safe_load(path.read_text(encoding="utf-8"))
            text = yaml.safe_dump(obj, allow_unicode=True, sort_keys=False)
        except ImportError:
            text = path.read_text(encoding="utf-8", errors="replace")
        return ParsedDocument(str(path), text, (ParsedPage(1, text),), self.content_type)

class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data.strip())
    def text(self) -> str:
        return "\n".join(self.parts)

class HtmlParser:
    extensions = (".html", ".htm")
    content_type = "text/html"
    def parse(self, path: Path) -> ParsedDocument:
        parser = _HTMLTextExtractor()
        parser.feed(path.read_text(encoding="utf-8", errors="replace"))
        text = parser.text()
        return ParsedDocument(str(path), text, (ParsedPage(1, text),), self.content_type)

class PdfParser:
    extensions = (".pdf",)
    content_type = "application/pdf"
    def parse(self, path: Path) -> ParsedDocument:
        try:
            from pypdf import PdfReader
        except ImportError as exc:
            raise RuntimeError("PDF ingestion requires pypdf") from exc
        reader = PdfReader(str(path))
        pages: list[ParsedPage] = []
        text_parts: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            pages.append(ParsedPage(idx, text))
            text_parts.append(text)
        return ParsedDocument(str(path), "\n\n".join(text_parts), tuple(pages), self.content_type)

class DocumentParserRegistry:
    def __init__(self, parsers: list[SupportsParser] | None = None) -> None:
        self.parsers = parsers or [TextParser(), JsonParser(), YamlParser(), HtmlParser(), PdfParser()]
        self._by_ext = {ext: parser for parser in self.parsers for ext in parser.extensions}

    def get(self, path: Path) -> SupportsParser:
        try:
            return self._by_ext[path.suffix.lower()]
        except KeyError as exc:
            raise ValueError(f"Unsupported document type: {path.suffix or '<none>'}") from exc

    def parse(self, path: str | Path) -> ParsedDocument:
        p = Path(path)
        if not p.is_file():
            raise FileNotFoundError(p)
        return self.get(p).parse(p)
