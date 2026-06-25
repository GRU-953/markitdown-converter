"""
MarkItDown Converter — GRU-953
pywebview desktop app: Python backend + HTML/CSS/JS frontend (WebView2).

This module owns the window and the Api bridge exposed to JavaScript as
``window.pywebview.api``. All heavy lifting lives in the pure-Python modules
(pipeline, ocr_engine, bijoy_unicode, settings) so the bridge stays thin.
"""

import os
import sys
import time
import threading
import urllib.request
import json as _json
from pathlib import Path

# In the PyInstaller --onefile bundle, hide the console window immediately.
# We build with --console (not --windowed) to avoid the runw.exe bootloader
# hang on Python 3.14, then suppress the console so users never see it.
if hasattr(sys, "_MEIPASS"):
    try:
        import ctypes as _ctypes
        _hwnd = _ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            _ctypes.windll.user32.ShowWindow(_hwnd, 0)   # SW_HIDE = 0
    except Exception:
        pass

import webview

import settings as _settings
from bijoy_unicode import convert_bijoy_to_unicode, detect_script
from ocr_engine import ocr_image, ocr_pdf, tesseract_available, pymupdf_available
from pipeline import convert_file, is_image, is_pdf, is_legacy_doc

APP_VERSION = "v4.3.0"
MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB hard limit
_RELEASES_API = "https://api.github.com/repos/GRU-953/markitdown-converter/releases/latest"


def _validate_path(path: str) -> None:
    """
    Raise ValueError on security violations before conversion.
    Catches path traversal, missing files, and oversized inputs.
    """
    p = Path(path).resolve()
    # Reject paths that escaped a common parent via traversal fragments
    try:
        p.relative_to(p.anchor)  # always true — real guard is the resolve() above
    except ValueError:
        pass
    # Disallow names with traversal markers that survived resolve()
    raw = str(path)
    if ".." in raw.replace("\\", "/").split("/"):
        raise ValueError("Invalid file path.")
    if not p.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if p.is_dir():
        raise ValueError("Path is a directory, not a file.")
    size = p.stat().st_size
    if size > MAX_FILE_BYTES:
        mb = size // (1024 * 1024)
        raise ValueError(f"File is too large ({mb} MB). Maximum allowed size is 200 MB.")


def _resource(rel: str) -> Path:
    """Resolve a path inside the bundle (PyInstaller) or the source tree."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / rel


def _now() -> str:
    """ISO-ish local timestamp for history entries."""
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Api:
    """Methods callable from the frontend as window.pywebview.api.<name>()."""

    def __init__(self):
        self._cfg = _settings.load()
        self._window = None

    # ── settings ────────────────────────────────────────────────────────────

    def get_config(self) -> dict:
        return self._cfg

    def save_config(self, patch: dict) -> dict:
        if isinstance(patch, dict):
            self._cfg.update(patch)
            _settings.save(self._cfg)
        return self._cfg

    # ── file selection ────────────────────────────────────────────────────────

    def pick_files(self) -> list:
        """Open the native file picker; return a list of {path, name}."""
        types = (
            "Supported files (*.pdf;*.doc;*.docx;*.xlsx;*.pptx;*.html;*.htm;*.csv;"
            "*.json;*.xml;*.zip;*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.tiff;*.wav;*.mp3)",
            "All files (*.*)",
        )
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True, file_types=types
        )
        return [self._meta(p) for p in (result or [])]

    def pick_image(self) -> dict:
        types = ("Images (*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.gif;*.webp)",
                 "All files (*.*)")
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=False, file_types=types
        )
        if result:
            return self._meta(result[0])
        return {}

    def pick_scan_file(self) -> dict:
        """Open picker for the Scan view — accepts images AND PDFs."""
        types = (
            "Images & PDFs (*.png;*.jpg;*.jpeg;*.bmp;*.tiff;*.gif;*.webp;*.pdf)",
            "All files (*.*)",
        )
        result = self._window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=False, file_types=types
        )
        if result:
            p = Path(result[0])
            _settings.add_recent(self._cfg, str(p))
            _settings.save(self._cfg)
            return {"path": str(p), "name": p.name, "is_pdf": is_pdf(p)}
        return {}

    def add_dropped(self, paths: list) -> list:
        """Validate dropped paths (from the HTML5 drop handler)."""
        out = []
        for p in paths or []:
            if p and Path(p).exists():
                out.append(self._meta(p))
        return out

    def _meta(self, path: str) -> dict:
        p = Path(path)
        _settings.add_recent(self._cfg, str(p))
        _settings.save(self._cfg)
        return {"path": str(p), "name": p.name, "is_image": is_image(p),
                "is_doc": is_legacy_doc(p)}

    # ── conversion ──────────────────────────────────────────────────────────

    def convert(self, path: str) -> dict:
        """Run the unified pipeline on one file; never raises to the frontend."""
        try:
            _validate_path(path)
            out = convert_file(
                path,
                auto_ocr=self._cfg.get("auto_ocr", True),
                auto_bijoy=self._cfg.get("auto_bijoy", True),
                ocr_lang=self._cfg.get("ocr_language", "English"),
            )
            entry = {
                "name": Path(path).name, "path": str(path),
                "ts": _now(), "steps": out["steps"], "ok": True,
            }
            _settings.add_history(self._cfg, entry)
            _settings.save(self._cfg)
            return {"ok": True, "text": out["text"], "steps": out["steps"]}
        except Exception as exc:
            _settings.add_history(self._cfg, {
                "name": Path(path).name, "path": str(path),
                "ts": _now(), "steps": [], "ok": False, "error": str(exc),
            })
            _settings.save(self._cfg)
            return {"ok": False, "error": str(exc)}

    # ── OCR + Bijoy (standalone views) ────────────────────────────────────────

    def ocr(self, path: str, language: str, auto_bijoy: bool) -> dict:
        try:
            if not tesseract_available():
                return {"ok": False, "error": "Tesseract OCR is not available."}
            if is_pdf(path):
                if not pymupdf_available():
                    return {"ok": False, "error": "PDF scanning requires pymupdf — run: pip install pymupdf"}
                text = ocr_pdf(path, language)
            else:
                text = ocr_image(path, language)
            if auto_bijoy and text:
                from bijoy_unicode import is_bijoy
                if is_bijoy(text):
                    text = convert_bijoy_to_unicode(text)
            return {"ok": True, "text": text}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def bijoy_convert(self, text: str) -> dict:
        return {"ok": True, "text": convert_bijoy_to_unicode(text or "")}

    def detect(self, text: str) -> str:
        return detect_script((text or "")[:300])

    def tesseract_ok(self) -> bool:
        return tesseract_available()

    def pymupdf_ok(self) -> bool:
        return pymupdf_available()

    # ── export ────────────────────────────────────────────────────────────────

    def export_text(self, text: str, ext: str, suggested: str) -> dict:
        """Save *text* via the native save dialog. ext like 'md','txt','html'."""
        try:
            init = self._cfg.get("last_output_folder") or None
            dest = self._window.create_file_dialog(
                webview.FileDialog.SAVE, directory=init or "",
                save_filename=suggested or f"output.{ext}",
            )
            if not dest:
                return {"ok": False, "cancelled": True}
            dest = dest if isinstance(dest, str) else dest[0]
            payload = _render(text or "", ext)
            Path(dest).write_text(payload, encoding="utf-8")
            self._cfg["last_output_folder"] = str(Path(dest).parent)
            _settings.save(self._cfg)
            return {"ok": True, "path": dest}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def export_combined(self, items: list, ext: str) -> dict:
        """Combine many {name, text} into one document and save it."""
        joined = "\n\n---\n\n".join(
            f"# {it.get('name','')}\n\n{it.get('text','')}" for it in (items or [])
        )
        return self.export_text(joined, ext, f"combined.{ext}")

    # ── history ────────────────────────────────────────────────────────────────

    def get_history(self) -> list:
        return self._cfg.get("history", [])

    def clear_history(self) -> list:
        self._cfg["history"] = []
        _settings.save(self._cfg)
        return []

    # ── updates ───────────────────────────────────────────────────────────────

    def get_version(self) -> str:
        return APP_VERSION

    def check_update(self) -> dict:
        """Query GitHub for the latest release. Returns {latest, url, has_update}."""
        try:
            req = urllib.request.Request(
                _RELEASES_API,
                headers={"Accept": "application/vnd.github+json",
                         "User-Agent": f"MarkItDownConverter/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode())
            latest = data.get("tag_name", APP_VERSION)
            url = data.get("html_url", "")
            return {"latest": latest, "url": url,
                    "has_update": latest != APP_VERSION}
        except Exception:
            return {"latest": APP_VERSION, "url": "", "has_update": False}


def _render(text: str, ext: str) -> str:
    """Turn Markdown into the requested output format."""
    if ext == "html":
        try:
            import markdown as _md
            body = _md.markdown(text, extensions=["tables", "fenced_code"])
        except Exception:
            body = "<pre>" + text + "</pre>"
        return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>MarkItDown export</title></head><body>"
                + body + "</body></html>")
    return text   # md / txt are written as-is


def _selftest(path: str) -> int:
    """Headless conversion check — used to smoke-test the frozen bundle.
    Writes the result to stdout so a redirected launch can capture it."""
    try:
        from pipeline import convert_file
        out = convert_file(path)
        sys.stdout.write(f"SELFTEST_OK steps={out['steps']} text={out['text'][:60]!r}\n")
        sys.stdout.flush()
        return 0
    except Exception as exc:
        sys.stdout.write(f"SELFTEST_FAIL {type(exc).__name__}: {exc}\n")
        sys.stdout.flush()
        return 1


def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--selftest":
        sys.exit(_selftest(sys.argv[2]))

    api = Api()
    cfg = api.get_config()
    bg = "#0F1020" if cfg.get("theme") != "Light" else "#FFFFFF"
    window = webview.create_window(
        "MarkItDown Converter",
        url=str(_resource("web/index.html")),
        js_api=api,
        width=1180, height=760, min_size=(900, 600),
        background_color=bg,
    )
    api._window = window
    webview.start()


if __name__ == "__main__":
    main()
