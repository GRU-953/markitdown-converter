"""
OCR engine: wraps pytesseract for English + Bengali extraction.
Handles both system Tesseract (dev) and bundled binary (PyInstaller .exe).
"""

import os
import sys
from pathlib import Path

import pytesseract
from PIL import Image


def _setup_tesseract():
    """Point pytesseract at the correct Tesseract binary and tessdata."""
    if getattr(sys, "_MEIPASS", None):
        # Running from PyInstaller bundle
        base = Path(sys._MEIPASS) / "tesseract"
        exe  = base / "tesseract.exe"
        data = base / "tessdata"
        if exe.exists():
            pytesseract.pytesseract.tesseract_cmd = str(exe)
        if data.exists():
            os.environ["TESSDATA_PREFIX"] = str(data)
    else:
        # Development: use system Tesseract
        system_exe = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
        if system_exe.exists():
            pytesseract.pytesseract.tesseract_cmd = str(system_exe)
        system_data = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
        if system_data.exists():
            os.environ.setdefault("TESSDATA_PREFIX", str(system_data))


_setup_tesseract()


LANG_CODES = {
    "English":    "eng",
    "বাংলা":     "ben",
    "Both":       "eng+ben",
}


def ocr_image(image_path: str, language: str = "English") -> str:
    """
    Run OCR on an image file and return the extracted text.

    Args:
        image_path: Path to the image file.
        language:   One of "English", "বাংলা", or "Both".

    Returns:
        Extracted text string.

    Raises:
        FileNotFoundError: If image_path does not exist.
        RuntimeError: If Tesseract is not available.
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    lang_code = LANG_CODES.get(language, "eng")

    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img, lang=lang_code)
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract not found. Install from https://github.com/UB-Mannheim/tesseract/wiki"
        )
    except Exception as exc:
        raise RuntimeError(f"OCR failed: {exc}") from exc


def tesseract_available() -> bool:
    """Return True if Tesseract binary is reachable."""
    try:
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False
