"""
Tests for bijoy_unicode.py — conversion correctness and script detection.
All tests are pure Python; no system dependencies required.
"""

import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def nfc(s):
    """Normalise to NFC so ya+nukta (U+09AF U+09BC) == yya (U+09DF)."""
    return unicodedata.normalize("NFC", s)

from bijoy_unicode import convert_bijoy_to_unicode, detect_script, is_bijoy


# ── detect_script ─────────────────────────────────────────────────────────────

class TestDetectScript:
    def test_bijoy_indicator_char(self):
        # 0xB0 ("°") is in the Bijoy detection range (0x00A0-0x00FF)
        assert detect_script("°") == "bijoy"

    def test_bijoy_indicator_wins_over_latin(self):
        assert detect_script("° Hello") == "bijoy"

    def test_unicode_bengali(self):
        assert detect_script("আমি বাংলায় লিখি") == "unicode_bn"

    def test_unicode_bengali_single_char(self):
        assert detect_script("ক") == "unicode_bn"

    def test_latin(self):
        assert detect_script("Hello world") == "latin"

    def test_latin_single_word(self):
        assert detect_script("Python") == "latin"

    def test_empty_returns_other(self):
        assert detect_script("") == "other"

    def test_digits_only_returns_other(self):
        assert detect_script("12345") == "other"


# ── is_bijoy ──────────────────────────────────────────────────────────────────

class TestIsBijoy:
    def test_bijoy_char_true(self):
        assert is_bijoy("°") is True

    def test_unicode_bengali_false(self):
        assert is_bijoy("আমি") is False

    def test_latin_false(self):
        assert is_bijoy("Hello") is False

    def test_empty_false(self):
        assert is_bijoy("") is False


# ── convert_bijoy_to_unicode ──────────────────────────────────────────────────

class TestConvertBijoyToUnicode:
    def test_empty_passthrough(self):
        assert convert_bijoy_to_unicode("") == ""

    # Single-character consonant mappings (ASCII range, direct)
    def test_consonant_k(self):
        assert convert_bijoy_to_unicode("K") == "ক"

    def test_consonant_kh(self):
        assert convert_bijoy_to_unicode("L") == "খ"

    def test_consonant_g(self):
        assert convert_bijoy_to_unicode("M") == "গ"

    def test_consonant_n(self):
        assert convert_bijoy_to_unicode("b") == "ন"

    def test_consonant_m(self):
        assert convert_bijoy_to_unicode("g") == "ম"

    # Vowel
    def test_vowel_a(self):
        assert convert_bijoy_to_unicode("A") == "অ"

    # Two-char special combo
    def test_combo_av_gives_aa_vowel(self):
        assert convert_bijoy_to_unicode("Av") == "আ"

    # Bengali digits
    def test_digit_zero(self):
        assert convert_bijoy_to_unicode("0") == "০"

    def test_digits_sequence(self):
        assert convert_bijoy_to_unicode("123") == "১২৩"

    def test_all_digits(self):
        assert convert_bijoy_to_unicode("0123456789") == "০১২৩৪৫৬৭৮৯"

    # Word-level: বাংলা
    def test_word_bangla(self):
        # e=ব v=া s=ং j=ল v=া  →  বাংলা
        assert convert_bijoy_to_unicode("evsjv") == "বাংলা"

    # Classic phrase: আমি বাংলায় লিখি
    def test_phrase_ami_banglay_likhi(self):
        result = convert_bijoy_to_unicode("Avwg evsjvq wjwL")
        assert nfc(result) == nfc("আমি বাংলায় লিখি")

    # Output should contain Bengali Unicode code points (U+0980–U+09FF)
    def test_output_is_unicode_bengali(self):
        result = convert_bijoy_to_unicode("evsjv")
        assert all(0x0980 <= ord(c) <= 0x09FF or c == " " for c in result)
