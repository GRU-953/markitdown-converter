"""
Unified conversion pipeline.

One entry point — convert_file() — that transparently chains the three
capabilities behind a single action:

    1. If the input is an image  -> Tesseract OCR  (ocr_engine)
       If the input is a PDF     -> MarkItDown (text-layer) with OCR fallback
       If the input is a .doc    -> OLE binary extraction (olefile)
       otherwise                 -> MarkItDown document conversion
    2. If the resulting text is Bijoy/SutonnyMJ encoded (and contains no
       Unicode Bengali codepoints)
       -> convert it to Unicode Bengali               (bijoy_unicode)

Every external dependency is injectable, so the whole pipeline is unit-testable
without MarkItDown, Tesseract, or any GUI.
"""

import re
import struct
from pathlib import Path

from bijoy_unicode import convert_bijoy_to_unicode, is_bijoy
from ocr_engine import ocr_image, ocr_pdf

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
PDF_EXT = ".pdf"
DOC_EXT = ".doc"
RTF_EXT = ".rtf"
# Formats that contain no text — return a friendly error instead of a cryptic one
UNSUPPORTED_EXTS = {
    ".eps", ".ai",          # PostScript / Illustrator vector
    ".indd", ".indt",       # Adobe InDesign
    ".otf", ".ttf", ".otc", # OpenType / TrueType fonts
    ".pfb", ".pfm",         # PostScript fonts
    ".woff", ".woff2",      # Web fonts
    ".psd",                 # Photoshop (binary layers, no plain text)
    ".odt", ".ods", ".odp", ".odg",  # OpenDocument — save as .docx/.pdf first
}

try:
    from striprtf.striprtf import rtf_to_text as _rtf_to_text
    _STRIPRTF_AVAILABLE = True
except ImportError:
    _STRIPRTF_AVAILABLE = False

_mid = None


def _get_markitdown():
    """Lazily construct a shared MarkItDown instance."""
    global _mid
    if _mid is None:
        from markitdown import MarkItDown
        _mid = MarkItDown()
    return _mid


def _extract_legacy_doc(path: str) -> str:
    """
    Extract text from old binary .doc (Word 97-2003) using olefile.

    Word 97-2003 non-complex files store their main text as a consecutive ANSI
    (cp1252) block in the WordDocument stream immediately after the StyleSheet
    table. We read the StyleSheet size from FibRgFcLcb97 pair 1 (fcStshf /
    lcbStshf) to locate the text start, then read ccpText bytes.

    Returns empty string if olefile is unavailable, the file is not a valid OLE
    Compound Document, or extraction produces no printable content.
    """
    try:
        import olefile
    except ImportError:
        return ""

    try:
        with olefile.OleFileIO(path) as ole:
            if not ole.exists("WordDocument"):
                return ""
            data = ole.openstream("WordDocument").read()

            # Parse FIB header chain to locate FibRgFcLcb97
            csw = struct.unpack_from("<H", data, 32)[0]
            cslw = struct.unpack_from("<H", data, 32 + 2 + csw * 2)[0]
            fib_rglw_start = 32 + 2 + csw * 2 + 2
            cc_text = struct.unpack_from("<I", data, fib_rglw_start + 12)[0]
            fib_rglw_end = fib_rglw_start + cslw * 4
            fib_rgfclcb_start = fib_rglw_end + 2  # skip cbRgFcLcb (2 bytes)

            if cc_text == 0 or cc_text > len(data):
                return ""

            # Which table stream (1Table = bit 9 of FibBase flags at offset 10)
            fib_flags = struct.unpack_from("<H", data, 10)[0]
            table_name = "1Table" if (fib_flags & 0x0200) else "0Table"

            text_start = None

            # Primary: read CP[0] from PlcfBteChpx in the Table stream.
            # In Word 97-2003 ANSI docs, CP[0] == byte offset of text start in
            # the WordDocument stream (character position == byte position for ANSI).
            if ole.exists(table_name):
                tdata = ole.openstream(table_name).read()
                fc_chpx = struct.unpack_from("<I", data, fib_rgfclcb_start + 12 * 8)[0]
                if fc_chpx + 4 <= len(tdata):
                    cp0 = struct.unpack_from("<I", tdata, fc_chpx)[0]
                    if 0 < cp0 < len(data) and cp0 + cc_text <= len(data):
                        text_start = cp0

            # Fallback: scan for highest-density ANSI region after FIB end
            if text_start is None:
                fib_end = fib_rgfclcb_start + struct.unpack_from("<H", data, fib_rglw_end)[0] * 8
                if fib_end + 2 <= len(data):
                    cswNew = struct.unpack_from("<H", data, fib_end)[0]
                    fib_end += 2 + cswNew * 2
                scan_len = min(cc_text, 300)
                best_ratio, best_off = 0.0, fib_end
                for start in range(fib_end, min(len(data) - scan_len, fib_end + 4000), 2):
                    if start + cc_text > len(data):
                        break
                    chunk = data[start:start + scan_len].decode("cp1252", errors="replace")
                    pr = sum(1 for c in chunk if 0x20 <= ord(c) <= 0x7E or c in "\r\n\t\x07") / len(chunk)
                    if pr > best_ratio:
                        best_ratio, best_off = pr, start
                text_start = best_off

            if text_start + cc_text > len(data):
                return ""

            raw = data[text_start: text_start + cc_text]
            text = raw.decode("cp1252", errors="replace")

            # Translate Word binary control characters to whitespace / newlines
            text = text.replace("\x07", "\n")   # paragraph end mark
            text = text.replace("\x0b", "\n")   # line break
            text = text.replace("\x0c", "\n")   # page break
            text = text.replace("\x00", "")     # null bytes (table cell separators)
            text = re.sub(r"[\x01-\x06\x08\x0e-\x1f]", " ", text)
            text = re.sub(r"[ \t]{4,}", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()

            # Sanity: require at least 10% printable chars
            printable = sum(1 for c in text if c.isprintable())
            if not text or printable / len(text) < 0.10:
                return ""

            return text
    except Exception:
        return ""


def is_image(path) -> bool:
    """Return True if *path* has a known raster-image extension."""
    return Path(path).suffix.lower() in IMAGE_EXTS


def is_pdf(path) -> bool:
    """Return True if *path* is a PDF file."""
    return Path(path).suffix.lower() == PDF_EXT


def is_legacy_doc(path) -> bool:
    """Return True if *path* is a .doc (old binary Word) file."""
    return Path(path).suffix.lower() == DOC_EXT


def is_rtf(path) -> bool:
    """Return True if *path* is an RTF file."""
    return Path(path).suffix.lower() == RTF_EXT


def is_unsupported(path) -> bool:
    """Return True if *path* has an extension that can never yield text."""
    return Path(path).suffix.lower() in UNSUPPORTED_EXTS


def convert_file(
    path,
    *,
    auto_ocr: bool = True,
    auto_bijoy: bool = True,
    ocr_lang: str = "English",
    markitdown=None,
    ocr_func=None,
    ocr_pdf_func=None,
    is_bijoy_func=is_bijoy,
    bijoy_func=convert_bijoy_to_unicode,
) -> dict:
    """
    Convert a single file to Markdown/text, applying OCR and Bijoy→Unicode
    automatically when applicable.

    For PDFs: tries MarkItDown text extraction first; if the result is empty
    (scanned/image-only PDF) and auto_ocr is enabled, falls back to
    page-by-page OCR via pymupdf.

    For .doc (old binary Word): uses OLE-based extraction, then falls back to
    MarkItDown if OLE extraction returns nothing.

    Returns a dict::

        {"text": str, "steps": ["ocr"|"markitdown"|"pdf_ocr"|"doc_ole", "bijoy"?]}

    Raises FileNotFoundError if the path does not exist; any converter error
    propagates to the caller (the Api layer turns it into a per-file status).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")

    if is_unsupported(p):
        ext = p.suffix
        raise ValueError(
            f"Unsupported format ({ext}): no text can be extracted from "
            "vector graphics, font files, or design documents."
        )

    steps = []

    if not auto_ocr and is_image(p):
        # B-4: image with OCR disabled — nothing to extract
        return {"text": "", "steps": ["image_ocr_disabled"]}
    elif auto_ocr and is_image(p):
        runner = ocr_func or ocr_image
        text = runner(str(p), ocr_lang)
        steps.append("ocr")
        if not text.strip():
            steps.append("ocr_empty")
    elif is_pdf(p):
        # Always try text-layer extraction first
        md = markitdown or _get_markitdown()
        result = md.convert(str(p))
        text = result.text_content or ""
        steps.append("markitdown")
        # Fall back to OCR if the PDF has no text layer
        if auto_ocr and not text.strip():
            pdf_runner = ocr_pdf_func or ocr_pdf
            text = pdf_runner(str(p), ocr_lang)
            steps = ["pdf_ocr"]
        # E-2: PDF with no text and OCR disabled (or OCR also returned empty)
        elif not text.strip() and "pdf_ocr" not in steps:
            steps.append("pdf_empty")
    elif is_legacy_doc(p):
        # Try OLE binary extraction first (handles Word 97-2003 ANSI/Bijoy docs)
        text = _extract_legacy_doc(str(p))
        if text.strip():
            steps.append("doc_ole")
        else:
            # Fall back to MarkItDown (may succeed for newer .doc saved as OOXML)
            try:
                md = markitdown or _get_markitdown()
                result = md.convert(str(p))
                text = result.text_content or ""
                steps.append("markitdown")
            except Exception:
                text = ""
        # E-1: .doc produced no text from either path
        if not text.strip():
            steps.append("doc_empty")
    elif is_rtf(p):
        # RTF: try striprtf first, fall back to MarkItDown
        text = ""
        if _STRIPRTF_AVAILABLE:
            try:
                raw_rtf = p.read_bytes().decode("cp1252", errors="replace")
                text = _rtf_to_text(raw_rtf)
            except Exception:
                text = ""
        if not text.strip():
            # Fall back to MarkItDown
            try:
                md = markitdown or _get_markitdown()
                result = md.convert(str(p))
                text = result.text_content or ""
            except Exception:
                text = ""
        steps.append("rtf")
    else:
        md = markitdown or _get_markitdown()
        result = md.convert(str(p))
        text = result.text_content or ""
        steps.append("markitdown")

    if auto_bijoy and text and is_bijoy_func(text):
        text = bijoy_func(text)
        steps.append("bijoy")

    return {"text": text, "steps": steps}
