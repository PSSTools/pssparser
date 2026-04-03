"""Unit tests for pssparser.cli.source_context."""
import os
import tempfile

import pytest

from pssparser.cli.source_context import SourceCache, make_caret_line


# -- SourceCache ------------------------------------------------------------

@pytest.fixture
def sample_file(tmp_path):
    p = tmp_path / "sample.pss"
    p.write_text("line1\nline2\nline3\nline4\nline5\n")
    return str(p)


class TestSourceCache:
    def test_get_line(self, sample_file):
        sc = SourceCache()
        assert sc.get_line(sample_file, 1) == "line1"
        assert sc.get_line(sample_file, 3) == "line3"
        assert sc.get_line(sample_file, 5) == "line5"

    def test_get_line_out_of_range(self, sample_file):
        sc = SourceCache()
        assert sc.get_line(sample_file, 0) is None
        assert sc.get_line(sample_file, 99) is None

    def test_get_line_missing_file(self):
        sc = SourceCache()
        assert sc.get_line("/no/such/file.pss", 1) is None

    def test_caching(self, sample_file):
        sc = SourceCache()
        sc.get_line(sample_file, 1)
        # Mutating the dict directly to prove cache hit
        sc._cache[sample_file][0] = "CACHED"
        assert sc.get_line(sample_file, 1) == "CACHED"

    def test_get_context(self, sample_file):
        sc = SourceCache()
        ctx = sc.get_context(sample_file, 3, before=1, after=1)
        assert ctx == [(2, "line2"), (3, "line3"), (4, "line4")]

    def test_get_context_clamped(self, sample_file):
        sc = SourceCache()
        ctx = sc.get_context(sample_file, 1, before=5, after=0)
        assert ctx == [(1, "line1")]

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.pss"
        p.write_text("")
        sc = SourceCache()
        assert sc.get_line(str(p), 1) is None


# -- make_caret_line --------------------------------------------------------

class TestMakeCaretLine:
    def test_single(self):
        assert make_caret_line(5) == "    ^"

    def test_span(self):
        assert make_caret_line(3, length=4) == "  ^~~~"

    def test_col_one(self):
        assert make_caret_line(1, length=2) == "^~"

    def test_zero_col_clamped(self):
        assert make_caret_line(0) == "^"

    def test_zero_length_clamped(self):
        assert make_caret_line(3, length=0) == "  ^"
