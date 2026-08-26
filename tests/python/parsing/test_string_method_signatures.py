"""
Tests for string-method signature checking (known issue P3-X6d).

String methods used to be validated against a hard-coded list of *names* in
``TaskResolveRefs``, so ``s.substr()`` passed with no arguments at all.  They now
resolve against real prototypes on the ``string`` pseudo-type built by
``BuiltinsFactory``, which puts them on the same footing as any other call: the
argument count is checked (``PSS006``) and so is the argument category
(``PSS007``).

A string variable has no type *reference* to follow -- ``IDataTypeString`` names
nothing -- so the lookup goes through the pseudo-type by name.  That bridge is
what these tests exercise.

NOTE: a built-in method's arguments are checked by TaskCheckCallArgs, which
phrases the mismatch as "argument 1 to 'find' expects string, got int". An
ordinary call goes through TaskResolveRefs::checkCallArgTypes and reads
"argument 1 of 'g' is a string, but parameter 'a' is numeric". Same diagnosis
and the same code (PSS006), two spellings -- the built-in path is the one
checkCallArity never reaches, so the two checkers divide the work by callee
kind rather than duplicating it. Worth unifying; see the merge notes.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


def _exec(body):
    return "component pss_top { exec init_up { string s; %s } }" % body


# ---------------------------------------------------------------------------
# Arity is now checked
# ---------------------------------------------------------------------------

def test_too_few_arguments():
    assert_marker(_exec('string t = s.substr();'), marker_id="PSS006",
                  text="call to 'substr' expects 1 to 2 arguments, got 0")


def test_too_many_arguments():
    assert_marker(_exec('int n = s.find("a", 1, 2);'), marker_id="PSS006",
                  text="call to 'find' expects 1 to 2 arguments, got 3")


def test_zero_argument_method_called_with_arguments():
    assert_marker(_exec('int n = s.size(1);'), marker_id="PSS006",
                  text="call to 'size' expects 0 arguments, got 1")


def test_a_defaulted_parameter_may_be_omitted():
    """`find(string sub_str, int first_pos = 0)` -- LRM 7.6.3."""
    assert_no_marker(_exec('int n = s.find("a");'), severity="error")


def test_a_defaulted_parameter_may_be_supplied():
    assert_no_marker(_exec('int n = s.find("a", 1);'), severity="error")


def test_a_string_field_is_checked_too():
    """Not just a procedural variable -- the field path reaches the same check."""
    pss = """
    component pss_top {
        string s;
        exec init_up { int n = s.size(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="call to 'size' expects")


# ---------------------------------------------------------------------------
# Argument types are checked, by category
# ---------------------------------------------------------------------------

def test_argument_type_mismatch():
    assert_marker(_exec('int n = s.find(1);'), marker_id="PSS006",
                  text="argument 1 to 'find' expects string, got int")


def test_second_argument_type_mismatch():
    assert_marker(_exec('int n = s.find("a", "b");'), marker_id="PSS006",
                  text="argument 2 to 'find' expects int, got string")


def test_matching_argument_types_are_silent():
    assert_no_marker(_exec('int n = s.find_last("a", 3);'), severity="error")


# ---------------------------------------------------------------------------
# Every method of LRM 7.6.3 resolves
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("call", [
    'int n = s.size();',
    'int n = s.find("a");',
    'int n = s.find_last("a");',
    'list<int> l = s.find_all("a");',
    'string t = s.lower();',
    'string t = s.upper();',
    'list<string> l = s.split(",");',
    'list<bit[8]> l = s.chars();',
])
def test_lrm_string_method(call):
    assert_no_marker(_exec(call), severity="error")


@pytest.mark.parametrize("call", [
    'int n = s.len();',
    'int n = s.rfind("a");',
    'string t = s.substr(0, 3);',
    'string t = s.to_lower();',
    'string t = s.to_upper();',
    'string t = s.trim();',
    'bool b = s.starts_with("a");',
    'bool b = s.ends_with("a");',
])
def test_non_lrm_string_method_still_accepted(call):
    """
    These are not in LRM 7.6.3.  They are kept so source written against earlier
    releases still parses; whether to deprecate them is P3-X6f.
    """
    assert_no_marker(_exec(call), severity="error")


# ---------------------------------------------------------------------------
# An unknown method is still reported the way it always was
# ---------------------------------------------------------------------------

def test_unknown_method_is_reported():
    assert_marker(_exec('int n = s.bogus();'), marker_id="PSS002",
                  text="unknown method 'bogus' on built-in type")


# ---------------------------------------------------------------------------
# Boundary: collection methods are a separate path and are not covered
# ---------------------------------------------------------------------------

def test_collection_method_is_not_affected():
    """
    Only `push_back` has a real prototype; the rest still go through a name
    list, so their arity is unchecked.  Pinned so the gap stays visible.
    """
    pss = """
    component pss_top {
        exec init_up { list<int> l; int n = l.size(1, 2); }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")
