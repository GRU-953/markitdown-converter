# Changelog

All notable changes to MarkItDown Converter are documented here.

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
