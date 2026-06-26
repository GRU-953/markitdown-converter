# UNBUILT

Deliberate omissions — formats the pipeline does not convert and never will without
a fundamentally different extraction approach. These are not bugs.

## Unsupported by design

| Format | Extensions | Reason |
|---|---|---|
| OpenType / TrueType fonts | .otf, .ttf, .otc, .ttc | Binary glyph data; no text content |
| PostScript fonts | .pfb, .pfm, .pfa | Binary/ASCII font definitions |
| Web fonts | .woff, .woff2 | Binary compressed font data |
| EPS / PostScript vector | .eps, .ai | Vector drawing instructions, no prose |
| Adobe InDesign | .indd, .indt | Proprietary binary; requires InDesign to export |
| Adobe Photoshop | .psd | Raster layer format; any embedded text requires OCR |

All extensions above are listed in `pipeline.UNSUPPORTED_EXTS` and raise a
`ValueError` with a plain-English message rather than a cryptic traceback.

## Partially unsupported

| Format | Extensions | Status |
|---|---|---|
| OpenDocument | .odt, .ods, .odp, .odg | Passes to MarkItDown; may fail if MarkItDown lacks the ODF extra. Should be saved as .docx or .pdf first. |
| Raw camera images | .cr2, .nef, .arw, .dng | No extractor; image OCR on the embedded JPEG preview is possible in a future release |
| Email archives | .pst, .ost | Requires Outlook/MAPI; out of scope |
| E-books | .epub | Depends on MarkItDown epub extra; not bundled — convert to PDF first |

## Known large-file limitations

These formats are supported but may hit limits on very large files:

| Scenario | Behaviour | Workaround |
|---|---|---|
| ZIP archive > ~50 MB | `MemoryError` — MarkItDown expands the entire archive into memory; raises a friendly "insufficient memory" error in the UI | Split the archive into smaller zips or extract the relevant files first |
| ZIP archive 15–50 MB | Conversion succeeds but may take 1–3 minutes | Convert in the app (no timeout); the corpus audit may report TIMEOUT |
| XLSX > ~6 MB with many columns | MarkItDown's `XlsxConverter` may trigger `ONNXRuntimeError` (magika model allocation) or `MemoryError` (numpy array too large). The pipeline automatically falls back to `openpyxl read_only` streaming — lazy row iteration, no ONNX, lower memory use | ⚠ amber badge if result is empty; otherwise converts normally |
| PDF scan-only > ~30 MB | Text-layer check takes 30–120 s to confirm there is no text | Enable OCR for scanned PDFs; large scans are slow even to detect as empty |
| PPTX with many embedded images | File size up to ~280 MB; text extraction is fast (MarkItDown reads slide XML, not images) | No action needed — works fine |

All these are converted by the app with no hard limit. The `full_corpus_audit.py` audit may report TIMEOUT for large ZIPs or PDFs due to its per-file time limit.

## Out of scope (intentional)

- Audio transcription beyond MarkItDown's built-in speech-to-text stub (requires API key)
- Real-time OCR on webcam / screen capture
- Cloud document formats (Google Docs, Notion) — require OAuth; out of scope for a local tool
