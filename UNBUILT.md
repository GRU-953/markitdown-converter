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

## Out of scope (intentional)

- Audio transcription beyond MarkItDown's built-in speech-to-text stub (requires API key)
- Real-time OCR on webcam / screen capture
- Cloud document formats (Google Docs, Notion) — require OAuth; out of scope for a local tool
