"""The fixture corpus has to mean what it says.

Fixture line numbers are hand-counted, and the header counts toward them, so
one added directive silently shifts every coordinate in the file.  That is
exactly the failure mode this module exists to catch -- a fixture whose `at:`
drifted off the defect would quietly turn a `detected` test into a
`detected_mislocated` one and read like a classifier bug.
"""
from __future__ import annotations

import re

from pss_errsuite.case import collect_cases

_EMIT_RE = re.compile(r"^//FAKE: emit (\d+):(\d+)")


def test_at_points_at_a_real_line_of_source(fixture_cases):
    for case in collect_cases(fixture_cases):
        if case.at is None:
            continue
        lines = case.source.splitlines()
        target = lines[case.at.line - 1]
        assert not target.startswith("//"), (
            f"{case.name}: at: {case.at.line} lands on a comment/header line, "
            f"not on source")
        assert case.at.col <= len(target) + 1, (
            f"{case.name}: at: column {case.at.col} is past the end of "
            f"{target!r}")


def test_fake_directives_reference_lines_that_exist(fixture_cases):
    for case in collect_cases(fixture_cases):
        n_lines = len(case.source.splitlines())
        for raw in case.source.splitlines():
            m = _EMIT_RE.match(raw)
            if not m:
                continue
            line = int(m.group(1))
            # `mislocated` and `noisy_jargon` point off the defect on purpose;
            # both still have to name a plausible position.
            assert 1 <= line <= n_lines + 1, (
                f"{case.name}: //FAKE: emit refers to line {line} of a "
                f"{n_lines}-line file")


def test_the_deliberately_mislocated_fixture_really_is(fixture_cases):
    case = next(c for c in collect_cases(fixture_cases)
                if c.case_id == "FX-MISLOCATED")
    emitted = [int(_EMIT_RE.match(l).group(1))
               for l in case.source.splitlines() if _EMIT_RE.match(l)]
    assert emitted and all(l != case.at.line for l in emitted)


def test_every_fixture_declares_a_control_or_is_an_accept_case(fixture_cases):
    for case in collect_cases(fixture_cases):
        if case.expect == "accept":
            continue
        assert case.control_source() is not None, case.name
