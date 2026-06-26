# Changelog

All notable changes to MarkItDown Converter are documented here.

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
