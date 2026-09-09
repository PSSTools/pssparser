"""Marker spans are measured from the token stream, not from ``getText()``.

ANTLR's ``ParserRuleContext::getText()`` concatenates the *text* of a rule's
tokens, silently dropping every space between them.  Four marker sites used it
to compute ``Location::extent``, so the caret drawn under a multi-token
construct stopped short of the construct whenever it was written with ordinary
spacing -- and the shortfall grew with the amount of whitespace, which is why
it was easy to miss on the tightly-written examples in the test suite.

Each case here writes the offending construct with *deliberate* internal
whitespace and pins the extent to the true character span, so a regression to
``getText().size()`` fails by exactly the number of spaces added.

See ``docs/design/cli-diagnostics-and-stats-plan.md`` D4-b / D4-e.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect  # noqa: E402


def _marker_matching(src: str, needle: str) -> dict:
    _root, markers = parse_collect(src, filename="extent.pss")
    matching = [m for m in markers if needle in m.get("message", "")]
    assert matching, (
        f"no marker matched {needle!r}; got "
        f"{[m.get('message') for m in markers]}"
    )
    return matching[0]


def _span_of(src: str, marker: dict) -> str:
    """The exact source text the marker's caret would underline."""
    line = src.splitlines()[marker["line"] - 1]
    start = marker["col"] - 1
    return line[start:start + marker["extent"]]


@pytest.mark.parametrize(
    "name,src,needle,expected",
    [
        (
            "compile_assert",
            'const int X = 1;\n'
            'compile assert ( X == 2 , "X must be two" );\n',
            "compile assert failed",
            'compile assert ( X == 2 , "X must be two" );',
        ),
        (
            "compile_if_branch",
            'const int X = 1;\n'
            'component C {\n'
            '    compile if (X == 1)\n'
            '        action A { int a; }\n'
            '}\n',
            "without enclosing braces is deprecated",
            "action A { int a; }",
        ),
        (
            "bit_low_bound",
            'struct S {\n'
            '    bit[15 : 2] x;\n'
            '}\n',
            "unexpected low bound",
            "2",
        ),
    ],
)
def test_extent_covers_internal_whitespace(name, src, needle, expected):
    marker = _marker_matching(src, needle)
    assert _span_of(src, marker) == expected, (
        f"{name}: caret underlines {_span_of(src, marker)!r}, expected "
        f"{expected!r} -- extent is {marker['extent']}, the construct is "
        f"{len(expected)} characters"
    )


def test_extent_would_fail_under_gettext_measurement():
    """Guards the guard: the compile-assert case must actually discriminate.

    ``getText()`` drops whitespace, so an assertion written with no internal
    spaces would pass under both the old and new measurement and pin nothing.
    """
    src = ('const int X = 1;\n'
           'compile assert ( X == 2 , "X must be two" );\n')
    marker = _marker_matching(src, "compile assert failed")
    stripped = "".join(_span_of(src, marker).split())
    assert len(stripped) < marker["extent"], (
        "the fixture has no internal whitespace, so it cannot detect a "
        "regression to getText()-based measurement"
    )
