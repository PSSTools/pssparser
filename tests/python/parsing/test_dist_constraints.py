"""
Distribution directive `dist` (plan item P1-G3, Annex B B.14).

Two defects, one on top of the other:

1. ``dist_item`` was spelled ``open_range_value TOK_LSBRACE dist_weight
   TOK_RSBRACE`` -- literal square brackets around the weight. The BNF's
   ``[ dist_weight ]`` marks *optional content*, not delimiters, so the grammar
   demanded a syntax no conforming source would ever contain and rejected every
   real `dist` directive.

2. ``dist_directive`` had no builder visitor and no AST node, so even source
   that had somehow parsed would have been silently discarded during AST
   construction.

Because of (2), the AST-shape assertions below are not incidental coverage --
they are the regression net for the silent-drop, which no parse-only test can
detect.

Note ``getItems()`` is not used: the generated Cython accessor appends the
return value of ``accept()`` (which is void), yielding a list of ``None``. The
singular ``getItem(i)`` uses the correct pattern. This affects every
list-of-node property in the bindings, not just this one.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402

from pssparser import Parser  # noqa: E402


def _wrap(constraint_body):
    return """
    component pss_top {
        action A {
            rand bit[8] k;
            rand bit[8] j;
            constraint c { %s }
        }
    }
    """ % constraint_body


# AST wrappers do not keep their owning Parser alive; see
# test_numeric_literals_31 for the same guard.
_LIVE_PARSERS = []


def _dist_nodes(constraint_body):
    """Parse `constraint_body` and return every ConstraintStmtDist node built."""
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", _wrap(constraint_body))])

    found = []
    seen = set()

    def visit(node):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        if type(node).__name__ == "ConstraintStmtDist":
            found.append(node)
        try:
            kids = list(node.children())
        except Exception:
            kids = []
        for k in kids:
            visit(k)
        if hasattr(node, "numConstraints") and hasattr(node, "getConstraint"):
            try:
                n = node.numConstraints()
            except Exception:
                n = 0
            for i in range(n):
                visit(node.getConstraint(i))

    for scope in parser._files[1:]:
        visit(scope)
    return found


def _items(dist_node):
    """Return [(lhs, rhs, weight, is_dividing)] for a dist node's items."""
    out = []
    for n in range(dist_node.numItems()):
        item = dist_node.getItem(n)
        rng = item.getRange()
        weight = item.getWeight()
        out.append((
            rng.getLhs().getValue() if rng.getLhs() else None,
            rng.getRhs().getValue() if rng.getRhs() else None,
            weight.getExpr().getValue() if weight else None,
            weight.getIs_dividing() if weight else None,
        ))
    return out


# =============================================================================
# Parsing
# =============================================================================

@pytest.mark.parametrize("body", [
    "dist k in [0 := 10, 1 := 20];",
    "dist k in [0..3 :/ 30];",
    "dist k in [0 := 10, 1..3 :/ 30, 7];",
    "dist k in [0, 1, 2];",
    "dist k in [0..7];",
    "dist k in [0];",
    "dist k in [0 := 10];",
    "dist k in [0..3 := 10, 4..7 := 20];",
])
def test_dist_parses(body):
    assert_parse_ok(_wrap(body))


def test_dist_target_may_be_hierarchical():
    assert_parse_ok("""
    struct S { rand bit[8] v; }
    component pss_top {
        action A {
            rand S s;
            constraint c { dist s.v in [0 := 10, 1 := 20]; }
        }
    }
    """)


def test_dist_weight_may_be_an_expression():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand bit[8] k;
            constraint c { dist k in [0 := 2 * 5, 1 := 20 + 1]; }
        }
    }
    """)


def test_multiple_dist_directives_in_one_constraint():
    nodes = _dist_nodes("dist k in [0 := 10]; dist j in [1 := 20];")
    assert len(nodes) == 2


@pytest.mark.parametrize("body", [
    "dist k in [0 [:= 10]];",   # the literal-bracket form the old rule required
    "dist k in [];",            # empty distribution list
    "dist k in [0 :=];",        # weight operator with no expression
    "dist k [0 := 10];",        # missing `in`
    "dist k in [0 := 10]",      # missing `;`
])
def test_malformed_dist_rejected(body):
    assert_parse_error(_wrap(body))


# =============================================================================
# AST shape -- guards the silent-drop regression
# =============================================================================

def test_dist_builds_an_ast_node():
    """
    Before this change `dist` produced no AST node at all. A parse-only
    assertion would still pass in that state, so assert the node exists.
    """
    assert len(_dist_nodes("dist k in [0 := 10, 1 := 20];")) == 1


def test_dist_records_target_expression():
    node = _dist_nodes("dist k in [0 := 10];")[0]
    assert node.getLhs() is not None
    assert type(node.getLhs()).__name__ == "ExprRefPathContext"


def test_dist_records_every_item():
    node = _dist_nodes("dist k in [0 := 10, 1 := 20, 2 := 30];")[0]
    assert node.numItems() == 3


def test_dist_single_value_item():
    (lhs, rhs, weight, dividing), = _items(_dist_nodes("dist k in [5 := 10];")[0])
    assert (lhs, rhs) == (5, None)
    assert weight == 10
    assert dividing is False


def test_dist_range_item():
    (lhs, rhs, _, _), = _items(_dist_nodes("dist k in [1..3 := 10];")[0])
    assert (lhs, rhs) == (1, 3)


def test_dist_weightless_item_has_no_weight_node():
    """An item with no weight carries the default (1); it must not fabricate one."""
    (_, _, weight, dividing), = _items(_dist_nodes("dist k in [7];")[0])
    assert weight is None
    assert dividing is None


def test_dist_distinguishes_assign_from_divide_weights():
    """
    `:=` weights each value in the range; `:/` divides the weight across the
    range. The two mean different things and are not recoverable from the
    expression alone, so the AST must keep them apart.
    """
    items = _items(_dist_nodes("dist k in [0 := 10, 1..3 :/ 30];")[0])
    assert items[0][3] is False, ":= must not be recorded as dividing"
    assert items[1][3] is True, ":/ must be recorded as dividing"


def test_dist_mixed_item_kinds_in_order():
    items = _items(_dist_nodes("dist k in [0 := 10, 1..3 :/ 30, 7];")[0])
    assert items == [
        (0, None, 10, False),
        (1, 3, 30, True),
        (7, None, None, None),
    ]
