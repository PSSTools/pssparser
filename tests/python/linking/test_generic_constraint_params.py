"""A generic constraint's parameters are in scope in its body (13.1.2; symbol-
resolution plan 8.7, F14).

They used to be skipped by name, so a parameter reference had no target:
`p.nosuch` linked clean, a parameter that shared a name with a field bound to
the field, and an enum-typed parameter gave no expected type. They are found
now as a `symbol`'s parameters are, by an `ElemKind_ArgIdx` step on the
declaration.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["line"], m["message"]) for m in ms]


def bindings(code, name):
    """(line of use, kind of declaration, line of declaration) for each use
    of `name`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.line, type(o.decl).__name__.lstrip("I"),
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text == name and not o.is_declaration]


P = """\
struct P { rand bit[8] a; }
"""


# ---------------------------------------------------------------------------
# A parameter is found, and its type is used
# ---------------------------------------------------------------------------


def test_a_parameter_binds_to_its_declaration():
    code = P + """\
struct S {
  rand P p1; rand bit[8] v1;
  constraint g(P p, bit[8] v) { p.a > v; }
  constraint { g(p1, v1); }
}
"""
    assert markers(code) == []
    assert bindings(code, "p") == [(4, "GenericConstraintParam", 4)]
    assert bindings(code, "v") == [(4, "GenericConstraintParam", 4)]
    assert bindings(code, "a") == [(4, "Field", 1)]


def test_an_unknown_member_of_a_parameter_is_reported():
    """The F14 repro: `p.nosuch` used to link clean."""
    code = P + """\
struct S {
  rand P p1; rand bit[8] v1;
  constraint g(P p, bit[8] v) { p.nosuch > v; zzz < 3; }
  constraint { g(p1, v1); }
}
"""
    assert markers(code) == [
        ("error", 4, "Failed to find elem nosuch"),
        ("error", 4, "unknown identifier 'zzz'"),
    ]


def test_a_value_generic_constraint():
    code = P + """\
struct S {
  rand P p1;
  constraint bool ok(P p) p.a > 3;
  constraint bool bad(P p) p.zz > 3;
  constraint { ok(p1); }
}
"""
    assert markers(code) == [("error", 5, "Failed to find elem zz")]
    assert bindings(code.replace("p.zz", "p.a"), "p") == [
        (4, "GenericConstraintParam", 4), (5, "GenericConstraintParam", 5)]


def test_a_parameter_hides_a_field_of_the_same_name():
    """It used to bind to the field."""
    code = """\
struct S {
  rand bit[8] v; rand bit[8] w;
  constraint g(bit[8] v) { v < w; }
  constraint { g(w); }
}
"""
    assert markers(code) == []
    assert bindings(code, "v") == [(3, "GenericConstraintParam", 3)]


def test_a_parameter_is_not_in_scope_outside_the_body():
    code = """\
struct S {
  rand bit[8] w;
  constraint g(bit[8] v) { v < 3; }
  constraint { v == w; }
}
"""
    assert markers(code) == [
        ("error", 4, "unknown identifier 'v'; did you mean 'S'?")]


def test_an_enum_parameter_is_the_expected_type():
    """No PSS046: the parameter's enum is the expected type (8.4.3)."""
    code = """\
enum e_t {A, B};
struct S {
  rand e_t x;
  constraint g(e_t v) { v == B; v != A; }
  constraint { g(x); }
}
"""
    assert markers(code) == []


def test_numeric_parameters():
    code = """\
struct S {
  rand bit[8] v1;
  constraint g(numeric n, const numeric m) { n < m; }
  constraint { g(v1, 4); }
}
"""
    assert markers(code) == []
    assert bindings(code, "n") == [(3, "GenericConstraintParam", 3)]


def test_a_static_generic_constraint():
    code = """\
struct S {
  rand bit[8] x;
  static constraint g(bit[8] v) { v < 3; }
  constraint { g(x); }
}
"""
    assert markers(code) == []


def test_a_list_parameter_and_foreach():
    """The body used to be wrapped in a ConstraintScope of its own, which a
    path to the iterator did not step into: `e` was left unbound."""
    code = """\
import std_pkg::*;
struct S {
  rand list<bit[8]> l1;
  constraint g(list<bit[8]> l) {
    l.size() > 2;
    foreach (e : l) { e < 10; }
    l[0] == 1;
  }
  constraint { g(l1); }
}
"""
    assert markers(code) == []


def test_a_parameter_in_an_extension():
    code = P + """\
struct S { rand P p1; }
extend struct S {
  constraint g(P p) { p.a > 1; }
  constraint { g(p1); }
}
"""
    assert markers(code) == []
    assert bindings(code, "p") == [(4, "GenericConstraintParam", 4)]


def test_a_parameter_in_a_parameterized_type():
    code = P + """\
struct S <int W = 4> {
  rand P p1;
  constraint g(P p) { p.a < W; p.nosuch == 0; }
  constraint { g(p1); }
}
struct T { S<8> s; }
"""
    assert [m for m in markers(code) if m[0] == "error"] == [
        ("error", 4, "Failed to find elem nosuch")]


def test_a_package_scope_generic_constraint():
    code = P + """\
package pk {
  static constraint gt(P p, numeric x) { p.a > x; }
}
"""
    assert markers(code) == []
    assert bindings(code, "p") == [(3, "GenericConstraintParam", 3)]


# ---------------------------------------------------------------------------
# LRM examples
# ---------------------------------------------------------------------------


def test_example_139_value_yielding():
    code = """\
constraint numeric max(numeric a, numeric b)
  (a < b)?b:a;
struct S {
  rand bit[8] j, k, l;
  constraint j == max(k,l);
}
"""
    assert markers(code) == []
    assert [b[1] for b in bindings(code, "a")] == ["GenericConstraintParam"] * 2


def test_example_140_recursive():
    code = """\
import std_pkg::*;
package p {
  constraint gt_a_list_elem(
    bit[64] val,
    list<bit[64]> l) {
    gt_a_list_elem_inner(val, l, 0);
  }
  constraint gt_a_list_elem_inner(
    bit[64] val,
    list<bit[64]> l,
    const bit[64] idx) {
    if (idx+1 < l.size()) {
      (val > l[idx]) || gt_a_list_elem_inner(val, l, idx+1);
    } else {
      (val > l[idx]);
    }
  }
}
"""
    assert markers(code) == []
    assert {b[1] for b in bindings(code, "idx")} == {"GenericConstraintParam"}


def test_example_150_forall_in_a_generic_constraint():
    code = """\
struct S {
  rand bit[8] x;
};
component pss_top {
  action A {
    rand S s1, s2;
  };
  action B {
    constraint c1() {
      forall (it: S) { it.x != 0xff; }
    }
    activity { do A; }
  };
  action entry {
    activity {
      do B;
      do B with { c1(); };
    }
  };
}
"""
    assert markers(code) == []
