"""
Phase 2 error handling tests: resolution error messages.

Verify that unresolved references produce clear, LLM-friendly messages
with "did you mean?" suggestions where applicable.
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


def test_typo_type_suggests_match():
    """Typo in type name → suggests close match"""
    err = get_error('struct Point { int x; }; struct S { Pont p; };')
    assert err is not None
    assert "did you mean 'Point'" in err


def test_typo_type_one_char_off():
    """Single character deletion → suggests match"""
    err = get_error('struct DataPacket { int x; }; struct S { DataPaket p; };')
    assert err is not None
    assert "did you mean 'DataPacket'" in err


def test_typo_type_case_mismatch():
    """Case variation → suggests match (edit distance includes case)"""
    err = get_error('struct MyStruct { int x; }; struct S { mystruct p; };')
    assert err is not None
    assert "did you mean" in err


def test_unknown_type_no_match():
    """Completely unknown type → no suggestion"""
    err = get_error('struct S { CompletelyUnknownXYZ x; };')
    assert err is not None
    assert "unknown type 'CompletelyUnknownXYZ'" in err
    assert "did you mean" not in err


def test_unknown_identifier_in_constraint():
    """Unknown field name in constraint"""
    err = get_error('''
component pss_top {
    action A {
        rand int value;
        constraint { bogus > 0; }
    }
}''')
    assert err is not None
    assert "unknown identifier 'bogus'" in err


def test_unresolved_enum_value():
    """Unknown enum value reference"""
    err = get_error('''
enum status_e { IDLE, BUSY, DONE };
struct S {
    rand status_e s;
    constraint { s == INVALID; }
};''')
    assert err is not None
    assert 'INVALID' in err


def test_unresolved_import_package():
    """Import of nonexistent package"""
    err = get_error('import nonexistent_pkg::*; struct S { int x; };')
    assert err is not None
    assert 'nonexistent_pkg' in err


def test_extend_unknown_type_message():
    """Extend of nonexistent type → clear error message"""
    err = get_error('extend struct Unknown { int z; };')
    assert err is not None
    assert 'Unknown' in err


def test_enum_typo_suggests_value():
    """Typo in enum value → suggests correct enum value"""
    err = get_error('''
enum status_e { IDLE, BUSY, DONE };
struct S {
    rand status_e s;
    constraint { s == IDEL; }
};''')
    assert err is not None
    assert "did you mean 'IDLE'" in err
