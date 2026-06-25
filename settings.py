"""
Persistent user settings — stored as JSON in the user's home directory.
All I/O is best-effort: exceptions are silenced so a bad settings file
never prevents the app from starting.
"""

import json
from pathlib import Path

_FILE = Path.home() / ".markitdown_converter.json"
_MAX_RECENT = 10
_MAX_HISTORY = 100

_DEFAULTS: dict = {
    "theme": "System",          # Light | Dark | System
    "palette": "indigo",        # indigo | violet | slate
    "ocr_language": "English",
    "auto_ocr": True,
    "auto_bijoy": True,
    "last_output_folder": "",
    "recent_files": [],
    "history": [],              # list of {name, path, ts, steps, ok}
    "onboarding_seen": False,   # show welcome overlay on first launch
}


def load() -> dict:
    """Return settings dict, falling back to defaults on any read/parse error."""
    try:
        data = json.loads(_FILE.read_text(encoding="utf-8"))
        merged = {**_DEFAULTS, **data}
        merged["recent_files"] = [
            p for p in merged.get("recent_files", [])
            if isinstance(p, str)
        ][:_MAX_RECENT]
        merged["history"] = [
            h for h in merged.get("history", [])
            if isinstance(h, dict)
        ][:_MAX_HISTORY]
        return merged
    except Exception:
        return dict(_DEFAULTS)


def save(settings: dict) -> None:
    """Write settings to disk; silently ignore any I/O error."""
    try:
        _FILE.write_text(
            json.dumps(settings, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except Exception:
        pass


def add_recent(settings: dict, path: str) -> None:
    """Prepend *path* to recent_files, deduplicating and capping at _MAX_RECENT."""
    recent = [p for p in settings.get("recent_files", []) if p != path]
    recent.insert(0, path)
    settings["recent_files"] = recent[:_MAX_RECENT]


def add_history(settings: dict, entry: dict) -> None:
    """Prepend a conversion-history *entry*, capping at _MAX_HISTORY."""
    hist = settings.get("history", [])
    hist.insert(0, entry)
    settings["history"] = hist[:_MAX_HISTORY]
