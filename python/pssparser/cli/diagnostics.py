"""Structured diagnostic data and collection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from .suggestion import extract_suggestion

# Regex to pull the erroneous symbol name from common marker messages so we
# can compute underline length.
_SYMBOL_RE = re.compile(
    r"(?:unknown (?:type|identifier)|unresolved) '([^']+)'"
)


@dataclass
class Relation:
    """A secondary location attached to a diagnostic (e.g. an opening brace)."""

    file: str
    line: int
    col: int
    label: str


@dataclass
class Diagnostic:
    """One diagnostic (error / warning / info / hint)."""

    file: str
    line: int
    col: int
    severity: str
    message: str
    suggestion: Optional[str] = None
    code: Optional[str] = None
    end_col: Optional[int] = None
    notes: List[str] = field(default_factory=list)
    related: List[Relation] = field(default_factory=list)

    @classmethod
    def from_marker(cls, marker: dict) -> "Diagnostic":
        """Build a ``Diagnostic`` from a structured marker dict.

        Marker dicts come from ``Parser.markers`` and have keys:
        severity, message, file, line, col, extent, related, code.
        """
        msg = marker.get("message", "")
        suggestion = extract_suggestion(msg)

        col = marker.get("col", 1)
        end_col: Optional[int] = None

        # Prefer the extent the C++ builder computed; fall back to guessing
        # the underline length from the symbol name in the message.
        extent = marker.get("extent") or 0
        if extent > 0:
            end_col = col + extent
        else:
            sym_m = _SYMBOL_RE.search(msg)
            if sym_m:
                end_col = col + len(sym_m.group(1))

        related = [
            Relation(
                file=rel.get("file", "<unknown>"),
                line=rel.get("line", 0),
                col=rel.get("col", 1),
                label=rel.get("label", ""),
            )
            for rel in marker.get("related", [])
        ]

        return cls(
            file=marker.get("file", "<unknown>"),
            line=marker.get("line", 0),
            col=col,
            severity=marker.get("severity", "error"),
            message=msg,
            suggestion=suggestion,
            code=marker.get("code"),
            end_col=end_col,
            related=related,
        )


class DiagnosticCollection:
    """Accumulates diagnostics and provides counts / filtering.

    ``--max-errors`` is enforced upstream, by the C++ marker collector (see
    ``Parser.set_max_errors``): a capped file's marker list already contains
    at most ``max_errors`` errors plus one PSS029 marker announcing the
    cutoff. This collection just holds whatever it is handed.
    """

    def __init__(self) -> None:
        self._diags: List[Diagnostic] = []
        self._processed_files: Optional[List[str]] = None

    def add(self, diag: Diagnostic) -> None:
        self._diags.append(diag)

    def set_processed_files(self, files: List[str]) -> None:
        """Record the files actually handed to the parser.

        ``files`` (diagnostic-derived, below) is empty for a clean parse
        with zero diagnostics, which made ``summary()`` misreport "0
        files" even though files were processed. Call this once the input
        file list is known so ``files`` can fall back to it.
        """
        self._processed_files = list(files)

    @property
    def diagnostics(self) -> List[Diagnostic]:
        return list(self._diags)

    @property
    def error_count(self) -> int:
        return sum(1 for d in self._diags if d.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for d in self._diags if d.severity == "warning")

    @property
    def files(self) -> set:
        diag_files = {d.file for d in self._diags}
        if self._processed_files is not None:
            return diag_files | set(self._processed_files)
        return diag_files

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0
