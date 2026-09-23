"""
`super` (symbol-resolution plan 5.2, the `super` half).

`super.x` was looked up like a plain `x`: lexically, from the innermost scope
outward. So the derived type's own `x` won over the base's, `super.f(1)` was
arity-checked against the derived `f`, and in a type with no base at all
`super.a` quietly found whatever `a` the enclosing scopes had.

Now `super.x` searches the context type's base type, and what the base
inherits, and nothing else (17.1, Table 27). The context type is the one
`this` names, so inside `a with { ... }` it is the containing action. A
`super;` statement in a type with no base is reported too: there is no base
activity or exec block for it to run.
"""
import pytest

import pssparser
from pssparser import refs

from ..test_helpers import parse_collect
from .test_activity_scopes import assert_links_and_binds


def errors(code):
    _, markers = parse_collect(code)
    return [(m["code"], m["message"]) for m in markers
            if m["severity"] == "error"]


def bindings(code, name):
    """(line, col) of each use of `name` -> (line, col) of its declaration."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return sorted((o.line, o.col, o.decl_location[1:3])
                  for o in refs.occurrences(p)
                  if o.text == name and not o.is_declaration)


# ---------------------------------------------------------------------------
# Legal uses link cleanly, and every reference in them resolves.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [
    # A shadowed field, in a constraint and in an exec.
    """component pss_top {
  struct B { rand int x; }
  struct D : B { rand int x; constraint super.x < x; exec post_solve { x = super.x; } }
}""",
    # Inherited from further up the chain.
    """component pss_top {
  struct B0 { rand int x; }
  struct B : B0 { }
  struct D : B { rand int x; constraint super.x < x; }
}""",
    # An instance function, statement and expression form (Table 27).
    """component base_c { function int f(int x) { return x; } function void g(int x) { } }
component d_c : base_c {
  function int f() { return super.f(1) + 1; }
  function void g() { super.g(1); }
}""",
    # A field of an action, from inside a `with` on a sub-action.
    """component pss_top {
  action A { rand int f; }
  action W : A { rand int f; A a; activity { a with { f == super.f; }; } }
}""",
    # From an extension of the derived type.
    """component pss_top {
  action A { rand int f; }
  action A2 : A { rand int f; }
  extend action A2 { constraint super.f > 0; }
}""",
    # Member of the base reached through `super.`.
    """component pss_top {
  struct S { rand int z; }
  struct B { rand S s; }
  struct D : B { constraint super.s.z == 1; }
}""",
    # `super;` in activities and exec blocks of derived types.
    """component pss_top {
  action A { activity { } exec body { } }
  action A2 : A { activity { super; } exec body { super; } }
  monitor M { activity { } }
  monitor M2 : M { activity { super; } }
  struct N { exec pre_solve { } }
  struct N2 : N { exec pre_solve { super; } }
}""",
])
def test_legal_super_uses_bind(tmp_path, code):
    assert_links_and_binds(tmp_path, code)


def test_lrm_example_284():
    assert errors("""
import std_pkg::*;
component pss_top {
  action A {
    int a;
    exec pre_solve { a=1; }
    exec body { std_pkg::message(LOW,"Hello from A %d", a); }
  }
  action A1 : A {
    exec body { super; std_pkg::message(LOW,"Hello from A1 %d", a); }
  }
  action A2 : A {
    exec body { std_pkg::message(LOW,"Hello from A2 %d", a); super; }
  }
}""") == []


def test_super_field_binds_to_the_base_field():
    assert bindings("""\
component pss_top {
  struct B { rand int x; }
  struct D : B {
    rand int x;
    constraint super.x < x;
  }
}
""", "x") == [(5, 22, (2, 23)), (5, 26, (4, 14))]


def test_super_call_binds_to_the_base_function():
    assert bindings("""\
component base_c { function void g(int x) { } }
component d_c : base_c {
  function void g() { super.g(1); }
}
""", "g") == [(3, 29, (1, 34))]


def test_inherited_super_field_binds_through_the_chain():
    assert bindings("""\
component pss_top {
  struct B0 { rand int x; }
  struct B : B0 { }
  struct D : B { rand int x; constraint super.x < 1; }
}
""", "x") == [(4, 47, (2, 24))]


def test_super_in_a_with_block_names_the_containing_actions_base():
    """`this` there is the containing action, and so `super` is its base."""
    assert bindings("""\
component pss_top {
  action A { rand int f; }
  action B { rand int f; }
  action W : B { A a; activity { a with { f == super.f; }; } }
}
""", "f") == [(4, 43, (2, 23)), (4, 54, (3, 23))]


# ---------------------------------------------------------------------------
# Misuse
# ---------------------------------------------------------------------------

def test_super_in_a_type_with_no_base():
    """It no longer falls back on an enclosing scope's `a`."""
    assert errors("""
component pss_top {
  int a;
  struct S { rand int b; constraint super.a == 1; }
}""") == [("PSS002", "'super' is only valid inside a type that has a base "
                     "type, and 'S' has none")]


def test_super_call_in_a_component_with_no_base():
    assert errors("""
component e_c { function void g() { super.f(); } function void f() { } }
""") == [("PSS002", "'super' is only valid inside a type that has a base "
                     "type, and 'e_c' has none")]


def test_super_names_a_member_the_base_does_not_have():
    assert errors("""
component pss_top {
  struct B { rand int a; }
  struct D : B { constraint super.nosuch == 1; }
}""") == [("PSS002", "base type 'B' has no member named 'nosuch'")]


def test_super_names_a_member_of_the_derived_type_only():
    assert errors("""
component pss_top {
  struct B { rand int a; }
  struct D : B { rand int c; constraint super.c == 1; }
}""") == [("PSS002", "base type 'B' has no member named 'c'; 'c' is declared "
                     "in 'D' itself, so refer to it without 'super.'")]


def test_super_call_arity_is_checked_against_the_base():
    assert errors("""
component base_c { function void g(int x) { } }
component d_c : base_c { function void g(int x, int y) { super.g(x, y); } }
""") == [("PSS006", "too many arguments to 'g': expected 1, got 2")]


def test_super_outside_a_type():
    assert errors("""
package p { function int f() { return super.x; } }
""") == [("PSS002", "'super' is only valid inside a type: an action, "
                     "component, struct or other type body")]


def test_unknown_base_type_is_not_reported_again():
    assert [c for c, _ in errors("""
component pss_top { struct D : nosuch_t { constraint super.a == 1; } }
""")] == ["PSS002"]


@pytest.mark.parametrize("code,name", [
    ("action A3 { activity { super; } }", "A3"),
    ("monitor M3 { activity { super; } }", "M3"),
    ("struct N3 { exec pre_solve { super; } }", "N3"),
])
def test_super_statement_in_a_type_with_no_base(code, name):
    assert errors("component pss_top { %s }" % code) == [
        ("PSS002", "'super;' is only valid inside a type that has a base "
                   "type, and '%s' has none" % name)]
