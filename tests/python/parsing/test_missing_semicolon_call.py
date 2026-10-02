"""A call missing its `;` is PSS020 at the next statement (pssc request Q2).

Two calls in a row with no `;` between them match no statement alternative.
ANTLR reports "no viable alternative" at the second call, and its recovery then
resyncs at the first call's `(`, because `(void) f();` starts with `(`. Re-reading
from there reported "unexpected 'NONE' … expecting 'void'" inside the first,
correct, call. That message sorted first and named nothing that was wrong.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import find_markers, parse_collect  # noqa: E402


CASES = [
    pytest.param(
        'import std_pkg::*;\n'
        'component pss_top {\n'
        '    action T {\n'
        '        exec body { message(NONE, "a")\n'
        '            message(NONE, "b"); }\n'
        '    }\n'
        '}\n',
        "message", 5, 13, id="the-request"),
    pytest.param(
        'component pss_top {\n'
        '    function void cf(int a) { }\n'
        '    action T {\n'
        '        exec body {\n'
        '            comp.cf(1)\n'
        '            comp.cf(2);\n'
        '        }\n'
        '    }\n'
        '}\n',
        "comp", 6, 13, id="method-call"),
    pytest.param(
        'function void g(int a);\n'
        'component pss_top {\n'
        '    action T {\n'
        '        int arr[2];\n'
        '        exec body {\n'
        '            g(1)\n'
        '            arr[0] = 1;\n'
        '        }\n'
        '    }\n'
        '}\n',
        "arr", 7, 13, id="call-then-assignment"),
    pytest.param(
        'component pss_top {\n'
        '    action A { }\n'
        '    action T {\n'
        '        symbol s(int n) { do A; }\n'
        '        activity {\n'
        '            s(1)\n'
        '            s(2);\n'
        '        }\n'
        '    }\n'
        '}\n',
        "s", 7, 13, id="activity-symbol-call"),
]


@pytest.mark.parametrize("pss,nxt,line,col", CASES)
def test_a_call_missing_its_semicolon_is_pss020(pss, nxt, line, col):
    _, markers = parse_collect(pss)
    errors = find_markers(markers, severity="error")
    assert len(errors) == 1, errors
    assert errors[0]["code"] == "PSS020", errors
    assert f"expected ';' before '{nxt}'" in errors[0]["message"], errors
    assert (errors[0]["line"], errors[0]["col"]) == (line, col), errors


def test_two_missing_semicolons_are_two_errors():
    """The suppression of recovery debris covers one statement, not the rest
    of the block."""
    pss = ('function void g(int a);\n'
           'component pss_top {\n'
           '    action T {\n'
           '        exec body {\n'
           '            g(1)\n'
           '            g(2);\n'
           '            g(3)\n'
           '            g(4);\n'
           '        }\n'
           '    }\n'
           '}\n')
    _, markers = parse_collect(pss)
    errors = find_markers(markers, severity="error")
    assert [(m["code"], m["line"]) for m in errors] == [("PSS020", 6), ("PSS020", 8)], errors


def test_garbage_on_one_line_is_not_called_a_missing_semicolon():
    """The rewrite needs a line break between the two statements. On one line,
    it is not clear that a `;` is what's missing."""
    pss = ('function void g(int a);\n'
           'component pss_top {\n'
           '    action T {\n'
           '        exec body {\n'
           '            g(1) g(2);\n'
           '        }\n'
           '    }\n'
           '}\n')
    _, markers = parse_collect(pss)
    errors = find_markers(markers, severity="error")
    assert errors, markers
    assert not any("expected ';' before 'g'" in m["message"] for m in errors), errors
