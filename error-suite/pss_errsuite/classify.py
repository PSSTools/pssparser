"""Case × ToolResult → status (design §4.1).

Pure functions, no I/O: this is the module whose correctness every number in
every report depends on, so it is kept trivially testable.

Two rules are load-bearing and easy to erode:

* **`count:` never affects status.**  Error counts vary legitimately with
  recovery strategy; a tool that emits two well-located errors where we emit
  one is *different*, not wrong.  The count shows up as an observation and
  feeds D6, never as a pass/fail.
* **A failed control makes the result uninterpretable**, not a detection.  A
  tool that rejects our scaffolding would otherwise score 100%.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .adapters.base import Diagnostic, ToolResult
from .case import Case
from .locate import Tolerance

DETECTED = "detected"
DETECTED_MISLOCATED = "detected_mislocated"
DETECTED_WRONG_SEVERITY = "detected_wrong_severity"
MISSED = "missed"
CLEAN = "clean"
SPURIOUS = "spurious"
CONTROL_FAILED = "control_failed"
CRASH = "crash"
TIMEOUT = "timeout"
TOOL_ERROR = "tool_error"
SKIPPED = "skipped"
SKIPPED_VERSION = "skipped_version"

ALL_STATUSES = (
    DETECTED, DETECTED_MISLOCATED, DETECTED_WRONG_SEVERITY, MISSED, CLEAN,
    SPURIOUS, CONTROL_FAILED, CRASH, TIMEOUT, TOOL_ERROR, SKIPPED,
    SKIPPED_VERSION,
)

_SEVERITY_RANK = {"note": 1, "warning": 2, "error": 3}


@dataclass
class Observations:
    """Recorded per case, never folded into status (design §4.2)."""
    error_count: int = 0
    warning_count: int = 0
    noise: int = 0
    has_code: bool = False
    has_related: bool = False
    has_suggestion: bool = False
    primary_index: int | None = None
    duration_s: float = 0.0
    lints: list[str] = field(default_factory=list)
    #: `"verified"`, `"invalid"`, or `None` when the tool offered no
    #: machine-applicable fix (or nobody checked).  Design §5.3's D4 = 3 test.
    fixit: str | None = None

    def as_dict(self) -> dict:
        return {
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "noise": self.noise,
            "has_code": self.has_code,
            "has_related": self.has_related,
            "has_suggestion": self.has_suggestion,
            "primary_index": self.primary_index,
            "duration_s": round(self.duration_s, 4),
            "lints": list(self.lints),
            "fixit": self.fixit,
        }


def _severity_at_least(diag: Diagnostic, floor: str) -> bool:
    return _SEVERITY_RANK.get(diag.severity, 0) >= _SEVERITY_RANK.get(floor, 3)


def _file_matches(case: Case, diag: Diagnostic) -> bool:
    if diag.file is None:
        return False
    expected = case.at_file or case.path.name
    # Tools report paths in whatever form they were handed; compare basenames.
    return diag.file.rsplit("/", 1)[-1] == expected


def pick_primary(case: Case, diags: list[Diagnostic],
                 tol: Tolerance) -> tuple[Diagnostic | None, int | None]:
    """The diagnostic a reader would call "the one about this defect"."""
    if not diags:
        return None, None
    if case.at is None:
        return diags[0], 0
    expected = (case.at.line, case.at.col)
    best_i, best_key = 0, None
    for i, d in enumerate(diags):
        actual = (d.line, d.col) if d.line is not None else None
        key = (0 if _file_matches(case, d) else 1,
               tol.distance(case.source, expected, actual))
        if best_key is None or key < best_key:
            best_i, best_key = i, key
    return diags[best_i], best_i


def observe(case: Case, result: ToolResult, primary: Diagnostic | None,
            primary_index: int | None, lints: list[str] | None = None
            ) -> Observations:
    errors = [d for d in result.diagnostics if d.severity == "error"]
    warnings = [d for d in result.diagnostics if d.severity == "warning"]
    obs = Observations(
        error_count=len(errors),
        warning_count=len(warnings),
        noise=max(0, len(errors) - case.count) if case.expect == "error" else 0,
        has_code=bool(primary and primary.code),
        has_suggestion=bool(primary and primary.suggestion),
        primary_index=primary_index,
        duration_s=result.duration_s,
        lints=list(lints or []),
    )
    if primary is not None and case.also:
        wanted = {(a.line, a.col) for a in case.also}
        got = {(r.line, r.col) for r in primary.related}
        obs.has_related = bool(wanted & got) or (
            bool(primary.related) and any(
                r.line == a.line for r in primary.related for a in case.also))
    elif primary is not None:
        obs.has_related = bool(primary.related)
    return obs


def classify(case: Case, result: ToolResult,
             control: ToolResult | None = None,
             tolerance: Tolerance | None = None,
             severity_floor: str = "error") -> tuple[str, Observations]:
    tol = tolerance or Tolerance()

    if result.invocation_error:
        return TOOL_ERROR, Observations(duration_s=result.duration_s)
    if result.timed_out:
        return TIMEOUT, Observations(duration_s=result.duration_s)
    if result.crashed:
        return CRASH, Observations(duration_s=result.duration_s)

    diags = [d for d in result.diagnostics
             if d.severity in ("error", "warning", "note")]

    if case.expect == "accept":
        offending = [d for d in diags if _severity_at_least(d, severity_floor)]
        primary, index = pick_primary(case, offending, tol)
        obs = observe(case, result, primary, index)
        return (SPURIOUS if offending else CLEAN), obs

    # An `expect: error` case whose control does not parse clean tells us
    # nothing about the defect.
    if control is not None and not control_is_clean(control, severity_floor):
        primary, index = pick_primary(case, diags, tol)
        return CONTROL_FAILED, observe(case, result, primary, index)

    expected = case.expect
    at_level = [d for d in diags if d.severity == expected]
    other_level = [d for d in diags
                   if d.severity in ("error", "warning")
                   and d.severity != expected]

    if at_level:
        primary, index = pick_primary(case, at_level, tol)
        obs = observe(case, result, primary, index)
        actual = (primary.line, primary.col) if primary else None
        located = (
            primary is not None
            and _file_matches(case, primary)
            and tol.accepts(case.source, (case.at.line, case.at.col), actual)
        )
        return (DETECTED if located else DETECTED_MISLOCATED), obs

    if other_level:
        primary, index = pick_primary(case, other_level, tol)
        return DETECTED_WRONG_SEVERITY, observe(case, result, primary, index)

    primary, index = pick_primary(case, diags, tol)
    return MISSED, observe(case, result, primary, index)


def control_is_clean(control: ToolResult, severity_floor: str) -> bool:
    if control.timed_out or control.crashed or control.invocation_error:
        return False
    return not any(_severity_at_least(d, severity_floor)
                   for d in control.diagnostics)
