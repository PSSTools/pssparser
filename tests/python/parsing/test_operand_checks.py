"""
Operand, argument and signature types (TaskCheckOperands; pssc's front-end
checks F4, F29, F30, F12 and F13), judged with the expression typer.

- PSS126: a cast from a chandle, struct, string or collection, or to a
  struct or collection type (7.12, 7.12.1).
- PSS127: `in` with a range list whose left side is not a scalar, or is an
  aggregate literal (8.5.9.1).
- PSS128: `==`/`!=` or assignment of an array of components or actions
  (7.9.2: only `[]`, `size()`, `foreach` and `in` apply).
- PSS006: an array argument of another size than its array parameter
  (8.3, 20.3.2).
- PSS129: a function returning, or taking, a component, action, or flow or
  resource object type without `ref` (20.2.2).

Each illegal case has a legal neighbour that must stay clean.
"""
import pytest

import pssparser

from ..test_helpers import _assign_codes


def markers(src):
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        ms = p.markers
    except Exception as e:
        ms = getattr(e, "markers", None)
        if ms is None:
            raise
    return [(m["line"], m.get("code"), m["message"]) for m in _assign_codes(ms)]


def codes(src):
    return [(line, code) for line, code, _ in markers(src)]


PRE = """\
import std_pkg::*;
enum col_e { RED, GREEN }
struct p_s { int a; }
buffer b_s { int a; }
component sub_c { int v; }
component pss_top {
  sub_c s[3], t[3];
  sub_c one;
  target function void run() {
    chandle h; string str; p_s v; int x; bit[8] b; bool q; col_e e;
    array<int, 2> w; float64 f;
    %s
  }
}
"""

LINE = 12


# ===========================================================================
# PSS126 -- casts
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    "x = (int)h;",
    "x = (int)v;",
    "x = (int)str;",
    "x = (int)w;",
    "v = (p_s)3;",
    "v = (p_s)v;",
])
def test_illegal_casts(stmt):
    assert codes(PRE % stmt) == [(LINE, "PSS126")]


@pytest.mark.parametrize("stmt", [
    "x = (int)b;",
    "x = (int)q;",
    "x = (int)e;",
    "x = (int)f;",
    "e = (col_e)x;",
    "q = (bool)x;",
    "b = (bit[8])v.a;",
    "x = (int)w[0];",
    "x = (int)str.size();",
    "f = (float64)x;",
])
def test_legal_casts(stmt):
    assert codes(PRE % stmt) == []


def test_cast_messages():
    [(_, _, from_msg)] = markers(PRE % "x = (int)h;")
    assert from_msg == ("a cast from chandle: only a numeric, Boolean or "
                        "enumeration value, or a reference, can be cast (LRM 7.12)")
    [(_, _, to_msg)] = markers(PRE % "v = (p_s)3;")
    assert to_msg == ("a cast to struct p_s: a casting type shall be a numeric, "
                      "Boolean, enumeration or reference type (LRM 7.12.1)")


# ===========================================================================
# PSS127 -- in with a range list
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    "if (v in [1]) { }",
    "if (w in [1, 2]) { }",
])
def test_in_with_a_non_scalar_left_side(stmt):
    assert codes(PRE % stmt) == [(LINE, "PSS127")]


@pytest.mark.parametrize("stmt", [
    "if (x in [1, 2..3]) { }",
    "if (e in [RED]) { }",
    "if (v.a in [1]) { }",
    'if (str in ["a", "b"]) { }',
    "if (x in w) { }",
])
def test_in_legal(stmt):
    assert codes(PRE % stmt) == []


# ===========================================================================
# PSS128 -- arrays of components
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    "if (s == t) { }",
    "if (s != t) { }",
    "s = t;",
])
def test_component_array_operators(stmt):
    assert codes(PRE % stmt) == [(LINE, "PSS128")]


@pytest.mark.parametrize("stmt", [
    "x = s.size();",
    "x = s[1].v;",
    "foreach (c : s) { x = c.v; }",
    "if (w == w) { }",
])
def test_component_array_legal(stmt):
    assert codes(PRE % stmt) == []


# ===========================================================================
# PSS006 -- array argument sizes
# ===========================================================================

SIZES = """\
component pss_top {
  function bit[8] sum(array<bit[8], 2> v) { return v[0] + v[1]; }
  target function void run() {
    array<bit[8], 3> w3; array<bit[8], 2> w2;
    %s
  }
}
"""


def test_an_array_argument_of_another_size():
    [(line, code, msg)] = markers(SIZES % "bit[8] r = sum(w3);")
    assert (line, code) == (5, "PSS006")
    assert msg == ("argument 1 of 'sum' is an array of 3 elements, but "
                   "parameter 'v' is an array of 2 (LRM 8.3)")


@pytest.mark.parametrize("stmt", ["bit[8] r = sum(w2);", "bit[8] r = sum(w2) + sum(w2);"])
def test_an_array_argument_of_the_same_size(stmt):
    assert codes(SIZES % stmt) == []


# ===========================================================================
# PSS129 -- signatures without ref
# ===========================================================================

SIG = """\
import std_pkg::*;
component sub_c { }
buffer b_s { int a; }
resource r_s { }
struct p_s { int a; }
component pss_top {
  sub_c sc;
  %s
}
"""


@pytest.mark.parametrize("decl", [
    "function sub_c g() { return sc; }",
    "function void f(sub_c c) { }",
    "function void f(b_s b) { }",
    "function void f(r_s r) { }",
    "function b_s g();",
])
def test_a_signature_without_ref(decl):
    assert codes(SIG % decl) == [(8, "PSS129")]


@pytest.mark.parametrize("decl", [
    "function ref sub_c g() { return sc; }",
    "function void f(ref sub_c c) { }",
    "function void f(ref b_s b) { }",
    "function void f(p_s p) { }",
    "function p_s g() { p_s r; return r; }",
])
def test_a_signature_with_ref(decl):
    assert codes(SIG % decl) == []


# ===========================================================================
# PSS131 -- operand types (8.4 Table 10, 8.3 Table 9, 7.7)
# ===========================================================================

OPS = """\
import std_pkg::*;
enum e_e { A, B }
component pss_top {
  target function void run() {
    int x, y; bit[8] b; bool p, q; chandle h, k; e_e e; float64 f;
    string s, t;
    %s
  }
}
"""


@pytest.mark.parametrize("stmt", [
    "if (p < q) { }",                 # relational on bool (8.5.2)
    "if (s < t) { }",                 # relational on string
    "if (x < y < 3) { }",             # bool compared with an int
    "p = ~p;",                        # bitwise on bool (8.5.5)
    "p = p & q;",
    "p &= false;",                    # Table 9
    "x = &p;",                        # reduction on bool
    "if (h == 1) { }",                # chandle with a non-zero literal (7.7)
    "h = h + 1;",                     # chandle arithmetic
    "x = f % 2;",                     # % on a float
    's = s + "c";',                   # no string + (W38)
    "q = !x;",                        # ! on an int
    "q = x && p;",                    # && on an int
    "x = x << p;",                    # a shift by a bool
    "s += t;",
])
def test_illegal_operand_types(stmt):
    assert [c for _, c in codes(OPS % stmt)] == ["PSS131"]


@pytest.mark.parametrize("stmt", [
    "if (x != 0) { }",
    "if (p == q) { }",
    "if (p && q) { }",
    "if (!p) { }",
    "if (h != 0) { }",
    "if (h == 0) { }",
    "if (h == k) { }",
    "y = p ? 1 : 2;",
    "if (e == A) { }",
    "if (e != B) { }",
    "x = b & 1; x = ~b; x = &b; x = x << 2; x = x % 3; x += 1;",
    "f = f + 1; f = f * 2.0; if (f < 1.5) { }",
    "if (s == t) { }",
    "if (x < y && y < 3) { }",
    'if (s in ["a"]) { }',
    "x = -x; f = -f;",
])
def test_legal_operand_types(stmt):
    assert codes(OPS % stmt) == []


def test_operand_message():
    [(_, _, msg)] = markers(OPS % "if (p < q) { }")
    assert msg == ("operator '<' takes numeric operands, not bool "
                   "(LRM 8.4 Table 10, 8.5.2)")


# ===========================================================================
# PSS132 -- conditions
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    "if (x) { }",
    "if (p) { } else if (x) { }",
    "while (x) { x -= 1; }",
    "repeat { x -= 1; } while (x);",
    "y = x ? 1 : 2;",
    "if (e) { }",
])
def test_a_condition_that_is_not_boolean(stmt):
    assert [c for _, c in codes(OPS % stmt)] == ["PSS132"]


@pytest.mark.parametrize("stmt", [
    "if (p) { }",
    "while (x > 0) { x -= 1; }",
    "repeat { x -= 1; } while (x != 0);",
    "y = (x == 1) ? 1 : 2;",
])
def test_a_boolean_condition(stmt):
    assert codes(OPS % stmt) == []


# ===========================================================================
# PSS133 -- null to a non-reference
# ===========================================================================

@pytest.mark.parametrize("stmt", ["int z = null;", "x = null;", "string u = null;"])
def test_null_to_a_value(stmt):
    assert [c for _, c in codes(OPS % stmt)] == ["PSS133"]


def test_null_to_a_chandle_is_not_judged():
    assert codes(OPS % "h = null; chandle z = null;") == []
