"""
Action traversals (symbol-resolution plan 4.2: U7/K6, U3).

A handle traversal's target was looked up by its root alone, and a miss was
silent: `nosuch;` in an activity linked cleanly. Whatever the target bound to,
the statement went on as if it were a handle, so traversing an `int` was
accepted too. And the `.x` side of an initializer list (`a {.x = 1}`) was never
resolved at all, on a traversal or on a handle declaration.

Now the target goes through the ordinary path resolver (PSS002 for an unknown
name), what it bound to is checked (PSS018 for something that cannot be
traversed, PSS117 for a deprecated `dynamic` constraint), and each initializer
path is resolved in the traversed type and nowhere else (11.3.1).
"""
import pytest

import pssparser
from pssparser import refs

from ..test_helpers import parse_collect
from .test_activity_scopes import assert_links_and_binds


def model(activity, fields="", extra=""):
    return """
component pss_top {
  struct S { rand int z; }
  action A { rand int x; rand bit[4] y; rand S s; }
  monitor M { }
  %s
  action T {
    rand int tx;
    %s
    activity {
      %s
    }
  }
}
""" % (extra, fields, activity)


def diagnostics(code):
    _, markers = parse_collect(code)
    return [(m["severity"], m["code"], m["message"]) for m in markers]


def errors(code):
    return [(c, msg) for sev, c, msg in diagnostics(code) if sev == "error"]


# ---------------------------------------------------------------------------
# Legal traversals link cleanly, and every reference in them resolves.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("activity,fields", [
    ("a1;", "A a1;"),
    ("a1 with { x == 1; };", "A a1;"),
    ("a1 {.x = tx, .s.z = 2};", "A a1;"),
    ("do A {.x = tx};", ""),
    ("a1;", "A a1 {.x = tx};"),
    ("A b {.x = 1}; b {.y = 2} with { x > 0; };", ""),
    ("aa[1] with { x == 1; }; aa[tx] {.x = 1};", "A aa[4];"),
    ("aa;", "A aa[4];"),
    ("foreach (e : aa) { e with { x == 1; }; }", "A aa[4];"),
    ("sy(a1);", "A a1; symbol sy(A h) { h with { x == 1; }; h {.x = 1}; }"),
    ("sy;", "A a1; symbol sy { a1; }"),
    ("gc;", "constraint gc() { tx > 0; }"),
    # Example 173: a data field with the `action` modifier is traversed.
    ("m;", "action bit[4] m;"),
    # The value side is resolved in the enclosing scope: `x` here is T's.
    ("a1 {.x = x};", "A a1; rand int x;"),
    ("a1 {.x = this.tx};", "A a1;"),
    ("T1: do A; T1 {.x = 1};", ""),
])
def test_legal_traversals_bind(tmp_path, activity, fields):
    assert_links_and_binds(tmp_path, model(activity, fields))


def test_monitor_handle_traversal(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
  monitor M { }
  monitor N { M mh; activity { mh; } }
}
""")


@pytest.mark.parametrize("name", ["ex83", "ex137", "ex173"])
def test_lrm_examples_link_cleanly(name):
    """The examples that 2.1, 5.4 and 4.4 had to land first for (plan §5)."""
    code = {
        "ex83": """
component pss_top {
  action A { rand bit[4] f1; }
  action B { A a1, a2; activity { a1; a2 with { f1 < 10; }; } }
  action C { action bit[4] max; B b1; activity { max; b1 with { a1.f1 <= max; }; } }
}""",
        "ex137": """
component pss_top {
  action B {
    action bit[32] addr;
    constraint dyn_addr1_c() { addr in [0x1000..0x1FFF]; }
    activity { addr; dyn_addr1_c; }
  }
}""",
        "ex173": """
component pss_top {
  action A { rand bit[4] a; }
  action B { action bit[4] a_bit; A a_1; constraint a_bit < 3; activity { a_bit; a_1; } }
}""",
    }[name]
    assert errors(code) == []


def test_lrm_example_120_symbol_traversal():
    assert errors("""
component entity {
  action a { } action b { } action c { }
  action top {
    a a1, a2, a3; b b1, b2, b3; c c1, c2, c3;
    symbol a_or_b { select {a1; b1; } select {a2; b2; } select {a3; b3; } }
    activity { a_or_b; c1; c2; c3; }
  }
}""") == []


# ---------------------------------------------------------------------------
# Unknown targets (U7/K6)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("activity", [
    "nosuch;",
    "sequence { nosuch; }",
    "parallel { nosuch; }",
    "nosuch with { x == 1; };",
    "nosuch {.x = 1};",
])
def test_unknown_target_is_reported(activity):
    assert errors(model(activity)) == [("PSS002", "unknown identifier 'nosuch'")]


def test_unknown_target_in_a_monitor_is_reported():
    assert errors("""
component pss_top { monitor M { } monitor N { M mh; activity { nosuch; } } }
""") == [("PSS002", "unknown identifier 'nosuch'")]


def test_unknown_target_in_a_symbol_body_is_reported():
    assert errors(model("sy;", "symbol sy { nosuch; }")) \
        == [("PSS002", "unknown identifier 'nosuch'")]


def test_unknown_subscript_is_reported():
    assert errors(model("aa[NOSUCH];", "A aa[4];")) \
        == [("PSS002", "unknown identifier 'NOSUCH'")]


def test_the_target_binds_to_its_declaration():
    p = pssparser.Parser()
    p.parses([("t.pss", """\
component pss_top {
  action A { }
  action T {
    A a1;
    activity { a1; }
  }
}
""")])
    p.link()
    uses = [o for o in refs.occurrences(p)
            if o.text == "a1" and not o.is_declaration]
    assert [(o.line, o.decl_location[1:3]) for o in uses] == [(5, (4, 7))]


# ---------------------------------------------------------------------------
# What the target bound to (PSS018, PSS117)
# ---------------------------------------------------------------------------

NOT_A_HANDLE = ("is not an action handle, and cannot be traversed; only a "
                "handle, or a data field declared with the 'action' modifier, "
                "can be")


@pytest.mark.parametrize("activity,fields,name", [
    ("tx;", "", "tx"),
    ("ss;", "S ss;", "ss"),
    ("foreach (i : ia) { i; }", "int ia[4];", "i"),
    ("repeat (i : 4) { i; }", "", "i"),
])
def test_a_variable_that_is_not_a_handle(activity, fields, name):
    assert errors(model(activity, fields)) \
        == [("PSS018", "'%s' %s" % (name, NOT_A_HANDLE))]


def test_a_type_is_not_a_handle():
    assert errors(model("A;")) == [
        ("PSS018", "'A' is a type, not an action handle; traverse it by type "
                   "with 'do A'")]


def test_a_block_label_is_not_a_handle():
    assert errors(model("L1: parallel { do A; do A; } L1;")) == [
        ("PSS018", "'L1' is an activity label, not an action handle, and "
                   "cannot be traversed")]


def test_do_on_a_type_that_is_not_an_action():
    assert errors(model("do S;")) == [
        ("PSS018", "'S' is not an action type, and cannot be traversed")]


def test_a_fixed_constraint_cannot_be_traversed():
    """Decision Q1: a fixed constraint always holds."""
    assert errors(model("fc;", "constraint fc { tx > 0; }")) == [
        ("PSS018", "'fc' is a fixed constraint, which always holds and cannot "
                   "be traversed; declare it as a generic constraint, "
                   "'constraint fc() { ... }', to apply it here")]


def test_a_dynamic_constraint_traversal_is_deprecated():
    assert diagnostics(model("dc;", "dynamic constraint dc { tx > 0; }")) == [
        ("warning", "PSS117",
         "traversal of dynamic constraint 'dc' is deprecated (13.1.1); "
         "declare it as a generic constraint, 'constraint dc() { ... }'")]


def test_unknown_handle_type_is_not_reported_again():
    """`nosuch_t` is reported at the declaration, not at each traversal."""
    assert [c for c, _ in errors(model("h;", "nosuch_t h;"))] == ["PSS002"]


# ---------------------------------------------------------------------------
# Initializer paths (U3)
# ---------------------------------------------------------------------------

NO_MEMBER = ("PSS002", "'A' has no member named 'nosuch'")


@pytest.mark.parametrize("activity,fields", [
    ("a1 {.nosuch = 1};", "A a1;"),
    ("do A {.nosuch = 1};", ""),
    ("a1;", "A a1 {.nosuch = 1};"),
    ("A b {.nosuch = 1}; b;", ""),
    ("aa[1] {.nosuch = 1};", "A aa[4];"),
])
def test_unknown_initializer_path_is_reported(activity, fields):
    assert errors(model(activity, fields)) == [NO_MEMBER]


def test_initializer_path_does_not_fall_back_to_the_enclosing_scope():
    """`.tx` names a member of A; T's own `tx` does not count."""
    assert errors(model("a1 {.tx = 1};", "A a1;")) \
        == [("PSS002", "'A' has no member named 'tx'")]


def test_nested_initializer_path_is_checked():
    assert [c for c, _ in errors(model("a1 {.s.nosuch = 1};", "A a1;"))] \
        == ["PSS002"]


def test_initializer_value_is_resolved_in_the_enclosing_scope():
    assert errors(model("a1 {.x = nosuch};", "A a1;")) \
        == [("PSS002", "unknown identifier 'nosuch'")]


def test_initializer_path_binds_to_the_member():
    p = pssparser.Parser()
    p.parses([("t.pss", """\
component pss_top {
  action A { rand int x; }
  action T {
    rand int x;
    A a1;
    activity { a1 {.x = x}; }
  }
}
""")])
    p.link()
    uses = [(o.line, o.col, o.decl_location[1:3])
            for o in refs.occurrences(p)
            if o.text == "x" and not o.is_declaration]
    # `.x` is A's field; the value `x` is T's.
    assert sorted(uses) == [(6, 21, (2, 23)), (6, 25, (4, 14))]
