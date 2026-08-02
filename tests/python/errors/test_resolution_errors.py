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


# ---------------------------------------------------------------------------
# Member access below the root of a hierarchical path
#
# The *root* of a ref-path has been checked for a long time ("root ref-path
# element x is not a composite scope").  Every position after it had no such
# check: when an element produced no scope to search, the loop hit a
# DEBUG_ERROR and broke out, which is debug chatter and not a marker, so the
# parse exited 0 and the reference linked.
#
# The check added here is a positive test on a short list of scalar types
# rather than "produced no scope", and the controls below are why.  Two other
# things reach that same point legitimately: a `string` or collection, which
# has methods but no scope, and a user-defined type that did not resolve,
# which is the normal state when one file of a multi-file model is parsed
# alone.  Reporting either would be a regression, and the second one did
# regress the corpus while this was being written.
# ---------------------------------------------------------------------------

from ..isolation import assert_clean, assert_rejects


def test_member_of_an_int_field_below_the_root_is_reported():
    assert_rejects([("t.pss", """
        package p {
            struct S { int a; }
            struct T { S s; int n; constraint { n == s.a.nosuch; } }
        }
    """)], "ref-path element a is not a composite scope")


def test_member_of_an_int_field_below_the_root_is_reported_in_an_exec():
    """The same path through procedural code rather than a constraint."""
    assert_rejects([("t.pss", """
        package p {
            struct S { int a; }
            component C { S s; exec init_up { s.a.nosuch = 1; } }
        }
    """)], "ref-path element a is not a composite scope")


def test_a_struct_member_below_the_root_still_links():
    """Control: the ordinary hierarchical read, which must be unaffected."""
    assert_clean([("t.pss", """
        package p {
            struct S { int a; }
            struct T { S s; int n; constraint { n == s.a; } }
        }
    """)])


def test_a_string_method_below_the_root_still_links():
    """Control, and the reason the check cannot be "produced no scope".

    A `string` field has no symbol scope either, so it arrives at exactly the
    line that now reports an error -- but `size()` is a legal call on it.
    Method checking had been wired to element index 1 alone, i.e. only
    directly after the root, so this had to be generalized rather than reused.
    """
    assert_clean([("t.pss", """
        package p {
            struct S { string a; }
            struct T { S s; int n; constraint { n == s.a.size(); } }
        }
    """)])


def test_an_unknown_method_on_a_string_below_the_root_is_reported():
    """The generalization above must still *check* the method, not wave it through."""
    assert_rejects([("t.pss", """
        package p {
            struct S { string a; }
            struct T { S s; int n; constraint { n == s.a.nosuch(); } }
        }
    """)], "nosuch")


# ---------------------------------------------------------------------------
# One cause, one diagnostic
#
# A root whose type never resolved has no scope, so a member access on it
# fails -- but `unknown type '<name>'` was already reported at the
# declaration.  Reporting "not a composite scope" as well gave two errors for
# one cause, and pointed the second at the use site rather than at the thing
# the user has to fix.
#
# This is a cascade, not a false rejection: the parse failed either way, and
# no case could be constructed where the extra line was the *only* error.
# That is why it is a diagnostic-quality fix and not a correctness one.
# ---------------------------------------------------------------------------

def test_an_unknown_root_type_reports_once():
    res = assert_rejects([("t.pss", """
        package p {
            struct T { nosuch_s s; int n; constraint { n == s.val; } }
        }
    """)], "unknown type 'nosuch_s'")
    assert "not a composite scope" not in res.output, (
        "the unresolved type is already reported at the declaration; "
        "the ref-path message is a second diagnostic for the same cause: %s"
        % res.describe())


def test_a_scalar_root_still_reports():
    """Control: suppression must key on *unresolved*, not on *no scope*.

    An `int` root has no scope either and is the case the root check exists
    for, so it must survive untouched.
    """
    assert_rejects([("t.pss", """
        package p {
            struct S { int x; int n; constraint { n == x.nosuch; } }
        }
    """)], "root ref-path element x is not a composite scope")
