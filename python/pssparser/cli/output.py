"""Output format drivers for diagnostic rendering.

Two drivers:
  - ``HumanOutput`` -- coloured, Rust/Clang-style diagnostics to stderr.
  - ``JsonOutput``  -- machine-readable JSON to stdout.
"""
from __future__ import annotations

import json
import os
import sys
from typing import IO, List, Optional, TextIO

from .diagnostics import Diagnostic, DiagnosticCollection
from .source_context import SourceCache, make_caret_line


# -- ANSI helpers ----------------------------------------------------------

def _use_color(stream: IO, force: Optional[bool] = None) -> bool:
    """Decide whether to emit ANSI colour codes."""
    if force is not None:
        return force
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(stream, "isatty") and stream.isatty()


_RESET = "\033[0m"
_BOLD = "\033[1m"
_SEV_COLORS = {
    "error": "\033[1;31m",    # bold red
    "warning": "\033[1;33m",  # bold yellow
    "info": "\033[1;36m",     # bold cyan
    "hint": "\033[1;36m",     # bold cyan
}
_GREEN = "\033[32m"
_DIM = "\033[2m"


def _c(text: str, code: str, use: bool) -> str:
    if not use:
        return text
    return f"{code}{text}{_RESET}"


# -- HumanOutput -----------------------------------------------------------

class HumanOutput:
    """Rust/Clang-style diagnostic output to *stream* (default: stderr)."""

    def __init__(
        self,
        source_cache: SourceCache,
        stream: TextIO | None = None,
        color: Optional[bool] = None,
    ) -> None:
        self._src = source_cache
        self._stream = stream or sys.stderr
        self._color = _use_color(self._stream, color)

    def _source_block(
        self,
        w,
        file: str,
        line: int,
        col: int,
        end_col: Optional[int],
        caret_col: str,
        indent: str = "",
    ) -> bool:
        """Write a gutter'd source line plus a caret line under it.

        Returns ``True`` if a source line was found and written (callers use
        this to decide whether a suggestion-replacement line makes sense).
        """
        c = self._color
        src_line = self._src.get_line(file, line)
        if src_line is None:
            return False

        gutter_w = len(str(line))
        gutter = f"{line:>{gutter_w}}"
        blank = " " * gutter_w

        w(f"{indent} {_c(gutter, _DIM, c)} | {src_line}\n")

        span = 1
        if end_col and end_col > col:
            span = end_col - col
        caret = make_caret_line(col, span)
        w(f"{indent} {blank} | {_c(caret, caret_col, c)}\n")
        return True

    def emit(self, diag: Diagnostic) -> None:
        w = self._stream.write
        c = self._color

        sev_col = _SEV_COLORS.get(diag.severity, "")

        # header: file:line:col: severity: message
        loc = f"{diag.file}:{diag.line}:{diag.col}"
        sev = _c(f"{diag.severity}:", sev_col, c)
        w(f"{_c(loc, _BOLD, c)}: {sev} {diag.message}\n")

        # source context line + caret
        has_src = self._source_block(
            w, diag.file, diag.line, diag.col, diag.end_col, sev_col
        )

        # suggestion replacement
        if has_src and diag.suggestion:
            gutter_w = len(str(diag.line))
            blank = " " * gutter_w
            pad = " " * (diag.col - 1)
            w(f" {blank} | {_c(pad + diag.suggestion, _GREEN, c)}\n")

        # related locations -- indented `note:` lines, each with its own
        # source line and caret (E-8; closes D5's related-location half).
        for rel in diag.related:
            note_loc = f"{rel.file}:{rel.line}:{rel.col}"
            w(f"  {_c('note:', _DIM, c)} {rel.label}\n")
            w(f"   {_c('-->', _DIM, c)} {note_loc}\n")
            self._source_block(
                w, rel.file, rel.line, rel.col, None, _DIM, indent="  "
            )

        w("\n")

    def summary(self, coll: DiagnosticCollection) -> None:
        parts = []
        ec = coll.error_count
        wc = coll.warning_count
        if ec:
            parts.append(f"{ec} error{'s' if ec != 1 else ''}")
        if wc:
            parts.append(f"{wc} warning{'s' if wc != 1 else ''}")
        if not parts:
            parts.append("0 errors")
        nf = len(coll.files)
        msg = ", ".join(parts) + f" in {nf} file{'s' if nf != 1 else ''}"
        self._stream.write(msg + "\n")


# -- JsonOutput -------------------------------------------------------------

class JsonOutput:
    """Collect diagnostics and emit a single JSON document to *stream*."""

    def __init__(
        self,
        stream: TextIO | None = None,
    ) -> None:
        self._stream = stream or sys.stdout
        self._items: List[dict] = []
        self._files: set = set()

    def emit(self, diag: Diagnostic) -> None:
        self._files.add(diag.file)
        entry: dict = {
            "file": diag.file,
            "line": diag.line,
            "col": diag.col,
            "severity": diag.severity,
            "message": diag.message,
        }
        if diag.end_col is not None:
            entry["end_col"] = diag.end_col
        if diag.suggestion:
            entry["suggestion"] = diag.suggestion
        if diag.code:
            entry["code"] = diag.code
        if diag.related:
            entry["related"] = [
                {"file": r.file, "line": r.line, "col": r.col, "label": r.label}
                for r in diag.related
            ]
        self._items.append(entry)

    def summary(self, coll: DiagnosticCollection) -> None:
        doc = {
            "diagnostics": self._items,
            "summary": {
                "errors": coll.error_count,
                "warnings": coll.warning_count,
                "files": len(coll.files),
            },
        }
        json.dump(doc, self._stream, indent=2)
        self._stream.write("\n")
