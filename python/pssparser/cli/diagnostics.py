"""Structured diagnostic data and collection."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Set

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
class Fix:
    """A machine-applicable repair: replace the span with ``replacement``.

    The span is ``extent`` characters starting at ``line``/``col`` (both
    1-based).  ``extent == 0`` is an insertion, which is the common case --
    a missing ``;`` replaces nothing.  This is deliberately *not* the
    diagnostic's own span: the caret has to point at something, so it covers
    a column the edit must not touch.
    """

    file: str
    line: int
    col: int
    extent: int
    replacement: str


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
    fix: Optional[Fix] = None

    # Set only when a warning was promoted to an error by ``-Werror``; holds
    # the severity the diagnostic was reported with before promotion.
    original_severity: Optional[str] = None
    # The flag spelling that caused the promotion, e.g. ``-Werror=PSS104``.
    # Human output renders it as a trailing ``[...]``; JSON does not, since
    # ``original_severity`` already carries the machine-readable fact.
    werror_flag: Optional[str] = None

    @classmethod
    def from_marker(cls, marker: dict) -> "Diagnostic":
        """Build a ``Diagnostic`` from a structured marker dict.

        Marker dicts come from ``Parser.markers`` and have keys:
        severity, message, file, line, col, extent, related, code.
        """
        msg = marker.get("message", "")
        # A structured fix from the builder beats the legacy path, which
        # recovers a replacement by regexing "did you mean 'X'" out of the
        # message text and has no span of its own at all.
        raw_fix = marker.get("fix")
        fix = None
        if raw_fix:
            fix = Fix(
                file=raw_fix.get("file", marker.get("file", "<unknown>")),
                line=raw_fix.get("line", marker.get("line", 0)),
                col=raw_fix.get("col", 1),
                extent=raw_fix.get("extent", 0),
                replacement=raw_fix.get("replacement", ""),
            )
        # `suggestion` is the one-line, human-facing spelling of the repair;
        # a multi-line replacement (the braces a truncated file is short of)
        # has no such spelling and travels only as `fix`.
        if fix is not None and "\n" not in fix.replacement:
            suggestion = fix.replacement
        else:
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
            fix=fix,
        )


@dataclass
class WarningPolicy:
    """How ``-Werror`` / ``--no-warnings`` reshape warning diagnostics.

    Suppression is applied before promotion, so ``--no-warnings -Werror``
    leaves nothing to promote.  ``no_error_codes`` exempts individual marker
    IDs from a blanket ``-Werror``.
    """

    no_warnings: bool = False
    error_all: bool = False
    error_codes: Set[str] = field(default_factory=set)
    no_error_codes: Set[str] = field(default_factory=set)

    @property
    def is_default(self) -> bool:
        return not (
            self.no_warnings
            or self.error_all
            or self.error_codes
            or self.no_error_codes
        )

    def promotion_flag(self, diag: Diagnostic) -> Optional[str]:
        """Return the flag spelling that promotes *diag*, or ``None``.

        A code-specific ``-Wno-error=ID`` always wins over a blanket
        ``-Werror``; that is the only way to spell an exception.
        """
        if diag.severity != "warning":
            return None
        code = diag.code
        if code and code in self.no_error_codes:
            return None
        if code and code in self.error_codes:
            return f"-Werror={code}"
        if self.error_all:
            return "-Werror"
        return None


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

    def replace_diagnostics(self, diags: List[Diagnostic]) -> None:
        """Swap the diagnostic list wholesale.

        Used by the warning-policy pass, which both drops and rewrites
        entries.  Every consumer -- human output, JSON, the counts, and the
        exit code -- reads this collection, so rewriting here covers all four.
        """
        self._diags = list(diags)

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
