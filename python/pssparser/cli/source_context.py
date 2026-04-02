"""Source file reading and caret-line generation for diagnostic display."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple


class SourceCache:
    """Lazy, cached reader -- each file is read at most once."""

    def __init__(self) -> None:
        self._cache: Dict[str, List[str]] = {}

    def _load(self, path: str) -> List[str]:
        if path not in self._cache:
            try:
                with open(path, "r", errors="replace") as fh:
                    self._cache[path] = fh.read().splitlines()
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


def make_caret_line(col: int, length: int = 1, char: str = "^") -> str:
    """Build a caret string like ``'    ^~~~'``.

    *col* is 1-based.  *length* includes the leading ``^``.
    """
    if col < 1:
        col = 1
    if length < 1:
        length = 1
    pad = " " * (col - 1)
    return pad + char + "~" * (length - 1)
