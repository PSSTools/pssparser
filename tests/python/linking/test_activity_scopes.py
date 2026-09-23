"""
Activity scopes (symbol-resolution plan WS4.1 with WS2.6; LRM 11.8.2, 11.8.3).

Every activity block is a scope for variables, and so is every compound
statement: a loop owns its index and iterator, and a handle belongs to the
block it is declared in. Before this:

- the builder hoisted every activity handle into the action, so two blocks
  each declaring `a` collided (F7, LRM Ex. 122 and 124);
- loop variables were injected as `int` fields into a braced body only, so a
  brace-less body could not see its index (F9, LRM Ex. 113), and the variable
  leaked into the whole activity (N2);
- nested blocks had no address, so every name resolved inside one recorded a
  path that led nowhere -- bound on paper, unbound to every consumer (RC1,
  A-N11, L-9).

The last is why most tests here also check that each reference's recorded
path resolves: a clean link is not enough on its own.
"""
import sys
from pathlib import Path

import pytest

from ..test_helpers import parse_collect

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from refcov import _walk_file  # noqa: E402


def refs_of(tmp_path, code):
    """(clean, [(field, class, state)]) for every reference in `code`, where
    state is bound, unbound or dead (a path that resolves to nothing)."""
    fn = tmp_path / "t.pss"
    fn.write_text(code)
    r = _walk_file(str(fn))
    return r["clean"], r["refs"]


def assert_links_and_binds(tmp_path, code):
    root, markers = parse_collect(code)
    errors = [m for m in markers if m["severity"] == "error"]
    assert not errors, "\n".join(
        "%s:%s %s" % (m["line"], m["col"], m["message"]) for m in errors)
    clean, refs = refs_of(tmp_path, code)
    assert clean
    bad = [r for r in refs if r[2] != "bound"]
    assert not bad, bad


def error_messages(code):
    _, markers = parse_collect(code)
    return [m["message"] for m in markers if m["severity"] == "error"]


def wrap(activity, fields=""):
    return """
component pss_top {
    action A { rand int v; }
    action B {
        rand int x;
        %s
        activity {
            %s
        }
    }
}
""" % (fields, activity)


# ---------------------------------------------------------------------------
# F7 -- a block is a scope for the handles declared in it
# ---------------------------------------------------------------------------


def test_lrm_example_122_legal_part(tmp_path):
    """Ex. 122 without its deliberately conflicting second `L2`: two unnamed
    blocks may each declare `a`."""
    assert_links_and_binds(tmp_path, wrap("""
            L1: parallel {
                if (x > 10) {
                    L2: {
                        A a;
                        a;
                    }
                    {
                        A a; // OK - a separate naming scope for variables
                        a;
                    }
                }
            }
    """))


def test_lrm_example_124_blocks_shadow_the_action_handle(tmp_path):
    """Ex. 124's action B: an action-level `a` and three activity-level ones,
    each in its own block."""
    assert_links_and_binds(tmp_path, """
component pss_top {
    action A { rand int x; }
    action B {
        A a;
        activity {
            a;
            my_seq: sequence {
                A a;
                a;
                parallel {
                    my_rep: repeat (3) {
                        A a;
                        a;
                    };
                    sequence {
                        A a;
                        a;
                    };
                };
            };
        };
    };
}
""")


def test_handle_is_a_child_of_its_block():
    """The AST says where a handle is declared: not in the action."""
    root, _ = parse_collect(wrap("sequence { A a; a; }"))
    comp = [c for c in root.getChildren() if type(c).__name__ == "SymbolTypeScope"
            and c.getName() == "pss_top"][0]
    b = [c for c in comp.getChildren() if type(c).__name__ == "SymbolTypeScope"
         and c.getName() == "B"][0].getTarget()
    assert not [c for c in b.getChildren() if type(c).__name__ == "ActionHandleField"]
    act = [c for c in b.getChildren() if type(c).__name__ == "ActivityDecl"][0]
    seq = act.getChildren()[0]
    assert type(seq).__name__ == "ActivitySequence"
    assert [type(c).__name__ for c in seq.getChildren()][0] == "ActionHandleField"


@pytest.mark.parametrize("stmt", [
    "if (x > 0) { A a; a with { v == 1; }; } else { A a; a; }",
    "select { { A b; b; } { A b; b with { v < 2; }; } }",
    "match (x) { [0]: { A c; c; } default: { A c; c; } }",
    "repeat { A d; d; } while (x < 3);",
    "atomic { A e; e; }",
    "schedule { A f; f; } parallel { A f; f; }",
])
def test_compound_statement_bodies_are_scopes(tmp_path, stmt):
    assert_links_and_binds(tmp_path, wrap(stmt))


def test_a_duplicate_in_one_block_is_still_reported():
    errs = error_messages(wrap("sequence { A a; A a; a; }"))
    assert any("duplicate declaration of 'a'" in e for e in errs), errs


def test_a_top_activity_handle_is_not_visible_in_the_action_scope():
    """11.8.3: "the top activity scope is unnamed", so a handle declared in it
    cannot be referenced from the action. Hoisting handles into the action
    used to make it visible."""
    errs = error_messages(wrap("A a; a;", fields="constraint a.v == 1;"))
    assert any("unknown identifier 'a'" in e for e in errs), errs


def test_a_handle_is_not_visible_after_its_block():
    # Named in a constraint: an unknown *traversal* target is still silent
    # (U7), which the traversal rewrite (WS4.2) fixes.
    errs = error_messages(wrap("sequence { A a; a; } constraint { a.v == 1; }"))
    assert any("unknown identifier 'a'" in e for e in errs), errs


# ---------------------------------------------------------------------------
# F9, N2 -- a loop owns its variables
# ---------------------------------------------------------------------------


def test_lrm_example_113_brace_less_replicate_body(tmp_path):
    """`replicate (i: 4) do A with {...}`: the body is a traversal, with no
    block to have put the index in."""
    assert_links_and_binds(tmp_path, """
component pss_top {
    action A { rand int f1; }
    action B {
        activity {
            replicate (i: 4) do A with { f1 == i; };
        }
    }
}
""")


@pytest.mark.parametrize("loop", [
    "repeat (i : 3) do A with { v == i; };",
    "repeat (i : 3) { do A with { v == i; }; }",
    "foreach (e : arr) do A with { v == e; };",
    "foreach (e : arr) { do A with { v == e; }; }",
    "foreach (arr[j]) do A with { v == j; };",
    "foreach (e : arr[j]) { do A with { v == e + j; }; }",
    "replicate (k : 2) { do A with { v == k; }; }",
])
def test_loop_variable_is_visible_in_every_body_form(tmp_path, loop):
    assert_links_and_binds(tmp_path, wrap(loop, fields="rand int arr[4];"))


def test_a_loop_variable_is_not_visible_after_the_loop():
    errs = error_messages(wrap(
        "repeat (i : 3) { do A; } do A with { v == i; };"))
    assert any("unknown identifier 'i'" in e for e in errs), errs


def test_sibling_loops_may_reuse_a_name(tmp_path):
    assert_links_and_binds(tmp_path, wrap(
        "repeat (i : 3) { do A with { v == i; }; }"
        " repeat (i : 2) { do A with { v == i; }; }"))


def test_a_loop_variable_may_shadow_a_field(tmp_path):
    assert_links_and_binds(tmp_path, wrap(
        "repeat (x : 3) { do A with { v == x; }; }"))


def test_foreach_iterator_over_handles_is_a_handle(tmp_path):
    """K3: the iterator takes the element type, so traversing it resolves its
    `with` block in the action type."""
    code = wrap("foreach (h : hs) { h with { v == 1; }; }", fields="A hs[3];")
    assert_links_and_binds(tmp_path, code)
    errs = error_messages(
        wrap("foreach (h : hs) { h with { nosuch == 1; }; }", fields="A hs[3];"))
    assert any("nosuch" in e for e in errs), errs


def test_foreach_collection_does_not_see_the_loop_variables():
    errs = error_messages(wrap(
        "foreach (e : arr[e]) { do A; }", fields="rand int arr[4];"))
    assert errs, "the collection resolved against its own iterator"


# ---------------------------------------------------------------------------
# Monitors and symbols -- the same model
# ---------------------------------------------------------------------------


def test_monitor_blocks_are_scopes(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
    action A { rand int x; }
    monitor M {
        A a;
        activity {
            a;
            S: sequence { A a; a; }
            concat { A b; b; }
        }
    }
}
""")


def test_symbol_body_blocks_are_scopes(tmp_path):
    assert_links_and_binds(tmp_path, """
component pss_top {
    action A { rand int v; }
    action B {
        symbol s (A p) {
            sequence { A a; a with { v == 1; }; }
            parallel { A a; a; p; }
        }
        A q;
        activity { s(q); }
    }
}
""")
