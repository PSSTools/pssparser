"""The adapter contract (design §2.1).

Nothing in an adapter knows about expectations; nothing in the runner knows
about PSS.  That separation is what lets a third party onboard a tool in ~20
lines of TOML.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol

SEVERITIES = ("error", "warning", "note", "unknown")

#: How much to trust the structure of what we parsed out of a tool.  Reported
#: next to every derived metric: if we had to regex a tool's human output, we
#: say so, and location-quality numbers are read with that in mind.
CONFIDENCE = ("structured", "regex", "none")


@dataclass(frozen=True)
class Related:
    file: str | None
    line: int | None
    col: int | None
    label: str = ""

    def as_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "col": self.col,
                "label": self.label}


@dataclass(frozen=True)
class Fix:
    """A tool's own edit span, separate from the diagnostic's underline.

    Design §5.1 asks for "a span and replacement text" and, until now, the
    only span available was the diagnostic's -- so a tool whose repair was
    narrower than its caret got a mangled file and a `fixit_invalid` verdict
    it did not deserve (this was `known-issues.md` ES-S2).  A tool that
    reports the edit separately is taken at its word instead.  `end_col` is
    exclusive, so `col == end_col` is an insertion.
    """

    file: str | None = None
    line: int | None = None
    col: int | None = None
    end_line: int | None = None
    end_col: int | None = None
    replacement: str = ""

    def __post_init__(self) -> None:
        if self.end_line is None:
            object.__setattr__(self, "end_line", self.line)
        if self.end_col is None:
            object.__setattr__(self, "end_col", self.col)

    @property
    def is_applicable(self) -> bool:
        return self.line is not None and self.col is not None

    def as_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "col": self.col,
                "end_line": self.end_line, "end_col": self.end_col,
                "replacement": self.replacement}


@dataclass(frozen=True)
class Diagnostic:
    severity: str
    message: str
    file: str | None = None
    line: int | None = None
    col: int | None = None
    end_line: int | None = None
    end_col: int | None = None
    code: str | None = None
    suggestion: str | None = None
    fix: Fix | None = None
    related: tuple[Related, ...] = ()
    raw: str | None = None

    def __post_init__(self) -> None:
        # A tool that reports `end_col` but no `end_line` means "same line" --
        # pssparser's --json is one of those (plan §0.2).  Normalizing here
        # keeps every consumer from having to know that, and the absence is a
        # tool limitation rather than a parse failure, so confidence is
        # unaffected.
        if self.end_col is not None and self.end_line is None:
            object.__setattr__(self, "end_line", self.line)
        if self.severity not in SEVERITIES:
            object.__setattr__(self, "severity", "unknown")

    @property
    def has_location(self) -> bool:
        return self.file is not None and self.line is not None

    def as_dict(self) -> dict:
        d: dict = {"severity": self.severity, "message": self.message}
        for key in ("file", "line", "col", "end_line", "end_col", "code",
                    "suggestion"):
            value = getattr(self, key)
            if value is not None:
                d[key] = value
        if self.fix is not None:
            d["fix"] = self.fix.as_dict()
        if self.related:
            d["related"] = [r.as_dict() for r in self.related]
        return d


@dataclass(frozen=True)
class ToolResult:
    exit_code: int | None = 0
    diagnostics: tuple[Diagnostic, ...] = ()
    stdout: str = ""
    stderr: str = ""
    duration_s: float = 0.0
    timed_out: bool = False
    crashed: bool = False
    #: Set when the tool could not be invoked at all (missing binary, licence,
    #: bad arguments).  Distinct from `crashed`, which means it ran and died.
    invocation_error: str | None = None
    parse_confidence: str = "structured"

    def errors(self) -> tuple[Diagnostic, ...]:
        return tuple(d for d in self.diagnostics if d.severity == "error")

    def with_diagnostics(self, diags) -> "ToolResult":
        return replace(self, diagnostics=tuple(diags))


@dataclass(frozen=True)
class CaseOpts:
    """Per-case knobs the runner hands the adapter."""
    max_errors: int | None = None
    timeout_s: float = 30.0


class ToolAdapter(Protocol):
    name: str
    version: str

    def run(self, files: list[Path], opts: CaseOpts) -> ToolResult: ...


@dataclass
class Capabilities:
    multifile: bool = True
    max_errors: bool = False
    json_output: bool = False
    exit_code_on_error: int = 1

    def has(self, name: str) -> bool:
        return bool(getattr(self, name, False))

    def as_dict(self) -> dict:
        return {"multifile": self.multifile, "max_errors": self.max_errors,
                "json_output": self.json_output,
                "exit_code_on_error": self.exit_code_on_error}
