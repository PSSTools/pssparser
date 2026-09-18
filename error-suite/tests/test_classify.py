"""The status matrix: one assertion per value of the vocabulary.

Classification is a pure function, so these tests build `(Case, ToolResult,
control)` triples directly and never touch a tool.  If one of these breaks,
every number in every run file is wrong, which is why the coverage here is
exhaustive rather than representative.
"""
from __future__ import annotations

import pytest

from pss_errsuite.adapters.base import Diagnostic, Related, ToolResult
from pss_errsuite.classify import (CLEAN, CONTROL_FAILED, CRASH,
                                   DETECTED, DETECTED_MISLOCATED,
                                   DETECTED_WRONG_SEVERITY, MISSED, SPURIOUS,
                                   TIMEOUT, TOOL_ERROR, classify)
from pss_errsuite.locate import Tolerance

SOURCE = """//! case:   X
//! class:  syntax.punct
//! expect: error
//! at:     6:14
//! count:  1
struct s {
    int a
    int b;
}
"""

ACCEPT_SOURCE = """//! case:   Y
//! class:  accept.misc
//! expect: accept
struct s { int a; }
"""


@pytest.fixture
def case(write_case):
    return write_case("c.pss", SOURCE)


@pytest.fixture
def accept_case(write_case):
    return write_case("a.pss", ACCEPT_SOURCE)


def diag(line=6, col=14, severity="error", message="expected ';'", **kw):
    return Diagnostic(severity=severity, message=message, file="c.pss",
                      line=line, col=col, **kw)


def result(*diags, **kw):
    return ToolResult(exit_code=1 if diags else 0, diagnostics=tuple(diags),
                      **kw)


CLEAN_CONTROL = ToolResult(exit_code=0)


def test_detected(case):
    status, obs = classify(case, result(diag()), CLEAN_CONTROL)
    assert status == DETECTED
    assert obs.error_count == 1
    assert obs.noise == 0


def test_detected_mislocated_wrong_line(case):
    status, _ = classify(case, result(diag(line=1, col=1)), CLEAN_CONTROL)
    assert status == DETECTED_MISLOCATED


def test_detected_mislocated_when_there_is_no_location_at_all(case):
    d = Diagnostic(severity="error", message="syntax error")
    assert classify(case, result(d), CLEAN_CONTROL)[0] == DETECTED_MISLOCATED


def test_detected_mislocated_wrong_file(case):
    d = diag()
    d = Diagnostic(severity="error", message="x", file="elsewhere.pss",
                   line=6, col=14)
    assert classify(case, result(d), CLEAN_CONTROL)[0] == DETECTED_MISLOCATED


def test_detected_wrong_severity(case):
    status, _ = classify(case, result(diag(severity="warning")), CLEAN_CONTROL)
    assert status == DETECTED_WRONG_SEVERITY


def test_missed(case):
    assert classify(case, result(), CLEAN_CONTROL)[0] == MISSED


def test_a_note_only_response_is_still_missed(case):
    d = diag(severity="note", message="fyi")
    assert classify(case, result(d), CLEAN_CONTROL)[0] == MISSED


def test_clean(accept_case):
    assert classify(accept_case, result())[0] == CLEAN


def test_spurious(accept_case):
    d = Diagnostic(severity="error", message="no", file="a.pss", line=4, col=1)
    assert classify(accept_case, result(d))[0] == SPURIOUS


def test_a_warning_on_an_accept_case_is_clean_under_the_default_floor(
        accept_case):
    d = Diagnostic(severity="warning", message="hmm", file="a.pss", line=4,
                   col=1)
    assert classify(accept_case, result(d))[0] == CLEAN
    assert classify(accept_case, result(d),
                    severity_floor="warning")[0] == SPURIOUS


def test_control_failed_beats_a_detection(case):
    """The tool found the defect -- but it also rejects the repaired file, so
    we cannot tell whether it found *this* defect or just dislikes the
    scaffolding."""
    bad_control = result(Diagnostic(severity="error", message="nope",
                                    file="c.pss", line=1, col=1))
    assert classify(case, result(diag()), bad_control)[0] == CONTROL_FAILED


def test_control_that_crashes_also_fails(case):
    assert classify(case, result(diag()),
                    ToolResult(crashed=True))[0] == CONTROL_FAILED


def test_crash(case):
    assert classify(case, ToolResult(crashed=True), CLEAN_CONTROL)[0] == CRASH


def test_timeout(case):
    assert classify(case, ToolResult(timed_out=True),
                    CLEAN_CONTROL)[0] == TIMEOUT


def test_tool_error(case):
    r = ToolResult(invocation_error="no such binary")
    assert classify(case, r, CLEAN_CONTROL)[0] == TOOL_ERROR


def test_tool_error_wins_over_a_crash_flag(case):
    r = ToolResult(invocation_error="no such binary", crashed=True)
    assert classify(case, r, CLEAN_CONTROL)[0] == TOOL_ERROR


# -- tolerance ---------------------------------------------------------------

@pytest.mark.parametrize("spec,col,expected", [
    ("exact", 14, DETECTED),
    ("exact", 9, DETECTED_MISLOCATED),
    ("line", 1, DETECTED),               # any column on the right line
    ("token:2", 9, DETECTED),            # one token away ("a")
    ("token:0", 9, DETECTED_MISLOCATED),
])
def test_tolerance_policies(case, spec, col, expected):
    status, _ = classify(case, result(diag(col=col)), CLEAN_CONTROL,
                         tolerance=Tolerance(spec))
    assert status == expected


def test_the_classic_next_line_report_is_within_two_tokens(case):
    """A missing ';' reported at the first token of the next line is one token
    away from where it belongs, so `token:2` calls it located.  That is the
    policy working as intended -- D2 in the rubric is where the distinction
    lives, not here."""
    status, _ = classify(case, result(diag(line=7, col=5)), CLEAN_CONTROL,
                         tolerance=Tolerance("token:2"))
    assert status == DETECTED
    status, _ = classify(case, result(diag(line=7, col=5)), CLEAN_CONTROL,
                         tolerance=Tolerance("line"))
    assert status == DETECTED_MISLOCATED


# -- observations ------------------------------------------------------------

def test_count_mismatch_never_changes_status(case):
    """Three errors where the case declares one is an observation, not a
    failure: error counts vary legitimately with recovery strategy."""
    r = result(diag(), diag(line=7, col=5), diag(line=8, col=1))
    status, obs = classify(case, r, CLEAN_CONTROL)
    assert status == DETECTED
    assert obs.error_count == 3
    assert obs.noise == 2


def test_primary_is_the_diagnostic_nearest_the_declared_location(case):
    far = diag(line=1, col=1, message="first but wrong")
    near = diag(message="second but right")
    status, obs = classify(case, result(far, near), CLEAN_CONTROL)
    assert status == DETECTED
    assert obs.primary_index == 1


def test_related_and_code_and_suggestion_are_observed(case):
    d = diag(code="PSS020", suggestion="int a;",
             related=(Related("c.pss", 7, 5, "input ends here"),))
    _, obs = classify(case, result(d), CLEAN_CONTROL)
    assert obs.has_code and obs.has_suggestion and obs.has_related
