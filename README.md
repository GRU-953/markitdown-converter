<div align="center">

<img src="assets/gru953-markdown-icon.svg" width="88" alt="GRU953 Markdown">

# GRU953 Markdown

**Turn any document into clean, readable text — in one click.**

Word files, PDFs, spreadsheets, and images — converted instantly, with no technical knowledge needed.

<br>

[![Download](https://img.shields.io/github/v/release/GRU-953/gru953-markdown?style=for-the-badge&color=0A6E5C&label=Download%20for%20Windows&logo=windows&logoColor=white)](https://github.com/GRU-953/gru953-markdown/releases/latest)
&nbsp;
[![License](https://img.shields.io/badge/Free%20%26%20Open%20Source-MIT-3A4A9E?style=for-the-badge)](LICENSE)
&nbsp;
[![CI](https://img.shields.io/github/actions/workflow/status/GRU-953/gru953-markdown/ci.yml?branch=main&style=for-the-badge&label=Tests&color=0A6E5C)](https://github.com/GRU-953/gru953-markdown/actions)

<br>

*Simple technology. For everyone.* &nbsp;·&nbsp; *সহজ প্রযুক্তি। সবার জন্য।*

</div>

---

## ⬇️ Download

> **[→ Click here to download GRU953 Markdown for Windows](https://github.com/GRU-953/gru953-markdown/releases/latest)**

- Click the link above and download **GRU953Markdown.exe**
- Double-click the file to open the app — **no installation needed**
- If Windows shows a warning, click **More info → Run anyway** *(this is normal for new apps)*

Runs on **Windows 10 and Windows 11** (64-bit). No Python, no extra software, no accounts.

---

## 🚀 Three steps to get started

### 1 · Open the app
Double-click **GRU953Markdown.exe**. It opens in a few seconds on first launch.

### 2 · Drop your file
Drag any document onto the app window — or click inside the drop area to browse your files.
You can add **multiple files** at once.

### 3 · Copy or save
Click **Convert all**. Your text is ready in seconds.
- **Copy** it straight to your clipboard
- **Export** to save as a `.md`, `.txt`, or `.html` file

That's everything. No sign-up, no internet needed, no subscription.

---

## 📄 What files does it work with?

| What you have | What to drop in |
|---|---|
| Word documents | `.docx`, `.doc` |
| PDF files | `.pdf` |
| PowerPoint slides | `.pptx` |
| Excel spreadsheets | `.xlsx`, `.xls` |
| Images with text | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.bmp`, `.gif`, `.webp` |
| Web pages saved as files | `.html` |
| Data files | `.csv`, `.json`, `.xml` |
| Compressed folders | `.zip` |
| Old-format text | `.rtf`, `.txt` |

> **Images are handled automatically.** Drop a photo or a scanned page and the app reads the text for you — no extra steps.

---

## 🔤 Bengali / Bangla support

GRU953 Markdown understands old Bangla computer fonts that are common in older documents from Bangladesh.

If your file uses a legacy Bangla font (Bijoy or SutonnyMJ), the app **automatically converts** the text to proper Unicode so it displays correctly in any app, website, or document.

There is also a dedicated **Bangla** tab where you can paste text and convert it directly — useful if you have copied text from an older source.

---

## 🎨 Themes

Go to **Settings** to change how the app looks:

| Theme | Mood |
|---|---|
| **GRU953 Teal** | Fresh and clean — the default |
| **GRU953 Indigo** | Deep and focused |
| **GRU953 Amber** | Warm and energetic |

Every theme works in both **Light** and **Dark** mode. Switch anytime — your choice is saved.

---

## ❓ Need help?

Something not converting correctly? Got a question?

👉 [Open an issue on GitHub](https://github.com/GRU-953/gru953-markdown/issues) — describe what happened and we will take a look.

---

## About GRU953

GRU953 is a not-for-profit, open-source product organisation on a mission to make technology simple and accessible for everyone — with a home in Bangladesh. All GRU953 apps are free, open-source, and built openly with a global community.

*Simple technology. For everyone.* &nbsp;·&nbsp; *সহজ প্রযুক্তি। সবার জন্য।*

&nbsp;

<details>
<summary>🔧 For developers</summary>

&nbsp;

**Run from source**

```bash
git clone https://github.com/GRU-953/gru953-markdown.git
cd gru953-markdown
pip install -r requirements.txt
python app.py
```

**Build the standalone exe**

```bash
build_exe.bat
# Output: dist\GRU953Markdown.exe
```

**Run the test suite**

```bash
pip install pytest pytest-cov
pytest tests/ -v
# 145 tests across pipeline, bijoy_unicode, ocr_engine, settings, utils
```

Built with [pywebview](https://pywebview.flowrl.com/) · [MarkItDown](https://github.com/microsoft/markitdown) · [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) · DM Sans · Noto Sans Bengali  
See [CHANGELOG.md](CHANGELOG.md) for version history.

</details>

---

**License:** MIT — free to use, modify, and share. See [LICENSE](LICENSE).
