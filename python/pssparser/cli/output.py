"""Output format drivers for diagnostic rendering.

  - ``HumanOutput`` -- coloured, Rust/Clang-style diagnostics to stderr.
  - ``JsonOutput``  -- machine-readable JSON to stdout (schema
    ``pssparser-diagnostics/2``; documented in ``docs/diagnostics-json.rst``).
  - ``SarifOutput`` (``sarif.py``) and ``GithubOutput`` (``github.py``).
"""
from __future__ import annotations

import json
import os
import sys
from typing import IO, List, Optional, TextIO

from pssparser.checkers.extension import NO_FILE
from .diagnostics import Diagnostic, DiagnosticCollection
from .source_context import SourceCache, make_caret_line

#: Identifies the JSON document's shape.  Version 2 added this key, the
#: ``notes``/``hints`` counts and the per-diagnostic rule metadata; every
#: version-1 key is unchanged.
JSON_SCHEMA = "pssparser-diagnostics/2"


def statistics_rows(coll: DiagnosticCollection, catalog=None) -> List[dict]:
    """One row per code: count, rule name and tier, most frequent first."""
    counts: dict = {}
    for d in coll.diagnostics:
        key = d.code or "<uncoded>"
        counts[key] = counts.get(key, 0) + 1
    rows = []
    for code, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        md = (catalog or {}).get(code)
        rows.append({
            "code": code,
            "count": n,
            "name": getattr(md, "name", "") or "",
            "tier": getattr(md, "tier", "") or "",
        })
    return rows


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
        show_hints: bool = False,
        statistics: bool = False,
        catalog=None,
    ) -> None:
        self._statistics = statistics
        self._catalog = catalog or {}
        self._src = source_cache
        self._stream = stream or sys.stderr
        self._color = _use_color(self._stream, color)
        #: ``hint`` is an editor nudge (lint-framework L1): hidden at the
        #: command line unless asked for, always present in JSON.
        self._show_hints = show_hints

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
        # A construct that spans several lines (a `compile if` branch, a
        # multi-line expression) has an extent longer than the line it starts
        # on. Underlining to the end of that first line says "this construct,
        # continuing below"; running the tildes out past it draws a caret
        # wider than the source it is pointing at.
        span = max(1, min(span, len(src_line) - col + 1))
        caret = make_caret_line(col, span)
        w(f"{indent} {blank} | {_c(caret, caret_col, c)}\n")
        return True

    def emit(self, diag: Diagnostic) -> None:
        if diag.severity == "hint" and not self._show_hints:
            return
        w = self._stream.write
        c = self._color

        sev_col = _SEV_COLORS.get(diag.severity, "")

        # A tool-level diagnostic -- an extension that failed to load -- has no
        # source location, so it is rendered the way a compiler renders its own
        # complaints: `pssparser: warning: ...`, with no caret block to follow.
        if diag.file == NO_FILE:
            sev = _c(f"{diag.severity}:", sev_col, c)
            flag = f" [{diag.werror_flag}]" if diag.werror_flag else ""
            w(f"{_c('pssparser', _BOLD, c)}: {sev} {diag.message}{flag}\n\n")
            return

        # header: file:line:col: severity: message
        loc = f"{diag.file}:{diag.line}:{diag.col}"
        sev = _c(f"{diag.severity}:", sev_col, c)
        # A promoted warning names the flag that promoted it, so the reader
        # can tell "this is an error" from "you asked for this to be an error".
        flag = f" [{diag.werror_flag}]" if diag.werror_flag else ""
        w(f"{_c(loc, _BOLD, c)}: {sev} {diag.message}{flag}\n")

        # source context line + caret
        has_src = self._source_block(
            w, diag.file, diag.line, diag.col, diag.end_col, sev_col
        )

        # suggestion replacement, aligned on the column the edit applies to --
        # which is the fix's, not the caret's, when the two differ
        # A multi-line replacement (the braces a truncated file is short of)
        # has no sensible one-line rendering under the caret; it stays in the
        # JSON, where a consumer can apply it.
        if has_src and diag.suggestion and "\n" not in diag.suggestion:
            col = diag.col
            if (diag.fix is not None and diag.fix.file == diag.file
                    and diag.fix.line == diag.line):
                col = diag.fix.col
            gutter_w = len(str(diag.line))
            blank = " " * gutter_w
            pad = " " * (col - 1)
            w(f" {blank} | {_c(pad + diag.suggestion, _GREEN, c)}\n")

        # related locations -- indented `note:` lines, each with its own
        # source line and caret (E-8; closes D5's related-location half).
        #
        # A note that lands on the line just printed above is the common case
        # for "struct 's' begins here" when the whole declaration is one line.
        # Repeating the same source line under it is pure noise, so such a note
        # is reduced to its label: the reader can already see where it points.
        for rel in diag.related:
            same_line = (rel.file == diag.file and rel.line == diag.line)
            w(f"  {_c('note:', _DIM, c)} {rel.label}\n")
            if same_line:
                continue
            note_loc = f"{rel.file}:{rel.line}:{rel.col}"
            w(f"   {_c('-->', _DIM, c)} {note_loc}\n")
            self._source_block(
                w, rel.file, rel.line, rel.col, None, _DIM, indent="  "
            )

        w("\n")

    def finish(self, coll: DiagnosticCollection, quiet: bool, stats=None) -> None:
        """Write the trailing summary line and, if asked, the stats block.

        ``-q --stats`` is a supported combination: the summary line is
        suppressed but the stats block still appears.
        """
        if self._statistics:
            self._write_statistics(coll)
        if not quiet:
            self.summary(coll)
        if stats is not None:
            from .stats import render_human
            self._stream.write(render_human(stats))

    def _write_statistics(self, coll: DiagnosticCollection) -> None:
        rows = statistics_rows(coll, self._catalog)
        if not rows:
            return
        width = max(len(r["code"]) for r in rows)
        for r in rows:
            label = r["name"] + (f" [{r['tier']}]" if r["tier"] else "")
            self._stream.write(
                f"{r['count']:>6}  {r['code']:<{width}}  {label}".rstrip() + "\n")
        self._stream.write("\n")

    def summary(self, coll: DiagnosticCollection) -> None:
        parts = []
        ec = coll.error_count
        wc = coll.warning_count
        nc = coll.info_count
        if ec:
            parts.append(f"{ec} error{'s' if ec != 1 else ''}")
        if wc:
            parts.append(f"{wc} warning{'s' if wc != 1 else ''}")
        if nc:
            parts.append(f"{nc} note{'s' if nc != 1 else ''}")
        if not parts:
            parts.append("0 errors")
        nf = len(coll.files)
        msg = ", ".join(parts) + f" in {nf} file{'s' if nf != 1 else ''}"
        hc = coll.hint_count
        if hc and not self._show_hints:
            msg += f" ({hc} hint{'s' if hc != 1 else ''} hidden)"
        self._stream.write(msg + "\n")


# -- JsonOutput -------------------------------------------------------------

class JsonOutput:
    """Collect diagnostics and emit a single JSON document to *stream*."""

    def __init__(
        self,
        stream: TextIO | None = None,
        catalog=None,
        statistics: bool = False,
    ) -> None:
        self._stream = stream or sys.stdout
        self._items: List[dict] = []
        self._files: set = set()
        self._catalog = catalog or {}
        self._statistics = statistics

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
        if diag.original_severity is not None:
            entry["original_severity"] = diag.original_severity
        if diag.suggestion:
            entry["suggestion"] = diag.suggestion
        # The fix carries its own span, which is what makes it applicable: a
        # consumer that patched `suggestion` over the diagnostic's span would
        # delete the character under the caret on every insertion.
        if diag.fix is not None:
            entry["fix"] = {
                "file": diag.fix.file,
                "line": diag.fix.line,
                "col": diag.fix.col,
                "end_line": diag.fix.line,
                "end_col": diag.fix.col + diag.fix.extent,
                "replacement": diag.fix.replacement,
            }
        if diag.code:
            entry["code"] = diag.code
            md = self._catalog.get(diag.code)
            if md is not None:
                if getattr(md, "name", ""):
                    entry["rule"] = md.name
                if getattr(md, "tier", ""):
                    entry["tier"] = md.tier
                if getattr(md, "family", ""):
                    entry["family"] = md.family
                if getattr(md, "lrm", ()):
                    entry["lrm"] = list(md.lrm)
        if diag.related:
            entry["related"] = [
                {"file": r.file, "line": r.line, "col": r.col, "label": r.label}
                for r in diag.related
            ]
        self._items.append(entry)

    def finish(self, coll: DiagnosticCollection, quiet: bool, stats=None) -> None:
        """Emit the JSON document.

        Under ``--quiet`` nothing is written unless stats were requested:
        asking for stats is asking for output.
        """
        if quiet and stats is None:
            return
        self.summary(coll, stats)

    def summary(self, coll: DiagnosticCollection, stats=None) -> None:
        doc = {
            "schema": JSON_SCHEMA,
            "diagnostics": self._items,
            "summary": {
                "errors": coll.error_count,
                "warnings": coll.warning_count,
                "notes": coll.info_count,
                "hints": coll.hint_count,
                "files": len(coll.files),
            },
        }
        if self._statistics:
            doc["statistics"] = statistics_rows(coll, self._catalog)
        if stats is not None:
            from .stats import to_json
            doc["stats"] = to_json(stats)
        json.dump(doc, self._stream, indent=2)
        self._stream.write("\n")
