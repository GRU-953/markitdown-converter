# Changelog

All notable changes to GRU953 Markdown are documented here.

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
