"""
Tests for ocr_engine.py — language codes, availability check, error handling.
Tesseract does not need to be installed for these tests to pass.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_engine import LANG_CODES, ocr_image, tesseract_available


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
