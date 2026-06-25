"""
Tests for pipeline.py — the unified MarkItDown -> OCR -> Bijoy chain.
All external converters are injected as fakes, so no MarkItDown/Tesseract needed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import pipeline
from pipeline import convert_file, is_image


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
        out = convert_file(f, markitdown=md, auto_ocr=False)
        assert out["text"] == ""
        assert out["steps"] == ["markitdown"]

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

    def test_auto_ocr_disabled_falls_back_to_markitdown(self, tmp_path):
        f = _touch(tmp_path, "scan.png")
        md = FakeMarkItDown("from markitdown")
        out = convert_file(f, auto_ocr=False, markitdown=md)
        assert out["text"] == "from markitdown"
        assert out["steps"] == ["markitdown"]


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
