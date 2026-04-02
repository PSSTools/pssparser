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

    @classmethod
    def from_marker(cls, marker: dict) -> "Diagnostic":
        """Build a ``Diagnostic`` from a structured marker dict.

        Marker dicts come from ``Parser.markers`` and have keys:
        severity, message, file, line, col.
        """
        msg = marker.get("message", "")
        suggestion = extract_suggestion(msg)

        col = marker.get("col", 1)
        end_col: Optional[int] = None

        # Try to derive underline length from the symbol name in the message
        sym_m = _SYMBOL_RE.search(msg)
        if sym_m:
            end_col = col + len(sym_m.group(1))

        return cls(
            file=marker.get("file", "<unknown>"),
            line=marker.get("line", 0),
            col=col,
            severity=marker.get("severity", "error"),
            message=msg,
            suggestion=suggestion,
            end_col=end_col,
        )


class DiagnosticCollection:
    """Accumulates diagnostics and provides counts / filtering."""

    def __init__(self, max_errors: int = 20) -> None:
        self._diags: List[Diagnostic] = []
        self._max_errors = max_errors  # 0 = unlimited

    def add(self, diag: Diagnostic) -> bool:
        """Append a diagnostic.  Returns ``False`` when max errors reached."""
        self._diags.append(diag)
        if self._max_errors and self.error_count > self._max_errors:
            return False
        return True

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
        return {d.file for d in self._diags}

    @property
    def has_errors(self) -> bool:
        return self.error_count > 0
