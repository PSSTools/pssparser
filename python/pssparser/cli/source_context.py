"""Source file reading and caret-line generation for diagnostic display."""
from __future__ import annotations

import unicodedata
from typing import Dict, List, Optional, Tuple

#: Tab stop used when a source line is displayed.  A column in a diagnostic
#: counts a tab as one character, as the lexer does; the terminal does not.
TAB_STOP = 8


class SourceCache:
    """Lazy, cached reader -- each file is read at most once."""

    def __init__(self) -> None:
        self._cache: Dict[str, List[str]] = {}

    def _load(self, path: str) -> List[str]:
        if path not in self._cache:
            try:
                # Lines end at '\n' only, as the lexer counts them.
                # `splitlines()` also breaks on form feed, U+2028 and friends,
                # which would show the wrong line under a diagnostic.
                with open(path, "r", errors="replace", newline="") as fh:
                    text = fh.read()
                lines = text.split("\n")
                if lines and lines[-1] == "":
                    lines.pop()
                self._cache[path] = [ln[:-1] if ln.endswith("\r") else ln
                                     for ln in lines]
            except OSError:
                self._cache[path] = []
        return self._cache[path]

    def get_line(self, path: str, lineno: int) -> Optional[str]:
        """Return a single source line (1-based) or ``None``."""
        lines = self._load(path)
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1]
        return None

    def get_context(
        self,
        path: str,
        lineno: int,
        before: int = 1,
        after: int = 0,
    ) -> List[Tuple[int, str]]:
        """Return ``(lineno, text)`` tuples around *lineno*."""
        lines = self._load(path)
        start = max(1, lineno - before)
        end = min(len(lines), lineno + after)
        return [(i, lines[i - 1]) for i in range(start, end + 1)]


def _char_width(ch: str) -> int:
    if unicodedata.combining(ch):
        return 0
    if unicodedata.east_asian_width(ch) in ("W", "F"):
        return 2
    return 1


def _display_starts(line: str) -> List[int]:
    """The 0-based display column each character of *line* starts at, plus
    one trailing entry for the end of the line."""
    starts = []
    pos = 0
    for ch in line:
        starts.append(pos)
        if ch == "\t":
            pos += TAB_STOP - pos % TAB_STOP
        else:
            pos += _char_width(ch)
    starts.append(pos)
    return starts


def expand_tabs(line: str) -> str:
    """*line* with each tab replaced by the spaces it occupies on screen.

    The gutter in front of a displayed line is not a multiple of the tab stop,
    so a raw tab would land somewhere the caret line cannot predict.
    """
    if "\t" not in line:
        return line
    out = []
    pos = 0
    for ch in line:
        if ch == "\t":
            n = TAB_STOP - pos % TAB_STOP
            out.append(" " * n)
            pos += n
        else:
            out.append(ch)
            pos += _char_width(ch)
    return "".join(out)


def display_col(line: Optional[str], col: int) -> int:
    """The 1-based on-screen column of 1-based character column *col* in
    *line*, once *line* is displayed with :func:`expand_tabs`."""
    if col < 1:
        col = 1
    if line is None:
        return col
    starts = _display_starts(line)
    i = col - 1
    if i < len(starts):
        return starts[i] + 1
    return starts[-1] + (i - len(line)) + 1


def make_caret_line(col: int, length: int = 1, char: str = "^",
                    line: Optional[str] = None) -> str:
    """Build a caret string like ``'    ^~~~'``.

    *col* is 1-based and counts characters, a tab as one.  *length* includes
    the leading ``^``.  Given the source *line*, the caret is placed under
    that line as :func:`expand_tabs` displays it: a tab or a wide character
    before or inside the span moves or widens the caret to match.
    """
    if col < 1:
        col = 1
    if length < 1:
        length = 1
    start = display_col(line, col)
    width = max(1, display_col(line, col + length) - start)
    return " " * (start - 1) + char + "~" * (width - 1)
