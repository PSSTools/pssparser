"""AST-builder defects that dropped or misplaced declarations (symbol-resolution
plan WS2).

Each of these was a construct the builder silently lost, so the linker never
saw it: every test pairs a legal use that must now link with an illegal one that
must now be reported.  Root causes are in
``docs/design/symbol-resolution/B-builtins.md`` (F13, super) and
``C-activity-scopes.md`` (F8 cause 1).
"""
import pytest

from ..test_helpers import assert_marker, assert_parse_ok, parse_collect, find_markers


# ---------------------------------------------------------------------------
# 2.1 -- `action` data fields (F13, C-N1): the declaration was never built
# ---------------------------------------------------------------------------

def test_action_field_in_action_body_is_declared():
    """LRM Ex. 173: an `action` field is visible to constraints and traversals."""
    assert_parse_ok("""
component pss_top {
  action A { rand bit[4] a; }
  action B {
    action bit[4] a_bit;
    A a_1;
    constraint a_bit < 3;
    activity { a_1 with { a < a_bit; }; }
  }
}
""")


def test_action_field_in_activity_is_declared():
    """LRM Ex. 83: `action bit[8] max;` inside the activity, used in a `with`."""
    assert_parse_ok("""
component pss_top {
  action A { rand bit[8] f1; }
  action B {
    A a1;
    activity {
      action bit[8] max;
      a1 with { f1 <= max; };
    }
  }
}
""")


def test_action_field_with_unknown_type_is_reported():
    assert_marker("""
component pss_top { action B { action nosuch_t a; } }
""", marker_id="PSS002", text="unknown type 'nosuch_t'")


def test_action_field_duplicate_is_reported():
    assert_marker("""
component pss_top { action B { action bit[4] b; rand int b; } }
""", marker_id="PSS003", text="'b'")


# ---------------------------------------------------------------------------
# 2.2 -- labels on repeat/if/foreach/atomic (F8(1), C-N6): the body used to
# consume the label before the statement claimed it
# ---------------------------------------------------------------------------

LABELLED = [
    "L: repeat (2) { a; }",
    "L: repeat { a; } while (1);",
    "L: if (1) { a; }",
    "L: if (1) { a; } else { a; }",
    "L: foreach (arr[i]) { a; }",
    "L: atomic { a; }",
    "L: select { a; a; }",
    "L: match (1) { [1]: a; default: a; }",
]


@pytest.mark.parametrize("stmt", LABELLED)
def test_statement_label_survives_a_labelled_body(stmt):
    """A second `L` in the same activity collides only if the first `L` exists.

    The body holds a nested labelled statement (`X:`), which is what used to
    take and then clear the outer label.
    """
    body = stmt.replace("{ a; }", "{ X: a; }", 1)
    root, markers = parse_collect("""
component pss_top {
  action A { }
  action B {
    A a; A arr[2];
    activity {
      %s
      L: a;
    }
  }
}
""" % body)
    dups = find_markers(markers, marker_id="PSS003")
    assert dups, "the label on %r was lost" % stmt
    assert "'L'" in dups[0]["message"], dups[0]["message"]


def test_join_branch_names_a_labelled_if():
    """LRM 10.5.2: join_branch names a labelled top-level branch."""
    assert_parse_ok("""
component pss_top {
  action A { }
  action B {
    A a; A b;
    activity {
      parallel join_branch(L) {
        L: if (1) { a; }
        b;
      }
    }
  }
}
""")


def test_duplicate_label_names_the_label():
    """PSS003 used to read "duplicate declaration of ''" for a label (12.2)."""
    assert_marker("""
component pss_top {
  action A { }
  action B {
    A a;
    activity {
      L: sequence { a; }
      L: parallel { a; }
    }
  }
}
""", marker_id="PSS003", text="duplicate declaration of 'L'")


# ---------------------------------------------------------------------------
# 2.4 -- `super.f();` as a statement (B super): the `super` was dropped
# ---------------------------------------------------------------------------

def _count_super_refs(root):
    import pssparser.ast as ast_mod
    found = []

    class _W(ast_mod.VisitorBase):
        def visitExprRefPathSuper(self, i):
            found.append(i)
            super().visitExprRefPathSuper(i)

    root.accept(_W())
    return len(found)


@pytest.mark.parametrize("call", ["super.g(1);", "(void)super.g(1);"])
def test_super_call_statement_builds_a_super_reference(call):
    """The statement form builds ExprRefPathSuper, as the expression form does.

    The binding to the *base* `g` is pinned by the next test and by
    linking/test_super.py.
    """
    root = assert_parse_ok("""
component base_c { function void g(int x) { } }
component d_c : base_c {
  function void g(int x) { %s }
}
""" % call)
    assert _count_super_refs(root) > 0  # the symbol-tree walk reaches a body more than once


def test_super_call_binds_to_the_base_function():
    """It bound to the derived `g`, and was arity-checked against it (5.2)."""
    assert_parse_ok("""
component base_c { function void g(int x) { } }
component d_c : base_c {
  function void g() { super.g(1); }
}
""")


def test_plain_call_statement_is_not_a_super_reference():
    root = assert_parse_ok("""
component c {
  function void g(int x) { }
  function void h() { g(1); }
}
""")
    assert _count_super_refs(root) == 0


# ---------------------------------------------------------------------------
# 2.3 -- dropped by the builder: action-body handle initializers (F-N2), enum
# domains (F-N3, pinned in parsing/test_grammar_fixes.py with F2), and a
# subscript on a static path (F-N6)
# ---------------------------------------------------------------------------

def test_action_body_handle_initializer_value_is_resolved():
    """`A a {.x = v};` in an action body parses as data; its list was dropped."""
    assert_marker("""
component pss_top {
  action A { rand bit[4] x; }
  action B { A a2 {.x = nosuch}; }
}
""", marker_id="PSS002", text="'nosuch'")


def test_action_body_handle_initializer_is_accepted():
    assert_parse_ok("""
component pss_top {
  action A { rand bit[4] x; }
  action B { rand bit[4] v; A a2 {.x = v}; activity { a2; } }
}
""")


def test_static_path_subscript_is_kept():
    """`p::S::K[NOSUCH]` built as `p::S::K`, so the index was never seen."""
    assert_marker("""
package p { struct S { static const int K[2] = {1, 2}; } }
component pss_top {
  action A { rand int x; constraint { x == p::S::K[NOSUCH]; } }
}
""", marker_id="PSS002", text="'NOSUCH'")


@pytest.mark.parametrize("expr", ["p::S::K[1]", "p::S::K[i]", "::p::S::K[0]", "p::S::W[3:0]"])
def test_static_path_subscript_forms_link(expr):
    assert_parse_ok("""
package p { struct S { static const int K[2] = {1, 2}; static const bit[8] W = 3; } }
component pss_top {
  action A { rand int x; rand int i; constraint { x != %s; } }
}
""" % expr)
