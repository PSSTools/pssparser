"""
Tests for the PSS 3.1 type-category restructure (P3-S4, LRM §3.2, Annex B B.13).

::

    ref_type_category   ::= action | monitor | component | object_kind
    plain_type_category ::= struct | numeric
    type_category       ::= ref_type_category | plain_type_category

The 3.0 rule folded `struct_kind` -- plain `struct` *plus* the object kinds --
into a single alternative, and had neither `monitor` nor `numeric`. The split is
not cosmetic: it decides what may follow `ref`. `ref buffer` is legal because
`buffer` is a ref category; `ref struct` and `ref numeric` are not.

Three places consume this: `category_type_param_decl`, `function_parameter` and
`varargs_parameter`. The latter two spelled the un-`ref`ed alternative as a bare
`struct` token, which is why `numeric` parameters were rejected.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402

_REF_CATEGORIES = ["action", "monitor", "component",
                   "buffer", "stream", "state", "resource"]
_PLAIN_CATEGORIES = ["struct", "numeric"]


# ===========================================================================
# Template type-category parameters
# ===========================================================================

@pytest.mark.parametrize("category", _REF_CATEGORIES + _PLAIN_CATEGORIES)
def test_every_category_is_accepted_as_a_template_parameter(category):
    """`type_category` is the union, so all seven plus both plain ones work."""
    assert_parse_ok("package p { struct S<%s T> { }; }" % category)


def test_monitor_category_was_previously_missing():
    assert_parse_ok("package p { struct S<monitor M> { }; }")


def test_numeric_category_was_previously_missing():
    assert_parse_ok("package p { struct S<numeric N> { }; }")


def test_category_parameter_with_a_type_restriction():
    assert_parse_ok("""
    package p {
        struct Base { }
        struct S<struct T : Base> { };
    }
    """)


def test_category_parameter_with_a_default():
    assert_parse_ok("""
    package p {
        struct Base { }
        struct S<struct T = Base> { };
    }
    """)


# ===========================================================================
# Function parameters
# ===========================================================================

@pytest.mark.parametrize("category", _REF_CATEGORIES)
def test_ref_accepts_every_ref_category(category):
    assert_parse_ok("package p { function void f(ref %s x); }" % category)


@pytest.mark.parametrize("category", _PLAIN_CATEGORIES)
def test_plain_category_parameter_is_accepted(category):
    assert_parse_ok("package p { function void f(%s x); }" % category)


def test_numeric_parameter_was_previously_rejected():
    """
    The un-`ref`ed alternative used to be a bare `struct` token, so `numeric`
    had no way through the grammar.
    """
    assert_parse_ok("package p { function void f(numeric n); }")


@pytest.mark.parametrize("category", _PLAIN_CATEGORIES)
def test_ref_rejects_a_plain_category(category):
    """
    The point of the split. `ref struct` parsed in 3.0 because `struct_kind`
    was reachable from the `ref` alternative; 3.1 says it is a plain category
    and may not follow `ref`.
    """
    assert_parse_error("package p { function void f(ref %s x); }" % category)


def test_type_parameter_is_still_accepted():
    assert_parse_ok("package p { function void f(type T); }")


def test_const_qualified_category_parameter():
    assert_parse_ok("package p { function void f(const struct s); }")


# ===========================================================================
# Varargs parameters
# ===========================================================================

def test_varargs_type_parameter():
    """`type... args`, which Annex C uses throughout for print/format/message."""
    assert_parse_ok("package p { function void f(string fmt, type... args); }")


@pytest.mark.parametrize("category", _REF_CATEGORIES)
def test_varargs_ref_category(category):
    assert_parse_ok("package p { function void f(ref %s... args); }" % category)


@pytest.mark.parametrize("category", _PLAIN_CATEGORIES)
def test_varargs_plain_category(category):
    assert_parse_ok("package p { function void f(%s... args); }" % category)


def test_varargs_data_type():
    assert_parse_ok("package p { function void f(int... args); }")


def test_varargs_must_be_last():
    assert_parse_error(
        "package p { function void f(type... args, int trailing); }")


# ===========================================================================
# Regressions from the restructure
# ===========================================================================

def test_struct_kind_declarations_still_parse():
    """
    `struct_kind` keeps its own role in `struct_declaration`; only its use as a
    *type category* was split out.
    """
    for kind in ["struct", "buffer", "stream", "state", "resource"]:
        assert_parse_ok("%s S { }" % kind)


def test_action_and_component_categories_still_parse():
    assert_parse_ok("package p { struct S<action A> { }; }")
    assert_parse_ok("package p { struct S<component C> { }; }")
