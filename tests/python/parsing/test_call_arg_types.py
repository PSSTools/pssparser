"""
Tests for call-site argument *type* checking (PSS007, known issue P3-X6c).

The linker has no expression type-inference pass, so this check works on broad
type *categories* rather than types: numeric (``int``/``bit``/``bool``/
``float``/enum), string, ``chandle``, aggregate literal, and ``null``.  Only a
definite cross-category mismatch is reported; anything that cannot be
classified is left alone.

The boundary tests at the bottom pin what is deliberately *not* classified, so
the gap cannot be mistaken for coverage.  The argument count is checked
separately -- see ``test_call_arity.py``.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


# ---------------------------------------------------------------------------
# Literal arguments
# ---------------------------------------------------------------------------

def test_string_literal_to_int_parameter():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g("not an int"); } }
    }
    """
    assert_marker(pss, marker_id="PSS007",
                  text="argument 1 to 'g' expects int, got string")


def test_int_literal_to_string_parameter():
    pss = """
    package p {
        function void g(string a);
        component pss_top { exec init_up { g(1); } }
    }
    """
    assert_marker(pss, marker_id="PSS007",
                  text="argument 1 to 'g' expects string, got int")


def test_bool_literal_to_string_parameter():
    pss = """
    package p {
        function void g(string a);
        component pss_top { exec init_up { g(true); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got bool")


def test_aggregate_literal_to_scalar_parameter():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g({1, 2}); } }
    }
    """
    assert_marker(pss, marker_id="PSS007",
                  text="expects int, got an aggregate literal")


def test_null_to_string_parameter():
    pss = """
    package p {
        function void g(string a);
        component pss_top { exec init_up { g(null); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got null")


def test_bit_parameter_is_named_bit_not_int():
    """The message reports the declared spelling, not the category name."""
    pss = """
    package p {
        function void g(bit[8] a);
        component pss_top { exec init_up { g("x"); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects bit, got string")


# ---------------------------------------------------------------------------
# Variables, parameters, and operators
# ---------------------------------------------------------------------------

def test_string_variable_to_int_parameter():
    pss = """
    package p {
        function void g(int a);
        component pss_top {
            exec init_up { string s = "a"; g(s); }
        }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects int, got string")


def test_int_variable_to_string_parameter():
    pss = """
    package p {
        function void g(string a);
        component pss_top {
            exec init_up { int v = 1; g(v); }
        }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got int")


def test_enclosing_function_parameter_is_classified():
    pss = """
    package p {
        function void g(string a);
        function void h(int x) { g(x); }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got int")


def test_comparison_yields_bool():
    pss = """
    package p {
        function void g(string a);
        component pss_top { exec init_up { g(1 < 2); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got bool")


def test_string_concatenation_yields_string():
    pss = """
    package p {
        function void g(int a);
        component pss_top {
            exec init_up { string s; g(s + "x"); }
        }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects int, got string")


def test_cast_states_the_category():
    pss = """
    package p {
        function void g(string a);
        component pss_top { exec init_up { g((int)1); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects string, got int")


def test_varargs_element_type_is_checked():
    """Arguments past the fixed parameters land on the varargs parameter."""
    pss = """
    package p {
        function void g(int... rest);
        component pss_top { exec init_up { g(1, "x", 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS007",
                  text="argument 2 to 'g' expects int, got string")


# ---------------------------------------------------------------------------
# The numeric family converts freely -- none of these is reported
# ---------------------------------------------------------------------------

def test_matching_types_are_silent():
    pss = """
    package p {
        function void g(int a, string b);
        component pss_top { exec init_up { g(1 + 2, "ok"); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_bool_to_int_parameter_is_accepted():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g(true); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_bit_variable_to_int_parameter_is_accepted():
    """Width and signedness are outside what a category comparison sees."""
    pss = """
    package p {
        function void g(int a);
        component pss_top {
            exec init_up { bit[8] b; g(b); }
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_enum_value_to_int_parameter_is_accepted():
    pss = """
    package p {
        enum e { A, B }
        function void g(int a);
        component pss_top {
            exec init_up { e v; g(v); }
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_core_library_call_is_silent():
    pss = """
    component pss_top { exec init_up { print("hi"); } }
    """
    assert_no_marker(pss, severity="error")


# ---------------------------------------------------------------------------
# Boundaries: expressions this pass deliberately does not classify
# ---------------------------------------------------------------------------

def test_member_path_argument_is_not_classified():
    """``v.f`` needs member lookup, which is the missing inference pass."""
    pss = """
    package p {
        struct s { int f; }
        function void g(string a);
        component pss_top {
            exec init_up { s v; g(v.f); }
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_call_result_argument_is_not_classified():
    """A nested call would need its return type threaded through."""
    pss = """
    package p {
        function int h();
        function void g(string a);
        component pss_top { exec init_up { g(h()); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_subscript_argument_is_not_classified():
    pss = """
    package p {
        function void g(string a);
        component pss_top {
            exec init_up { list<int> l; g(l[0]); }
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_user_defined_argument_type_is_not_classified():
    pss = """
    package p {
        struct s { int f; }
        function void g(int a);
        component pss_top {
            exec init_up { s v; g(v); }
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


def test_overloaded_function_arguments_are_not_checked():
    """Choosing a parameter list would mean implementing overload resolution."""
    pss = """
    package p {
        function void g(int a);
        function void g(int a, int b);
        component pss_top { exec init_up { g("x"); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS007")


@pytest.mark.xfail(strict=True,
                   reason="P3-X6c: an enum-typed parameter is written as a "
                          "user-defined type reference, so it is not "
                          "classified")
def test_string_to_enum_parameter_is_reported():
    pss = """
    package p {
        enum e { A, B }
        function void g(e a);
        component pss_top { exec init_up { g("x"); } }
    }
    """
    assert_marker(pss, marker_id="PSS007", text="expects an enum value")
