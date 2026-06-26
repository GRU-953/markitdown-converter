"""
Tests for settings.py — load/save/add_recent correctness.
All tests use a tmp_path fixture so they never touch ~/.markitdown_converter.json.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import settings


# ── helpers ───────────────────────────────────────────────────────────────────

def _patch_file(tmp_path, monkeypatch):
    """Redirect settings._FILE to a temp path for the duration of the test."""
    f = tmp_path / "settings.json"
    monkeypatch.setattr(settings, "_FILE", f)
    return f


# ── load ──────────────────────────────────────────────────────────────────────

class TestLoad:
    def test_returns_defaults_when_file_missing(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        s = settings.load()
        assert s["theme"] == "System"
        assert s["ocr_language"] == "English"
        assert s["last_output_folder"] == ""
        assert s["recent_files"] == []

    def test_returns_saved_values(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        f.write_text(json.dumps({"theme": "Dark", "ocr_language": "বাংলা"}),
                     encoding="utf-8")
        s = settings.load()
        assert s["theme"] == "Dark"
        assert s["ocr_language"] == "বাংলা"

    def test_merges_with_defaults(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        f.write_text(json.dumps({"theme": "Light"}), encoding="utf-8")
        s = settings.load()
        assert s["theme"] == "Light"
        assert s["ocr_language"] == "English"   # default intact

    def test_returns_defaults_on_corrupt_json(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        f.write_text("not json {{{", encoding="utf-8")
        s = settings.load()
        assert s["theme"] == "System"

    def test_recent_files_capped_at_max(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        big = [f"/file{i}.pdf" for i in range(20)]
        f.write_text(json.dumps({"recent_files": big}), encoding="utf-8")
        s = settings.load()
        assert len(s["recent_files"]) == settings._MAX_RECENT

    def test_non_string_recent_entries_filtered(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        f.write_text(json.dumps({"recent_files": ["/a.pdf", 42, None, "/b.pdf"]}),
                     encoding="utf-8")
        s = settings.load()
        assert s["recent_files"] == ["/a.pdf", "/b.pdf"]


# ── save ──────────────────────────────────────────────────────────────────────

class TestSave:
    def test_writes_json_file(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        settings.save({"theme": "Dark", "recent_files": []})
        data = json.loads(f.read_text(encoding="utf-8"))
        assert data["theme"] == "Dark"

    def test_roundtrip(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        original = {"theme": "Light", "ocr_language": "বাংলা",
                    "last_output_folder": "/tmp", "recent_files": ["/a.pdf"]}
        settings.save(original)
        loaded = settings.load()
        assert loaded["theme"] == "Light"
        assert loaded["ocr_language"] == "বাংলা"
        assert loaded["recent_files"] == ["/a.pdf"]

    def test_silently_ignores_write_error(self, tmp_path, monkeypatch):
        bad = tmp_path / "no_such_dir" / "settings.json"
        monkeypatch.setattr(settings, "_FILE", bad)
        settings.save({"theme": "Dark"})   # should not raise


# ── add_recent ────────────────────────────────────────────────────────────────

class TestAddRecent:
    def test_prepends_new_path(self):
        s = {"recent_files": ["/b.pdf"]}
        settings.add_recent(s, "/a.pdf")
        assert s["recent_files"][0] == "/a.pdf"

    def test_deduplicates(self):
        s = {"recent_files": ["/a.pdf", "/b.pdf"]}
        settings.add_recent(s, "/b.pdf")
        assert s["recent_files"].count("/b.pdf") == 1
        assert s["recent_files"][0] == "/b.pdf"

    def test_caps_at_max_recent(self):
        paths = [f"/file{i}.pdf" for i in range(settings._MAX_RECENT)]
        s = {"recent_files": paths}
        settings.add_recent(s, "/new.pdf")
        assert len(s["recent_files"]) == settings._MAX_RECENT
        assert s["recent_files"][0] == "/new.pdf"

    def test_creates_key_if_missing(self):
        s = {}
        settings.add_recent(s, "/a.pdf")
        assert s["recent_files"] == ["/a.pdf"]

    def test_empty_list_becomes_singleton(self):
        s = {"recent_files": []}
        settings.add_recent(s, "/a.pdf")
        assert s["recent_files"] == ["/a.pdf"]


# ── add_history ─────────────────────────────────────────────────────────────

class TestAddHistory:
    def test_prepends_entry(self):
        s = {"history": [{"name": "old"}]}
        settings.add_history(s, {"name": "new"})
        assert s["history"][0]["name"] == "new"
        assert len(s["history"]) == 2

    def test_creates_key_if_missing(self):
        s = {}
        settings.add_history(s, {"name": "a"})
        assert s["history"] == [{"name": "a"}]

    def test_caps_at_max_history(self):
        entries = [{"name": f"f{i}"} for i in range(settings._MAX_HISTORY)]
        s = {"history": entries}
        settings.add_history(s, {"name": "newest"})
        assert len(s["history"]) == settings._MAX_HISTORY
        assert s["history"][0]["name"] == "newest"


# ── new default keys ────────────────────────────────────────────────────────

class TestNewDefaults:
    def test_palette_default(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        assert settings.load()["palette"] == "indigo"

    def test_auto_flags_default_true(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        s = settings.load()
        assert s["auto_ocr"] is True
        assert s["auto_bijoy"] is True

    def test_history_default_empty(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        assert settings.load()["history"] == []

    def test_history_capped_on_load(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        big = [{"name": f"f{i}"} for i in range(200)]
        f.write_text(json.dumps({"history": big}), encoding="utf-8")
        assert len(settings.load()["history"]) == settings._MAX_HISTORY

    def test_non_dict_history_entries_filtered(self, tmp_path, monkeypatch):
        f = _patch_file(tmp_path, monkeypatch)
        f.write_text(json.dumps({"history": [{"name": "ok"}, "junk", 5]}),
                     encoding="utf-8")
        assert settings.load()["history"] == [{"name": "ok"}]

    def test_onboarding_seen_default_false(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        assert settings.load()["onboarding_seen"] is False

    def test_use_windows_colors_default_false(self, tmp_path, monkeypatch):
        _patch_file(tmp_path, monkeypatch)
        assert settings.load()["use_windows_colors"] is False
