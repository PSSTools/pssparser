"""Named constraints and symbols as members (symbol-resolution plan WS5.4, WS4.4).

A named constraint was added to its type's scope *unnamed*, so a duplicate went
unnoticed and a `dynamic` constraint could not be found by name.  A symbol's
parameters were in no scope at all, and a symbol call was never visited.
Root causes: ``docs/design/symbol-resolution/B-builtins.md`` ("Dynamic and fixed
constraints", P7-X5 S1/S2).
"""
import pytest

from ..test_helpers import assert_marker, assert_parse_ok, parse_collect, find_markers


# ---------------------------------------------------------------------------
# 5.4 -- named constraints
# ---------------------------------------------------------------------------

def test_duplicate_named_constraint_is_reported():
    assert_marker("""
component pss_top {
  action A { rand int x; constraint c { x > 1; } constraint c { x < 5; } }
}
""", marker_id="PSS003", text="duplicate declaration of 'c'")


def test_constraint_named_like_a_field_is_reported():
    """18.3: member names are unique across kinds."""
    assert_marker("""
component pss_top {
  action A { rand int x; constraint x { x < 3; } }
}
""", marker_id="PSS003", text="duplicate declaration of 'x'")


def test_named_constraint_may_shadow_a_base_constraint():
    """13.1.3: a subtype's `c` shadows the supertype's `c`."""
    assert_parse_ok("""
struct B { rand int x; constraint c { x > 1; } }
struct D : B { constraint c { x < 5; } }
""")


def test_dynamic_constraint_may_be_referenced():
    assert_parse_ok("""
component pss_top {
  action A {
    rand int x;
    dynamic constraint dc { x > 1; }
    constraint { dc; }
  }
}
""")


def test_anonymous_constraints_do_not_collide():
    assert_parse_ok("""
struct S { rand int x; constraint { x > 1; } constraint { x < 5; } }
""")


# ---------------------------------------------------------------------------
# 4.4 -- symbols
# ---------------------------------------------------------------------------

def test_symbol_parameter_is_in_scope():
    """`symbol s(A aa) { aa with {...}; }` -- the `with` resolves in aa's type."""
    assert_parse_ok("""
component c {
  action A { rand bit[4] x; }
  action top {
    A a1;
    symbol s (A aa) { aa with { x < 3; }; }
    activity { s(a1); }
  }
}
""")


def test_symbol_parameter_with_block_is_checked():
    assert_marker("""
component c {
  action A { rand bit[4] x; }
  action top {
    A a1;
    symbol s (A aa) { aa with { nosuch < 3; }; }
    activity { s(a1); }
  }
}
""", marker_id="PSS002", text="'nosuch'")


def test_symbol_parameter_type_is_resolved():
    assert_marker("""
component c {
  action top {
    symbol s (nosuch_t aa) { aa; }
  }
}
""", marker_id="PSS002", text="'nosuch_t'")


@pytest.mark.parametrize("call,marker_id,text", [
    ("nosuch(a1);", "PSS002", "unknown identifier 'nosuch'"),
    ("v(a1);", "PSS006", "'v' is not a symbol"),
    ("s(a1, a1);", "PSS006", "call to 's' expects 1 argument, got 2"),
    ("s();", "PSS006", "call to 's' expects 1 argument, got 0"),
    ("z(a1);", "PSS006", "call to 'z' expects 0 arguments, got 1"),
    ("s(zz);", "PSS002", "'zz'"),
])
def test_symbol_call_is_checked(call, marker_id, text):
    assert_marker("""
component c {
  action A { }
  action top {
    A a1; rand int v;
    symbol s (A aa) { aa; }
    symbol z { a1; }
    activity { %s }
  }
}
""" % call, marker_id=marker_id, text=text)


def test_symbol_calls_link():
    """LRM Ex. 120, plus the call forms with and without arguments."""
    assert_parse_ok("""
component entity {
  action a { } action b { } action c { }
  action top {
    a a1, a2; b b1, b2; c c1;
    symbol a_or_b { select { a1; b1; } select { a2; b2; } }
    symbol one (a x) { x; }
    activity { a_or_b; a_or_b(); one(a1); c1; }
  }
}
""")
