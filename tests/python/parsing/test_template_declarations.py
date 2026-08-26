"""Declaring a parameterized type: every parameter form, on every type category.

Broad and cheap.  These pin the *input* side of the template machinery -- the
shape of the declaration and its parameter list -- so that a failure in the
binding or identity suites can be attributed to binding rather than to the
declaration never having parsed the way it was meant to.

Each case both links the model and asserts the resulting parameter list, so a
declaration that parses into the wrong parameter *kind* is caught here rather
than showing up as a mysterious binding failure later.

See ``docs/template-parameter-test-suite.md`` section 4.1.
"""
import pytest

from ..isolation import assert_clean, run_isolated
from ..template_helpers import bindings, param_decls, specializations
from ..test_helpers import parse_pss


PKG = """
package p {
    struct base_s { int b; }
    struct derived_s : base_s { int d; }
%s
}
"""


# ---------------------------------------------------------------------------
# Parameter forms
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "decl,use,kinds,expected",
    [
        ("struct S<type T> { T v; }",
         "S<int> a;", ["TemplateGenericTypeParamDecl"], ["int"]),
        ("struct S<struct T> { T v; }",
         "S<derived_s> a;", ["TemplateGenericTypeParamDecl"], ["derived_s"]),
        ("struct S<int N> { bit[N] v; }",
         "S<4> a;", ["TemplateValueParamDecl"], ["4"]),
        ("struct S<type T, int N> { bit[N] v; }",
         "S<int,4> a;",
         ["TemplateGenericTypeParamDecl", "TemplateValueParamDecl"],
         ["int", "4"]),
        ("struct S<type T = int> { T v; }",
         "S<> a;", ["TemplateGenericTypeParamDecl"], ["int"]),
        ("struct S<int N = 4> { bit[N] v; }",
         "S<> a;", ["TemplateValueParamDecl"], ["4"]),
        ("struct S<struct T : base_s> { T v; }",
         "S<derived_s> a;", ["TemplateGenericTypeParamDecl"], ["derived_s"]),
        ("struct S<type T, int N = 4> { bit[N] v; }",
         "S<int> a;",
         ["TemplateGenericTypeParamDecl", "TemplateValueParamDecl"],
         ["int", "4"]),
        ("struct S<type T, type U, int N> { T a; U b; }",
         "S<int,bool,4> x;",
         ["TemplateGenericTypeParamDecl", "TemplateGenericTypeParamDecl",
          "TemplateValueParamDecl"],
         ["int", "bool", "4"]),
    ],
    ids=[
        "type", "struct-category", "int-value", "type-and-value",
        "type-default", "value-default", "category-restriction",
        "trailing-default", "three-params",
    ],
)
def test_parameter_declaration_form(decl, use, kinds, expected):
    root = parse_pss(PKG % ("%s struct Top { %s }" % (decl, use)))
    specs = specializations(root, "p::S")
    assert len(specs) == 1, "expected one specialization, got %d" % len(specs)

    spec = specs[0]
    assert [type(pd).__name__ for pd in param_decls(spec)] == kinds
    assert bindings(root, spec) == expected


@pytest.mark.parametrize(
    "decl,use",
    [
        ("struct S<bit[4] N = 2> { int v; }", "S<> a;"),
        ("struct S<bool B = true> { int v; }", "S<> a;"),
    ],
    ids=["bit-value", "bool-value"],
)
def test_non_int_value_parameter_declares(decl, use):
    assert_clean([("t.pss", PKG % ("%s struct Top { %s }" % (decl, use)))])


# ---------------------------------------------------------------------------
# Type categories
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "src",
    [
        "package p { struct S<type T> { T v; } struct Top { S<int> x; } }",
        "package p { buffer B<type T> { T v; } struct Top { B<int> x; } }",
        "package p { stream St<type T> { T v; } struct Top { St<int> x; } }",
        "package p { state Stt<type T> { T v; } struct Top { Stt<int> x; } }",
        "package p { resource R<type T> { T v; } struct Top { R<int> x; } }",
        "component C<type T> { int w; } component pss_top { C<int> c; }",
    ],
    ids=["struct", "buffer", "stream", "state", "resource", "component"],
)
def test_generic_type_category_specializes(src):
    assert_clean([("t.pss", src)])


# Specializing a generic action used to segfault regardless of body -- an
# action with an entirely empty body was enough.  Two separate defects, both
# fixed:
#
# * an action carries an implicit component reference (an ``IFieldCompRef``
#   child), and ``TaskCopyAst::visitFieldCompRef`` was an empty stub, so the
#   copy returned null and the caller dereferenced it;
# * ``TaskResolveSymbolPathRef::mkIterator`` then read
#   ``getParams()->getSpecialized()`` on every enclosing scope, and an action's
#   enclosing component has no parameter list.
#
# The second is why actions crashed where generic structs in a package did not:
# a package scope is not a type scope, so it never reached that read.


def test_generic_action_specializes():
    assert_clean([("t.pss", "component pss_top { action A<type T> { } A<int> a; }")])


def test_generic_action_with_field_specializes():
    assert_clean([("t.pss",
                   "component pss_top { action A<type T> { rand T v; } A<int> a; }")])


def test_generic_action_declared_but_never_used_links():
    """Control: no use means no specialization, so nothing is copied."""
    assert_clean([("t.pss", "component pss_top { action A<type T> { } }")])


def test_non_generic_action_links():
    """Control: the same action without a parameter list."""
    assert_clean([("t.pss", "component pss_top { action A { } A a; }")])


# ---------------------------------------------------------------------------
# Malformed declarations
# ---------------------------------------------------------------------------

def test_parameter_list_on_an_enum_is_rejected():
    """Enums are not parameterizable; the declaration must not be accepted."""
    res = run_isolated([("t.pss", "package p { enum E<type T> { A } }")])
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
