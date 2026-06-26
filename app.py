# SPDX-FileCopyrightText: 2026 Aninda Sundar Howlader (GRU-953)
# SPDX-License-Identifier: Apache-2.0
"""
GRU953 Markdown — GRU953
pywebview desktop app: Python backend + HTML/CSS/JS frontend (WebView2).

This module owns the window and the Api bridge exposed to JavaScript as
``window.pywebview.api``. All heavy lifting lives in the pure-Python modules
(pipeline, ocr_engine, bijoy_unicode, settings) so the bridge stays thin.
"""

import sys
import time
import urllib.request
import json as _json
from pathlib import Path

import webview

import settings as _settings
from bijoy_unicode import convert_bijoy_to_unicode, detect_script
# ocr_engine imported lazily inside each Api method — defers pytesseract + PIL
# init until first actual OCR call so the window opens faster on startup.
from pipeline import convert_file, is_image, is_pdf, is_legacy_doc

APP_VERSION = "v4.10.39"
MAX_FILE_BYTES = 200 * 1024 * 1024  # 200 MB hard limit
_RELEASES_API = "https://api.github.com/repos/GRU-953/gru953-markdown/releases/latest"


def _validate_path(path: str) -> None:
    """
    Raise ValueError on security violations before conversion.
    Catches path traversal, symlinks, missing files, and oversized inputs.
    """
    orig = Path(path)
    # Check symlink BEFORE resolve() — resolve() follows symlinks so is_symlink() would be False after
    if orig.is_symlink():
        raise ValueError("Symlink paths are not permitted.")
    # Disallow traversal markers in the raw path string
    raw = str(path)
    if ".." in raw.replace("\\", "/").split("/"):
        raise ValueError("Invalid file path.")
    p = orig.resolve()
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

    def get_locales(self) -> dict:
        """Return the bilingual UI string catalogues as {"en": {...}, "bn": {...}}.

        Read from the bundled ``locales/`` directory so the frontend can switch
        languages instantly with no further round-trips. Best-effort: a missing
        or unreadable file yields an empty dict so the UI falls back to its keys.
        """
        out = {}
        for code in ("en", "bn"):
            try:
                p = _resource(f"locales/{code}.json")
                out[code] = _json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                out[code] = {}
        return out

    def save_config(self, patch: dict) -> dict:
        if isinstance(patch, dict):
            self._cfg.update(patch)
            _settings.save(self._cfg)
        return self._cfg

    # ── file selection ────────────────────────────────────────────────────────

    def pick_files(self) -> list:
        """Open the native file picker; return a list of {path, name}."""
        types = (
            "Supported files (*.pdf;*.doc;*.docx;*.rtf;*.xlsx;*.pptx;*.html;*.htm;*.csv;"
            "*.json;*.xml;*.zip;*.png;*.jpg;*.jpeg;*.gif;*.bmp;*.tif;*.tiff;*.webp;*.wav;*.mp3)",
            "All files (*.*)",
        )
        try:
            result = self._window.create_file_dialog(
                webview.FileDialog.OPEN, allow_multiple=True, file_types=types,
                **self._dialog_dir(),
            )
        except Exception:
            result = None
        if result:
            folder = str(Path(result[0]).parent)
            self._cfg["last_input_folder"] = folder
            _settings.save(self._cfg)
        return [self._meta(p) for p in (result or [])]

    def _dialog_dir(self) -> dict:
        """Return a {directory: ...} kwarg with the best available starting folder.

        WebView2's file dialog silently fails (or raises) when ``directory`` is
        absent or an empty string on some Windows configurations, so we always
        resolve a real path: saved last-used folder → Documents → home dir.
        """
        init_dir = self._cfg.get("last_input_folder") or ""
        if init_dir and Path(init_dir).is_dir():
            return {"directory": init_dir}
        for fallback in (Path.home() / "Documents", Path.home()):
            if fallback.is_dir():
                return {"directory": str(fallback)}
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
                "is_doc": is_legacy_doc(p), "size": p.stat().st_size}

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

    # ── Bijoy (standalone view) ───────────────────────────────────────────────

    def bijoy_convert(self, text: str) -> dict:
        return {"ok": True, "text": convert_bijoy_to_unicode(text or "")}

    def detect(self, text: str) -> str:
        return detect_script((text or "")[:300])

    # ── Windows appearance ────────────────────────────────────────────────────

    def get_windows_accent(self) -> dict:
        """Return the Windows accent colour as a hex string (e.g. '#0078D4').

        Reads DWM\\ColorizationColor from HKCU. The DWORD is 0xAARRGGBB.
        Falls back to GRU953 Teal on any error (non-Windows, permission, etc.).
        """
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\DWM",
            )
            val, _ = winreg.QueryValueEx(key, "ColorizationColor")
            winreg.CloseKey(key)
            r = (val >> 16) & 0xFF
            g = (val >> 8) & 0xFF
            b = val & 0xFF
            return {"ok": True, "hex": f"#{r:02X}{g:02X}{b:02X}"}
        except Exception as exc:
            return {"ok": False, "hex": "#0A6E5C", "error": str(exc)}

    def get_platform(self) -> str:
        """Return the OS platform: 'windows', 'darwin', or 'linux'."""
        import sys as _sys
        if _sys.platform == "win32":
            return "windows"
        if _sys.platform == "darwin":
            return "darwin"
        return _sys.platform

    def get_system_info(self) -> dict:
        """Return lightweight hardware capability hints for adaptive behaviour."""
        import os as _os
        cpu = _os.cpu_count() or 1
        return {"cpu_count": cpu, "is_low_end": cpu <= 2}

    # ── export ────────────────────────────────────────────────────────────────

    def _export_dir(self) -> dict:
        """Return {directory: ...} for the save dialog, mirroring _dialog_dir() logic."""
        d = self._cfg.get("last_output_folder") or ""
        if d and Path(d).is_dir():
            return {"directory": d}
        for fb in (Path.home() / "Documents", Path.home()):
            if fb.is_dir():
                return {"directory": str(fb)}
        return {}

    def export_text(self, text: str, ext: str, suggested: str) -> dict:
        """Save *text* via the native save dialog. ext like 'md','txt','html'."""
        try:
            dest = self._window.create_file_dialog(
                webview.FileDialog.SAVE, save_filename=suggested or f"output.{ext}",
                **self._export_dir(),
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
        """Query GitHub for the latest release.

        Returns {latest, url, installer, has_update}. ``installer`` is the direct
        download URL of the Setup installer asset (falls back to the portable exe),
        so the frontend can offer one-click download-and-install.
        """
        try:
            req = urllib.request.Request(
                _RELEASES_API,
                headers={"Accept": "application/vnd.github+json",
                         "User-Agent": f"GRU953Markdown/{APP_VERSION}"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = _json.loads(resp.read().decode())
            latest = data.get("tag_name", APP_VERSION)
            url = data.get("html_url", "")
            assets = data.get("assets", []) or []
            installer = ""
            for a in assets:                              # prefer the guided installer
                if a.get("name", "").lower().endswith("setup.exe"):
                    installer = a.get("browser_download_url", "")
                    break
            if not installer:                             # fall back to the portable exe
                for a in assets:
                    if a.get("name", "").lower().endswith(".exe"):
                        installer = a.get("browser_download_url", "")
                        break
            return {"latest": latest, "url": url, "installer": installer,
                    "has_update": latest != APP_VERSION}
        except Exception:
            return {"latest": APP_VERSION, "url": "", "installer": "",
                    "has_update": False}

    def install_update(self, download_url: str) -> dict:
        """Open the download URL in the user's default browser.

        Downloading a file to temp and executing it with os.startfile() is a
        pattern Windows Defender treats as potentially malicious.  Instead we
        hand the URL to the browser and let the user run the installer manually.
        Only https github.com / *.githubusercontent.com URLs are accepted.
        """
        try:
            if not download_url or not download_url.lower().startswith("https://"):
                return {"ok": False, "error": "No valid URL."}
            import urllib.parse, webbrowser
            _host = urllib.parse.urlparse(download_url).netloc.lower()
            if _host != "github.com" and not _host.endswith(".githubusercontent.com"):
                return {"ok": False, "error": "URL must be from github.com or githubusercontent.com."}
            webbrowser.open(download_url)
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def quit_app(self) -> None:
        """Close the main window (reserved for callers that need it)."""
        try:
            if self._window:
                self._window.destroy()
        except Exception:
            pass


def _render(text: str, ext: str) -> str:
    """Turn Markdown into the requested output format."""
    if ext == "html":
        try:
            import markdown as _md
            body = _md.markdown(text, extensions=["tables", "fenced_code"])
        except Exception:
            import html as _html
            body = "<pre>" + _html.escape(text) + "</pre>"
        return ("<!DOCTYPE html><html><head><meta charset='utf-8'>"
                "<title>GRU953 Markdown export</title></head><body>"
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
    bg = "#10211D" if cfg.get("theme") != "Light" else "#F7F8F7"
    window = webview.create_window(
        "GRU953 Markdown",
        url=str(_resource("web/index.html")),
        js_api=api,
        width=1180, height=760, min_size=(900, 600),
        background_color=bg,
    )
    api._window = window
    webview.start()


if __name__ == "__main__":
    main()
