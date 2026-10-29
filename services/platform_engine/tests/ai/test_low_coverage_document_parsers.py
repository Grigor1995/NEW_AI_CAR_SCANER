import json
import sys
import types
from pathlib import Path

import pytest

import ai.ingestion.parsers as parsers


def test_text_parser_preserves_form_feed_pages_and_replaces_invalid_utf8(tmp_path):
    path = tmp_path / "manual.TXT"
    path.write_bytes(b"page one\fpage two\xff")

    parsed = parsers.DocumentParserRegistry().parse(path)

    assert parsed.content_type == "text/plain"
    assert "page one" in parsed.content
    assert "\ufffd" in parsed.content
    assert [page.page_number for page in parsed.pages] == [1, 2]
    assert parsed.pages[1].text.endswith("\ufffd")


def test_json_parser_pretty_prints_and_preserves_unicode(tmp_path):
    path = tmp_path / "vehicle.json"
    path.write_text('{"name":"Մեքենա","codes":["P0302"]}', encoding="utf-8")

    parsed = parsers.DocumentParserRegistry().parse(path)

    assert parsed.content_type == "application/json"
    assert '"name": "Մեքենա"' in parsed.content
    assert len(parsed.pages) == 1
    assert json.loads(parsed.content)["codes"] == ["P0302"]


def test_json_parser_surfaces_invalid_json(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text("{bad json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        parsers.JsonParser().parse(path)


def test_yaml_parser_parses_when_dependency_is_available(monkeypatch, tmp_path):
    path = tmp_path / "vehicle.yaml"
    path.write_text("make: Mercedes-Benz\nyear: 2006\n", encoding="utf-8")
    fake_yaml = types.SimpleNamespace(
        safe_load=lambda raw: {"make": "Mercedes-Benz", "year": 2006},
        safe_dump=lambda obj, **kwargs: "make: Mercedes-Benz\nyear: 2006\n",
    )
    monkeypatch.setitem(sys.modules, "yaml", fake_yaml)

    parsed = parsers.YamlParser().parse(path)
    assert parsed.content_type == "application/yaml"
    assert "year: 2006" in parsed.content


def test_yaml_parser_falls_back_to_raw_text_without_optional_dependency(monkeypatch, tmp_path):
    path = tmp_path / "fallback.yml"
    path.write_text("make: Mercedes-Benz\n", encoding="utf-8")
    monkeypatch.setitem(sys.modules, "yaml", None)

    parsed = parsers.YamlParser().parse(path)
    assert parsed.content == "make: Mercedes-Benz\n"


def test_html_parser_extracts_visible_text_and_ignores_empty_whitespace(tmp_path):
    path = tmp_path / "manual.html"
    path.write_text("<html><head><title>Ignore?</title></head><body><h1>P0302</h1>  <p> Cylinder 2 misfire </p></body></html>", encoding="utf-8")

    parsed = parsers.HtmlParser().parse(path)
    assert parsed.content_type == "text/html"
    assert "P0302" in parsed.content
    assert "Cylinder 2 misfire" in parsed.content
    assert parsed.content.count("\n") >= 1


def test_pdf_parser_extracts_pages_and_handles_empty_text(monkeypatch, tmp_path):
    class Page:
        def __init__(self, text):
            self.value = text
        def extract_text(self):
            return self.value

    class Reader:
        def __init__(self, filename):
            assert filename.endswith("manual.pdf")
            self.pages = [Page(" P0302 misfire "), Page(None), Page("Repair notes")]

    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=Reader))
    path = tmp_path / "manual.pdf"
    path.write_bytes(b"%PDF-fake")

    parsed = parsers.PdfParser().parse(path)
    assert parsed.content_type == "application/pdf"
    assert [page.text for page in parsed.pages] == ["P0302 misfire", "", "Repair notes"]
    assert parsed.content == "P0302 misfire\n\n\n\nRepair notes"


def test_pdf_parser_explains_missing_optional_dependency(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "pypdf", None)
    path = tmp_path / "manual.pdf"
    path.write_bytes(b"%PDF-fake")
    with pytest.raises(RuntimeError, match="PDF ingestion requires pypdf"):
        parsers.PdfParser().parse(path)


def test_registry_rejects_missing_and_unsupported_paths(tmp_path):
    registry = parsers.DocumentParserRegistry()
    with pytest.raises(FileNotFoundError):
        registry.parse(tmp_path / "missing.txt")

    unsupported = tmp_path / "manual.docx"
    unsupported.write_text("not actually a document", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported document type: .docx"):
        registry.parse(unsupported)


def test_registry_accepts_custom_parser_and_normalizes_extension_case(tmp_path):
    class CustomParser:
        extensions = (".custom",)
        content_type = "text/custom"
        def parse(self, path: Path):
            return parsers.ParsedDocument(str(path), "custom", (parsers.ParsedPage(1, "custom"),), self.content_type)

    path = tmp_path / "doc.CUSTOM"
    path.write_text("payload", encoding="utf-8")
    parsed = parsers.DocumentParserRegistry([CustomParser()]).parse(path)
    assert parsed.content == "custom"
    assert parsed.content_type == "text/custom"
