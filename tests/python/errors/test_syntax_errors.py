"""
Phase 3 error handling tests: readable syntax error messages.

Verify that ANTLR parse errors are rewritten to human-readable messages
instead of raw token-set jargon.

Migrated off exception-string assertions (D7): these now assert on the
structured marker dict via ``parse_collect``/``find_markers``, so location
and count are checked, not just a substring of the stringified exception.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect, find_markers  # noqa: E402


def test_missing_semicolon_message():
    """Missing semicolon -> message mentions ';', located at the gap."""
    _root, markers = parse_collect('struct S { int x }')
    errs = find_markers(markers, severity="error")
    assert len(errs) == 1
    assert "';'" in errs[0]["message"]
    assert errs[0]["line"] == 1
    assert errs[0]["col"] == 18


def test_missing_name_message():
    """Missing identifier -> 'expected identifier'."""
    _root, markers = parse_collect('component { }')
    errs = find_markers(markers, severity="error", text="expected identifier")
    assert len(errs) == 1
    assert errs[0]["line"] == 1
    assert errs[0]["col"] == 11


def test_extends_vs_colon_message():
    """'extends' instead of ':' -> helpful hint naming both tokens."""
    _root, markers = parse_collect('struct D extends B { };')
    errs = find_markers(markers, severity="error")
    assert len(errs) == 1
    assert "':'" in errs[0]["message"]
    assert "extends" in errs[0]["message"]


def test_extraneous_keyword_message():
    """Keyword in wrong place -> 'unexpected keyword'."""
    _root, markers = parse_collect('rand struct S { };')
    errs = find_markers(markers, severity="error", text="unexpected keyword")
    assert len(errs) == 1
    assert errs[0]["line"] == 1
    assert errs[0]["col"] == 1


def test_syntax_error_at():
    """No viable alternative -> 'syntax error at'."""
    _root, markers = parse_collect('struct S { x; };')
    errs = find_markers(markers, severity="error", text="syntax error")
    assert len(errs) == 1


def test_error_includes_location():
    """All errors include file, line, and column."""
    _root, markers = parse_collect('struct S { int x }', filename="test.pss")
    errs = find_markers(markers, severity="error")
    assert len(errs) == 1
    assert errs[0]["file"] == "test.pss"
    assert errs[0]["line"] == 1
    assert errs[0]["col"] == 18


def test_missing_closing_brace():
    """Unclosed brace -> exactly one error, at end of input."""
    _root, markers = parse_collect('struct S { int x; ')
    errs = find_markers(markers, severity="error")
    assert len(errs) == 1
    assert errs[0]["line"] == 1


def test_invalid_operator_in_constraint():
    """Invalid operator ('===') -> a syntax error inside the constraint."""
    _root, markers = parse_collect('''
component pss_top {
    action A { rand int x; constraint { x === 5; } }
}''')
    errs = find_markers(markers, severity="error", text="syntax error")
    assert len(errs) == 1
    assert errs[0]["line"] == 3
