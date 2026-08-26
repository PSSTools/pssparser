"""
Tests for call-site argument-count checking (PSS006, known issue P3-X6).

Every call in the AST -- statement or expression, plain or method -- is an
``ExprMemberPathElem`` carrying a ``params`` list, so all these forms reach the
same check.  This file covers the argument *count*; argument types are checked
separately, as PSS007 -- see ``test_call_arg_types.py``.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


# ---------------------------------------------------------------------------
# Too few / too many, across every call form
# ---------------------------------------------------------------------------

def test_too_many_arguments():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g(1, 2, 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="too many arguments to 'g': expected 1, got 3")


def test_too_few_arguments():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g(); } }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="too few arguments to 'g': expected 1, got 0")


def test_correct_arity_is_silent():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g(1); } }
    }
    """
    assert_no_marker(pss, severity="error")


def test_zero_arg_function_called_with_arguments():
    pss = """
    package p {
        function void g();
        component pss_top { exec init_up { g(1); } }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="expected 0, got 1")


def test_defined_function_is_checked():
    """A function with a body, not just a prototype."""
    pss = """
    package p {
        function void g(int a) { int q = a; }
        component pss_top { exec init_up { g(1, 2, 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 3")


def test_imported_function_is_checked():
    pss = """
    package p {
        import function void g(int a);
        component pss_top { exec init_up { g(1, 2, 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 3")


def test_call_in_value_context_is_checked():
    """A call used as an expression, not as a statement."""
    pss = """
    package p {
        function int g(int a);
        component pss_top { exec init_up { int x = g(1, 2, 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 3")


def test_method_call_is_checked():
    pss = """
    component c { function void g(int a); }
    component pss_top {
        c inst;
        exec init_up { inst.g(1, 2, 3); }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 3")


# ---------------------------------------------------------------------------
# Defaults widen the accepted range
# ---------------------------------------------------------------------------

def test_default_parameter_may_be_omitted():
    pss = """
    package p {
        function void g(int a, int b = 2);
        component pss_top { exec init_up { g(1); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_required_parameter_may_not_be_omitted():
    pss = """
    package p {
        function void g(int a, int b = 2);
        component pss_top { exec init_up { g(); } }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="expected at least 1, got 0")


def test_too_many_past_the_defaults():
    pss = """
    package p {
        function void g(int a, int b = 2);
        component pss_top { exec init_up { g(1, 2, 3); } }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="expected at most 2, got 3")


# ---------------------------------------------------------------------------
# Varargs remove the upper bound but keep the lower one
# ---------------------------------------------------------------------------

def test_varargs_accepts_any_trailing_count():
    pss = """
    package p {
        function void g(int a, int... rest);
        component pss_top { exec init_up { g(1, 2, 3, 4); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_varargs_still_requires_the_fixed_parameters():
    pss = """
    package p {
        function void g(int a, int... rest);
        component pss_top { exec init_up { g(); } }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="expected at least 1, got 0")


# ---------------------------------------------------------------------------
# Core-library and collection methods go through the same path
# ---------------------------------------------------------------------------

def test_core_function_is_checked():
    pss = """
    component pss_top { exec init_up { print(); } }
    """
    assert_marker(pss, marker_id="PSS006", text="arguments to 'print'")


def test_collection_method_is_checked():
    pss = """
    component pss_top {
        exec init_up {
            list<int> l;
            l.push_back(1, 2, 3);
        }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="arguments to 'push_back'")


# ---------------------------------------------------------------------------
# Boundaries: what this check deliberately does not do
# ---------------------------------------------------------------------------

def test_argument_type_mismatch_is_not_an_arity_error():
    """A wrong argument *type* must not be reported as a wrong argument *count*.

    Both share PSS006 -- the code covers "the call does not match the callee's
    parameters" as a whole -- so the distinction has to be asserted on the
    message rather than on the id. See test_call_arg_types.py.
    """
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g("not an int"); } }
    }
    """
    assert_no_marker(pss, text="arguments to 'g'")
    assert_marker(pss, marker_id="PSS006", text="argument 1 of 'g'")


def test_package_qualified_call_is_checked():
    """P3-X6e.

    The leaf of a qualified path was visited but never looked up *against its
    root*, so the call site was never reached.
    """
    pss = """
    package p { function void g(int a); }
    component pss_top { exec init_up { p::g(1, 2, 3); } }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 3")


def test_package_qualified_call_with_correct_arity_is_silent():
    pss = """
    package p { function void g(int a); }
    component pss_top { exec init_up { p::g(1); } }
    """
    assert_no_marker(pss, severity="error")


def test_package_qualified_call_to_an_unknown_name_is_reported():
    """The other half of the same gap: the name was not checked to exist."""
    pss = """
    package p { function void g(int a); }
    component pss_top { exec init_up { p::nope(1); } }
    """
    assert_marker(pss, text="'p' has no member named 'nope'")


def test_nested_package_qualified_call_is_checked():
    """The root may itself be several elements deep."""
    pss = """
    package p::q { function void g(int a); }
    component pss_top { exec init_up { p::q::g(1, 2); } }
    """
    assert_marker(pss, marker_id="PSS006", text="expected 1, got 2")


# ---------------------------------------------------------------------------
# A prototype followed by a definition used to segfault
# ---------------------------------------------------------------------------

def test_prototype_then_definition_does_not_crash():
    """
    ``TaskBuildSymbolTree::visitFunctionPrototype`` builds a function scope with
    no ``plist``; the following definition reuses that scope and attaches a body
    whose statements then resolve through ``TaskResolveRootRef``, which
    dereferenced the null ``plist``.  Regression guard: this must terminate.
    """
    pss = """
    package p {
        function void g(int a);
        function void g(int a) { int q = a; }
    }
    """
    from test_helpers import parse_collect
    parse_collect(pss)   # must not segfault


def test_prototype_then_definition_resolves_parameters():
    """P3-X8.

    The definition reuses the scope the prototype built, so it never runs its
    own parameter-registering block.  That was only survivable once the
    prototype path registered parameters too -- before, ``a`` was in no scope
    at all and the body reported ``PSS002 unknown identifier 'a'``.
    """
    pss = """
    package p {
        function void g(int a);
        function void g(int a) { int q = a; }
    }
    """
    assert_no_marker(pss, severity="error")


def test_duplicate_function_parameter_is_reported():
    """P3-X8, the other half.

    ``visitFunctionDefinition`` searched the ``<plist>`` symtab and compared the
    result against the *function scope's* symtab ``end()`` -- undefined
    behaviour, and one that made the diagnostic it guards dead code: this input
    used to produce no marker at all.
    """
    pss = """
    package p { function void f(int a, int a) { } }
    """
    assert_marker(pss, text="duplicate parameter name 'a'")


def test_duplicate_parameter_on_a_bare_prototype_is_reported():
    pss = """
    package p { function void f(int a, int a); }
    """
    assert_marker(pss, text="duplicate parameter name 'a'")


def test_distinct_parameters_are_not_reported_as_duplicates():
    """Guard on the import path, which reaches the prototype visitor a second
    time after building the scope: re-registering there would report every
    parameter as a duplicate of itself."""
    pss = """
    package p {
        import target C function void f(int a, int b);
        function void g(int a, int b) { int q = a + b; }
    }
    """
    assert_no_marker(pss, severity="error")


@pytest.mark.xfail(strict=True,
                   reason="P3-X6d (collections): collection methods other than "
                          "push_back still resolve through a name allow-list")
def test_collection_method_arity_is_checked_beyond_push_back():
    pss = """
    component pss_top {
        exec init_up {
            list<int> l;
            int n = l.size(1, 2);
        }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="arguments to 'size'")
