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
# ocr_engine is imported lazily inside convert_file — defers pytesseract + PIL init
# to the first conversion that actually needs OCR, keeping startup lean.

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".gif", ".webp"}
PDF_EXT = ".pdf"
DOC_EXT = ".doc"
RTF_EXT = ".rtf"
XLSX_EXT = {".xlsx"}
# Formats where direct UTF-8/cp1252 read is sufficient — no MarkItDown/ONNX needed.
# Avoids loading the 400 MB magika model for trivial text files.
PLAIN_TEXT_EXTS = {
    ".txt", ".md",
    ".ini", ".cfg", ".conf", ".log",
    ".csv", ".tsv",
}
# Formats that contain no text — return a friendly error instead of a cryptic one
UNSUPPORTED_EXTS = {
    ".eps", ".ai",          # PostScript / Illustrator vector
    ".indd", ".indt",       # Adobe InDesign
    ".otf", ".ttf", ".otc", # OpenType / TrueType fonts
    ".pfb", ".pfm",         # PostScript fonts
    ".woff", ".woff2",      # Web fonts
    ".psd",                 # Photoshop (binary layers, no plain text)
}

try:
    from striprtf.striprtf import rtf_to_text as _rtf_to_text
    _STRIPRTF_AVAILABLE = True
except ImportError:
    _STRIPRTF_AVAILABLE = False
    def _rtf_to_text(rtf_text: str) -> str:  # noqa: F811
        return ""

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


# Known Bijoy/SutonnyMJ font names (normalised: lowercase, whitespace collapsed,
# comma-suffix stripped). Ported from Mukti's FontRegistry curated allowlist.
# Only EXACT matches classify as Bijoy — no fuzzy MJ-suffix heuristic (Mukti
# decision D-0006: NikoshMJ, TangonMotaMJ, SonkhoMJ are confirmed Unicode fonts).
_BIJOY_FONTS = frozenset([
    "sutonnymj", "sutonnymj bold", "sutonnymj italic",
    "sutonnymj regular", "sutonnymj-regular", "sutonnymjbold",
    "sutonny mj", "sutonnycmj", "sutonnyemj", "sutonnysushreemj",
    "tonnybanglaj",
    "gangamj", "padmamj", "jomunamj", "meghnamj",
    "teeshtamj", "turagmj", "sandipanmj",
    "jugantormj", "samakalmj", "jaijaidinmj",
    "siyam rupali ansi",   # ANSI build only; plain "siyam rupali" is Unicode
])

_WS_RE = re.compile(r"\s+")


def _docx_font_has_bijoy(path: str) -> bool:
    """Return True if any run or style in the DOCX uses a known Bijoy font.

    Scans both word/document.xml (per-run fonts) and word/styles.xml (style
    definitions) because old Bijoy documents commonly set SutonnyMJ on a
    paragraph style, leaving word/document.xml runs with no explicit w:rFonts.
    Normalisation mirrors Mukti's FontRegistry.Normalize: strip, lowercase,
    collapse whitespace, drop everything from the first comma onward.
    Returns False on any error (unreadable, not a ZIP, malformed XML).
    """
    import zipfile
    import xml.etree.ElementTree as ET
    _DOCX_XML_PARTS = ("word/document.xml", "word/styles.xml")
    try:
        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            parts = [z.read(p) for p in _DOCX_XML_PARTS if p in names]
        if not parts:
            return False
        ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
        for xml_bytes in parts:
            root = ET.fromstring(xml_bytes)
            for elem in root.iter(f"{{{ns}}}rFonts"):
                for val in elem.attrib.values():
                    norm = _WS_RE.sub(" ", val.strip().lower())
                    comma = norm.find(",")
                    if comma >= 0:
                        norm = norm[:comma].strip()
                    if norm in _BIJOY_FONTS:
                        return True
    except Exception:
        pass
    return False


def _rtf_font_has_bijoy(raw_rtf: str) -> bool:
    """Return True if the RTF font table declares a known Bijoy font.

    Scans the {\fonttbl} block of raw RTF text for font names matching the
    curated _BIJOY_FONTS allowlist. Normalisation mirrors _docx_font_has_bijoy:
    lowercase, collapse whitespace, drop comma-suffix style variants.
    Returns False when no fonttbl block is found or on any parse failure.
    """
    import re
    m = re.search(r'\{\\fonttbl((?:[^{}]|\{[^}]*\})*)\}', raw_rtf)
    if not m:
        return False
    fonttbl = m.group(1)
    # Each ';'-terminated segment holds one font declaration.  Remove RTF
    # control words (\word or \wordN) and braces to isolate the font name.
    for seg in fonttbl.split(";"):
        name = re.sub(r"\\[a-z]+\d*", "", seg)
        name = name.replace("{", "").replace("}", "").strip().lower()
        if not name:
            continue
        comma = name.find(",")
        if comma >= 0:
            name = name[:comma].strip()
        name = _WS_RE.sub(" ", name).strip()
        if name in _BIJOY_FONTS:
            return True
    return False


def _pptx_font_has_bijoy(path: str) -> bool:
    """Return True if any slide, master, layout, or theme in the PPTX uses a
    known Bijoy font.

    PPTX (and its variants .pptm/.ppsx/.potx) is a ZIP of XML files.  Font
    names appear on ``<a:latin typeface="..."/>`` elements in the DrawingML
    namespace.  We scan slides, slide masters, slide layouts, and the theme
    file — the places where a presentation template font is most likely set.
    Normalisation mirrors _docx_font_has_bijoy.  Returns False on any error.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    _DML_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
    _PPTX_TARGETS = ("ppt/slides/slide", "ppt/slideMasters/slideMaster",
                     "ppt/slideLayouts/slideLayout", "ppt/theme/theme")
    try:
        with zipfile.ZipFile(path, "r") as z:
            names = z.namelist()
            parts = [
                z.read(n) for n in names
                if any(n.startswith(prefix) for prefix in _PPTX_TARGETS)
            ]
        if not parts:
            return False
        for xml_bytes in parts:
            root = ET.fromstring(xml_bytes)
            for tag in (f"{{{_DML_NS}}}latin", f"{{{_DML_NS}}}ea",
                        f"{{{_DML_NS}}}cs"):
                for elem in root.iter(tag):
                    val = elem.get("typeface", "")
                    if not val or val.startswith("+"):  # skip theme-font refs
                        continue
                    norm = _WS_RE.sub(" ", val.strip().lower())
                    comma = norm.find(",")
                    if comma >= 0:
                        norm = norm[:comma].strip()
                    if norm in _BIJOY_FONTS:
                        return True
    except Exception:
        pass
    return False


def _odt_font_has_bijoy(path: str) -> bool:
    """
    Return True if any ODF text document part declares a Bijoy/SutonnyMJ font.

    ODT (and OTT) is a ZIP of XML files.  Font names appear as ``svg:font-family``
    on ``<style:font-face>`` elements and as ``fo:font-name`` on
    ``<style:text-properties>`` elements in both content.xml and styles.xml.
    Normalisation mirrors the other font-detection helpers.  Returns False on any error.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    _STYLE_NS = "urn:oasis:names:tc:opendocument:xmlns:style:1.0"
    _SVG_NS   = "http://www.w3.org/2000/svg"
    _FO_NS    = "http://www.w3.org/1999/XSL/Format"
    try:
        with zipfile.ZipFile(path, "r") as z:
            parts = []
            for name in ("content.xml", "styles.xml"):
                if name in z.namelist():
                    parts.append(z.read(name))
        if not parts:
            return False
        for xml_bytes in parts:
            root = ET.fromstring(xml_bytes)
            # svg:font-family on <style:font-face>
            for elem in root.iter(f"{{{_STYLE_NS}}}font-face"):
                val = elem.get(f"{{{_SVG_NS}}}font-family", "")
                if val:
                    norm = _WS_RE.sub(" ", val.strip().lower())
                    comma = norm.find(",")
                    if comma >= 0:
                        norm = norm[:comma].strip()
                    if norm in _BIJOY_FONTS:
                        return True
            # fo:font-name on <style:text-properties>
            for elem in root.iter(f"{{{_STYLE_NS}}}text-properties"):
                val = elem.get(f"{{{_FO_NS}}}font-name", "")
                if val:
                    norm = _WS_RE.sub(" ", val.strip().lower())
                    comma = norm.find(",")
                    if comma >= 0:
                        norm = norm[:comma].strip()
                    if norm in _BIJOY_FONTS:
                        return True
    except Exception:
        pass
    return False


def _xlsx_font_has_bijoy(path: str) -> bool:
    """Return True if the XLSX workbook declares a known Bijoy font in xl/styles.xml.

    XLSX is a ZIP of XML files.  Font names appear on ``<name val="..."/>``
    children of ``<font>`` elements inside the SpreadsheetML ``<fonts>`` block
    in ``xl/styles.xml``.  Catches XLSX/XLSM files that contain Bijoy-encoded
    Bengali text in cell values without sufficient Bijoy character density to
    trigger the text-scan threshold (common when a header row is Bijoy but the
    bulk of data is numeric or ASCII).  Returns False on any error.
    """
    import zipfile
    import xml.etree.ElementTree as ET
    _SS_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    try:
        with zipfile.ZipFile(path, "r") as z:
            if "xl/styles.xml" not in z.namelist():
                return False
            xml_bytes = z.read("xl/styles.xml")
        root = ET.fromstring(xml_bytes)
        for elem in root.iter(f"{{{_SS_NS}}}name"):
            val = elem.get("val", "")
            if not val:
                continue
            norm = _WS_RE.sub(" ", val.strip().lower())
            comma = norm.find(",")
            if comma >= 0:
                norm = norm[:comma].strip()
            if norm in _BIJOY_FONTS:
                return True
    except Exception:
        pass
    return False


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


def is_xlsx(path) -> bool:
    """Return True if *path* is a modern Excel (.xlsx) file."""
    return Path(path).suffix.lower() in XLSX_EXT


def _extract_xlsx_direct(path: str) -> str:
    """
    Extract text from an XLSX file using openpyxl in read_only mode.

    Uses read_only=True so memory is proportional to one row at a time, not the
    full sheet. Outputs one GFM markdown table per worksheet (first row = header).
    Multi-sheet workbooks get an H2 heading per sheet.

    Returns empty string if openpyxl is unavailable or extraction fails.
    """
    try:
        import openpyxl
    except ImportError:
        return ""
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        sections = []
        for sheet in wb.worksheets:
            sheet_rows = []
            for row in sheet.iter_rows(values_only=True):
                cells = [
                    str(v).replace("|", "\\|").replace("\n", " ")
                    if v is not None else ""
                    for v in row
                ]
                if any(c.strip() for c in cells):
                    sheet_rows.append(cells)
            if not sheet_rows:
                continue
            # Pad all rows to the same column count so GFM table is valid
            max_cols = max(len(r) for r in sheet_rows)
            padded = [r + [""] * (max_cols - len(r)) for r in sheet_rows]
            header = "| " + " | ".join(padded[0]) + " |"
            sep    = "| " + " | ".join(["---"] * max_cols) + " |"
            data   = "\n".join("| " + " | ".join(r) + " |" for r in padded[1:])
            table  = header + "\n" + sep + ("\n" + data if len(padded) > 1 else "")
            if len(wb.worksheets) > 1 and sheet.title:
                sections.append("## " + sheet.title + "\n\n" + table)
            else:
                sections.append(table)
        wb.close()
        return "\n\n".join(sections)
    except Exception:
        return ""


def is_plain_text(path) -> bool:
    """Return True if *path* can be decoded as plain text without MarkItDown/ONNX."""
    return Path(path).suffix.lower() in PLAIN_TEXT_EXTS


def _read_plain_text(path: str) -> str:
    """Decode a plain-text file trying common encodings in order."""
    p = Path(path)
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return p.read_text(encoding=enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return p.read_bytes().decode("utf-8", errors="replace")


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

    # macOS writes binary resource-fork sidecar files named ._<original>
    # inside ZIP archives; they look like images but are not readable by PIL.
    if p.name.startswith("._"):
        return {"text": "", "steps": ["mac_resource_fork"]}

    steps = []
    _rtf_raw = ""  # populated in the RTF branch; used for font-name detection below

    if not auto_ocr and is_image(p):
        # B-4: image with OCR disabled — nothing to extract
        return {"text": "", "steps": ["image_ocr_disabled"]}
    elif auto_ocr and is_image(p):
        if ocr_func is None:
            from ocr_engine import ocr_image as _ocr_image
            ocr_func = _ocr_image
        text = ocr_func(str(p), ocr_lang)
        steps.append("ocr")
        if not text.strip():
            steps.append("ocr_empty")
    elif is_pdf(p):
        # Always try text-layer extraction first
        md = markitdown or _get_markitdown()
        try:
            result = md.convert(str(p))
            text = result.text_content or ""
        except Exception as e:
            if isinstance(e, MemoryError) or "MemoryError" in str(e):
                raise ValueError(
                    "File is too large to convert: insufficient memory. "
                    "Try closing other applications or converting a smaller file."
                )
            raise
        steps.append("markitdown")
        # Fall back to OCR if the PDF has no text layer
        if auto_ocr and not text.strip():
            if ocr_pdf_func is None:
                from ocr_engine import ocr_pdf as _ocr_pdf
                ocr_pdf_func = _ocr_pdf
            text = ocr_pdf_func(str(p), ocr_lang)
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
        # RTF: read raw bytes once — used by striprtf AND font detection below.
        try:
            _rtf_raw = p.read_bytes().decode("cp1252", errors="replace")
        except Exception:
            _rtf_raw = ""
        text = ""
        if _rtf_raw and _STRIPRTF_AVAILABLE:
            try:
                text = _rtf_to_text(_rtf_raw)
            except Exception:
                pass
        if not text.strip():
            # Fall back to MarkItDown
            try:
                md = markitdown or _get_markitdown()
                result = md.convert(str(p))
                text = result.text_content or ""
            except Exception:
                text = ""
        steps.append("rtf")
        if not text.strip():
            steps.append("rtf_empty")
    elif is_xlsx(p):
        # XLSX ≥ 2 MB: MarkItDown's table formatter builds the full sheet in
        # memory and can hang indefinitely on survey-style files (no exception raised).
        # Use openpyxl read_only streaming directly — lazy row iteration, no ONNX.
        # XLSX < 2 MB: try MarkItDown first (richer markdown table output);
        # fall back to openpyxl on any exception (MemoryError, ONNX error, etc.).
        _xlsx_mb = p.stat().st_size / (1024 * 1024)
        if _xlsx_mb >= 2.0:
            text = _extract_xlsx_direct(str(p))
            steps.append("xlsx_direct")
        else:
            try:
                md = markitdown or _get_markitdown()
                result = md.convert(str(p))
                text = result.text_content or ""
                steps.append("markitdown")
            except Exception:
                text = _extract_xlsx_direct(str(p))
                steps.append("xlsx_direct")
        if not text.strip():
            steps.append("xlsx_empty")
    elif is_plain_text(p):
        # Read directly — no MarkItDown, no ONNX, saves ~400 MB RAM per call.
        # Covers .txt, .md, .ini, .cfg, .conf, .log, .csv, .tsv.
        text = _read_plain_text(str(p))
        steps.append("plaintext")
        if not text.strip():
            steps.append("plaintext_empty")
    else:
        md = markitdown or _get_markitdown()
        try:
            result = md.convert(str(p))
            text = result.text_content or ""
        except Exception as e:
            if isinstance(e, MemoryError) or "MemoryError" in str(e):
                raise ValueError(
                    "File is too large to convert: insufficient memory. "
                    "Try closing other applications or converting a smaller file."
                )
            raise
        steps.append("markitdown")

    if auto_bijoy and text:
        needs_bijoy = is_bijoy_func(text)
        # Font-assisted detection for DOCX: when text-scan misses pure-ASCII
        # Bijoy text (simple consonants with no conjunct chars), the font name
        # embedded in the DOCX metadata is a reliable secondary signal.
        if not needs_bijoy and p.suffix.lower() in (".docx", ".docm", ".dotx", ".dotm"):
            needs_bijoy = _docx_font_has_bijoy(str(p))
        # Font-assisted detection for RTF: same idea — scan the {\fonttbl} block
        # extracted when reading the raw RTF bytes above.
        if not needs_bijoy and _rtf_raw:
            needs_bijoy = _rtf_font_has_bijoy(_rtf_raw)
        # Font-assisted detection for PPTX: scan <a:latin typeface="..."/> in
        # slides, masters, layouts, and theme XML parts.
        _PPTX_EXTS = (".pptx", ".pptm", ".ppsx", ".ppsm", ".potx", ".potm")
        if not needs_bijoy and p.suffix.lower() in _PPTX_EXTS:
            needs_bijoy = _pptx_font_has_bijoy(str(p))
        _ODT_EXTS = (".odt", ".ott")
        if not needs_bijoy and p.suffix.lower() in _ODT_EXTS:
            needs_bijoy = _odt_font_has_bijoy(str(p))
        # Font-assisted detection for XLSX: scan <name val="..."/> in xl/styles.xml.
        # Catches headers-in-Bijoy spreadsheets where numeric/ASCII body dilutes density.
        _XLSX_EXTS = (".xlsx", ".xlsm")
        if not needs_bijoy and p.suffix.lower() in _XLSX_EXTS:
            needs_bijoy = _xlsx_font_has_bijoy(str(p))
        if needs_bijoy:
            text = bijoy_func(text)
            steps.append("bijoy")

    return {"text": text, "steps": steps}
