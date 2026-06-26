# Changelog

All notable changes to GRU953 Markdown are documented here.

---

## [v4.10.70] — 2026-06-27

### Tests — malformed-XML and XLSX MemoryError branches (339 total, up from 335)

Four new tests covering the `except Exception: pass` exception-silencing paths in font detection
and the XLSX MemoryError fallback distinction:

- `TestDocxFontDetection` (1): valid DOCX ZIP but malformed `word/document.xml` → `ET.fromstring` raises → caught → `False`
- `TestPptxFontDetection` (1): valid PPTX ZIP but malformed `ppt/slides/slide1.xml` → `ET.fromstring` raises → caught → `False`
- `TestXlsxFontDetection` (1): valid XLSX ZIP but malformed `xl/styles.xml` → `ET.fromstring` raises → caught → `False`
- `TestXlsx` (1): real `MemoryError` from MarkItDown in the XLSX branch is caught by `except Exception` and falls back to `xlsx_direct` — NOT re-raised as `ValueError` like the generic and PDF branches

---

## [v4.10.69] — 2026-06-27

### Tests — attribute-guard and cp0 boundary branches (335 total, up from 331)

Four new tests covering previously untested attribute-guard and boundary paths:

- `TestPptxFontDetection` (1): `typeface=""` (attribute present but empty) — `not val` guard fires → element skipped → `False`; distinct from the `+` theme-font-ref case
- `TestDocxFontDetection` (1): `w:rFonts w:ascii="Arial" w:hAnsi="SutonnyMJ"` — loop over all `attrib.values()` continues past non-Bijoy first attr, finds Bijoy in second → `True`
- `TestExtractLegacyDoc` (1): `cp0 = 512 = len(data)` — fails the strict `0 < cp0 < len(data)` (boundary value, not `<=`) → `text_start` stays `None` → fallback scan used
- `TestOdtFontDetection` (1): `svg:font-family=""` (attribute present in XML but empty string) — `if val:` guard → `False`; distinct from the absent-attribute case

---

## [v4.10.68] — 2026-06-27

### Fix — macOS resource-fork sidecar files no longer crash the pipeline (331 tests)

macOS writes binary `._<filename>` sidecar files inside ZIP archives to store extended
attributes.  These files look like images by extension but are not readable by PIL,
causing `RuntimeError: OCR failed: cannot identify image file` for every such file.

`convert_file` now checks `path.name.startswith("._")` immediately after the
unsupported-format guard and returns `{"text": "", "steps": ["mac_resource_fork"]}`
without attempting OCR.  This eliminates the 7 ERRORs seen in the integration audit
of `D:\Test_files` (972 files) where macOS ZIP archives had deposited these sidecars.

One new test: `TestUnsupported.test_mac_resource_fork_returns_empty` — a `._photo.jpg`
file yields empty text and the `mac_resource_fork` step, no exception.

---

## [v4.10.67] — 2026-06-27

### Tests — whitespace normalisation and FIB guard branches (330 total, up from 326)

Four new tests covering previously untested paths in font detection and legacy DOC parsing:

- `TestPptxFontDetection` (1): `typeface="Siyam  Rupali  ANSI"` with internal double spaces — `_WS_RE` collapses before lookup → match found → `True`
- `TestOdtFontDetection` (1): `svg:font-family="Siyam  Rupali  ANSI"` with double spaces → `_WS_RE` collapses → match → `True`
- `TestXlsxFontDetection` (1): `<name val="Siyam  Rupali  ANSI"/>` with double spaces → `_WS_RE` collapses → match → `True`
- `TestExtractLegacyDoc` (1): `cbRgFcLcb=60` pushes `fib_end=518 > 510` → `fib_end+2 <= len(data)` guard fails → `cswNew` is NOT read; scan range is empty → `return ""`

---

## [v4.10.66] — 2026-06-27

### Tests — dispatch and font-detection gaps closed (326 total, up from 321)

Six new tests targeting previously uncovered branches:

- `TestIsImage` (2): `.gif` and `.tif` extensions now in the parametrize list
- `TestXlsx` (1): `is_xlsx("data.xlsm")` explicitly asserts False, documenting that `.xlsm` routes through the generic MarkItDown else-branch
- `TestExtractXlsxDirect` (1): 2-sheet workbook with one blank sheet — the non-empty sheet still receives an H2 heading because `len(wb.worksheets) > 1` checks the total workbook, not the count of processed sheets
- `TestBijoyStep` (1): `.xlsm` extension triggers `_xlsx_font_has_bijoy` via `_XLSX_EXTS = (".xlsx", ".xlsm")` even though `is_xlsx` returns False for `.xlsm`
- `TestDocxFontDetection` (1): valid DOCX ZIP with neither `word/document.xml` nor `word/styles.xml` → `parts=[]` → `return False` (the `if not parts` guard, mirroring the equivalent ODT and PPTX tests)

---

## [v4.10.65] — 2026-06-27

### Tests — boundary coverage: detect_script thresholds, reph/OLE edge cases, RTF guard (321 total, up from 312)

Nine new tests closing branch gaps identified by systematic audit:

**`TestDetectScript` — 5 new tests:**
- `test_sig_exactly_30_bj_fails_ratio`: sig=30 (short threshold), bj=2, la=28 → ratio 2×10=20 < 28 → `"latin"`
- `test_sig_exactly_30_bj_passes_ratio`: sig=30, bj=3, la=27 → 3×10=30 ≥ 27 → `"bijoy"`
- `test_sig_31_uses_medium_min_bj`: sig=31 crosses into medium tier (min_bj=3); bj=2 < 3 → `"latin"`
- `test_sig_100_uses_medium_thresholds`: sig=100 (still medium, ≤100); bj=3, ratio 3×13=39 < 97 → `"latin"`
- `test_sig_101_uses_long_min_bj`: sig=101 crosses into long tier (min_bj=5); bj=4 < 5 → `"latin"`

**`TestConvertBijoyToUnicode` — 1 new test:**
- `test_reph_preceded_only_by_kars_not_repositioned`: `"ার্ক"` — all chars before র্ are kars, `check` walks to −1 → guard `check >= 0` is False → reph not repositioned

**`TestExtractLegacyDoc` — 1 new test:**
- `test_cp0_valid_but_cc_text_overrun_falls_back_to_scan`: cp0 in-bounds (0 < cp0 < len(data)) but cp0+cc_text overruns; `cp0+cc_text <= len(data)` guard fails → text_start stays None → fallback scan used → empty result from zero-filled binary

**`TestApplyLiteralEdge` — 1 new test (new class):**
- `test_empty_old_string_skipped`: charmap entry with `old == ""` is skipped by the `if old:` guard in `_apply_literal`; only valid entries fire

**`TestBijoyStep` — 1 new test:**
- `test_rtf_empty_raw_skips_font_detection`: when `p.read_bytes()` raises, `_rtf_raw = ""`; the `if _rtf_raw:` guard in `convert_file` prevents `_rtf_font_has_bijoy` from being called (verified with a sentinel mock)

---

## [v4.10.64] — 2026-06-27

### Fix + Feature — XLSX Bijoy font detection (312 tests, up from 305)

**Bug fixed:** XLSX files using SutonnyMJ/Bijoy fonts for Bengali column headers failed to convert when the overall file had too many English/numeric cells to trigger the text-density threshold. The headers remained garbled Bijoy encoding in the output.

**Root cause:** `detect_script` on the full XLSX text correctly returned `"latin"` (6 % Bijoy density, below the 7.7 % threshold) even though the first 300 chars — the Bengali header row — were clearly Bijoy-encoded.

**Fix:** Added `_xlsx_font_has_bijoy(path)` — reads `xl/styles.xml` from the XLSX ZIP and checks `<name val="..."/>` elements inside `<fonts>` against the curated `_BIJOY_FONTS` allowlist. Hooked into `convert_file` as a secondary detection step for `.xlsx`/`.xlsm` files, identical in spirit to the existing DOCX, RTF, PPTX, and ODT font-detection guards.

**Tests — 7 new tests in `TestXlsxFontDetection`:**
- `test_bijoy_font_detected`: SutonnyMJ in xl/styles.xml → True
- `test_non_bijoy_font_returns_false`: Calibri → False
- `test_no_styles_xml_returns_false`: XLSX with no styles file → False
- `test_invalid_zip_returns_false`: non-ZIP file → exception swallowed → False
- `test_comma_suffix_stripped`: `"SutonnyMJ,Bold"` stripped to `"sutonnymj"` before lookup → True
- `test_name_val_empty_skipped`: `<name val=""/>` → `if not val: continue` → False
- `test_font_detection_triggers_bijoy_conversion`: end-to-end: mocked detection returns True → bijoy step applied in convert_file

---

## [v4.10.63] — 2026-06-27

### Tests — RTF empty segments, ODT absent attributes, needs_bijoy short-circuit (305 total, up from 301)

- `TestRtfFontDetection.test_all_segments_empty_after_strip_returns_false`: fonttbl with control-word-only entries; every segment produces an empty name after `re.sub` + strip → all skipped via `if not name: continue` → False
- `TestOdtFontDetection.test_svg_font_family_absent_skips_element`: `<style:font-face>` with no `svg:font-family` attribute → `elem.get(..., "")` returns `""` → `if val:` is False → element skipped → False
- `TestOdtFontDetection.test_fo_font_name_absent_skips_element`: `<style:text-properties>` with no `fo:font-name` attribute → same guard fires → element skipped → False
- `TestBijoyStep.test_needs_bijoy_true_skips_docx_font_detection`: when `is_bijoy_func` returns True, `needs_bijoy = True` → `not needs_bijoy and suffix in docx_exts` is False → `_docx_font_has_bijoy` never called; verified with a sentinel mock

---

## [v4.10.62] — 2026-06-27

### Tests — 0Table flag, cp0 zero fallback, AI-kar pre-kar else branch, Cyrillic other, all-pages-fail OCR (301 total, up from 296)

- `TestExtractLegacyDoc.test_0table_flag_extracts_text`: FIB flags bit 9 clear → `table_name = "0Table"`; cp0 path returns text (complements the 1Table test)
- `TestExtractLegacyDoc.test_cp0_zero_falls_back_to_scan`: table stream present, fc_chpx in-bounds, but `cp0 = 0` fails `0 < cp0` → `text_start` stays `None` → fallback ASCII scan runs and succeeds
- `TestConvertBijoyToUnicode.test_prekar_ai_kar_repositioned_via_else_branch`: `_rearrange` Pass 2 — ৈ (AI-kar, `_PRE_KARS` member) is not ে, so the composite-vowel `else: base += c` branch (line 398) fires; consonant + AI-kar repositioned correctly
- `TestDetectScript.test_only_non_counted_chars_returns_other`: Cyrillic-only string has `bn = bj = la = 0`; `total == 0` triggers `return "other"` (line 444–445)
- `TestOcrPdf.test_all_pages_fail_returns_empty`: every PDF page raises `ValueError`; all `pages_text` entries are `""`; the `if p` filter in `"\n\n".join(...)` produces an empty string

---

## [v4.10.61] — 2026-06-27

### Tests — legacy doc cp0 bounds + OCR partial failure (296 total, up from 294)

- `TestExtractLegacyDoc.test_fc_chpx_too_large_falls_back_to_scan`: table stream exists but `fc_chpx + 4 > len(tdata)` → cp0 unreadable → fallback ASCII scan succeeds and returns text
- `TestOcrPdf.test_partial_page_failure_empty_filtered_from_result`: first PDF page throws a generic exception (appended as `""`), second page succeeds; the `if p` filter in `"\n\n".join(...)` drops the empty entry

---

## [v4.10.60] — 2026-06-27

### Tests — xlsx padding, legacy doc overflow, bijoy nukta (294 total, up from 291)

- `TestExtractXlsxDirect.test_rows_with_different_widths_are_padded`: rows with fewer columns than the sheet maximum are padded with empty strings so the GFM table is well-formed
- `TestExtractLegacyDoc.test_fallback_scan_overflow_returns_empty`: when the fallback ASCII scan's `best_off + cc_text` exceeds the stream length, the final guard fires and returns `""`
- `TestConvertBijoyToUnicode.test_nukta_before_halant_consonant_reordered`: Pass 1 of `_rearrange` — `_is_nukta(text[i-1])` True branch; chandrabindu (ঁ) before a halant-consonant pair is reordered so the halant-consonant comes first

---

## [v4.10.59] — 2026-06-27

### Tests — legacy doc + ocr_engine branch coverage (291 total, up from 288)

- `TestExtractLegacyDoc.test_1table_flag_extracts_text`: FIB flags bit 9 set → `table_name="1Table"` is chosen; also covers the successful extraction `return text` path for the first time in unit tests
- `TestExtractLegacyDoc.test_no_table_stream_fallback_scan_extracts_text`: when neither `0Table` nor `1Table` exists, the fallback ASCII density scan (lines 121–135 of pipeline.py) locates the printable region and returns text
- `TestSetupTesseractBundle.test_other_platform_is_noop`: on non-win32 without `MEIPASS`, `_setup_tesseract()` skips both branches and leaves `tesseract_cmd` unchanged

---

## [v4.10.58] — 2026-06-27

### Tests — 3 pipeline branch tests (288 total, up from 285)

- `TestReadPlainTextEncoding.test_plain_utf8_no_bom`: plain UTF-8 file without BOM decoded correctly by `utf-8-sig` (which treats it identically to `utf-8`)
- `TestDocumentConversion.test_pdf_ocr_also_empty_no_pdf_empty_step`: when MarkItDown returns empty and OCR also returns empty, `steps=["pdf_ocr"]` and `pdf_empty` is NOT appended (the `"pdf_ocr" not in steps` guard at pipeline.py:505)
- `TestRtf.test_rtf_read_bytes_exception_falls_back_to_markitdown`: when `p.read_bytes()` raises during RTF raw-byte read, `_rtf_raw=""` (the `except Exception` at pipeline.py:528) and MarkItDown fallback still recovers text

---

## [v4.10.57] — 2026-06-27

### Tests — _rearrange halant-guard branches (285 total, up from 283)

- `TestConvertBijoyToUnicode.test_reph_preceded_by_halant_not_repositioned`: `ক্র্গ` — র is preceded by ্ (halant), so `not _is_halant(text[i-1])` guard fires, reph repositioning is skipped; র stays in conjunct interior
- `TestConvertBijoyToUnicode.test_ra_halant_vowel_guard_when_ra_in_conjunct`: `ক্র্া` vs `র্া` — in the conjunct case a halant precedes র so the RA+HALANT+Vowel reorder guard also fires; standalone `র্া` does reorder while the conjunct case does not

---

## [v4.10.56] — 2026-06-27

### Tests — PRE_MAP and _PRE_REGEX untested entries (283 total, up from 268)

New classes `TestPreMapEntries` and `TestPreRegex` in `test_bijoy.py`:
- `TestPreMapEntries` (13 tests): soft-hyphen collapse, y&/„& ampersand drop, ‡u and wu character swaps, space-before-comma/pipe removal, backslash-space/space-backslash/bare-backslash removal, triple/quad/quintuple newline collapse
- `TestPreRegex` (2 tests): `\n +` → `\n` (newline then spaces) and ` +\n` → `\n` (spaces then newline) from the three compiled `_PRE_REGEX` patterns

---

## [v4.10.55] — 2026-06-27

### Tests — POST_MAP untested entries via _apply_literal (268 total, up from 261)

New class `TestPostMapEntries` in `test_bijoy.py` directly tests the seven POST_MAP substitutions that no existing test exercised:
- `" ঃ"` → `":"` (space-visarga → colon)
- `"\nঃ"` → `"\n:"` (newline-visarga → newline-colon)
- `"]ঃ"` → `"]:"` and `"[ঃ"` → `"[:"` (bracket-visarga → bracket-colon)
- `"  "` → `" "` (double space in Unicode output collapsed)
- `"স্ত্ম"` → `"স্ত"` and `"ন্ত্ম"` → `"ন্ত"` (spurious ম stripped from s/nta conjuncts)

---

## [v4.10.54] — 2026-06-27

### Tests — _setup_tesseract tessdata-absent branches (261 total, up from 259)

- `TestSetupTesseractBundle.test_bundle_tessdata_not_found_leaves_prefix_unset`: PyInstaller bundle with exe found but tessdata directory absent — TESSDATA_PREFIX is not set; uses `side_effect=[True, False]` to return different values per .exists() call
- `TestSetupTesseractBundle.test_win32_system_data_not_found_leaves_prefix_unset`: Win32 non-bundle with system exe found but tessdata directory absent — TESSDATA_PREFIX not set; same side_effect pattern

---

## [v4.10.53] — 2026-06-27

### Tests — legacy-doc printable-ratio guard + whitespace normalization (259 total, up from 256)

- `TestExtractLegacyDoc.test_low_printable_ratio_returns_empty`: Text region consisting entirely of DEL (0x7F) bytes — non-printable, non-whitespace, survived all substitutions — yields 0% printable ratio, triggering the `< 0.10` sanity guard in `_extract_legacy_doc`; required the fake Table stream to control `text_start` independent of the FIB scan
- `TestDocxFontDetection.test_internal_whitespace_collapsed_in_font_name`: `w:ascii="Siyam  Rupali  ANSI"` (double internal spaces) → `_WS_RE.sub(" ", ...)` collapses to `"siyam rupali ansi"` → match found → True
- `TestRtfFontDetection.test_internal_whitespace_collapsed_in_font_name`: RTF font name with double spaces → `_WS_RE.sub(" ", name).strip()` collapses → match → True

---

## [v4.10.52] — 2026-06-27

### Tests — PPTX remaining extensions (.ppsm, .potx, .potm) and a:ea tag (256 total, up from 252)

- `TestPptxFontDetection.test_ea_font_tag_detected`: Bijoy font in `a:ea` (East Asian) run-property tag detected — completes the three DrawingML font tags (latin, cs, ea)
- `TestPptxFontDetection.test_ppsm_also_triggers_font_detection`: `.ppsm` extension in `_PPTX_EXTS` → font detection applies
- `TestPptxFontDetection.test_potx_also_triggers_font_detection`: `.potx` (PowerPoint template) extension → font detection applies
- `TestPptxFontDetection.test_potm_also_triggers_font_detection`: `.potm` (macro-enabled template) extension → font detection applies

---

## [v4.10.51] — 2026-06-27

### Tests — PPTX slide-layout path and ODT fo:font-name comma-suffix (252 total, up from 250)

- `TestPptxFontDetection.test_slide_layout_font_detected`: Bijoy font in `ppt/slideLayouts/slideLayout1.xml` triggers detection — completes the four PPTX scan prefixes (slides, masters, layouts, theme)
- `TestOdtFontDetection.test_fo_font_name_comma_suffix_stripped`: `fo:font-name="SutonnyMJ,Bold"` — comma suffix stripped before lookup — True; mirrors the svg:font-family comma test for the FO namespace

---

## [v4.10.50] — 2026-06-27

### Tests — PPTX master/theme paths and ODT comma-suffix (250 total, up from 247)

Three new tests covering previously untested XML scanning paths:

**`TestPptxFontDetection`:**
- `test_slide_master_font_detected`: Bijoy font in `ppt/slideMasters/slideMaster1.xml` → `True`; confirms the `ppt/slideMasters/` prefix is scanned (templates often set the body font on the master, not individual slides)
- `test_theme_font_detected`: Bijoy font in `ppt/theme/theme1.xml` as `<a:majorFont>` → `True`; confirms the `ppt/theme/` prefix is scanned

**`TestOdtFontDetection`:**
- `test_comma_suffix_in_svg_font_family_stripped`: `svg:font-family="SutonnyMJ,Bold"` → comma stripped → `"sutonnymj"` → `True`; directly exercises the `comma = norm.find(","); if comma >= 0: norm = norm[:comma].strip()` path in `_odt_font_has_bijoy` for SVG font-family declarations

---

## [v4.10.49] — 2026-06-27

### Tests — font-attribute-level coverage for DOCX, PPTX, ODT (247 total, up from 244)

Closed 3 attribute-level gaps in the Bijoy font-detection functions:

**`TestDocxFontDetection`:**
- `test_hAnsi_only_font_attr_detected`: `w:rFonts` with only `w:hAnsi="SutonnyMJ"` (no `w:ascii`) → `elem.attrib.values()` iterates ALL attributes → `True`; confirms that non-ascii Word font attributes are also detected

**`TestPptxFontDetection`:**
- `test_cs_font_tag_detected`: Bijoy font on `<a:cs typeface="SutonnyMJ"/>` (complex-script tag, not `a:latin`) → `True`; the function scans `a:latin`, `a:ea`, and `a:cs` — this test exercises the `a:cs` branch

**`TestOdtFontDetection`:**
- `test_bijoy_fo_font_in_styles_xml_detected`: `fo:font-name="SutonnyMJ"` on `<style:text-properties>` in `styles.xml` (not `content.xml`) → `True`; tests the intersection of the `styles.xml` file path and the `fo:font-name` attribute path

---

## [v4.10.48] — 2026-06-27

### Tests — Word template and PPTX Show extension coverage (244 total, up from 241)

Three new integration tests verify that all Office format extensions wired into the auto-Bijoy font-detection block are correctly triggered:

**`TestDocxFontDetection`:**
- `test_dotx_also_triggers_font_detection`: `.dotx` (Word template) is in the DOCX extension set → `_docx_font_has_bijoy` is called and Bijoy conversion fires
- `test_dotm_also_triggers_font_detection`: `.dotm` (macro-enabled Word template) — same path

**`TestPptxFontDetection`:**
- `test_ppsx_also_triggers_font_detection`: `.ppsx` (PowerPoint Show) is in `_PPTX_EXTS` → `_pptx_font_has_bijoy` called → Bijoy conversion fires

---

## [v4.10.47] — 2026-06-27

### Tests — PRE_MAP, `_PRE_REGEX`, and `_is_space` guard in bijoy_unicode (241 total, up from 237)

Added `TestPreMapAndPreRegex` class (4 tests) covering preprocessing paths not previously exercised directly:

- `test_yy_pre_map_collapses_to_single`: PRE_MAP `("yy", "y")` — double-y input produces same Unicode output as single-y
- `test_vv_pre_map_collapses_to_single`: PRE_MAP `("vv", "v")` — double-v collapses before conversion
- `test_multiple_spaces_collapsed_to_single`: `_PRE_REGEX` `r" +"` pattern — consecutive spaces in Bijoy input become a single space in the Unicode result
- `test_prekar_before_space_not_reordered`: `_rearrange()` Pass 2 `_is_space` guard — a pre-kar (ে) immediately followed by a space is NOT reordered, while a pre-kar before a consonant IS (გে vs ে followed by space)

---

## [v4.10.46] — 2026-06-27

### Tests — `_setup_tesseract` win32 paths and `ocr_pdf` multi-page (237 total, up from 232)

Closed 5 remaining branches in `ocr_engine.py`:

**`TestSetupTesseractBundle` (3 new tests — win32 non-bundle paths):**
- `test_win32_system_exe_exists_sets_cmd`: no MEIPASS + `Path.exists` → True → `tesseract_cmd` updated to system path
- `test_win32_system_exe_not_found_leaves_cmd_unchanged`: no MEIPASS + `Path.exists` → False → cmd unchanged
- `test_win32_system_data_exists_sets_tessdata_prefix`: no MEIPASS + tessdata dir found → `TESSDATA_PREFIX` set via `os.environ.setdefault`

**`TestOcrPdf` (2 new tests):**
- `test_multi_page_success_joined_by_double_newline`: 2 pages both succeed → text joined with `\n\n`
- `test_unknown_language_uses_eng_fallback`: unrecognised language → `LANG_CODES.get(lang, "eng")` default → `"eng"` passed to pytesseract

---

## [v4.10.45] — 2026-06-27

### Tests — font-detection empty-parts guards and .doc/.ott path coverage (232 total, up from 225)

Closed 7 previously untested branches across four test classes:

**`TestLegacyDoc`:**
- `test_doc_ole_empty_markitdown_returns_text`: OLE extraction returns empty → MarkItDown succeeds → `"markitdown"` in steps, no `"doc_empty"`

**`TestDocxFontDetection`:**
- `test_empty_zip_no_parts_returns_false`: DOCX ZIP with no `word/*.xml` → `parts = []` → `False` (the `if not parts: return False` guard)

**`TestPptxFontDetection`:**
- `test_empty_zip_no_parts_returns_false`: PPTX ZIP with no matching slide/master/theme parts → `parts = []` → `False`

**`TestExtractXlsxDirect`:**
- `test_multi_sheet_blank_title_no_heading`: 2-sheet workbook with blank titles → `not sheet.title` → `else` branch, no `## ` headings emitted

**`TestOdtFontDetection`:**
- `test_odt_empty_zip_returns_false`: ODT ZIP with no `content.xml`/`styles.xml` → `parts = []` → `False`
- `test_bijoy_font_in_styles_xml_detected`: Bijoy font declared only in `styles.xml` (not `content.xml`) → `True`
- `test_ott_extension_triggers_font_detection`: `.ott` (ODF template) is in `_ODT_EXTS` → font detection runs → bijoy conversion triggered

---

## [v4.10.44] — 2026-06-27

### Feature — ODT/OTT Bijoy font detection (225 tests, up from 220)

LibreOffice `.odt` and `.ott` files are Open Document Format ZIP archives whose font declarations live in `content.xml` and `styles.xml`, not in a binary stream. Added `_odt_font_has_bijoy()` to scan both XML files for known Bijoy font names in two ODF locations:

- `svg:font-family` on `<style:font-face>` elements (the font-face declaration block)
- `fo:font-name` on `<style:text-properties>` elements (per-run applied font)

Updated `convert_file()` auto-bijoy block: if the file is `.odt`/`.ott` and no Bijoy content was detected via text heuristics, `_odt_font_has_bijoy()` is checked and forces Bijoy conversion if it returns `True` — consistent with the DOCX, RTF, and PPTX font-detection chains.

**New tests — `TestOdtFontDetection` (5 tests):**
- `test_bijoy_svg_font_detected`: `SutonnyMJ` in `svg:font-family` → `True`
- `test_bijoy_fo_font_detected`: `SutonnyMJ` in `fo:font-name` → `True`
- `test_non_bijoy_font_returns_false`: `Liberation Serif` → `False`
- `test_invalid_zip_returns_false`: non-ZIP `.odt` → `False` (no raise)
- `test_odt_font_detection_triggers_bijoy_conversion`: monkeypatched `_odt_font_has_bijoy` → `True` on an ASCII-content `.odt` → `"bijoy"` in steps, text converted

---

## [v4.10.43] — 2026-06-27

### Tests — ocr_pdf per-page TesseractNotFoundError path (220 total, up from 219)

Refactored `TestOcrPdf` to share page-iteration setup via `_make_mock_doc()` helper, and added the last untested `ocr_pdf()` path:

- `test_tesseract_not_found_per_page_raises_runtime`: `pytesseract.image_to_string()` raises `TesseractNotFoundError` inside the page loop → propagates as `RuntimeError("Tesseract not found ...")` (the `finally: doc.close()` still executes)

All `ocr_pdf()` error branches are now covered:
- pymupdf not installed → RuntimeError ✓
- PDF file not found → FileNotFoundError ✓
- `pymupdf.open()` fails → RuntimeError("Could not open PDF") ✓
- Per-page TesseractNotFoundError → RuntimeError ✓
- Per-page generic exception → silently skipped (empty string appended) ✓

---

## [v4.10.42] — 2026-06-27

### Tests — ocr_pdf open-failure and bad-page paths (219 total, up from 217)

Added 2 tests to `TestOcrPdf` covering the remaining error paths in `ocr_pdf()`:

- `test_pdf_open_failure_raises_runtime`: `pymupdf.open()` raises → caught at `except Exception as exc: raise RuntimeError(f"Could not open PDF: {exc}") from exc`
- `test_bad_page_skipped_returns_empty`: per-page generic exception → `except Exception: pages_text.append("")` — bad page silently skipped, overall result is `""`

---

## [v4.10.41] — 2026-06-27

### Tests — XLSX direct-extraction error paths (217 total, up from 215)

Added 2 tests to `TestExtractXlsxDirect` covering the two silent-return paths in `_extract_xlsx_direct()`:

- `test_openpyxl_not_installed_returns_empty`: `sys.modules["openpyxl"] = None` (ImportError) → returns `""`
- `test_load_workbook_exception_returns_empty`: `load_workbook()` raises `OSError` → outer `except Exception: return ""` at pipeline.py:354

---

## [v4.10.40] — 2026-06-27

### Tests — RTF exception-silencing branches (215 total, up from 213)

Closed two silent-swallow branches in the RTF path of `convert_file()`:

`TestRtf` (pipeline):
- `test_rtf_striprtf_exception_falls_back_to_markitdown`: when `_rtf_to_text()` raises, the `except Exception: pass` at pipeline.py:485 silences it and the MarkItDown fallback produces the final text
- `test_rtf_both_paths_fail_yields_rtf_empty`: when both striprtf and MarkItDown raise, both exceptions are silenced → `"rtf_empty"` in steps, `text = ""`

---

## [v4.10.39] — 2026-06-27

### Tests — PDF and .doc exception path coverage (213 total, up from 211)

Closed two bare-`raise` / silent-swallow branches in `convert_file()`:

`TestErrors` (pipeline):
- `test_pdf_non_memory_error_reraises`: non-MemoryError from MarkItDown on a `.pdf` file propagates unchanged via the bare `raise` at pipeline.py:446

`TestLegacyDoc` (pipeline):
- `test_doc_markitdown_exception_silenced_returns_doc_empty`: when OLE extraction returns empty AND the MarkItDown fallback raises, the exception is silenced (`except Exception: text = ""`), yielding `"doc_empty"` in steps

---

## [v4.10.38] — 2026-06-27

### Tests — OLE cc_text overflow guard (211 total, up from 210)

Added `test_cc_text_exceeds_data_length_returns_empty` to `TestExtractLegacyDoc` in `test_pipeline.py`.

The guard at `pipeline.py:100` (`cc_text > len(data)`) is now explicitly covered: a mocked OLE stream with `cc_text = 0xFFFFFFFF` (≫ 512-byte stream) exercises the early-return path that protects against struct.unpack reading beyond the buffer.

---

## [v4.10.37] — 2026-06-27

### Tests — Bijoy detection edge cases (210 total, up from 208)

Filled two gaps in `test_bijoy.py` that exercise detection logic not previously covered by direct assertions:

`TestDetectScript`:
- `test_unicode_bengali_beats_bijoy_range_chars`: text with Bijoy-range chars (©©©) AND a Unicode Bengali codepoint (ক) → `"unicode_bn"` — verifies the `bn > 0` short-circuit always wins

`TestIsBijoy`:
- `test_bijoy_two_char_adaptive_true`: `is_bijoy("°©")` → `True` — verifies the adaptive `min_bj=2` threshold for short texts (sig ≤ 30) that the old fixed floor of 5 would have rejected

---

## [v4.10.36] — 2026-06-27

### Tests — boundary and re-raise coverage (208 total, up from 203)

Closed three concrete coverage gaps identified in audit:

`TestChBoundary` (bijoy_unicode):
- `test_negative_index_returns_empty`: `_ch("abc", -1)` → `""` (guard: `0 <= i`)
- `test_beyond_length_returns_empty`: `_ch("abc", 10)` → `""` (guard: `i < len`)
- `test_valid_index_returns_char`: `_ch("abc", 0)` → `"a"` (normal path)

`TestSetupTesseractBundle` (ocr_engine):
- `test_bundle_path_exe_not_found_leaves_cmd_unchanged`: `_MEIPASS` present but `exe.exists()` → False → `tesseract_cmd` is not mutated

`TestErrors` (pipeline):
- `test_generic_format_non_memory_error_reraises`: non-MemoryError from MarkItDown in the generic `else:` branch propagates unchanged (bare `raise` at pipeline.py:537)

---

## [v4.10.35] — 2026-06-27

### Tests — OCR PDF and pymupdf availability coverage (203 total, up from 199)

Added `TestPymupdfAvailable` and `TestOcrPdf` to `test_ocr_engine.py`, closing the last gap in OCR engine test coverage.

`TestPymupdfAvailable`:
- `test_returns_true_when_available`: mocked pymupdf module in `sys.modules` → `pymupdf_available()` returns `True`
- `test_returns_false_when_not_installed`: `sys.modules["pymupdf"] = None` → returns `False`

`TestOcrPdf`:
- `test_missing_file_raises_file_not_found`: with pymupdf mocked as available, nonexistent path → `FileNotFoundError`
- `test_pymupdf_not_installed_raises_runtime`: `sys.modules["pymupdf"] = None` → `RuntimeError` with "pymupdf" in message

---

## [v4.10.34] — 2026-06-27

### Improved — PPTX Bijoy font detection via DrawingML a:latin scanning

Added `_pptx_font_has_bijoy()` to `pipeline.py`. PowerPoint presentations (`.pptx`, `.pptm`, `.ppsx`, `.ppsm`, `.potx`, `.potm`) that use Bijoy/SutonnyMJ fonts for Bengali text now get font-assisted detection as a secondary signal when the character-range scan misses pure-ASCII Bijoy text.

The function opens the PPTX ZIP and scans `ppt/slides/slide*.xml`, `ppt/slideMasters/`, `ppt/slideLayouts/`, and `ppt/theme/theme*.xml` for `<a:latin typeface="..."/>` (DrawingML namespace) elements. Theme font references (`+mj-lt`, `+mn-lt`) are skipped — only concrete typeface names are matched against the `_BIJOY_FONTS` allowlist.

This mirrors the DOCX font detection (v4.10.27) and the RTF font detection (v4.10.30), completing font-level detection across all three major Office document families.

### Tests — 6 new tests (199 total, up from 193)

`TestPptxFontDetection` (pipeline):
- `test_bijoy_font_detected`: SutonnyMJ in slide `<a:latin>` → True
- `test_non_bijoy_font_returns_false`: Calibri → False
- `test_theme_font_ref_skipped`: `+mn-lt` theme reference → False (must not trigger)
- `test_invalid_zip_returns_false`: non-ZIP → False (no raise)
- `test_pptm_also_triggers_font_detection`: `.pptm` extension → font detection fires → bijoy step
- `test_pptx_font_detection_triggers_bijoy_conversion`: ASCII-only PPTX + font flag → bijoy step

---

## [v4.10.33] — 2026-06-27

### Tests — 4 new coverage-gap tests (193 total, up from 189)

**`test_settings.py`** — three untested default keys added to `TestNewDefaults`:
- `test_language_default_en`: `language` defaults to `"en"`
- `test_last_input_folder_default_empty`: `last_input_folder` defaults to `""`
- `test_last_output_folder_default_empty`: `last_output_folder` defaults to `""`

**`test_pipeline.py`**:
- `TestExtractXlsxDirect.test_newline_in_cell_replaced_by_space`: embedded newlines inside XLSX cell values must be normalised to a single space before being written into GFM table rows; the `.replace("\n", " ")` call at `pipeline.py:265` was untested

---

## [v4.10.32] — 2026-06-27

### Tests — 5 new coverage-gap tests (189 total, up from 184)

**`test_pipeline.py`**
- `TestExtractXlsxDirect.test_header_only_sheet`: a sheet with exactly one row produces `header | separator` with no data lines — the `len(padded) > 1` guard was previously untested
- `TestDocumentConversion.test_generic_format_uses_markitdown` (4 parametrize cases): non-special formats `.html`, `.pptx`, `.json`, `.xml` route through the generic MarkItDown `else` branch and emit the `"markitdown"` step — this entire code path had no test

---

## [v4.10.31] — 2026-06-27

### Tests — 11 new coverage-gap tests (184 total, up from 173)

Closed test coverage gaps identified by audit across four modules:

**`test_pipeline.py`**
- `TestIsPdf` (new class, 7 tests via parametrize): `is_pdf()` had no unit tests — exercised `.pdf`, `.PDF`, `.SCAN.PDF` → True; `.docx`, `.xlsx`, `.png`, `noext` → False
- `TestReadPlainTextEncoding.test_latin1_fallback`: bytes undefined in cp1252 (0x81) must fall through to the latin-1 decoder; previously only utf-8-sig and cp1252 fallbacks were tested

**`test_bijoy.py`**
- `TestDetectScript.test_whitespace_only_returns_other`: whitespace/tab/newline-only strings should return "other" (no alpha, no Bengali, no Bijoy-range chars)

**`test_settings.py`**
- `TestNewDefaults.test_onboarding_seen_default_false`: `onboarding_seen` was an untested default key
- `TestNewDefaults.test_use_windows_colors_default_false`: `use_windows_colors` was an untested default key

---

## [v4.10.30] — 2026-06-26

### Improved — RTF Bijoy font detection via fonttbl scanning

Added `_rtf_font_has_bijoy()` to `pipeline.py`, which scans the `{\fonttbl}` block of raw RTF text and checks each declared font name against the curated `_BIJOY_FONTS` allowlist. This mirrors the DOCX font detection added in v4.10.27 and closes the same gap for RTF files: pure-ASCII Bijoy text (e.g. `evsjv` = বাংলা, no conjunct characters) cannot be detected by character-range scanning alone, but the RTF font table reliably names the typeface.

The RTF conversion branch now reads raw bytes once at the start (rather than only when striprtf is available), feeding both the striprtf extractor and the new font detection. The fallback path via MarkItDown is unchanged.

### Tests — 7 new RTF font detection tests (173 total, up from 166)

`TestRtfFontDetection` (pipeline):
- `test_bijoy_font_detected`: SutonnyMJ in fonttbl → True
- `test_non_bijoy_font_returns_false`: Arial → False
- `test_no_fonttbl_returns_false`: RTF without fonttbl block → False
- `test_siyam_rupali_ansi_detected`: multi-word name "Siyam Rupali ANSI" → True
- `test_multiple_fonts_bijoy_among_others`: SutonnyMJ among non-Bijoy fonts → True
- `test_empty_fonttbl_returns_false`: empty `{\fonttbl}` block → False
- `test_rtf_font_detection_triggers_bijoy_conversion`: ASCII-only Bijoy RTF + font flag → bijoy step

---

## [v4.10.29] — 2026-06-26

### Fixed — detect_script false positive on short English texts with typographic chars

`detect_script()` introduced in v4.10.26 applied the relaxed 13× Bijoy density ratio uniformly to all text lengths. Short texts (sig ≤ 30) with 2 Bijoy-range chars (e.g., © and —) and ~20 Latin chars could cross the 7.7% threshold and be wrongly classified as Bijoy.

Fix: the strict 10× ratio (same as the original pre-v4.10.26 threshold) is kept for short texts (sig ≤ 30). The relaxed 13× ratio applies only to medium and long texts (sig > 30) where the intent — catching mixed Bijoy+Latin documents at lower density — is valid.

Example fixed: `detect_script("© 2024 Company Name — Annual Report")` returned "bijoy"; now correctly returns "latin".

### Tests — 1 new regression guard (166 total, up from 165)
- `TestDetectScript.test_english_copyright_notice_not_bijoy`: bj=2, la=23, sig=25 ≤ 30 → strict 10× ratio → "latin"

---

## [v4.10.28] — 2026-06-26

### Fixed — DOCX Bijoy font detection covers .docm / .dotx / .dotm variants

The font-detection path only fired for `.docx` files. `.docm` (macro-enabled), `.dotx` (template), and `.dotm` (macro-enabled template) share the same internal ZIP+XML structure as `.docx` and now also trigger `_docx_font_has_bijoy()`.

### Tests — 1 new test (165 total, up from 164)
- `TestDocxFontDetection.test_docm_also_triggers_font_detection`: `.docm` file + Bijoy font flag → bijoy step

---

## [v4.10.27] — 2026-06-26

### Fixed — DOCX font detection now also scans word/styles.xml

`_docx_font_has_bijoy()` previously only checked `word/document.xml`. Old Bijoy documents commonly define SutonnyMJ as a paragraph style in `word/styles.xml` and individual runs carry no explicit `w:rFonts`. The function now reads both XML parts in a single ZIP open, so style-level Bijoy font declarations are caught.

### Tests — 1 new DOCX styles.xml test (164 total, up from 163)
- `TestDocxFontDetection.test_bijoy_font_in_styles_xml_detected`: DOCX with SutonnyMJ only in word/styles.xml (no rFonts in document.xml) → True

---

## [v4.10.26] — 2026-06-26

### Improved — Bijoy detection: adaptive thresholds + DOCX font-name sniffing

Ported detection improvements from Mukti's FontRegistry (https://github.com/GRU-953/Mukti):

**`bijoy_unicode.detect_script()` — adaptive minimum threshold**
- Short texts (≤ 30 significant chars): 2 Bijoy-range chars suffice (was: 5). Fixes missed detection on paste snippets, single-sentence captions, and any content shorter than ~30 characters.
- Medium texts (31–100 chars): minimum raised to 3 (was: 5).
- Long texts (> 100 chars): minimum stays at 5.
- Relaxed ratio: `bj × 13 ≥ la` (≈ 7.7 % density) replaces `bj × 10` (10 %), catching Bijoy+Latin mixed documents at lower Bijoy density.

**`pipeline._docx_font_has_bijoy()` — DOCX font-name detection**
- New function reads `word/document.xml` inside the DOCX ZIP and checks `w:rFonts` attribute values against Mukti's curated Bijoy font allowlist (SutonnyMJ family, Ananda river-named fonts, Siyam Rupali ANSI, newspaper fonts).
- Normalisation mirrors Mukti: lowercase, strip, collapse whitespace, drop comma-suffix style variants (`SutonnyMJ,Bold` → `sutonnymj`).
- No MJ-suffix fuzzy matching (Mukti decision D-0006: NikoshMJ, TangonMotaMJ, SonkhoMJ are confirmed Unicode fonts).
- `convert_file()` calls this as a secondary signal for `.docx` files when text-scan alone misses pure-ASCII Bijoy text (e.g. simple consonants like `evsjv` = বাংলা with no conjunct chars).

### Tests — 10 new detection tests (163 total, up from 153)

`TestDetectScript` (bijoy_unicode):
- `test_short_bijoy_two_chars_no_latin`: bj=2, la=0, sig=2 → bijoy
- `test_short_bijoy_two_chars_with_latin`: bj=2, la=3, sig=5 → bijoy (ratio 2×13≥3)
- `test_medium_text_three_bijoy_chars`: bj=3, la=37, sig=40 → bijoy (old threshold failed)
- `test_relaxed_ratio_catches_low_density`: bj=8, la=100 → bijoy (old 8×10=80<100 failed)
- `test_two_distinct_bijoy_chars_no_latin`: © + ¨ → bijoy

`TestDocxFontDetection` (pipeline):
- `test_bijoy_font_detected`: SutonnyMJ → True
- `test_bijoy_font_comma_suffix_detected`: SutonnyMJ,Bold strips to sutonnymj → True
- `test_non_bijoy_font_returns_false`: Arial → False
- `test_invalid_zip_returns_false`: non-ZIP → False (no raise)
- `test_font_detection_triggers_bijoy_conversion`: ASCII-only Bijoy + font flag → bijoy step

---

## [v4.10.25] — 2026-06-26

### Fixed — update download fallback used in-app window.open
- When the update installer download failed, the fallback path called `window.open(pageUrl)` to open the GitHub release page. In WebView2 (the browser engine used on Windows), `window.open()` opens a new in-app webview frame rather than the system browser, so users would see a blank embedded window. The fallback now calls `api().install_update(pageUrl)`, which hands the URL to Python's `webbrowser.open()` and opens the user's default browser correctly.

### Tests — 5 new `_extract_legacy_doc` and `doc_ole` tests (153 total, up from 148)
- `TestExtractLegacyDoc.test_no_olefile_returns_empty`: `olefile` not installed → returns `""`
- `TestExtractLegacyDoc.test_ole_open_error_returns_empty`: `OleFileIO` raises on open → returns `""`
- `TestExtractLegacyDoc.test_no_word_document_stream_returns_empty`: missing `WordDocument` OLE stream → returns `""`
- `TestExtractLegacyDoc.test_cc_text_zero_returns_empty`: FIB header with `cc_text == 0` → returns `""`
- `TestLegacyDoc.test_doc_ole_step_on_success`: when OLE extraction succeeds, `doc_ole` step appears and MarkItDown is not called

---

## [v4.10.24] — 2026-06-26

### Tests — 4 new Bijoy POST_MAP regression tests (148 total, up from 144)
- `test_aa_ligature_fixed`: verifies `অা` is collapsed to `আ` by POST_MAP
- `test_digit_visarga_becomes_colon`: verifies `০ঃ` → `০:` colon fix
- `test_all_digit_visarga_to_colon`: same check for all 10 Bengali digits
- `test_double_halant_zwnj_collapsed`: verifies double `্‌্‌` → `্‌` dedup

---

## [v4.10.23] — 2026-06-26

### Added — keyboard shortcuts for export
- **Ctrl + S** exports the currently selected file (opens the format picker). **Ctrl + Shift + S** exports all converted files as a single combined document. Both shortcuts are active only when the Convert view is open. The README FAQ has been updated to document all available shortcuts.

---

## [v4.10.22] — 2026-06-26

### Fixed — export format modal covered by scrolled content
- The export format picker (MD / HTML / TXT) used `position: absolute`, which positioned it relative to the nearest ancestor rather than the viewport. If the page content was scrolled, the modal could appear off-screen. Changed to `position: fixed` so it always centres in the visible window.

### Fixed — update banner dismiss button wired in JavaScript
- The "×" button on the update banner used an inline `onclick` HTML attribute to hide the banner. Inline event handlers bypass Content Security Policy in strict environments and are harder to test. The `onclick` has been removed and the handler is now registered in JavaScript via `wireUpdateDismiss()`.

### Fixed — export format dialog announced to screen readers
- The export modal had `role="dialog"` and `aria-modal="true"` but no `aria-labelledby`, so screen readers could not announce the dialog name when it opened. The title element now has `id="export-modal-title"` and the backdrop references it via `aria-labelledby`.

### Fixed — Bijoy detect pill announced to screen readers
- The script-detection pill in the Bijoy view changed text (e.g. "Bijoy detected", "Unicode") but had no live-region markup. Screen reader users would not hear the detection result without navigating to the element manually. The element now carries `role="status"` and `aria-live="polite"`.

---

## [v4.10.21] — 2026-06-26

### Added — re-add file from History to the conversion queue
- Each item in the History view now shows a **+** button when hovered or focused. Clicking it calls `add_dropped()` to validate the path, adds the file to the Convert queue, and switches to the Convert view with a confirmation toast. If the original file no longer exists, an error toast is shown instead. Works in both English and বাংলা.

### Fixed — export format dialog: Tab key now stays inside the modal
- When the "Export format" modal was open (MD / HTML / TXT), pressing Tab moved focus outside the dialog to other page elements. Focus now cycles between the three format buttons. Shift+Tab also works. Escape still closes the dialog.

---

## [v4.10.20] — 2026-06-26

### Fixed — RTF "no text" status was never reported
- When both the striprtf extractor and the MarkItDown fallback returned empty text for an RTF file, the file was silently marked as converted with no warning. It now correctly reports the `rtf_empty` step, which turns the file status yellow (warning) in the file list — matching the behaviour of all other format branches (PDF, DOC, OCR, XLSX, plain text). The i18n strings "No text in RTF" / "RTF-এ কোনো লেখা নেই" are added to both locales.

### Fixed — UTF-8 BOM files: byte-order mark was preserved in output
- Plain-text files written by Windows editors with a UTF-8 BOM (`.txt`, `.md`, `.csv`, etc.) previously decoded using plain `utf-8`, which does not strip the BOM character (U+FEFF). The encoding trial order in `_read_plain_text()` is now `utf-8-sig` → `utf-8` → `cp1252` → `latin-1`, so the BOM is always stripped before the text reaches the output panel or export.

### Tests — 10 new test cases (144 total, up from 134)
- `TestReadPlainTextEncoding`: cp1252 fallback and UTF-8 BOM stripping
- `TestRtfEmpty`: `rtf_empty` step when both extractors return empty; step absent when text is found
- `TestXlsxEmpty`: `xlsx_empty` step when XLSX extraction returns empty; step absent when text is found
- `TestExtractXlsxDirect`: GFM table format, multi-sheet H2 headings, pipe escaping, empty-sheet skipping

---

## [v4.10.19] — 2026-06-26

### Removed — dead code cleanup (utils.py)
- `utils.py` and its 11 tests (`test_utils.py`) have been removed. The file contained a path parser for tkinter's drag-and-drop event format — a leftover from the old CTk UI that was never imported in the current pywebview-based codebase. The CI syntax-check and coverage steps have been updated to match.

---

## [v4.10.18] — 2026-06-26

### Improved — Excel output renders as a formatted table
- `_extract_xlsx_direct()` (used for XLSX files ≥ 2 MB and as the fallback for smaller files that fail MarkItDown) now outputs valid GitHub-Flavored Markdown tables instead of pipe-separated plain text. The first row of each sheet is treated as the column header, followed by a separator row, then data rows. All rows are padded to the same column count so the table is well-formed.
- Multi-sheet workbooks output one table per sheet, with an H2 heading for each sheet title.
- Pipe characters inside cell values are escaped (`\|`) so they do not break the table structure. Embedded newlines inside cells are replaced with spaces.

---

## [v4.10.17] — 2026-06-26

### Added — Check for updates button in Settings
- A **Check for updates** button appears in the About section of Settings. Users who start the app while offline, or who dismissed the automatic update banner, can now trigger the check on demand. The button shows a "Checking…" label while the request is in flight and toasts the result: either the update banner is shown if a new version is found, or a "You have the latest version" confirmation is shown if already up to date. Works in both English and বাংলা.

---

## [v4.10.16] — 2026-06-26

### Fixed — PDF OCR: single bad page no longer aborts all remaining pages
- When Tesseract fails on one page of a multi-page PDF (corrupt raster, unsupported pixel format, etc.), OCR now continues with the remaining pages and collects whatever text it can. Previously, any single-page failure raised an exception and discarded all text extracted from earlier pages. Only a missing Tesseract binary still aborts immediately.

### Improved — PDF OCR memory: pixmap released before Tesseract loads
- The rendered page pixmap is now explicitly freed before `pytesseract.image_to_string()` is called. Both objects hold full-resolution image data; on a 200 DPI page they can each reach 30–60 MB. Releasing the pixmap first means peak RAM during PDF OCR is roughly halved, which matters on machines with 2 GB RAM.

### Fixed — README: removed incorrectly advertised `.xls` format
- The file type table listed `.xls` (old binary Excel 97-2003) as supported, but the file picker did not include it and MarkItDown's Excel handler uses openpyxl which does not read the old binary format. Removed to avoid user confusion.

---

## [v4.10.15] — 2026-06-26

### Improved — screen reader: active navigation view announced
- The sidebar navigation buttons now carry `aria-current="page"` on the active item. Screen readers previously had no semantic signal that one of the four buttons represented the current view; they would read each button identically. The attribute is toggled by JavaScript whenever the view changes.

### Improved — screen reader: batch conversion progress announced
- The Convert button has `aria-live="polite"`, so its text content changes ("Converting 2 / 5…") are announced by screen readers as they happen without interrupting the current reading flow.

### Improved — export-all toast shows save location
- The confirmation toast after saving a combined export now shows the parent folder and filename (e.g. `Documents/combined.md`), matching the behaviour of single-file exports added in v4.10.13.

---

## [v4.10.14] — 2026-06-26

### Improved — file list is now fully keyboard-navigable
- Each file row can receive keyboard focus. The currently-selected row has `tabindex="0"` so Tab cycles into the list; all other rows use `tabindex="-1"` so Tab does not get stuck cycling through every file. Once focus is in the list, **Arrow Up / Arrow Down** move between files (existing behaviour, now visible with a focus ring) and **Enter** or **Space** selects the focused row.
- The file list container is marked `role="listbox"` with `aria-selected` on each row, giving screen readers correct semantic context.
- When arrow-key navigation moves to a new row while a row already has keyboard focus, focus follows automatically so the visual focus indicator stays in sync.

### Improved — large preview is now safely truncated
- If a converted file produces more than 80 000 characters of text (roughly 80 KB — most common with large PDFs or dense spreadsheets), the preview panel now renders only the first 80 KB and appends a notice explaining how much is hidden. This prevents `marked.parse()` from blocking the main thread for several seconds on very large outputs. The full text remains accessible via the Edit tab and is exported in full.

---

## [v4.10.13] — 2026-06-26

### Fixed — system-info failure now defaults to low-end mode
- If `get_system_info()` fails at startup (API timeout, frozen bundle quirk, or any unexpected error), the app now assumes single-core / low-end hardware instead of silently leaving high-end defaults active. This means animations are suppressed and conversions remain sequential — the correct conservative behaviour when hardware capability is unknown. Previously a startup-API failure would leave the machine classified as capable, potentially triggering expensive animations or concurrent conversions on a machine that cannot handle them.

### Improved — concurrent conversion cap lowered to 2
- The maximum number of files converted in parallel is reduced from 4 to 2. On machines with 8+ cores the previous cap of 4 simultaneous conversions could cause significant memory pressure (each conversion can briefly load a full 200 MB file plus MarkItDown's working buffers). Two concurrent conversions still gives a meaningful speed improvement on multi-core machines while keeping peak RAM usage predictable.

### Improved — failed file auto-selected after batch conversion
- When a batch conversion finishes and one or more files failed, the first failed file is now automatically selected. The user can immediately see the error detail in the output panel without having to scroll through the list to find which file failed.

### Improved — export toast shows folder + filename
- The "Saved" notification after export now shows the parent folder and filename together (e.g. `Documents/output.md`) instead of just the filename. On a machine where files can be saved to many different locations, this makes it immediately clear where the file landed without needing to open a file manager.

---

## [v4.10.12] — 2026-06-26

### Improved — low-end hardware: remove GPU-expensive backdrop blur
- On low-end hardware (`data-perf="low"`), `backdrop-filter: blur()` is now suppressed on both the onboarding overlay and the export format modal. Blur compositing requires a GPU texture layer; removing it eliminates a visible stutter point on integrated graphics without any meaningful visual degradation.

---

## [v4.10.11] — 2026-06-26

### Improved — concurrent batch conversion on multi-core machines
- `convertAll()` now uses an adaptive worker-pool pattern. On machines with more than 2 CPU cores, it launches up to `floor(cpu_count / 2)` conversions in parallel (capped at 4 to avoid memory pressure). On low-end hardware (≤ 2 cores), the behaviour is unchanged — strictly sequential.
- A 4-core machine converts batches roughly twice as fast; an 8-core machine up to 4× faster, depending on file types and I/O.
- Single-file conversions are unaffected. The CPU count is obtained from `get_system_info()` which already runs in parallel with the other startup calls.

---

## [v4.10.10] — 2026-06-26

### Improved — README keyboard shortcuts
- Added a "Are there keyboard shortcuts?" FAQ entry documenting Ctrl+Enter (convert all), Ctrl+O (open files), and Arrow Up/Down (navigate file list).

---

## [v4.10.9] — 2026-06-26

### Improved — file list keyboard navigation
- Arrow Up / Arrow Down now moves the file selection in the Convert tab (when focus is not inside the editor or a text input). The selected row scrolls into view automatically.
- On low-end hardware (`data-perf="low"`), scrolling uses `behavior: instant` instead of smooth to avoid animation overhead.

### Improved — selected file auto-scrolls into view
- Selecting a file programmatically (e.g., after a conversion finishes) now ensures the row is visible in the file list panel via `scrollIntoView({ block: "nearest" })`. Previously, on long lists, the active row could scroll off screen and the list would not reposition.

---

## [v4.10.8] — 2026-06-26

### Improved — adaptive animation for low-end hardware
- On startup, the app now calls `get_system_info()` alongside the other startup API calls. If the machine reports 2 or fewer CPU cores (`is_low_end: true`), `data-perf="low"` is set on the root element and CSS animations (shimmer, skeleton, view transitions, toasts) are suppressed. CSS transitions under 200 ms are kept because they are GPU-composited and cheap even on integrated graphics.
- The API call fires in parallel with the existing config/locales/platform calls so there is no additional startup latency.
- This specifically targets the stated minimum-spec target: single-core 1 GHz with integrated GPU.

---

## [v4.10.7] — 2026-06-26

### Improved — faster app startup
- The three startup API calls (config, locales, platform) are now fired in parallel using `Promise.allSettled()` instead of sequentially. On average this reduces the time between window appearing and UI becoming interactive.

### Fixed — image file handle left open after OCR
- `ocr_image()` in `ocr_engine.py` now uses `Image.open()` as a context manager (`with Image.open(...) as img:`). Previously the PIL file handle was never explicitly closed, which could prevent the source image from being moved or deleted on Windows while the conversion result was still being used.

---

## [v4.10.6] — 2026-06-26

### Fixed — export format modal double-open and focus
- `pickFormat()` now has a guard (`_pickFormatOpen` flag) that returns `null` immediately if the modal is already visible. Rapid double-clicks on Export no longer produce two overlapping modals.
- The modal now sets `role="dialog" aria-modal="true"` and moves keyboard focus to the first format button when it opens.
- The dismiss path clears the guard flag so subsequent exports work normally.

### Fixed — onboarding focus trap and initial focus
- When the onboarding overlay appears, keyboard focus is now moved to the "Get started" button so the user can dismiss it with the keyboard (Enter/Space) without tabbing there first.
- Pressing Tab while the overlay is open now keeps focus on that button (there is only one interactive element) instead of letting it leak through to the window behind.
- Pressing Escape closes the overlay and cleans up the keydown listener.
- The `keydown` listener is now on the overlay element (not `document`), so it is automatically removed along with the element and does not linger.

---

## [v4.10.5] — 2026-06-26

### Fixed — convert loop robustness
- `convertAll()` is now wrapped in `try { … } finally { … }`. Previously, an unexpected exception inside the loop would leave the Convert button permanently disabled and files stuck in the "doing" state until the app was restarted. The finally block guarantees the button is always re-enabled and its label restored.
- Each individual file conversion is also wrapped in its own `try/catch`. An unexpected exception from a single file now marks that file as failed rather than aborting the entire batch.

### Fixed — Bijoy view unhandled rejections
- `detectBijoy()` and `runBijoy()` now handle errors from `api().detect()` and `api().bijoy_convert()` respectively. Previously an API failure in either call would produce an unhandled Promise rejection; now detection leaves the pill unchanged and conversion shows the generic error toast.

---

## [v4.10.4] — 2026-06-26

### Improved — indeterminate progress bar animation
- Conversion rows now show a continuously animated shimmer bar while a file is being converted, replacing the previous static bar frozen at 65%. The existing `@keyframes shimmer` (already used by skeleton loaders) is reused — no new animation asset needed.
- Guarded by `@media (prefers-reduced-motion: reduce)`: the animation is suppressed and users with that preference see a full-width static bar instead.
- Added `aria-label="Converting"` to the `progressbar` role element for screen-reader clarity.

---

## [v4.10.3] — 2026-06-26

### Fixed — onboarding text accuracy
- Onboarding step 1 said 'click "Add files"' — there is no "Add files" button; the correct action is clicking inside the drop area. Updated in `en.json` and `bn.json`.

### Improved — version number caching in JS
- `populateAbout()` now caches `_appVersion` on first call. Previously it called `api().get_version()` on every language switch, which is unnecessary since the version never changes during a session.

---

## [v4.10.2] — 2026-06-26

### Fixed — export dialog directory fallback
- `Api.export_text()` now uses the same Documents → home-dir fallback that `pick_files()` already uses via `_dialog_dir()`. Previously, if `last_output_folder` was empty or had been deleted, the SAVE dialog received no `directory` kwarg, which causes silent failure or an unexpected starting location on some WebView2 configurations. New helper `_export_dir()` provides the fallback.

### Fixed — HTML export XSS guard in fallback path
- `_render()` now calls `html.escape()` on the raw text before wrapping it in `<pre>` when the `markdown` library import fails. The previous code concatenated unescaped text directly into HTML — a defence-in-depth fix for an unlikely but theoretically unsafe path.

### Removed — stale locale keys
- Removed `"update.install"` (duplicate of `"update.download"`, never referenced in JS) from both `en.json` and `bn.json`.
- Removed `"bijoy.detect.type"` (never referenced in JS) from both locale files.

---

## [v4.10.1] — 2026-06-26

### Removed — dead API bridge methods
- `Api.ocr()` — became dead code when the Scan tab was removed in v4.9.0; no frontend JS calls it. Removed to shrink the attack surface.
- `Api.tesseract_ok()` — was called by the Scan tab's feature-detection flow; no caller since v4.9.0. Removed.
- `Api.pymupdf_ok()` — same; no caller since v4.9.0. Removed.

---

## [v4.10.0] — 2026-06-26

### Performance — faster startup
- **Lazy OCR imports**: `ocr_engine` (which loads `pytesseract` and `Pillow`) is no longer imported at module level in `pipeline.py` or `app.py`. The import now happens inside the first function call that actually needs OCR. On typical usage (converting Word/PDF/XLSX files) OCR is never triggered at all, so `pytesseract` + `Pillow` never load. Result: noticeably faster window-open time, especially on low-end hardware.

### Platform readiness — macOS
- **`ocr_engine._setup_tesseract()` is now platform-aware**: the Windows-specific Tesseract paths (`C:\Program Files\Tesseract-OCR`) are now guarded by `sys.platform == "win32"`. On macOS and Linux the function exits cleanly and relies on the system PATH (Homebrew/apt install). No functional change on Windows.
- **New `Api.get_platform()` bridge method**: returns `"windows"`, `"darwin"`, or the raw `sys.platform` string. Used by the frontend to conditionally show or hide OS-specific settings.
- **Windows colours hidden on non-Windows**: the Settings panel now hides the "Windows colours" toggle when running on macOS or Linux via the new `applyPlatform()` JS function and `.win-only` CSS class. The setting is inert on those platforms anyway; hiding it avoids confusion.
- **New `Api.get_system_info()` bridge method**: returns `{cpu_count, is_low_end}` — a lightweight hook for future adaptive behaviour (e.g. capping concurrency on single-core machines).

### README — full redesign
- Rewritten for non-technical users: plain language, step-by-step instructions, full Settings table, FAQ section, and accurate feature descriptions throughout.
- Fixed: "language toggle at the top" → now correctly describes Settings.
- Added: Windows colours feature, Settings table, History tab, FAQ.

---

## [v4.9.0] — 2026-06-26

### Removed — Scan tab
- The dedicated **Scan to text** tab is removed. Images and PDFs dropped in the Convert tab still get OCR text automatically — the auto-OCR pipeline is fully intact. This simplifies the interface without losing any capability.

### Changed — Settings
- **Language toggle** (English / বাংলা) moved from the topbar into the **Settings** view under a new "Language" section.
- **Appearance mode** toggle (Light / Auto / Dark) moved from the topbar into Settings under a new "Appearance mode" section.
- The topbar is now clean title + subtitle only.

### Added — Windows colours
- New **"Windows colours"** toggle in Settings. When on: the app reads the Windows accent colour from the system registry and applies it as the primary colour throughout the UI, and the appearance mode is forced to **Auto** so light/dark follows Windows automatically. Turning it off restores the GRU953 palette choice. Works on any Windows 10/11 accent colour.

### Fixed — Security / AV
- **Removed `ctypes` console-hide block** from `app.py`. The `GetConsoleWindow / ShowWindow SW_HIDE` pattern is a textbook malware heuristic that AV engines flag. The block was already dead code because the exe is built with `--windowed` (no console is created at the OS level). Removed entirely.
- **Added `--noupx` to the PyInstaller build** in `release.yml`. UPX-packed executables match the signature of many packers used by malware; explicitly disabling UPX keeps the binary in its clean uncompressed form.
- **Added Windows application manifest** (`app.manifest`): declares `asInvoker` (no UAC elevation), targets Windows 10/11, and sets Per-Monitor DPI v2 awareness. Embedded into the exe via `--manifest`. A properly-manifested exe is less likely to be flagged as a suspicious unsigned binary.

### Removed — Locales
- Removed 14 scan-tab-only i18n keys from `en.json` and `bn.json` (`ocr.title`, `ocr.sub`, `ocr.dropzone.*`, `ocr.langLabel`, `ocr.bijoyCheckbox`, `ocr.run`, `ocr.output.placeholder`, `ocr.saveTxt`, `ocr.pdfSuffix`, `ocr.scanningPdf`, `ocr.extracting`, `toast.chooseScanFile`, `nav.ocr`, `nav.ocr.tip`). OCR error strings used by the Convert pipeline are preserved.
- Added 7 new keys in both languages: `settings.lang.*`, `settings.mode.*`, `settings.winColors.*`.

---

## [v4.8.3] — 2026-06-26

### Fixed — accessibility
- **`#out-tabs` missing `aria-checked`**: Preview / Edit tab buttons carry `role="radio"` but had no `aria-checked` in the HTML and `setOutMode()` never wrote it. Both initial markup and the JS toggle now set the attribute correctly.
- **`#ocr-lang` missing initial `aria-checked`**: The OCR-language picker's English button started `active` in HTML but without `aria-checked="true"`. Added to the markup.
- **`#set-ocr-lang` missing `aria-checked`**: `syncSettingsControls()` toggled the `active` class but never set `aria-checked`. Now sets both on every call.

### Fixed — UX
- **Export format modal Escape key**: pressing Escape now dismisses the format picker (MD / HTML / TXT). Previously only backdrop-click or a format button would close it.

### Removed — dead code
- `pick_image()` API bridge method — never called from the frontend; removed.
- `import os` and `import threading` — unused after the v4.8.2 switch from `os.startfile()` to `webbrowser.open()`.

---

## [v4.8.2] — 2026-06-26

### Fixed
- **Scan picker toast flooding**: the Scan tab "click to browse" button could trigger a cascade of "Could not open file picker" toasts if clicked rapidly. Root causes were: (a) `_dialog_dir()` returned `{}` when no saved folder existed, causing WebView2 to fail silently or raise; (b) `pick_scan_file()` had no `try/except`, so any exception rejected the JS promise and the `catch` block showed a toast; (c) no click guard prevented rapid re-entry. All three are fixed: `_dialog_dir()` now always resolves a real path (last-used → Documents → home), both picker methods are wrapped in `try/except`, and a `_ocrPickerBusy` flag blocks re-entry while a dialog is open. Same guard applied to `pick_files()`.
- **Windows Defender flagging the app**: the previous auto-update flow downloaded the installer exe to `%TEMP%` and launched it with `os.startfile()` — a textbook pattern Windows Defender flags as potentially malicious. Replaced with `webbrowser.open()`: the download URL is handed to the user's browser and the user runs the installer themselves. No silent execution from temp.
- **Nav tab indicator too narrow**: nav button width widened from 48 px to 60 px so the tab label has clear breathing room inside the active indicator outline.

---

## [v4.8.1] — 2026-06-26

### Fixed — from adversarial review
- **Theme-adaptive logo**: the sidebar and onboarding logos now correctly swap between a Teal tile (light mode) and an Indigo tile with amber bird (dark mode). CSS `display` toggling via `[data-mode="dark"]` selectors, no JS needed.
- **`aria-hidden` on visible dark logo**: both `.logo-dark` SVGs had `aria-hidden="true"` AND `role="img" aria-label` — contradictory attributes that caused screen readers to skip the visible logo in dark mode. Removed `aria-hidden="true"`.
- **Mode-seg missing `aria-checked`**: the Light / Auto / Dark buttons had `role="radio"` but no `aria-checked` in the HTML. Added initial values matching the System default.
- **Update banner text lost on language switch**: `applyI18n()` overwrote the dynamic "Update available: v4.x.x" text with the static `update.message` key. Fixed by caching update info in `_updateInfo` and calling `renderUpdateBanner()` after every `applyI18n()` run.
- **`#update-link` text regression on language switch**: `data-i18n="update.download"` on the link caused `applyI18n()` to overwrite the JS-set text. Removed the `data-i18n` attribute; JS owns the link text entirely.
- **`export_text()` empty-directory save dialog**: same WebView2 empty-string directory bug as the scan picker; the save dialog `_save_kw` dict now only includes `"directory"` when `last_output_folder` is a real existing path.
- **`convert.removeFile` aria-label localised**: the per-file remove (×) button's `aria-label` was hardcoded English; now uses `t('convert.removeFile')`.
- **Ctrl+O CapsLock interference**: the keyboard shortcut to add files now uses `e.key.toLowerCase() === "o"` so it fires regardless of CapsLock state.
- **Settings persistence for `last_input_folder`**: added `"last_input_folder": ""` to `_DEFAULTS` in `settings.py` for consistent merging.

---

## [v4.8.0] — 2026-06-26

### Added — bilingual interface
- **Full English / বাংলা language toggle** in the top bar. Every label, button, placeholder, tooltip, toast, and error message is translated, with native modern-standard Bangla (চলিত, respectful আপনি). Switching swaps the whole UI to Noto Sans Bengali. Choice is remembered. Catalogues live in `locales/en.json` + `locales/bn.json` (153 keys each), loaded through the `get_locales()` bridge.

### Changed — ground-up redesign to the GRU953 brand
- **New app icon**: the GRU953 master mark — **the Soaring Bird** — rendered in the Open Spectrum gradient (indigo → teal → amber → coral) on an ink `#10211D` tile, replacing the previous "M" glyph. Used for the window, sidebar, onboarding, and built `.exe`.
- **Full UI overhaul** against the brand design system: 8px spacing grid, `--radius-sm/md/lg/xl` scale, borders-over-shadows elevation, motion tokens (150/250/400 ms) honouring `prefers-reduced-motion`, every interactive control shipping all 8 states, and `≥44 × 44 px` touch targets throughout.
- **Accessibility (WCAG 2.2 AA)**: every text/background pair contrast-verified in light and dark; visible `:focus-visible` rings (≥3:1); status conveyed by icon + text, never colour alone; radiogroup semantics on segmented controls and palette cards; the four designed states (empty, loading, error, offline).

### Changed — licence & governance
- **Licence migrated MIT → Apache-2.0** with SPDX headers on source files and a `NOTICE` listing bundled third-party components.
- Added the brand-required governance files: `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `SECURITY.md`, `GOVERNANCE.md`, and `docs/design-system-notes.md`.

---

## [v4.7.0] — 2026-06-26

### Added — quality-of-life
- **Conversion progress counter** in the Convert button ("Converting 2 / 5…").
- **Word & character count** in the output panel.
- **Keyboard shortcuts**: Ctrl+O to add files, Ctrl+Enter to convert all.
- **File size** shown in the file list; **last input folder** remembered across sessions.

### Fixed
- Corpus audit gained `--exclude` and `--skip-large` flags; raised base per-file timeout headroom for dense map PDFs.

---

## [v4.6.0] — 2026-06-26

### Changed — brand rebrand
- **App renamed**: MarkItDown Converter → **GRU953 Markdown**. Repository renamed to `gru953-markdown`. Exe renamed to `GRU953Markdown.exe`. All internal references updated.
- **Three GRU953 brand themes**: replaced Indigo Nocturne / Violet Bloom / Slate & Amber with **GRU953 Teal** · **GRU953 Indigo** · **GRU953 Amber**, all drawn from the GRU953 Open Spectrum palette (Teal 700 `#0A6E5C`, Indigo 600 `#3A4A9E`, Amber 600 `#9C6B12`).
- **Typography**: replaced Figtree / Hind Siliguri / Tiro Bangla with **DM Sans** (variable, covers 100–900) and **Noto Sans Bengali** (Regular + Bold), both self-hosted per GRU953 brand guidelines (no third-party CDN).
- **Neutral surfaces**: dark bg `#10211D` → `#18302A` surface (GRU953 brand dark); light bg `#F7F8F7` (brand Neutral 50). Status colours aligned to GRU953 semantic tokens.
- **App icon**: new geometric SVG — Teal 700 tile (64 × 64, rx 15), white M (markdown letter), Amber 400 down-arrow. Matches the GRU953 product icon family spec.
- **Sidebar brand mark**: replaced letter "M" with inline SVG icon matching the new app icon.
- **Settings file**: renamed `.markitdown_converter.json` → `.gru953_markdown.json` to avoid conflicts with old installs.

---

## [v4.5.2] — 2026-06-26

### Added
- **XLSX ≥5 MB fast-path**: `pipeline.py` now bypasses MarkItDown entirely for large XLSX files (≥5 MB) and calls `_extract_xlsx_direct` (openpyxl `read_only=True`) directly. Prevents indefinite hangs on large single-sheet XLSX files where MarkItDown's table formatter never raises an exception but never finishes either. Smaller XLSX files (< 5 MB) still try MarkItDown first for richer markdown table output.
- **Plain-text direct read** (`PLAIN_TEXT_EXTS`): `.txt`, `.md`, `.ini`, `.cfg`, `.conf`, `.log`, `.csv`, `.tsv` files are now decoded directly via UTF-8/cp1252/latin-1 — no MarkItDown, no magika ONNX model. Saves ~400 MB RAM per conversion and eliminates the 8–15 s cold-start cost for trivial text files. Step name: `plaintext` / `plaintext_empty`.
- **Persistent-worker corpus audit** (`full_corpus_audit.py`): Rewritten from a subprocess-per-file design (magika ONNX reloaded every file, 8–15 s overhead each) to a persistent-worker design (one subprocess per slot stays alive across all files, ONNX loaded once). Defaults tuned for 2 GB RAM: `--workers 1`, `--file-timeout 120`, `--skip-large 200`. Workers auto-restart (up to 5 times) on crash or timeout. Expected throughput improvement: ~3–10× on low-end hardware.
- **`plaintext`/`plaintext_empty` UI labels**: `STEP_LABEL` and `EMPTY_STEPS` in `web/js/app.js` updated to display plain-text step badges correctly.

### Tests
- 6 new plain-text tests: `is_plain_text()` true/false, UTF-8 decode, empty file, CSV, and a "must NOT call MarkItDown" guard.
- 1 new XLSX test: `xlsx_large_bypasses_markitdown` (≥5 MB must not call MarkItDown). **Total: 138 → 145 tests.**

---

## [v4.5.1] — 2026-06-26

### Fixed
- **XLSX openpyxl fallback**: Large `.xlsx` files (6+ MB) could trigger `ONNXRuntimeError: bad allocation` (magika ONNX model exhausts RAM) or a `MarkItDownException` wrapping `MemoryError` (numpy array allocation for 14 000+ row sheets). The pipeline now tries MarkItDown first and, on any failure, falls back to a direct `openpyxl` `read_only=True` streaming pass — no ONNX models, no full-array allocation, lazy row iteration. Step name: `xlsx_direct`.
- **MemoryError guard for PDF branch**: `PdfConverter threw MemoryError` was unhandled in the `is_pdf` branch; now surfaced as a friendly `ValueError`.
- **Wrapped MemoryError in generic branch**: MarkItDown catches `MemoryError` internally for DOCX, PPTX, and other formats and re-raises as a `RuntimeError`/`MarkItDownException` with `"MemoryError"` in the message. The pipeline's generic `else` branch now catches any exception containing `"MemoryError"` in its string representation and converts it to a friendly `ValueError`.

### Tests
- 4 new XLSX tests: `is_xlsx()`, MarkItDown success path, openpyxl fallback on MarkItDown failure.
- 2 new MemoryError guard tests: wrapped PDF MemoryError, wrapped DOCX MemoryError.
- **Total: 132 → 138 tests.**

---

## [v4.5.0] — 2026-06-26

### Fixed
- **MemoryError on large ZIPs**: `MarkItDown`'s `ZipConverter` loads the full expanded archive into memory. Files above ~50 MB could exhaust RAM and raise an unhandled `MemoryError`. The pipeline now catches `MemoryError` in the generic MarkItDown branch and re-raises as a friendly `ValueError` — the UI shows a clear "insufficient memory" message instead of a traceback.
- **RTF stub when `striprtf` absent**: `_rtf_to_text` was only defined when `striprtf` was installed; `monkeypatch.setattr(pipeline, "_rtf_to_text", ...)` raised `AttributeError` in CI (where `striprtf` is not available). Added a no-op stub so the attribute always exists and all RTF tests pass in CI.

### Tests
- 5 new RTF pipeline tests: `is_rtf()`, `striprtf`-based extraction, `MarkItDown` fallback when `striprtf` unavailable, empty `striprtf` result falls back to `MarkItDown`. **Total: 126 → 131 tests.**

### Tooling
- `full_corpus_audit.py`: switched per-file timeout from `ThreadPoolExecutor` + inner `ThreadPoolExecutor` (thread-based, cannot interrupt a blocked `zipfile` or `MarkItDown` call) to `ThreadPoolExecutor` + `subprocess.run` per file. Subprocess timeouts are OS-enforced and truly kill the worker process.
- Per-file timeout now scales 1 s/MB beyond 1 MB so large legitimate files are given adequate time.
- Progress line every 50 files (or 30 s), rate, and ETA.

### Documentation
- `UNBUILT.md`: added "Known large-file limitations" table — ZIP MemoryError threshold (~50 MB), slow scan-PDF empty detection, audit vs app timeout behaviour.

---

## [v4.4.1] — 2026-06-26

### Fixed
- `_validate_path`: symlink guard was dead code — `Path.resolve()` follows symlinks, so `is_symlink()` after resolve is always False. Now checks the original (unresolved) path.
- Restored ODF pass-through: `.odt`, `.ods`, `.odp`, `.odg` were incorrectly added to `UNSUPPORTED_EXTS` in v4.4.0, breaking users who rely on MarkItDown's ODF support.
- Removed dead `STEP_LABEL['unsupported']` key — the unsupported-format path raises `ValueError` before any step is recorded.

### Added
- Amber **⚠ warn** status for files that convert but produce no text (`ocr_empty`, `doc_empty`, `pdf_empty`, `image_ocr_disabled`) — triangle icon, amber colour.
- Toast summary now reports empty-result count separately ("3 converted, 1 empty").

---

## [v4.4.0] — 2026-06-26

### Added
- **.rtf support**: RTF files extracted via `striprtf` with MarkItDown fallback (step label: "RTF extract").
- `doc_empty` pipeline step when a `.doc` file produces no text from either OLE extraction or MarkItDown.
- `pdf_empty` pipeline step when a PDF text-layer is empty and OCR is disabled.
- `image_ocr_disabled` pipeline step when an image is processed with `auto_ocr=False`.
- `UNBUILT.md`: documents deliberately unsupported formats (fonts, vector, InDesign, etc.).
- `full_corpus_audit.py`: parallel audit tool for testing all files in a corpus directory.
- ODF formats (`.odt`, `.ods`, `.odp`, `.odg`) added to `UNSUPPORTED_EXTS` with a "save as .docx/.pdf first" message. *(Reverted in v4.4.1 — see Fixed above.)*

### Fixed
- **B-1**: `ocr_pdf()` leaked the pymupdf file handle when an exception occurred inside the page loop. Wrapped in `try/finally` to guarantee `doc.close()`.
- **B-2**: Bijoy false-positive for very short strings: `is_bijoy()` now requires a minimum of 5 Bijoy-range characters before classifying text as Bijoy.
- **B-3**: `Api.ocr()` did not call `_validate_path()` before passing the path to the OCR engine — oversized or traversal paths could bypass the security check.
- **M-1/M-2**: `.webp` and `.tif` (single-f) were missing from the `pick_files()` native file-picker filter.
- **M-3**: `.rtf` added to `pick_files()` filter now that RTF extraction is supported.
- **U-1**: Step label for `doc_ole` changed from "Binary Doc" (developer jargon) to "Legacy Word (.doc)".
- **U-4**: `friendlyError()` MissingDependency match simplified to `"missingdependency"` to be resilient across MarkItDown versions.

### Security
- **S-1**: `_validate_path` now blocks symlink paths (checked before `resolve()`).

### Tests
- 126 tests passing (up from 113 in v4.3.0). Added test classes: `TestLegacyDoc`, `TestUnsupported`, `TestOcrEmpty`, `TestImageOcrDisabled`.

---

## [v4.3.0] — 2026-06-26

### Added
- **Legacy .doc support**: Word 97–2003 binary files extracted via OLE/cp1252 using `olefile`. Reads `PlcfBteChpx CP[0]` from the 1Table stream to locate the text start byte. Falls back to MarkItDown for newer `.doc` files saved as OOXML.
- **Friendly errors for unsupported formats**: `.eps`, `.ai`, `.indd`, `.otf`, `.ttf`, `.woff`, `.woff2`, `.psd` now raise `ValueError` with a clear plain-English message instead of a cryptic MarkItDown traceback.
- `ocr_empty` pipeline step when image OCR runs but finds no text (e.g. logo images).
- **Security hardening**: `_validate_path()` added to `Api.convert()` — checks for path traversal, missing files, directory paths, and files > 200 MB.

### Changed
- `.doc` added to `pick_files()` native file-picker filter.
- `STEP_LABEL` extended: `doc_ole`, `pdf_ocr`, `ocr_empty`.
- `friendlyError()` handles unsupported format, too-large file, directory path, invalid path.

---

## [v4.2.2] — 2026-06-25

### Fixed
- Bijoy false-positive on English-only documents with no Bengali characters.
- `release.yml` YAML indentation error that caused the CI release workflow to fail.

---

## [v4.2.0] — 2026-06-25

### Fixed
- `APP_VERSION` mismatch caused the update banner to incorrectly show an update available on first launch.
- Polish: improved step labels, onboarding copy, and history timestamps.

---

## [v4.1.0] — 2026-06-24

### Added
- Inno Setup installer (`MarkItDownConverter-Setup.exe`) with optional desktop shortcut.
- Auto-update banner: checks GitHub releases API on startup and shows a dismissible banner when a newer version is available.
- Offline-safe Tabler Icons (SVG sprites bundled, no CDN calls).

---

## [v4.0.0] — 2026-06-23

Full ground-up redesign. Replaced the CustomTkinter GUI with a pywebview + WebView2 frontend.

### Highlights
- Modern web-based UI: three colour palettes (Indigo Nocturne, Violet Bloom, Slate & Amber), light/dark/system modes.
- Unified one-button pipeline: MarkItDown → OCR → Bijoy→Unicode, applied automatically per file.
- Batch file queue with drag-and-drop, per-file status, and Retry failed.
- Live Markdown editor and preview with Bengali font rendering.
- Export to `.md`, `.html`, `.txt`, and "Export all combined".
- Conversion history with timestamps.
- Dedicated OCR (Scan) and Bijoy→Unicode converter views.
- Persistent settings (theme, palette, OCR language, smart-conversion toggles).

---

## [v3.x] — earlier

Earlier versions used a CustomTkinter GUI. See `docs/` for historical design notes.
