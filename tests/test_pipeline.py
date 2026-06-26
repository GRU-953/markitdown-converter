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
    convert_file, is_image, is_legacy_doc, is_unsupported, is_rtf, is_xlsx, is_plain_text,
    _read_plain_text, _extract_xlsx_direct, _extract_legacy_doc, _docx_font_has_bijoy,
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


# ── document path ───────────────────────────────────────────────────────────

class TestDocumentConversion:
    def test_uses_markitdown_for_documents(self, tmp_path):
        f = _touch(tmp_path, "doc.pdf")
        md = FakeMarkItDown("# Hello")
        out = convert_file(f, markitdown=md)
        assert out["text"] == "# Hello"
        assert out["steps"] == ["markitdown"]
        assert md.calls == [f]

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

    def test_doc_ole_step_on_success(self, tmp_path, monkeypatch):
        """When OLE extraction succeeds, 'doc_ole' appears and MarkItDown is not called."""
        f = _touch(tmp_path, "old.doc")
        monkeypatch.setattr(pipeline, "_extract_legacy_doc", lambda path: "Extracted content")
        out = convert_file(str(f), auto_bijoy=False)
        assert "doc_ole" in out["steps"]
        assert "doc_empty" not in out["steps"]
        assert out["text"] == "Extracted content"


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
