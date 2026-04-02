"""
Phase 3 error handling tests: readable syntax error messages.

Verify that ANTLR parse errors are rewritten to human-readable messages
instead of raw token-set jargon.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def get_error(code):
    """Parse code and return error message string, or None if no error."""
    from pssparser import Parser
    try:
        p = Parser()
        p.parses([('test.pss', code)])
        p.link()
        return None
    except Exception as e:
        return str(e)


def test_missing_semicolon_message():
    """Missing semicolon → message mentions ';'"""
    err = get_error('struct S { int x }')
    assert err is not None
    assert "';'" in err


def test_missing_name_message():
    """Missing identifier → 'expected identifier'"""
    err = get_error('component { }')
    assert err is not None
    assert "expected identifier" in err


def test_extends_vs_colon_message():
    """'extends' instead of ':' → helpful hint"""
    err = get_error('struct D extends B { };')
    assert err is not None
    assert "':'" in err
    assert "extends" in err


def test_extraneous_keyword_message():
    """Keyword in wrong place → 'unexpected keyword'"""
    err = get_error('rand struct S { };')
    assert err is not None
    assert "unexpected" in err


def test_syntax_error_at():
    """No viable alternative → 'syntax error at'"""
    err = get_error('struct S { x; };')
    assert err is not None
    assert "syntax error" in err


def test_error_includes_location():
    """All errors include file:line:col"""
    err = get_error('struct S { int x }')
    assert err is not None
    assert "test.pss:" in err


def test_missing_closing_brace():
    """Unclosed brace → produces error"""
    err = get_error('struct S { int x; ')
    assert err is not None


def test_invalid_operator_in_constraint():
    """Invalid operator → syntax error"""
    err = get_error('''
component pss_top {
    action A { rand int x; constraint { x === 5; } }
}''')
    assert err is not None
