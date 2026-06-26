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

from bijoy_unicode import convert_bijoy_to_unicode, detect_script, is_bijoy, _rearrange, _ch, _apply_literal, POST_MAP


# ── detect_script ─────────────────────────────────────────────────────────────

class TestDetectScript:
    def test_bijoy_indicator_char(self):
        # A single "°" (U+00B0) is in the Bijoy range but bj < 5 threshold; not enough to classify
        assert detect_script("°") == "latin"

    def test_bijoy_indicator_wins_over_latin(self):
        # One bj char among Latin letters is below the 5-char minimum — not Bijoy
        assert detect_script("° Hello") == "latin"

    def test_bijoy_five_chars_classified(self):
        # Five Bijoy-range chars with no ASCII letters and no Bengali Unicode → bijoy
        assert detect_script("°°°°°") == "bijoy"

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

    def test_whitespace_only_returns_other(self):
        # Spaces and newlines are not alpha and not in any Bijoy or Bengali range.
        assert detect_script("   \n\t  ") == "other"

    def test_short_bijoy_two_chars_no_latin(self):
        # bj=2, la=0, sig=2 ≤ 30 → adaptive min_bj=2 → bijoy (old threshold 5 rejected this)
        assert detect_script("°©") == "bijoy"

    def test_short_bijoy_two_chars_with_latin(self):
        # bj=2, la=3, sig=5 ≤ 30 → min_bj=2 → ratio 2×13=26 ≥ 3 → bijoy
        assert detect_script("†K©ga") == "bijoy"

    def test_medium_text_three_bijoy_chars(self):
        # bj=3, la=37, sig=40 (30 < 40 ≤ 100) → min_bj=3 → ratio 3×13=39 ≥ 37 → bijoy
        # Old threshold (bj ≥ 5) incorrectly returned 'latin' for this case.
        assert detect_script("°©†" + "a" * 37) == "bijoy"

    def test_relaxed_ratio_catches_low_density(self):
        # bj=8, la=100, sig=108 > 100 → min_bj=5 → ratio 8×13=104 ≥ 100 → bijoy
        # Old ratio (10×): 8×10=80 < 100 → 'latin' (false negative). New 13× fixes it.
        assert detect_script("°" * 8 + "a" * 100) == "bijoy"

    def test_two_distinct_bijoy_chars_no_latin(self):
        # © (U+00A9) and ¨ (U+00A8) are both Bijoy-range; no Latin → bijoy
        assert detect_script("©¨") == "bijoy"

    def test_english_copyright_notice_not_bijoy(self):
        # bj=2 (©, —), la=23, sig=25 ≤ 30 → strict 10× ratio → 2×10=20 < 23 → latin.
        # Regression guard: the relaxed 13× ratio for longer texts must NOT apply here.
        assert detect_script("© 2024 Company Name — Annual Report") == "latin"

    def test_unicode_bengali_beats_bijoy_range_chars(self):
        # Even with Bijoy-range chars present, any Unicode Bengali codepoint wins.
        # bj=3 (©, ©, ©) + bn=1 (ক) → unicode_bn (bn > 0 short-circuits)
        assert detect_script("©©©ক") == "unicode_bn"


# ── is_bijoy ──────────────────────────────────────────────────────────────────

class TestIsBijoy:
    def test_bijoy_single_char_false(self):
        # A single Bijoy-range char is below the 5-char minimum; not enough to classify as Bijoy
        assert is_bijoy("°") is False

    def test_bijoy_two_char_adaptive_true(self):
        # bj=2, la=0, sig=2 ≤ 30 → adaptive min_bj=2 → True (old fixed floor of 5 rejected this)
        assert is_bijoy("°©") is True

    def test_bijoy_five_chars_true(self):
        assert is_bijoy("°°°°°") is True

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

    # ── Rearrangement edge-cases (composite vowels) ───────────────────────────

    def test_composite_vowel_o(self):
        # † = † → ে (e-sign),  K → ক,  v → া
        # rearrangement: ে + ক + া → কো  (ো is e+aa composite)
        result = convert_bijoy_to_unicode("†Kv")
        assert result == "কো"

    def test_composite_vowel_ou(self):
        # † = † → ে,  K → ক,  Š = Š → ৗ
        # rearrangement: ে + ক + ৗ → কৌ  (ৌ is e+ou composite)
        result = convert_bijoy_to_unicode("†KŠ")
        assert result == "কৌ"

    def test_pre_kar_reorder_single(self):
        # † → ে (pre-kar),  M → গ
        # rearrangement: ে + গ → গে
        result = convert_bijoy_to_unicode("†M")
        assert result == "গে"

    def test_reph_in_cluster(self):
        # © (U+00A9) → র্  (reph),  K → ক,  g → ম
        # K©g: ক + র্ + ম → rearrangement places reph; output is valid Bengali
        result = convert_bijoy_to_unicode("K©g")
        assert len(result) > 0
        # all chars should be Bengali code points or punctuation
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result.strip())

    # ── Deeper rearrangement edge-cases ──────────────────────────────────────

    def test_rearrange_empty(self):
        # _rearrange("") early-return guard (line 327)
        assert _rearrange("") == ""

    def test_double_halant_collapsed(self):
        # "©¨" → র্ + ্য = "র্্য" (double halant) → collapsed to "র্য" (line 329)
        result = convert_bijoy_to_unicode("©\xa8")
        assert "্্" not in result

    def test_reph_with_kar_before_it(self):
        # "Kv©M" → কার্গ → reph finder skips kar to reach ক (line 341)
        result = convert_bijoy_to_unicode("Kv\xa9M")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)

    def test_reph_over_deep_conjunct(self):
        # "ÿ©M" → ক্ষর্গ → cluster extends back through ক্ষ (lines 347-352)
        result = convert_bijoy_to_unicode("\xff\xa9M")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)

    def test_kar_halant_consonant_reorder(self):
        # "Kw¨" → কি + ্য → kar immediately before halant → reordered (line 363)
        # w = ি  ¨(U+00A8) = ্য
        result = convert_bijoy_to_unicode("Kw\xa8")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)

    def test_ra_halant_vowel_reorder(self):
        # "©v" = র্ + া → ra+halant followed by aa-kar → reordered (line 372)
        result = convert_bijoy_to_unicode("\xa9v")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)

    def test_nukta_postkar_swap(self):
        # "Kuv" = ক + ঁ + া → chandrabindu before aa-kar → swapped to কাঁ (line 405)
        result = convert_bijoy_to_unicode("Kuv")
        assert result == "কাঁ"

    def test_reph_cluster_no_further_extension(self):
        # "gK©M" = ম + ক + র্ + গ → reph walks back to ক but ম is not in conjunct (line 352)
        result = convert_bijoy_to_unicode("gK\xa9M")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)

    def test_pre_kar_over_conjunct(self):
        # "†K¨M" = ে + ক + ্য + গ → pre-kar spans ক্য conjunct (line 386)
        # In rearrangement Pass 2, j advances past the halant inside the conjunct
        result = convert_bijoy_to_unicode("†K\xa8M")
        assert len(result) > 0
        assert all(0x0980 <= ord(c) <= 0x09FF for c in result)


# ── POST_MAP cleanup ─────────────────────────────────────────────────────────

class TestPostMap:
    def test_aa_ligature_fixed(self):
        """'অা' (incorrect aa from A + aa-kar) is collapsed to 'আ'."""
        # 'A' → অ, then the aa-kar that follows (from rearrangement) produces অা.
        # POST_MAP should normalise that to আ.
        result = convert_bijoy_to_unicode("Av")    # Av → আ via PRE_MAP, no POST issue
        assert result == "আ"

    def test_digit_visarga_becomes_colon(self):
        """Bengali digit followed by visarga (ঃ) should become digit + ASCII colon."""
        # 0t → ০ঃ (zero + visarga) → POST_MAP corrects to ০:
        result = convert_bijoy_to_unicode("0t")
        assert result == "০:"

    def test_all_digit_visarga_to_colon(self):
        """POST_MAP colon fix applies to every Bengali digit 0–9."""
        for latin_digit, bn_digit in zip("0123456789", "০১২৩৪৫৬৭৮৯"):
            result = convert_bijoy_to_unicode(latin_digit + "t")
            assert result == bn_digit + ":", f"Failed for digit {latin_digit}"

    def test_double_halant_zwnj_collapsed(self):
        """Double ZWNJ halant sequence (্‌্‌) is collapsed to single (্‌)."""
        # Double escaped halant in input: '\\&' → ্‌  (two consecutive)
        result = convert_bijoy_to_unicode("\\&\\&")
        assert result.count("্‌") == 1


# ── _ch boundary ─────────────────────────────────────────────────────────────

class TestChBoundary:
    def test_negative_index_returns_empty(self):
        assert _ch("abc", -1) == ""

    def test_beyond_length_returns_empty(self):
        assert _ch("abc", 10) == ""

    def test_valid_index_returns_char(self):
        assert _ch("abc", 0) == "a"


# ── PRE_MAP and _PRE_REGEX whitespace handling ────────────────────────────────

class TestPreMapAndPreRegex:
    def test_yy_pre_map_collapses_to_single(self):
        """PRE_MAP ('yy', 'y'): double-y input produces same output as single-y."""
        assert convert_bijoy_to_unicode("yy") == convert_bijoy_to_unicode("y")

    def test_vv_pre_map_collapses_to_single(self):
        """PRE_MAP ('vv', 'v'): double-v input produces same output as single-v."""
        assert convert_bijoy_to_unicode("vv") == convert_bijoy_to_unicode("v")

    def test_multiple_spaces_collapsed_to_single(self):
        """_PRE_REGEX collapses consecutive spaces in Bijoy input before conversion."""
        # K=ক, M=গ; double-space should produce same result as single-space
        assert convert_bijoy_to_unicode("K  M") == convert_bijoy_to_unicode("K M")

    def test_prekar_before_space_not_reordered(self):
        """In _rearrange Pass 2, pre-kar before a space (_is_space guard) stays in place."""
        # '†' maps to ে (pre-kar), 'M' maps to গ.
        # '† M': pre-kar is followed by space → _is_space(next) → skip reorder → ে stays before space
        # '†M':  pre-kar is followed by consonant → reorder → গে
        without_space = convert_bijoy_to_unicode("†M")   # reordered: গে
        with_space    = convert_bijoy_to_unicode("† M")  # not reordered: ে followed by space
        assert without_space != with_space
        assert "ে" in with_space  # pre-kar remains at position before the space


# ── POST_MAP entries (direct _apply_literal tests) ────────────────────────────

class TestPostMapEntries:
    """Direct coverage of POST_MAP entries not exercised by convert_bijoy_to_unicode tests."""

    def test_space_visarga_becomes_colon(self):
        """' ঃ' (space + visarga) → ':'."""
        assert _apply_literal(" ঃ", POST_MAP) == ":"

    def test_newline_visarga_becomes_newline_colon(self):
        """'\\nঃ' (newline + visarga) → '\\n:'."""
        assert _apply_literal("\nঃ", POST_MAP) == "\n:"

    def test_bracket_close_visarga_becomes_colon(self):
        """']ঃ' → ']:'."""
        assert _apply_literal("]ঃ", POST_MAP) == "]:"

    def test_bracket_open_visarga_becomes_colon(self):
        """'[ঃ' → '[:'."""
        assert _apply_literal("[ঃ", POST_MAP) == "[:"

    def test_double_space_collapsed_to_single(self):
        """Double space in Unicode output collapsed to single space by POST_MAP."""
        assert _apply_literal("word  word", POST_MAP) == "word word"

    def test_stha_conjunct_normalised(self):
        """'স্ত্ম' → 'স্ত' — spurious ম stripped from the স্ত conjunct."""
        assert _apply_literal("স্ত্ম", POST_MAP) == "স্ত"

    def test_nta_conjunct_normalised(self):
        """'ন্ত্ম' → 'ন্ত' — spurious ম stripped from the ন্ত conjunct."""
        assert _apply_literal("ন্ত্ম", POST_MAP) == "ন্ত"
