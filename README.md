# MarkItDown Converter

**A standalone Windows desktop app that converts documents, images, and spreadsheets to clean Markdown — with built-in OCR and Bengali text support.**

[![Release](https://img.shields.io/github/v/release/GRU-953/markitdown-converter?style=flat-square&color=0E8C7A)](https://github.com/GRU-953/markitdown-converter/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/GRU-953/markitdown-converter/ci.yml?branch=master&style=flat-square&label=CI)](https://github.com/GRU-953/markitdown-converter/actions/workflows/ci.yml)
[![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen?style=flat-square)](https://github.com/GRU-953/markitdown-converter/actions/workflows/ci.yml)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue?style=flat-square&logo=windows)](https://github.com/GRU-953/markitdown-converter/releases/latest)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Built with](https://img.shields.io/badge/Built%20with-MarkItDown-0E8C7A?style=flat-square)](https://github.com/microsoft/markitdown)

---

## Download

> **[→ Download MarkItDownConverter.exe](https://github.com/GRU-953/markitdown-converter/releases/latest)**

No Python installation. No setup wizard. Just download and run.

| | |
|---|---|
| **OS** | Windows 10 / 11 (64-bit) |
| **Size** | ~91 MB (self-extracting, all dependencies bundled) |
| **First launch** | Allow 5–10 seconds — the bundle extracts itself once |

---

## Features

### Convert Files

Convert any of the following to clean Markdown in one click:

| Format | Extensions |
|---|---|
| Documents | PDF, Word (.docx), PowerPoint (.pptx), HTML, HTM |
| Spreadsheets | Excel (.xlsx), CSV |
| Data | JSON, XML |
| Images | PNG, JPG/JPEG, GIF, BMP, TIFF |
| Archives | ZIP (contents recursively converted) |
| Audio | WAV, MP3 (transcription via MarkItDown) |

**Workflow:**
1. Drag files into the drop zone — or click **+ Add Files** (supports batch selection)
2. Click **Convert All** — each row shows a live ✓ / ✗ status
3. Select any file to see its Markdown in the **Raw MD** tab or rendered in **Preview**
4. **Copy** to clipboard, **Save .md** for a single file, or **Save All** to write every converted file to a folder in one step

**Keyboard shortcuts:** `Ctrl + O` to add files · `Ctrl + Enter` to convert

---

### OCR — English & Bengali

Extract text from images using Tesseract OCR v5.5.0, bundled with the app.

- Supports **English**, **বাংলা**, or **both at once**
- Drop an image or click to browse
- Tick **Auto-convert Bijoy → Unicode** to automatically fix Bijoy-encoded OCR output
- Copy or save the extracted text

---

### Bijoy → Unicode

Convert legacy SutonnyMJ / Bijoy-encoded Bengali text to proper Unicode (UTF-8).

- Paste text — the script (Bijoy / Unicode Bengali / Latin) is **detected automatically**
- Click **Convert ↓** — Unicode output appears instantly
- Works on clipboard content, scanned documents, or any Bijoy-encoded source

---

### Interface

- **Dark / Light / System** mode toggle in the header
- Status bar with live feedback: initialization state, per-file conversion progress, copy and save confirmations
- GRU-953 brand — teal palette, Figtree · Hind Siliguri · Tiro Bangla fonts (all OFL licensed)

---

## Build from Source

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11 – 3.13 | Python 3.14 requires `--console` flag (see below) |
| [Tesseract OCR v5](https://github.com/UB-Mannheim/tesseract/wiki) | 5.x | Install to `C:\Program Files\Tesseract-OCR\`; add `eng.traineddata` + `ben.traineddata` |
| PyInstaller | 6.x | `pip install pyinstaller` |

### Steps

```bash
git clone https://github.com/GRU-953/markitdown-converter.git
cd markitdown-converter
pip install -r requirements.txt

# Run directly (development)
python converter.py

# Build standalone .exe
build_exe.bat
```

The compiled exe is written to `dist\MarkItDownConverter.exe`.

### PyInstaller notes

- Use `--console` (not `--windowed`) — the `runw.exe` bootloader hangs silently on Python 3.14 with `--onefile`. The console window is hidden programmatically at startup.
- `--collect-all magika` is required — MarkItDown depends on magika ML models that PyInstaller won't auto-discover.
- `--collect-all tkhtmlview` is required — without it, the HTML preview widget attempts a runtime download of `tkhtml3`, blocking the UI.

---

## Project Structure

```
markitdown-converter/
├── converter.py          # Main app — CustomTkinter UI, all tab logic
├── brand.py              # GRU-953 colour tokens, font loader, asset paths
├── bijoy_unicode.py      # Bijoy / SutonnyMJ → Unicode conversion (Mukti port)
├── ocr_engine.py         # Tesseract wrapper — bundle-aware path resolution
├── utils.py              # Shared utilities (DnD path parsing)
├── build_exe.bat         # PyInstaller build script
├── requirements.txt      # Python dependencies
├── assets/               # Fonts (OFL), app icon, brand mark
├── tests/                # pytest suite — 68 tests, 100% coverage
│   ├── test_bijoy.py
│   ├── test_ocr_engine.py
│   └── test_utils.py
└── .github/workflows/    # CI (pytest + coverage) and auto-release (exe on tag)
```

---

## Credits & Attributions

| Component | Credit |
|---|---|
| [MarkItDown](https://github.com/microsoft/markitdown) | Microsoft — core document-to-Markdown conversion engine |
| [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) | Google — bundled as `tesseract.exe` v5.5.0 |
| [Mukti](https://github.com/Aninda-Howlader/bijoy-unicode) | Aninda S Howlader — Bijoy→Unicode JS library (ported to Python) |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | Tom Schimansky — modern tkinter UI framework |
| [TkinterDnD2](https://github.com/pmgagne/tkinterdnd2) | Drag-and-drop support for tkinter |
| Figtree · Hind Siliguri · Tiro Bangla | OFL licensed fonts |

---

## License

MIT — see [LICENSE](LICENSE) for details.
