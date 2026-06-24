"""
Tests for utils.py — parse_dnd_paths correctness.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils import parse_dnd_paths


class TestParseDndPaths:
    def test_single_simple_path(self):
        assert parse_dnd_paths("/home/user/file.pdf") == ["/home/user/file.pdf"]

    def test_windows_simple_path(self):
        assert parse_dnd_paths(r"C:\Users\user\file.pdf") == [r"C:\Users\user\file.pdf"]

    def test_path_with_spaces_in_braces(self):
        assert parse_dnd_paths("{/path with spaces/file.pdf}") == ["/path with spaces/file.pdf"]

    def test_windows_path_with_spaces(self):
        result = parse_dnd_paths(r"{C:\My Documents\report.docx}")
        assert result == [r"C:\My Documents\report.docx"]

    def test_multiple_simple_paths(self):
        result = parse_dnd_paths("/file1.pdf /file2.docx /file3.xlsx")
        assert result == ["/file1.pdf", "/file2.docx", "/file3.xlsx"]

    def test_mixed_plain_and_braced(self):
        result = parse_dnd_paths("/simple.pdf {/path with spaces/doc.docx}")
        assert result == ["/simple.pdf", "/path with spaces/doc.docx"]

    def test_braced_and_plain(self):
        result = parse_dnd_paths("{/path with spaces/a.pdf} /b.pdf")
        assert result == ["/path with spaces/a.pdf", "/b.pdf"]

    def test_multiple_braced(self):
        result = parse_dnd_paths("{/path one/a.pdf} {/path two/b.pdf}")
        assert result == ["/path one/a.pdf", "/path two/b.pdf"]

    def test_empty_string(self):
        assert parse_dnd_paths("") == []

    def test_whitespace_only(self):
        assert parse_dnd_paths("   ") == []

    def test_returns_list(self):
        assert isinstance(parse_dnd_paths("/file.pdf"), list)
