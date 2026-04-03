"""
Phase 1 error handling tests: crash safety.

Invalid input must never crash the tool — it should always produce
an error message via the marker system.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss


def assert_no_crash(code, description=""):
    """Assert code does not crash (segfault), even if it has errors."""
    try:
        p_mod = __import__('pssparser', fromlist=['Parser'])
        p = p_mod.Parser()
        p.parses([('test.pss', code)])
        p.link()
    except Exception:
        pass


def assert_error_contains(code, expected_substring):
    """Assert code produces an error containing expected text."""
    try:
        p_mod = __import__('pssparser', fromlist=['Parser'])
        p = p_mod.Parser()
        p.parses([('test.pss', code)])
        p.link()
        pytest.fail("Expected error but parsing/linking succeeded")
    except Exception as e:
        msg = str(e)
        assert expected_substring in msg, \
            f"Expected '{expected_substring}' in error, got:\n{msg}"


def test_extend_unknown_struct():
    """extend struct with nonexistent type name → error, not crash"""
    assert_error_contains(
        'extend struct Unknown { int z; };',
        'Unknown')


def test_extend_unknown_enum():
    """extend enum with nonexistent type name → error, not crash"""
    assert_error_contains(
        'extend enum Unknown { Z }',
        'Unknown')


def test_extend_unknown_component():
    """extend component with nonexistent type name → error, not crash"""
    assert_error_contains(
        'extend component Unknown { }',
        'Unknown')


def test_extend_unknown_buffer():
    """extend buffer with nonexistent type name → error, not crash"""
    assert_no_crash('extend buffer Unknown { int z; };')


def test_extend_unknown_resource():
    """extend resource with nonexistent type name → error, not crash"""
    assert_no_crash('extend resource Unknown { };')


def test_deeply_invalid_syntax():
    """Completely garbled input → error, not crash"""
    assert_no_crash('}{}{}{::;;rand rand rand')


def test_empty_input():
    """Empty string → no crash"""
    assert_no_crash('')


def test_null_bytes_in_input():
    """Input with unusual whitespace → no crash"""
    assert_no_crash('struct S { int x; };\t\n\r\n')


def test_very_deep_nesting():
    """Deeply nested braces → no crash"""
    code = 'component pss_top {' * 5 + '}' * 5
    assert_no_crash(code)


def test_unterminated_string():
    """Unterminated string literal → error, not crash"""
    assert_no_crash('struct S { string s = "unterminated; };')


def test_unresolved_type_in_extend_body():
    """Extend with unresolved type in field → error, not crash"""
    assert_no_crash('''
struct Known { int x; };
extend struct Known { BadType extra; };
''')
