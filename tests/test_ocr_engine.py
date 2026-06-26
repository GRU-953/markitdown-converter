"""
Tests for ocr_engine.py — language codes, availability check, error handling.
Tesseract does not need to be installed for these tests to pass.
"""

import sys
import unittest.mock
from pathlib import Path

import pytest
import pytesseract
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_engine import LANG_CODES, ocr_image, ocr_pdf, tesseract_available, pymupdf_available, _setup_tesseract


# ── LANG_CODES ────────────────────────────────────────────────────────────────

class TestLangCodes:
    def test_english_key_present(self):
        assert "English" in LANG_CODES

    def test_bangla_key_present(self):
        assert "বাংলা" in LANG_CODES

    def test_both_key_present(self):
        assert "Both" in LANG_CODES

    def test_english_value(self):
        assert LANG_CODES["English"] == "eng"

    def test_bangla_value(self):
        assert LANG_CODES["বাংলা"] == "ben"

    def test_both_value(self):
        assert LANG_CODES["Both"] == "eng+ben"


# ── tesseract_available ───────────────────────────────────────────────────────

class TestTesseractAvailable:
    def test_returns_bool(self):
        result = tesseract_available()
        assert isinstance(result, bool)


# ── ocr_image error handling ──────────────────────────────────────────────────

class TestOcrImageErrors:
    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            ocr_image("/nonexistent/path/image.png")

    def test_missing_file_message_contains_path(self):
        path = "/nonexistent/image.png"
        with pytest.raises(FileNotFoundError, match=path):
            ocr_image(path)


# ── _setup_tesseract (PyInstaller bundle path) ────────────────────────────────

class TestSetupTesseractBundle:
    def test_bundle_path_sets_tesseract_cmd(self):
        with unittest.mock.patch.object(sys, "_MEIPASS", "/fake/bundle", create=True), \
             unittest.mock.patch.object(Path, "exists", return_value=True):
            _setup_tesseract()
            assert "tesseract.exe" in pytesseract.pytesseract.tesseract_cmd

    def test_bundle_path_sets_tessdata_prefix(self, monkeypatch):
        monkeypatch.delenv("TESSDATA_PREFIX", raising=False)
        with unittest.mock.patch.object(sys, "_MEIPASS", "/fake/bundle", create=True), \
             unittest.mock.patch.object(Path, "exists", return_value=True):
            _setup_tesseract()
            import os
            assert "TESSDATA_PREFIX" in os.environ

    def test_bundle_path_exe_not_found_leaves_cmd_unchanged(self):
        orig_cmd = pytesseract.pytesseract.tesseract_cmd
        with unittest.mock.patch.object(sys, "_MEIPASS", "/fake/bundle", create=True), \
             unittest.mock.patch.object(Path, "exists", return_value=False):
            _setup_tesseract()
            assert pytesseract.pytesseract.tesseract_cmd == orig_cmd


# ── ocr_image (mocked pytesseract) ───────────────────────────────────────────

class TestOcrImageWithMock:
    def test_returns_extracted_text(self, tmp_path):
        img_file = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(str(img_file))
        with unittest.mock.patch("pytesseract.image_to_string", return_value="Hello"):
            assert ocr_image(str(img_file)) == "Hello"

    def test_strips_whitespace(self, tmp_path):
        img_file = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(str(img_file))
        with unittest.mock.patch("pytesseract.image_to_string", return_value="  text  \n"):
            assert ocr_image(str(img_file)) == "text"

    def test_unknown_language_falls_back_to_eng(self, tmp_path):
        img_file = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(str(img_file))
        with unittest.mock.patch("pytesseract.image_to_string", return_value="ok") as m:
            ocr_image(str(img_file), language="Unknown")
            m.assert_called_once()
            assert m.call_args.kwargs.get("lang") == "eng" or m.call_args[1].get("lang") == "eng"

    def test_tesseract_not_found_raises_runtime(self, tmp_path):
        img_file = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(str(img_file))
        with unittest.mock.patch("pytesseract.image_to_string",
                                  side_effect=pytesseract.TesseractNotFoundError):
            with pytest.raises(RuntimeError, match="Tesseract not found"):
                ocr_image(str(img_file))

    def test_generic_exception_raises_runtime(self, tmp_path):
        img_file = tmp_path / "test.png"
        Image.new("RGB", (100, 50), color="white").save(str(img_file))
        with unittest.mock.patch("pytesseract.image_to_string",
                                  side_effect=ValueError("boom")):
            with pytest.raises(RuntimeError, match="OCR failed"):
                ocr_image(str(img_file))


# ── tesseract_available → True ────────────────────────────────────────────────

class TestTesseractAvailableTrue:
    def test_returns_true_when_reachable(self):
        with unittest.mock.patch("pytesseract.get_tesseract_version", return_value="5.0"):
            assert tesseract_available() is True

    def test_returns_false_when_not_reachable(self):
        with unittest.mock.patch("pytesseract.get_tesseract_version",
                                  side_effect=Exception("not found")):
            assert tesseract_available() is False


# ── pymupdf_available ─────────────────────────────────────────────────────────

class TestPymupdfAvailable:
    def test_returns_true_when_available(self):
        fake_mod = unittest.mock.MagicMock()
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": fake_mod}):
            assert pymupdf_available() is True

    def test_returns_false_when_not_installed(self):
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": None}):
            assert pymupdf_available() is False


# ── ocr_pdf error handling ────────────────────────────────────────────────────

class TestOcrPdf:
    def test_missing_file_raises_file_not_found(self):
        fake_mod = unittest.mock.MagicMock()
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": fake_mod}):
            with pytest.raises(FileNotFoundError):
                ocr_pdf("/nonexistent/path/doc.pdf")

    def test_pymupdf_not_installed_raises_runtime(self):
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": None}):
            with pytest.raises(RuntimeError, match="pymupdf"):
                ocr_pdf("/any/path.pdf")

    def test_pdf_open_failure_raises_runtime(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"dummy")
        fake_pymupdf = unittest.mock.MagicMock()
        fake_pymupdf.open.side_effect = Exception("corrupt")
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": fake_pymupdf}):
            with pytest.raises(RuntimeError, match="Could not open PDF"):
                ocr_pdf(str(f))

    def _make_mock_doc(self):
        """Return a (fake_pymupdf, mock_doc, mock_page) trio for per-page tests."""
        mock_pix = unittest.mock.MagicMock()
        mock_pix.width = 1
        mock_pix.height = 1
        mock_pix.samples = b"\x00\x00\x00"
        mock_page = unittest.mock.MagicMock()
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = unittest.mock.MagicMock()
        mock_doc.__iter__ = unittest.mock.MagicMock(side_effect=lambda: iter([mock_page]))
        fake_pymupdf = unittest.mock.MagicMock()
        fake_pymupdf.open.return_value = mock_doc
        return fake_pymupdf, mock_doc, mock_page

    def test_bad_page_skipped_returns_empty(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"dummy")
        fake_pymupdf, _, _ = self._make_mock_doc()
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": fake_pymupdf}), \
             unittest.mock.patch("pytesseract.image_to_string",
                                  side_effect=ValueError("bad image")):
            result = ocr_pdf(str(f))
        assert result == ""

    def test_tesseract_not_found_per_page_raises_runtime(self, tmp_path):
        f = tmp_path / "doc.pdf"
        f.write_bytes(b"dummy")
        fake_pymupdf, _, _ = self._make_mock_doc()
        with unittest.mock.patch.dict(sys.modules, {"pymupdf": fake_pymupdf}), \
             unittest.mock.patch("pytesseract.image_to_string",
                                  side_effect=pytesseract.TesseractNotFoundError):
            with pytest.raises(RuntimeError, match="Tesseract not found"):
                ocr_pdf(str(f))
