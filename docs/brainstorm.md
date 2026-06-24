# Brainstorm

## Idea (verbatim)
Develop a Windows application to convert files to markdown formats using
https://github.com/microsoft/markitdown

## One-line restatement
A Windows GUI app where you pick a file, click Convert, and get clean Markdown out -
powered by Microsoft's MarkItDown library.

## Core need
Users have files in office formats (Word, Excel, PowerPoint, PDF, HTML, etc.)
and need their content as plain Markdown text - for notes, wikis, AI pipelines,
or static sites.

## What MarkItDown gives us
- Python library (and CLI) by Microsoft
- Converts: PDF, .docx, .xlsx, .pptx, .html, images, audio, CSV, JSON, XML, ZIP
- Output: Markdown string
- Install: pip install markitdown

## Constraints (original v1 — all superseded by v3)
1. Python required - MarkItDown is a Python package; the app runs in Python.
2. Windows target - GUI must work on Windows 10/11.
3. Smallest-correct GUI - tkinter is bundled with Python (zero extra deps).
4. Distribution - plain Python script + requirements.txt; no bundling needed for now.

## Acceptance items — v1 baseline (all done ✓)
- [x] User can open a file via a dialog
- [x] Clicking Convert calls MarkItDown and shows Markdown in a scrollable area
- [x] User can save the output as a .md file
- [x] Errors (unsupported file, MarkItDown exception) are shown as a plain message

## V3 additions (all shipped ✓)
- [x] Drag and drop (single + batch)
- [x] Batch conversion with per-file status indicators
- [x] Markdown preview (HTML render via tkhtmlview, raw MD fallback)
- [x] Dark / Light / System mode toggle
- [x] PyInstaller standalone .exe (91 MB, no Python install required)
- [x] Bangla + English OCR via Tesseract v5.5.0 (bundled)
- [x] Bijoy → Unicode conversion via Mukti engine port (bijoy_unicode.py)
- [x] GRU-953 brand — teal palette, Figtree + Hind Siliguri + Tiro Bangla fonts

## Key build notes
- Use `--console` (not `--windowed`) for PyInstaller on Python 3.14 — runw.exe bootloader hangs
- Console window suppressed via `ShowWindow(GetConsoleWindow(), SW_HIDE)` in converter.py
- `--collect-all magika` and `--collect-all tkhtmlview` are both required
- MarkItDown init deferred via `app.after(500, ...)` to avoid GIL deadlock at startup
