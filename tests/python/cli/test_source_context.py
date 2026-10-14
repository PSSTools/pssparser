"""Unit tests for pssparser.cli.source_context."""
import os
import tempfile

import pytest

from pssparser.cli.source_context import (SourceCache, display_col,
                                          expand_tabs, make_caret_line)


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

    def test_lines_end_at_newline_only(self, tmp_path):
        # The lexer counts '\n' only; a form feed or U+2028 inside a line
        # must not shift every later line by one.
        p = tmp_path / "ff.pss"
        p.write_bytes("a\fb\u2028c\r\nline2\n".encode())
        sc = SourceCache()
        assert sc.get_line(str(p), 1) == "a\fb\u2028c"
        assert sc.get_line(str(p), 2) == "line2"
        assert sc.get_line(str(p), 3) is None

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


# -- tabs and wide characters (GitHub #15 follow-up) -----------------------
#
# A diagnostic column counts a tab as one character.  The displayed source
# line has its tabs expanded, and the caret is placed under that.

class TestDisplayColumns:
    def test_expand_tabs(self):
        assert expand_tabs("\tab\tc") == "        ab      c"

    def test_no_tabs_unchanged(self):
        assert expand_tabs("plain") == "plain"

    def test_caret_after_tab(self):
        line = "\tx = N;"
        col = line.index("N") + 1
        caret = make_caret_line(col, 1, line=line)
        assert caret.index("^") == expand_tabs(line).index("N")

    def test_caret_after_two_tabs(self):
        line = "\t\trand bit[8] a[UNDEF];"
        col = line.index("UNDEF") + 1
        caret = make_caret_line(col, 5, line=line)
        assert caret.index("^") == expand_tabs(line).index("UNDEF")
        assert caret.endswith("^~~~~")

    def test_span_over_tab_widens(self):
        # The tab after `v` runs from screen column 1 to the stop at 8.
        assert make_caret_line(2, 1, line="v\tc") == " ^" + "~" * 6

    def test_wide_characters_take_two_columns(self):
        line = "/* \u65e5\u672c */ N"
        col = line.index("N") + 1
        assert display_col(line, col) == col + 2

    def test_past_end_of_line(self):
        assert display_col("\tab", 5) == 12

    def test_without_line_is_unchanged(self):
        assert make_caret_line(5, 3) == "    ^~~"
