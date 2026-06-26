"""
Tests for pipeline.py — the unified MarkItDown -> OCR -> Bijoy chain.
All external converters are injected as fakes, so no MarkItDown/Tesseract needed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import pipeline
from pipeline import (
    convert_file, is_image, is_pdf, is_legacy_doc, is_unsupported, is_rtf, is_xlsx, is_plain_text,
    _read_plain_text, _extract_xlsx_direct, _extract_legacy_doc,
    _docx_font_has_bijoy, _rtf_font_has_bijoy, _pptx_font_has_bijoy, _odt_font_has_bijoy,
)


# ── fakes ───────────────────────────────────────────────────────────────────

class FakeMarkItDown:
    def __init__(self, text):
        self._text = text
        self.calls = []

    def convert(self, path):
        self.calls.append(path)
        return type("R", (), {"text_content": self._text})()


def _touch(tmp_path, name):
    f = tmp_path / name
    f.write_bytes(b"x")
    return str(f)


# ── is_image ──────────────────────────────────────────────────────────────────

class TestIsImage:
    @pytest.mark.parametrize("name", ["a.png", "b.JPG", "c.jpeg", "d.tiff", "e.webp", "f.bmp"])
    def test_image_extensions(self, name):
        assert is_image(name) is True

    @pytest.mark.parametrize("name", ["a.pdf", "b.docx", "c.txt", "d.xlsx", "noext"])
    def test_non_image_extensions(self, name):
        assert is_image(name) is False


# ── is_pdf ────────────────────────────────────────────────────────────────────

class TestIsPdf:
    @pytest.mark.parametrize("name", ["report.pdf", "SCAN.PDF", "file.PDF"])
    def test_pdf_extensions(self, name):
        assert is_pdf(name) is True

    @pytest.mark.parametrize("name", ["report.docx", "data.xlsx", "image.png", "noext"])
    def test_non_pdf_extensions(self, name):
        assert is_pdf(name) is False


# ── document path ───────────────────────────────────────────────────────────

class TestDocumentConversion:
    def test_uses_markitdown_for_documents(self, tmp_path):
        f = _touch(tmp_path, "doc.pdf")
        md = FakeMarkItDown("# Hello")
        out = convert_file(f, markitdown=md)
        assert out["text"] == "# Hello"
        assert out["steps"] == ["markitdown"]
        assert md.calls == [f]

    @pytest.mark.parametrize("name", ["page.html", "deck.pptx", "data.json", "feed.xml"])
    def test_generic_format_uses_markitdown(self, tmp_path, name):
        """Non-special formats (.html, .pptx, .json, .xml) go through the generic MarkItDown else-branch."""
        f = _touch(tmp_path, name)
        md = FakeMarkItDown("converted content")
        out = convert_file(str(f), markitdown=md, auto_bijoy=False)
        assert "markitdown" in out["steps"]
        assert out["text"] == "converted content"

    def test_none_text_content_becomes_empty(self, tmp_path):
        f = _touch(tmp_path, "doc.pdf")
        md = FakeMarkItDown(None)
        # Disable OCR fallback so we're testing only the MarkItDown-None path.
        # When MarkItDown returns nothing and OCR is off, pdf_empty step is added.
        out = convert_file(f, markitdown=md, auto_ocr=False)
        assert out["text"] == ""
        assert "markitdown" in out["steps"]
        assert "pdf_empty" in out["steps"]

    def test_pdf_ocr_fallback_when_markitdown_empty(self, tmp_path):
        f = _touch(tmp_path, "scan.pdf")
        md = FakeMarkItDown(None)
        # When MarkItDown returns empty and auto_ocr=True, pdf_ocr_func is called.
        calls = {}
        def fake_pdf_ocr(path, lang):
            calls["path"] = path; calls["lang"] = lang
            return "scanned text"
        out = convert_file(f, markitdown=md, auto_ocr=True, ocr_pdf_func=fake_pdf_ocr)
        assert out["text"] == "scanned text"
        assert out["steps"] == ["pdf_ocr"]
        assert calls["path"] == str(f)


# ── image / OCR path ──────────────────────────────────────────────────────────

class TestImageConversion:
    def test_uses_ocr_for_images(self, tmp_path):
        f = _touch(tmp_path, "scan.png")
        captured = {}

        def fake_ocr(path, lang):
            captured["path"], captured["lang"] = path, lang
            return "extracted text"

        out = convert_file(f, ocr_func=fake_ocr, ocr_lang="Both")
        assert out["text"] == "extracted text"
        assert out["steps"] == ["ocr"]
        assert captured == {"path": f, "lang": "Both"}

    def test_auto_ocr_disabled_returns_image_ocr_disabled_step(self, tmp_path):
        f = _touch(tmp_path, "scan.png")
        md = FakeMarkItDown("from markitdown")
        out = convert_file(f, auto_ocr=False, markitdown=md)
        assert out["text"] == ""
        assert out["steps"] == ["image_ocr_disabled"]


# ── Bijoy post-step ───────────────────────────────────────────────────────────

class TestBijoyStep:
    def test_bijoy_applied_when_detected(self, tmp_path):
        f = _touch(tmp_path, "doc.docx")
        md = FakeMarkItDown("raw-bijoy")
        out = convert_file(
            f, markitdown=md,
            is_bijoy_func=lambda t: True,
            bijoy_func=lambda t: "ইউনিকোড",
        )
        assert out["text"] == "ইউনিকোড"
        assert out["steps"] == ["markitdown", "bijoy"]

    def test_bijoy_skipped_when_not_detected(self, tmp_path):
        f = _touch(tmp_path, "doc.docx")
        md = FakeMarkItDown("plain english")
        out = convert_file(
            f, markitdown=md,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "SHOULD NOT RUN",
        )
        assert out["text"] == "plain english"
        assert out["steps"] == ["markitdown"]

    def test_bijoy_applies_to_ocr_output_too(self, tmp_path):
        f = _touch(tmp_path, "scan.jpg")
        out = convert_file(
            f,
            ocr_func=lambda p, l: "raw",
            is_bijoy_func=lambda t: True,
            bijoy_func=lambda t: "converted",
        )
        assert out["text"] == "converted"
        assert out["steps"] == ["ocr", "bijoy"]

    def test_auto_bijoy_disabled(self, tmp_path):
        f = _touch(tmp_path, "doc.docx")
        md = FakeMarkItDown("raw-bijoy")
        out = convert_file(
            f, markitdown=md, auto_bijoy=False,
            is_bijoy_func=lambda t: True,
            bijoy_func=lambda t: "SHOULD NOT RUN",
        )
        assert out["text"] == "raw-bijoy"
        assert out["steps"] == ["markitdown"]

    def test_empty_text_skips_bijoy(self, tmp_path):
        f = _touch(tmp_path, "doc.docx")
        md = FakeMarkItDown("")
        called = []
        out = convert_file(
            f, markitdown=md,
            is_bijoy_func=lambda t: called.append(t) or True,
            bijoy_func=lambda t: "x",
        )
        assert out["text"] == ""
        assert called == []   # is_bijoy never consulted on empty text


# ── errors / lazy markitdown ──────────────────────────────────────────────────

class TestErrors:
    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            convert_file("/no/such/file.pdf")

    def test_memory_error_becomes_value_error(self, tmp_path):
        """MemoryError from MarkItDown (e.g. huge ZIP) surfaces as a friendly ValueError."""
        f = _touch(tmp_path, "huge.zip")

        class OOMMarkItDown:
            def convert(self, path):
                raise MemoryError("ran out of RAM")

        with pytest.raises(ValueError, match="(?i)too large|insufficient memory"):
            convert_file(str(f), markitdown=OOMMarkItDown())

    def test_wrapped_memory_error_pdf_becomes_value_error(self, tmp_path):
        """MarkItDown-wrapped MemoryError on PDF (PdfConverter) surfaces as friendly ValueError."""
        f = _touch(tmp_path, "huge.pdf")

        class OOMMarkItDown:
            def convert(self, path):
                raise RuntimeError(
                    "File conversion failed after 1 attempts: "
                    "- PdfConverter threw MemoryError with message: "
                    "Unable to allocate 1.2 GiB"
                )

        with pytest.raises(ValueError, match="(?i)too large|insufficient memory"):
            convert_file(str(f), markitdown=OOMMarkItDown())

    def test_wrapped_memory_error_docx_becomes_value_error(self, tmp_path):
        """MarkItDown-wrapped MemoryError on DOCX/PPTX surfaces as friendly ValueError."""
        f = _touch(tmp_path, "huge.docx")

        class OOMMarkItDown:
            def convert(self, path):
                raise RuntimeError(
                    "File conversion failed after 1 attempts: "
                    "- DocxConverter threw MemoryError with message: "
                    "Unable to allocate 800 MiB"
                )

        with pytest.raises(ValueError, match="(?i)too large|insufficient memory"):
            convert_file(str(f), markitdown=OOMMarkItDown())

    def test_generic_format_non_memory_error_reraises(self, tmp_path):
        """Non-MemoryError from MarkItDown in generic branch propagates unchanged."""
        f = _touch(tmp_path, "doc.html")

        class BrokenMD:
            def convert(self, path):
                raise ValueError("parse failed")

        with pytest.raises(ValueError, match="parse failed"):
            convert_file(str(f), markitdown=BrokenMD())

    def test_pdf_non_memory_error_reraises(self, tmp_path):
        """Non-MemoryError from MarkItDown on a PDF propagates unchanged."""
        f = _touch(tmp_path, "locked.pdf")

        class BrokenMD:
            def convert(self, path):
                raise RuntimeError("PDF is encrypted")

        with pytest.raises(RuntimeError, match="PDF is encrypted"):
            convert_file(str(f), markitdown=BrokenMD())

    def test_lazy_markitdown_singleton(self, monkeypatch):
        created = []

        class FakeMID:
            def __init__(self):
                created.append(1)

            def convert(self, p):
                return type("R", (), {"text_content": "ok"})()

        fake_module = type("M", (), {"MarkItDown": FakeMID})
        monkeypatch.setitem(sys.modules, "markitdown", fake_module)
        monkeypatch.setattr(pipeline, "_mid", None)

        a = pipeline._get_markitdown()
        b = pipeline._get_markitdown()
        assert a is b
        assert len(created) == 1


# ── T-1: is_legacy_doc + .doc empty step ──────────────────────────────────────

class TestLegacyDoc:
    def test_is_legacy_doc_true(self):
        assert is_legacy_doc("report.doc") is True

    def test_is_legacy_doc_false(self):
        assert is_legacy_doc("report.docx") is False

    def test_doc_empty_step(self, tmp_path, monkeypatch):
        """When both OLE extraction and MarkItDown return empty, 'doc_empty' must appear."""
        f = _touch(tmp_path, "old.doc")

        # OLE extraction always returns "" for this fake file
        monkeypatch.setattr(pipeline, "_extract_legacy_doc", lambda path: "")

        # MarkItDown also returns empty
        md = FakeMarkItDown("")
        out = convert_file(str(f), markitdown=md)

        assert "doc_empty" in out["steps"]
        assert out["text"] == ""

    def test_doc_markitdown_exception_silenced_returns_doc_empty(self, tmp_path, monkeypatch):
        """When OLE extraction returns empty and MarkItDown raises, exception is silenced → doc_empty."""
        f = _touch(tmp_path, "old.doc")
        monkeypatch.setattr(pipeline, "_extract_legacy_doc", lambda path: "")

        class BrokenMD:
            def convert(self, path):
                raise RuntimeError("unreadable")

        out = convert_file(str(f), markitdown=BrokenMD())
        assert "doc_empty" in out["steps"]
        assert out["text"] == ""

    def test_doc_ole_step_on_success(self, tmp_path, monkeypatch):
        """When OLE extraction succeeds, 'doc_ole' appears and MarkItDown is not called."""
        f = _touch(tmp_path, "old.doc")
        monkeypatch.setattr(pipeline, "_extract_legacy_doc", lambda path: "Extracted content")
        out = convert_file(str(f), auto_bijoy=False)
        assert "doc_ole" in out["steps"]
        assert "doc_empty" not in out["steps"]
        assert out["text"] == "Extracted content"

    def test_doc_ole_empty_markitdown_returns_text(self, tmp_path, monkeypatch):
        """When OLE extraction returns empty and MarkItDown returns text, 'markitdown' step appears."""
        f = _touch(tmp_path, "old.doc")
        monkeypatch.setattr(pipeline, "_extract_legacy_doc", lambda path: "")
        md = FakeMarkItDown("recovered text from MarkItDown")
        out = convert_file(str(f), markitdown=md, auto_bijoy=False)
        assert "markitdown" in out["steps"]
        assert "doc_empty" not in out["steps"]
        assert out["text"] == "recovered text from MarkItDown"


# ── T-2: is_unsupported + ValueError ─────────────────────────────────────────

class TestUnsupported:
    def test_is_unsupported_otf(self):
        assert is_unsupported("font.otf") is True

    def test_is_unsupported_docx(self):
        assert is_unsupported("doc.docx") is False

    @pytest.mark.parametrize("name", ["graphic.eps", "icon.otf", "typeface.ttf", "layout.indd"])
    def test_convert_unsupported_raises(self, tmp_path, name):
        f = _touch(tmp_path, name)
        with pytest.raises(ValueError, match="(?i)unsupported format"):
            convert_file(str(f))


# ── T-4: ocr_empty step ───────────────────────────────────────────────────────

class TestOcrEmpty:
    def test_ocr_empty_step(self, tmp_path):
        """When ocr_func returns empty string, 'ocr_empty' must appear in steps."""
        f = _touch(tmp_path, "blank.png")
        out = convert_file(str(f), ocr_func=lambda path, lang: "")
        assert "ocr_empty" in out["steps"]
        assert out["text"] == ""


# ── image_ocr_disabled (standalone) ──────────────────────────────────────────


# ── RTF extraction ────────────────────────────────────────────────────────────

class TestRtf:
    def test_is_rtf_true(self):
        assert is_rtf("document.rtf") is True
        assert is_rtf("REPORT.RTF") is True

    def test_is_rtf_false(self):
        assert is_rtf("document.docx") is False
        assert is_rtf("document.doc") is False

    def test_rtf_step_via_markitdown_fallback(self, tmp_path, monkeypatch):
        """When striprtf is unavailable, RTF falls through to MarkItDown; step='rtf'."""
        f = tmp_path / "report.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", False)
        md = FakeMarkItDown("rtf content here")
        out = convert_file(str(f), markitdown=md)
        assert "rtf" in out["steps"]
        assert out["text"] == "rtf content here"

    def test_rtf_step_via_striprtf(self, tmp_path, monkeypatch):
        """When striprtf is available and returns text, 'rtf' step appears."""
        f = tmp_path / "report.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: "extracted via striprtf")
        out = convert_file(str(f), auto_bijoy=False)
        assert "rtf" in out["steps"]
        assert out["text"] == "extracted via striprtf"

    def test_rtf_markitdown_fallback_when_striprtf_empty(self, tmp_path, monkeypatch):
        """When striprtf returns empty, falls back to MarkItDown."""
        f = tmp_path / "empty.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: "")
        md = FakeMarkItDown("fallback text")
        out = convert_file(str(f), markitdown=md)
        assert "rtf" in out["steps"]
        assert out["text"] == "fallback text"

    def test_rtf_striprtf_exception_falls_back_to_markitdown(self, tmp_path, monkeypatch):
        """When _rtf_to_text() raises, the exception is silenced and MarkItDown is used."""
        f = tmp_path / "broken.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: (_ for _ in ()).throw(ValueError("bad rtf")))
        md = FakeMarkItDown("recovered text")
        out = convert_file(str(f), markitdown=md)
        assert "rtf" in out["steps"]
        assert out["text"] == "recovered text"

    def test_rtf_both_paths_fail_yields_rtf_empty(self, tmp_path, monkeypatch):
        """When both _rtf_to_text and MarkItDown fail, 'rtf_empty' appears in steps."""
        f = tmp_path / "unreadable.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: (_ for _ in ()).throw(ValueError("bad")))

        class BrokenMD:
            def convert(self, path):
                raise RuntimeError("unreadable")

        out = convert_file(str(f), markitdown=BrokenMD())
        assert "rtf" in out["steps"]
        assert "rtf_empty" in out["steps"]
        assert out["text"] == ""


class TestImageOcrDisabled:
    def test_image_ocr_disabled(self, tmp_path):
        """When auto_ocr=False and path is an image, steps must contain 'image_ocr_disabled'."""
        f = _touch(tmp_path, "photo.jpg")
        out = convert_file(str(f), auto_ocr=False)
        assert out["steps"] == ["image_ocr_disabled"]
        assert out["text"] == ""


# ── XLSX extraction ───────────────────────────────────────────────────────────

class TestXlsx:
    def test_is_xlsx_true(self):
        assert is_xlsx("data.xlsx") is True
        assert is_xlsx("DATA.XLSX") is True

    def test_is_xlsx_false(self):
        assert is_xlsx("data.xls") is False
        assert is_xlsx("data.docx") is False

    def test_xlsx_uses_markitdown_when_it_works(self, tmp_path):
        f = tmp_path / "data.xlsx"
        f.write_bytes(b"dummy")
        md = FakeMarkItDown("col1 | col2\nrow1 | row2")
        out = convert_file(str(f), markitdown=md)
        assert "markitdown" in out["steps"]
        assert out["text"] == "col1 | col2\nrow1 | row2"

    def test_xlsx_falls_back_to_openpyxl_on_markitdown_failure(self, tmp_path, monkeypatch):
        """ONNXRuntimeError / wrapped MemoryError triggers openpyxl fallback."""
        f = tmp_path / "huge.xlsx"
        f.write_bytes(b"dummy")

        class OOMMarkItDown:
            def convert(self, path):
                raise RuntimeError(
                    "File conversion failed after 1 attempts: "
                    "- XlsxConverter threw MemoryError"
                )

        monkeypatch.setattr(pipeline, "_extract_xlsx_direct", lambda path: "row1 | col1\nrow2 | col2")
        out = convert_file(str(f), markitdown=OOMMarkItDown())
        assert "xlsx_direct" in out["steps"]
        assert out["text"] == "row1 | col1\nrow2 | col2"

    def test_xlsx_large_bypasses_markitdown(self, tmp_path, monkeypatch):
        """XLSX >= 2 MB must use xlsx_direct without calling MarkItDown at all."""
        f = tmp_path / "big.xlsx"
        f.write_bytes(b"\x00" * (2 * 1024 * 1024 + 1))   # 2 MB + 1 byte

        class ExplodingMarkItDown:
            def convert(self, path):
                raise AssertionError("MarkItDown must NOT be called for XLSX >= 2 MB")

        monkeypatch.setattr(pipeline, "_extract_xlsx_direct", lambda path: "a | b\nc | d")
        out = convert_file(str(f), markitdown=ExplodingMarkItDown())
        assert "xlsx_direct" in out["steps"]
        assert "markitdown" not in out["steps"]
        assert out["text"] == "a | b\nc | d"


# ── plain-text direct read ────────────────────────────────────────────────────

class TestPlainText:
    def test_is_plain_text_true(self):
        for ext in (".txt", ".TXT", ".md", ".ini", ".cfg", ".conf", ".log", ".csv", ".tsv"):
            assert is_plain_text(f"file{ext}") is True, f"Expected True for {ext}"

    def test_is_plain_text_false(self):
        for ext in (".docx", ".pdf", ".xlsx", ".jpg", ".py", ".html"):
            assert is_plain_text(f"file{ext}") is False, f"Expected False for {ext}"

    def test_plain_text_utf8(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("Hello world\nLine two", encoding="utf-8")
        out = convert_file(str(f), auto_bijoy=False)
        assert "plaintext" in out["steps"]
        assert "Hello world" in out["text"]

    def test_plain_text_empty_file(self, tmp_path):
        f = tmp_path / "empty.ini"
        f.write_text("", encoding="utf-8")
        out = convert_file(str(f), auto_bijoy=False)
        assert "plaintext" in out["steps"]
        assert "plaintext_empty" in out["steps"]

    def test_plain_text_csv(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("name,age\nAlice,30\nBob,25", encoding="utf-8")
        out = convert_file(str(f), auto_bijoy=False)
        assert "plaintext" in out["steps"]
        assert "Alice" in out["text"]

    def test_plain_text_does_not_call_markitdown(self, tmp_path):
        f = tmp_path / "notes.md"
        f.write_text("# Notes\nContent here", encoding="utf-8")

        class ExplodingMarkItDown:
            def convert(self, path):
                raise AssertionError("MarkItDown must NOT be called for plain-text files")

        out = convert_file(str(f), markitdown=ExplodingMarkItDown(), auto_bijoy=False)
        assert "plaintext" in out["steps"]
        assert "# Notes" in out["text"]


# ── _read_plain_text encoding fallback ──────────────────────────────────────

class TestReadPlainTextEncoding:
    def test_cp1252_fallback(self, tmp_path):
        """cp1252 bytes invalid in UTF-8 must be decoded via cp1252 fallback."""
        # 0x93 / 0x94 are Windows smart-quotes — valid cp1252, invalid UTF-8
        f = tmp_path / "wintext.txt"
        f.write_bytes(b"Hello \x93world\x94")
        text = _read_plain_text(str(f))
        assert "“" in text   # U+201C left double quotation mark
        assert "”" in text   # U+201D right double quotation mark
        assert "world" in text

    def test_utf8_sig_bom(self, tmp_path):
        """Files with UTF-8 BOM must decode cleanly (no BOM in result text)."""
        f = tmp_path / "bom.txt"
        f.write_bytes(b"\xef\xbb\xbfHello BOM")
        text = _read_plain_text(str(f))
        assert text == "Hello BOM"

    def test_latin1_fallback(self, tmp_path):
        """Bytes undefined in cp1252 (0x81, 0x8D, etc.) fall through to latin-1."""
        f = tmp_path / "latin1.txt"
        f.write_bytes(b"Hello \x81 World")  # 0x81 is undefined in cp1252
        text = _read_plain_text(str(f))
        assert "Hello" in text
        assert "World" in text


# ── rtf_empty step ────────────────────────────────────────────────────────────

class TestRtfEmpty:
    def test_rtf_empty_step_when_both_extractors_return_empty(self, tmp_path, monkeypatch):
        """When striprtf AND MarkItDown both return empty, 'rtf_empty' must appear."""
        f = tmp_path / "empty.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: "")
        md = FakeMarkItDown("")
        out = convert_file(str(f), markitdown=md)
        assert "rtf" in out["steps"]
        assert "rtf_empty" in out["steps"]
        assert out["text"] == ""

    def test_rtf_no_empty_step_when_text_found(self, tmp_path, monkeypatch):
        """'rtf_empty' must NOT appear when text is successfully extracted."""
        f = tmp_path / "report.rtf"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: "extracted text")
        out = convert_file(str(f), auto_bijoy=False)
        assert "rtf" in out["steps"]
        assert "rtf_empty" not in out["steps"]


# ── xlsx_empty step ──────────────────────────────────────────────────────────

class TestXlsxEmpty:
    def test_xlsx_empty_step_when_extraction_returns_empty(self, tmp_path, monkeypatch):
        """When all XLSX extraction returns empty, 'xlsx_empty' must appear in steps."""
        f = tmp_path / "blank.xlsx"
        f.write_bytes(b"dummy")
        monkeypatch.setattr(pipeline, "_extract_xlsx_direct", lambda path: "")
        out = convert_file(str(f), markitdown=FakeMarkItDown(""))
        assert "xlsx_empty" in out["steps"]
        assert out["text"] == ""

    def test_xlsx_no_empty_step_when_text_found(self, tmp_path, monkeypatch):
        """'xlsx_empty' must NOT appear when MarkItDown returns text."""
        f = tmp_path / "data.xlsx"
        f.write_bytes(b"dummy")
        out = convert_file(str(f), markitdown=FakeMarkItDown("| a | b |\n| --- | --- |\n| 1 | 2 |"))
        assert "xlsx_empty" not in out["steps"]


# ── _extract_xlsx_direct unit tests ──────────────────────────────────────────

class TestExtractXlsxDirect:
    def _make_fake_openpyxl(self, worksheets):
        class FakeWorkbook:
            def __init__(self):
                self.worksheets = worksheets
            def close(self):
                pass

        return type("openpyxl", (), {
            "load_workbook": staticmethod(lambda *a, **kw: FakeWorkbook()),
        })

    def _make_sheet(self, title, rows):
        class FakeSheet:
            pass
        s = FakeSheet()
        s.title = title
        s.iter_rows = lambda values_only=True: iter(rows)
        return s

    def test_single_sheet_gfm_table(self, tmp_path, monkeypatch):
        """Single-sheet workbook produces a GFM table: header | sep | data rows."""
        import sys
        sheet = self._make_sheet("Sheet1", [
            ("Name", "Age"),
            ("Alice", 30),
            ("Bob", None),
        ])
        fake_mod = self._make_fake_openpyxl([sheet])
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "data.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        lines = result.strip().split("\n")

        assert lines[0] == "| Name | Age |"
        assert lines[1] == "| --- | --- |"
        assert lines[2] == "| Alice | 30 |"
        assert lines[3] == "| Bob |  |"

    def test_multi_sheet_adds_h2_headings(self, tmp_path, monkeypatch):
        """Multi-sheet workbooks get an H2 heading per sheet."""
        import sys
        sheets = [
            self._make_sheet("Sales", [("Q1", "Q2"), ("100", "200")]),
            self._make_sheet("Costs", [("Item",), ("50",)]),
        ]
        fake_mod = self._make_fake_openpyxl(sheets)
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "multi.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        assert "## Sales" in result
        assert "## Costs" in result

    def test_pipe_chars_escaped(self, tmp_path, monkeypatch):
        """Pipe characters inside cell values must be escaped as \\|."""
        import sys
        sheet = self._make_sheet("S", [("A|B", "C")])
        fake_mod = self._make_fake_openpyxl([sheet])
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "pipes.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        assert "A\\|B" in result

    def test_empty_sheet_skipped(self, tmp_path, monkeypatch):
        """Sheets with no non-empty rows produce no output."""
        import sys
        sheet = self._make_sheet("Empty", [("", ""), (None, None)])
        fake_mod = self._make_fake_openpyxl([sheet])
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "empty.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        assert result == ""

    def test_newline_in_cell_replaced_by_space(self, tmp_path, monkeypatch):
        """Newlines inside cell values must be normalised to spaces (GFM table safety)."""
        import sys
        sheet = self._make_sheet("Sheet1", [("Header",), ("line1\nline2",)])
        fake_mod = self._make_fake_openpyxl([sheet])
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "nl.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        # The raw newline inside the cell value must be collapsed to a space;
        # the GFM row-separator newlines between table rows are still present.
        assert "line1 line2" in result
        assert "line1\nline2" not in result

    def test_header_only_sheet(self, tmp_path, monkeypatch):
        """A sheet with only a header row (no data rows) emits header + GFM separator only."""
        import sys
        sheet = self._make_sheet("Sheet1", [("Name", "Score")])
        fake_mod = self._make_fake_openpyxl([sheet])
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)

        f = tmp_path / "header_only.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        lines = result.strip().split("\n")
        assert lines[0] == "| Name | Score |"
        assert lines[1] == "| --- | --- |"
        assert len(lines) == 2

    def test_openpyxl_not_installed_returns_empty(self, tmp_path, monkeypatch):
        """When openpyxl is not importable, returns empty string."""
        import sys
        monkeypatch.setitem(sys.modules, "openpyxl", None)
        f = tmp_path / "data.xlsx"
        f.write_bytes(b"dummy")
        assert _extract_xlsx_direct(str(f)) == ""

    def test_load_workbook_exception_returns_empty(self, tmp_path, monkeypatch):
        """When load_workbook raises, the outer except swallows it and returns empty string."""
        import sys
        broken_mod = type("openpyxl", (), {
            "load_workbook": staticmethod(lambda *a, **kw: (_ for _ in ()).throw(OSError("corrupt")))
        })
        monkeypatch.setitem(sys.modules, "openpyxl", broken_mod)
        f = tmp_path / "data.xlsx"
        f.write_bytes(b"dummy")
        assert _extract_xlsx_direct(str(f)) == ""

    def test_multi_sheet_blank_title_no_heading(self, tmp_path, monkeypatch):
        """Multi-sheet workbook where sheet titles are blank → no H2 headings emitted."""
        import sys
        sheets = [
            self._make_sheet("", [("A",), ("1",)]),
            self._make_sheet("", [("B",), ("2",)]),
        ]
        fake_mod = self._make_fake_openpyxl(sheets)
        monkeypatch.setitem(sys.modules, "openpyxl", fake_mod)
        f = tmp_path / "notitle.xlsx"
        f.write_bytes(b"dummy")
        result = _extract_xlsx_direct(str(f))
        assert "## " not in result
        assert "| A |" in result
        assert "| B |" in result


# ── _extract_legacy_doc unit tests ───────────────────────────────────────────

class TestExtractLegacyDoc:
    def test_no_olefile_returns_empty(self, monkeypatch):
        """When olefile is not installed, returns empty string."""
        monkeypatch.setitem(sys.modules, "olefile", None)
        assert _extract_legacy_doc("any.doc") == ""

    def test_ole_open_error_returns_empty(self, monkeypatch):
        """When OleFileIO raises on open (file is not an OLE container), returns empty string."""
        class FailOleFileIO:
            def __init__(self, path):
                raise ValueError("not an OLE file")
            def __enter__(self): return self
            def __exit__(self, *a): pass

        fake_mod = type("olefile", (), {"OleFileIO": FailOleFileIO})
        monkeypatch.setitem(sys.modules, "olefile", fake_mod)
        assert _extract_legacy_doc("x.doc") == ""

    def test_no_word_document_stream_returns_empty(self, monkeypatch):
        """When the WordDocument stream is absent inside the OLE container, returns empty string."""
        class FakeOleFileIO:
            def __init__(self, path): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def exists(self, name): return False

        fake_mod = type("olefile", (), {"OleFileIO": FakeOleFileIO})
        monkeypatch.setitem(sys.modules, "olefile", fake_mod)
        assert _extract_legacy_doc("x.doc") == ""

    def test_cc_text_zero_returns_empty(self, monkeypatch):
        """When the FIB header reports cc_text == 0, returns empty string immediately."""
        # A 512-byte all-zero buffer: csw=0 → fib_rglw_start=36, cc_text at offset 48 = 0.
        binary = bytes(512)

        class FakeStream:
            def read(self): return binary

        class FakeOleFileIO:
            def __init__(self, path): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def exists(self, name): return name == "WordDocument"
            def openstream(self, name): return FakeStream()

        fake_mod = type("olefile", (), {"OleFileIO": FakeOleFileIO})
        monkeypatch.setitem(sys.modules, "olefile", fake_mod)
        assert _extract_legacy_doc("x.doc") == ""

    def test_cc_text_exceeds_data_length_returns_empty(self, monkeypatch):
        """When cc_text reported in the FIB exceeds the stream length, returns empty string."""
        import struct as _struct
        binary = bytearray(512)
        # csw=0 → fib_rglw_start=36; cc_text is at offset 48.  Set it to 0xFFFFFFFF > 512.
        _struct.pack_into("<I", binary, 48, 0xFFFFFFFF)
        binary = bytes(binary)

        class FakeStream:
            def read(self): return binary

        class FakeOleFileIO:
            def __init__(self, path): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def exists(self, name): return name == "WordDocument"
            def openstream(self, name): return FakeStream()

        fake_mod = type("olefile", (), {"OleFileIO": FakeOleFileIO})
        monkeypatch.setitem(sys.modules, "olefile", fake_mod)
        assert _extract_legacy_doc("x.doc") == ""


# ── DOCX font-name Bijoy detection ───────────────────────────────────────────

class TestDocxFontDetection:
    def _make_docx_with_font(self, tmp_path, font_name):
        """Minimal DOCX ZIP containing one rFonts element with the given font name."""
        import zipfile
        docx_path = tmp_path / "test.docx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r>'
            f'<w:rPr><w:rFonts w:ascii="{font_name}"/></w:rPr>'
            '<w:t>evsjv</w:t>'
            '</w:r></w:p></w:body></w:document>'
        )
        with zipfile.ZipFile(str(docx_path), "w") as z:
            z.writestr("word/document.xml", xml)
        return str(docx_path)

    def test_bijoy_font_detected(self, tmp_path):
        """SutonnyMJ is on the curated Bijoy allowlist → True."""
        assert _docx_font_has_bijoy(self._make_docx_with_font(tmp_path, "SutonnyMJ")) is True

    def test_bijoy_font_comma_suffix_detected(self, tmp_path):
        """Comma-suffixed style variant 'SutonnyMJ,Bold' strips to 'sutonnymj' → True."""
        assert _docx_font_has_bijoy(self._make_docx_with_font(tmp_path, "SutonnyMJ,Bold")) is True

    def test_non_bijoy_font_returns_false(self, tmp_path):
        """Arial is not a Bengali font → False."""
        assert _docx_font_has_bijoy(self._make_docx_with_font(tmp_path, "Arial")) is False

    def test_invalid_zip_returns_false(self, tmp_path):
        """Non-ZIP file doesn't raise — just returns False."""
        bad = tmp_path / "bad.docx"
        bad.write_bytes(b"not a zip file at all")
        assert _docx_font_has_bijoy(str(bad)) is False

    def test_font_detection_triggers_bijoy_conversion(self, tmp_path, monkeypatch):
        """ASCII-only Bijoy text + SutonnyMJ font → bijoy step even when text-scan fails."""
        f = _touch(tmp_path, "bangla.docx")
        monkeypatch.setattr(pipeline, "_docx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),   # ASCII-only: text-scan won't detect
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,         # simulate text-scan miss
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_docm_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.docm (macro-enabled Word) uses the same ZIP structure → font detection applies."""
        f = _touch(tmp_path, "macro.docm")
        monkeypatch.setattr(pipeline, "_docx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_hAnsi_only_font_attr_detected(self, tmp_path):
        """w:rFonts with only w:hAnsi (no w:ascii) → all attrib.values() are checked → True."""
        import zipfile
        docx_path = tmp_path / "hansi_only.docx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r>'
            '<w:rPr><w:rFonts w:hAnsi="SutonnyMJ"/></w:rPr>'
            '<w:t>evsjv</w:t>'
            '</w:r></w:p></w:body></w:document>'
        )
        with zipfile.ZipFile(str(docx_path), "w") as z:
            z.writestr("word/document.xml", xml)
        assert _docx_font_has_bijoy(str(docx_path)) is True

    def test_bijoy_font_in_styles_xml_detected(self, tmp_path):
        """Font declared only in word/styles.xml (paragraph style) is also detected."""
        import zipfile
        docx_path = tmp_path / "styled.docx"
        doc_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>evsjv</w:t></w:r></w:p></w:body></w:document>'
        )
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:style w:type="paragraph" w:styleId="BijoyNormal">'
            '<w:rPr><w:rFonts w:ascii="SutonnyMJ" w:hAnsi="SutonnyMJ"/></w:rPr>'
            '</w:style></w:styles>'
        )
        with zipfile.ZipFile(str(docx_path), "w") as z:
            z.writestr("word/document.xml", doc_xml)
            z.writestr("word/styles.xml", styles_xml)
        assert _docx_font_has_bijoy(str(docx_path)) is True

    def test_dotx_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.dotx (Word template) is in the DOCX extension list → font detection applies."""
        f = _touch(tmp_path, "template.dotx")
        monkeypatch.setattr(pipeline, "_docx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_dotm_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.dotm (macro-enabled Word template) is in the DOCX extension list → font detection applies."""
        f = _touch(tmp_path, "template.dotm")
        monkeypatch.setattr(pipeline, "_docx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_empty_zip_no_parts_returns_false(self, tmp_path):
        """DOCX ZIP that contains no word/*.xml → parts is empty → False."""
        import zipfile
        docx_path = tmp_path / "no_xml.docx"
        with zipfile.ZipFile(str(docx_path), "w") as z:
            z.writestr("mimetype", "placeholder")
        assert _docx_font_has_bijoy(str(docx_path)) is False


# ── RTF font-name Bijoy detection ─────────────────────────────────────────────

class TestRtfFontDetection:
    def test_bijoy_font_detected(self):
        """SutonnyMJ in fonttbl → True."""
        rtf = r'{\fonttbl{\f0\fnil\fcharset0 SutonnyMJ;}}'
        assert _rtf_font_has_bijoy(rtf) is True

    def test_non_bijoy_font_returns_false(self):
        """Arial is not a Bijoy font → False."""
        rtf = r'{\fonttbl{\f0\fnil\fcharset0 Arial;}}'
        assert _rtf_font_has_bijoy(rtf) is False

    def test_no_fonttbl_returns_false(self):
        """RTF without a fonttbl block → False."""
        rtf = r'{\rtf1\ansi This is plain text with no font table.}'
        assert _rtf_font_has_bijoy(rtf) is False

    def test_siyam_rupali_ansi_detected(self):
        """Multi-word Bijoy font 'Siyam Rupali ANSI' → True."""
        rtf = r'{\fonttbl{\f0\fnil\fcharset0 Siyam Rupali ANSI;}}'
        assert _rtf_font_has_bijoy(rtf) is True

    def test_multiple_fonts_bijoy_among_others(self):
        """SutonnyMJ mixed with non-Bijoy fonts in the same fonttbl → True."""
        rtf = (r'{\fonttbl'
               r'{\f0\fnil\fcharset0 Arial;}'
               r'{\f1\fnil\fcharset0 SutonnyMJ;}'
               r'{\f2\fnil\fcharset0 Times New Roman;}'
               r'}')
        assert _rtf_font_has_bijoy(rtf) is True

    def test_empty_fonttbl_returns_false(self):
        """Empty fonttbl block → False (no font entries to parse)."""
        rtf = r'{\fonttbl}'
        assert _rtf_font_has_bijoy(rtf) is False

    def test_rtf_font_detection_triggers_bijoy_conversion(self, tmp_path, monkeypatch):
        """Pure-ASCII Bijoy RTF + SutonnyMJ font → bijoy step via RTF font detection."""
        f = tmp_path / "bangla.rtf"
        f.write_bytes(b"dummy rtf content")
        monkeypatch.setattr(pipeline, "_STRIPRTF_AVAILABLE", True)
        monkeypatch.setattr(pipeline, "_rtf_to_text", lambda raw: "evsjv")
        monkeypatch.setattr(pipeline, "_rtf_font_has_bijoy", lambda raw: True)
        out = convert_file(
            str(f),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"


# ── PPTX font-name Bijoy detection ───────────────────────────────────────────

class TestPptxFontDetection:
    def _make_pptx_with_font(self, tmp_path, font_name, ext="pptx"):
        """Minimal PPTX ZIP containing one slide with the given font name."""
        import zipfile
        pptx_path = tmp_path / f"test.{ext}"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            '       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:spTree><p:sp><p:txBody><a:p><a:r>'
            f'<a:rPr><a:latin typeface="{font_name}"/></a:rPr>'
            '<a:t>evsjv</a:t>'
            '</a:r></a:p></p:txBody></p:sp></p:spTree></p:sld>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/slides/slide1.xml", xml)
        return str(pptx_path)

    def test_bijoy_font_detected(self, tmp_path):
        """SutonnyMJ in slide a:latin typeface → True."""
        assert _pptx_font_has_bijoy(self._make_pptx_with_font(tmp_path, "SutonnyMJ")) is True

    def test_non_bijoy_font_returns_false(self, tmp_path):
        """Calibri is not a Bijoy font → False."""
        assert _pptx_font_has_bijoy(self._make_pptx_with_font(tmp_path, "Calibri")) is False

    def test_theme_font_ref_skipped(self, tmp_path):
        """Theme font references (+mj-lt, +mn-lt) must not trigger Bijoy detection."""
        assert _pptx_font_has_bijoy(self._make_pptx_with_font(tmp_path, "+mn-lt")) is False

    def test_invalid_zip_returns_false(self, tmp_path):
        """Non-ZIP file doesn't raise — just returns False."""
        bad = tmp_path / "bad.pptx"
        bad.write_bytes(b"not a zip file at all")
        assert _pptx_font_has_bijoy(str(bad)) is False

    def test_pptm_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.pptm (macro-enabled PPTX) shares the same ZIP structure → font detection applies."""
        f = _touch(tmp_path, "macro.pptm")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_pptx_font_detection_triggers_bijoy_conversion(self, tmp_path, monkeypatch):
        """ASCII-only Bijoy PPTX + SutonnyMJ font → bijoy step via font detection."""
        f = _touch(tmp_path, "slides.pptx")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_ppsx_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.ppsx (PowerPoint Show) is in _PPTX_EXTS → font detection applies."""
        f = _touch(tmp_path, "show.ppsx")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_cs_font_tag_detected(self, tmp_path):
        """Bijoy font on a:cs (complex-script tag) → True."""
        import zipfile
        pptx_path = tmp_path / "cs_font.pptx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            '       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:spTree><p:sp><p:txBody><a:p><a:r>'
            '<a:rPr><a:cs typeface="SutonnyMJ"/></a:rPr>'
            '<a:t>evsjv</a:t>'
            '</a:r></a:p></p:txBody></p:sp></p:spTree></p:sld>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/slides/slide1.xml", xml)
        assert _pptx_font_has_bijoy(str(pptx_path)) is True

    def test_slide_master_font_detected(self, tmp_path):
        """Bijoy font in a slide master (ppt/slideMasters/) is also scanned → True."""
        import zipfile
        pptx_path = tmp_path / "master_font.pptx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sldMaster xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            '             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:spTree><p:sp><p:txBody><a:p><a:r>'
            '<a:rPr><a:latin typeface="SutonnyMJ"/></a:rPr>'
            '<a:t>evsjv</a:t>'
            '</a:r></a:p></p:txBody></p:sp></p:spTree></p:sldMaster>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/slideMasters/slideMaster1.xml", xml)
        assert _pptx_font_has_bijoy(str(pptx_path)) is True

    def test_theme_font_detected(self, tmp_path):
        """Bijoy font in the theme file (ppt/theme/) is also scanned → True."""
        import zipfile
        pptx_path = tmp_path / "theme_font.pptx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"'
            '         name="BijoyTheme">'
            '<a:themeElements>'
            '<a:fontScheme name="Office">'
            '<a:majorFont><a:latin typeface="SutonnyMJ"/></a:majorFont>'
            '</a:fontScheme>'
            '</a:themeElements>'
            '</a:theme>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/theme/theme1.xml", xml)
        assert _pptx_font_has_bijoy(str(pptx_path)) is True

    def test_slide_layout_font_detected(self, tmp_path):
        """Bijoy font in a slide layout (ppt/slideLayouts/) is also scanned → True."""
        import zipfile
        pptx_path = tmp_path / "layout_font.pptx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sldLayout xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            '             xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:spTree><p:sp><p:txBody><a:p><a:r>'
            '<a:rPr><a:latin typeface="SutonnyMJ"/></a:rPr>'
            '<a:t>evsjv</a:t>'
            '</a:r></a:p></p:txBody></p:sp></p:spTree></p:sldLayout>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/slideLayouts/slideLayout1.xml", xml)
        assert _pptx_font_has_bijoy(str(pptx_path)) is True

    def test_ea_font_tag_detected(self, tmp_path):
        """Bijoy font in a:ea (East Asian) run property tag → True."""
        import zipfile
        pptx_path = tmp_path / "ea_font.pptx"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"'
            '       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            '<p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r>'
            '<a:rPr><a:ea typeface="SutonnyMJ"/></a:rPr>'
            '<a:t>evsjv</a:t>'
            '</a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld></p:sld>'
        )
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("ppt/slides/slide1.xml", xml)
        assert _pptx_font_has_bijoy(str(pptx_path)) is True

    def test_ppsm_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.ppsm is in _PPTX_EXTS → font detection applies."""
        f = _touch(tmp_path, "show.ppsm")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_potx_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.potx (PowerPoint template) is in _PPTX_EXTS → font detection applies."""
        f = _touch(tmp_path, "template.potx")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_potm_also_triggers_font_detection(self, tmp_path, monkeypatch):
        """.potm (macro-enabled template) is in _PPTX_EXTS → font detection applies."""
        f = _touch(tmp_path, "macro_template.potm")
        monkeypatch.setattr(pipeline, "_pptx_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_empty_zip_no_parts_returns_false(self, tmp_path):
        """PPTX ZIP with no matching XML parts → parts is empty → False."""
        import zipfile
        pptx_path = tmp_path / "empty.pptx"
        with zipfile.ZipFile(str(pptx_path), "w") as z:
            z.writestr("mimetype", "placeholder")
        assert _pptx_font_has_bijoy(str(pptx_path)) is False


# ── ODT font-name Bijoy detection ─────────────────────────────────────────────

class TestOdtFontDetection:
    def _make_odt_svg(self, tmp_path, font_name, ext="odt"):
        """Minimal ODT ZIP with svg:font-family on style:font-face in content.xml."""
        import zipfile
        odt_path = tmp_path / f"test.{ext}"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:svg="http://www.w3.org/2000/svg">'
            '<office:font-face-decls>'
            f'<style:font-face style:name="{font_name}" svg:font-family="{font_name}"/>'
            '</office:font-face-decls>'
            '</office:document-content>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("content.xml", xml)
        return str(odt_path)

    def _make_odt_fo(self, tmp_path, font_name):
        """Minimal ODT ZIP with fo:font-name on style:text-properties in content.xml."""
        import zipfile
        odt_path = tmp_path / "test_fo.odt"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:fo="http://www.w3.org/1999/XSL/Format">'
            '<office:automatic-styles>'
            '<style:style style:name="T1" style:family="text">'
            f'<style:text-properties fo:font-name="{font_name}"/>'
            '</style:style>'
            '</office:automatic-styles>'
            '</office:document-content>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("content.xml", xml)
        return str(odt_path)

    def test_bijoy_svg_font_detected(self, tmp_path):
        """SutonnyMJ in svg:font-family on style:font-face → True."""
        assert _odt_font_has_bijoy(self._make_odt_svg(tmp_path, "SutonnyMJ")) is True

    def test_bijoy_fo_font_detected(self, tmp_path):
        """SutonnyMJ in fo:font-name on style:text-properties → True."""
        assert _odt_font_has_bijoy(self._make_odt_fo(tmp_path, "SutonnyMJ")) is True

    def test_non_bijoy_font_returns_false(self, tmp_path):
        """Liberation Serif is not a Bijoy font → False."""
        assert _odt_font_has_bijoy(self._make_odt_svg(tmp_path, "Liberation Serif")) is False

    def test_invalid_zip_returns_false(self, tmp_path):
        """Non-ZIP file doesn't raise — just returns False."""
        bad = tmp_path / "bad.odt"
        bad.write_bytes(b"not a zip file at all")
        assert _odt_font_has_bijoy(str(bad)) is False

    def test_odt_font_detection_triggers_bijoy_conversion(self, tmp_path, monkeypatch):
        """ASCII-only Bijoy ODT + SutonnyMJ font → bijoy step via font detection."""
        f = _touch(tmp_path, "doc.odt")
        monkeypatch.setattr(pipeline, "_odt_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_odt_empty_zip_returns_false(self, tmp_path):
        """ZIP with no content.xml or styles.xml → parts is empty → False."""
        import zipfile
        odt_path = tmp_path / "no_xml.odt"
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        assert _odt_font_has_bijoy(str(odt_path)) is False

    def test_bijoy_font_in_styles_xml_detected(self, tmp_path):
        """SutonnyMJ declared only in styles.xml (not content.xml) is also detected."""
        import zipfile
        odt_path = tmp_path / "styles_only.odt"
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-styles'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:svg="http://www.w3.org/2000/svg">'
            '<office:font-face-decls>'
            '<style:font-face style:name="SutonnyMJ" svg:font-family="SutonnyMJ"/>'
            '</office:font-face-decls>'
            '</office:document-styles>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("styles.xml", styles_xml)
        assert _odt_font_has_bijoy(str(odt_path)) is True

    def test_comma_suffix_in_svg_font_family_stripped(self, tmp_path):
        """svg:font-family='SutonnyMJ,Bold' → comma stripped → 'sutonnymj' → True."""
        import zipfile
        odt_path = tmp_path / "comma_font.odt"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:svg="http://www.w3.org/2000/svg">'
            '<office:font-face-decls>'
            '<style:font-face style:name="SutonnyMJ" svg:font-family="SutonnyMJ,Bold"/>'
            '</office:font-face-decls>'
            '</office:document-content>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("content.xml", xml)
        assert _odt_font_has_bijoy(str(odt_path)) is True

    def test_bijoy_fo_font_in_styles_xml_detected(self, tmp_path):
        """SutonnyMJ in fo:font-name on styles.xml (not content.xml) → True."""
        import zipfile
        odt_path = tmp_path / "styles_fo.odt"
        styles_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-styles'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:fo="http://www.w3.org/1999/XSL/Format">'
            '<office:styles>'
            '<style:style style:name="Default" style:family="paragraph">'
            '<style:text-properties fo:font-name="SutonnyMJ"/>'
            '</style:style>'
            '</office:styles>'
            '</office:document-styles>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("styles.xml", styles_xml)
        assert _odt_font_has_bijoy(str(odt_path)) is True

    def test_ott_extension_triggers_font_detection(self, tmp_path, monkeypatch):
        """.ott (ODF template) is also in _ODT_EXTS → font detection applies."""
        f = _touch(tmp_path, "template.ott")
        monkeypatch.setattr(pipeline, "_odt_font_has_bijoy", lambda p: True)
        out = convert_file(
            str(f),
            markitdown=FakeMarkItDown("evsjv"),
            auto_bijoy=True,
            is_bijoy_func=lambda t: False,
            bijoy_func=lambda t: "বাংলা",
        )
        assert "bijoy" in out["steps"]
        assert out["text"] == "বাংলা"

    def test_fo_font_name_comma_suffix_stripped(self, tmp_path):
        """fo:font-name='SutonnyMJ,Bold' → comma stripped before lookup → True."""
        import zipfile
        odt_path = tmp_path / "fo_comma.odt"
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<office:document-content'
            '  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"'
            '  xmlns:style="urn:oasis:names:tc:opendocument:xmlns:style:1.0"'
            '  xmlns:fo="http://www.w3.org/1999/XSL/Format">'
            '<office:automatic-styles>'
            '<style:style style:name="T1" style:family="text">'
            '<style:text-properties fo:font-name="SutonnyMJ,Bold"/>'
            '</style:style>'
            '</office:automatic-styles>'
            '</office:document-content>'
        )
        with zipfile.ZipFile(str(odt_path), "w") as z:
            z.writestr("content.xml", xml)
        assert _odt_font_has_bijoy(str(odt_path)) is True
