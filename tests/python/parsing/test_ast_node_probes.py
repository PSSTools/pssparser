"""AST-node probes for the pssparser-detox effort (docs/pssparser-detox-plan.md).

Unlike the sibling parsing tests, which only assert ``assert_parse_ok`` plus
symbol presence, these probes walk the *pre-link* AST (``parser._files``) and
assert that each construct actually produces the expected AST node with the
expected fields. They are the regression net for the grammar / AST-builder
changes the detox plan introduces.

Constructs that the parser does NOT yet surface are marked
``xfail(strict=True)`` with a ``# DETOX:`` note naming the plan phase that fixes
them. When the fix lands, the test XPASSes -> strict xfail turns that into a
hard failure, which is the signal to drop the marker. Do not delete an xfail
marker without making its body pass.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss  # noqa: E402


# ---------------------------------------------------------------------------
# Pre-link AST walking helpers
# ---------------------------------------------------------------------------

def _find_nodes(parser, type_name):
    """Return all pre-link AST nodes whose class name == type_name.

    Walks ``parser._files`` (skipping index 0, the builtin/stdlib scope). Note
    that ``children()`` does *not* descend into constraint-statement lists, so we
    also follow ``numConstraints()``/``getConstraint()`` on constraint scopes.
    """
    found = []
    seen = set()

    def visit(node):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))
        if type(node).__name__ == type_name:
            found.append(node)
        try:
            kids = list(node.children())
        except Exception:
            kids = []
        for k in kids:
            visit(k)
        # Constraint scopes (ConstraintBlock, ConstraintStmtForeach/Forall, ...)
        # expose their body via numConstraints()/getConstraint(), not children().
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


def _parse_only(code, parser):
    """Parse without linking; return the parser (for pre-link AST inspection)."""
    parser.parses([("test.pss", code)])
    return parser


# ---------------------------------------------------------------------------
# 1. forall  ->  ConstraintStmtForall   (DETOX Phase A1 / builder gap)
# ---------------------------------------------------------------------------
# Grammar accepts `forall`, but visitForall_constraint_item is a TODO stub in
# AstBuilderInt.cpp, so no ConstraintStmtForall node is built today.

FORALL_SRC = """
struct S { rand int v; }
component pss_top {
    action A {
        rand S arr[4];
        constraint c { forall (it : S in arr) { it.v < 10; } }
    }
}
"""


@pytest.mark.xfail(strict=True, reason="DETOX B0: forall builder needs linker resolution work — see plan §6 B0")
def test_forall_builds_node(parser):
    # NOTE: the builder change alone is easy, but merely producing a
    # ConstraintStmtForall node makes the linker's ref-resolution passes
    # (TaskResolveEnumRef/TaskResolveRootRef) infinitely recurse resolving the
    # quantified type. B0 must also fix forall resolution in the linker.
    p = _parse_only(FORALL_SRC, parser)
    nodes = _find_nodes(p, "ConstraintStmtForall")
    assert len(nodes) == 1
    fa = nodes[0]
    # iterator_id, type_id, ref_path are the populated fields
    assert fa.getIterator_id().getId() == "it"
    assert fa.getType_id() is not None
    assert fa.getRef_path() is not None
    # body constraint(s) preserved
    assert fa.numConstraints() >= 1


# ---------------------------------------------------------------------------
# 4. do X with {}  ->  ActivityActionTypeTraversal.with_c   (DETOX Phase A2)
# ---------------------------------------------------------------------------
# This one already works: the inline constraint is captured in the AST today.

DO_WITH_SRC = """
component pss_top {
    action A { rand int x; }
    action B { A a; activity { do A with { x < 5; x > 0; } } }
}
"""


def test_do_with_inline_constraints_present(parser):
    p = _parse_only(DO_WITH_SRC, parser)
    travs = _find_nodes(p, "ActivityActionTypeTraversal")
    assert len(travs) == 1
    with_c = travs[0].getWith_c()
    assert with_c is not None, "do..with{} inline constraints dropped"
    assert with_c.numConstraints() == 2


# ---------------------------------------------------------------------------
# 5. pool [N]  ->  (no AST node today)   (DETOX Phase B1)
# ---------------------------------------------------------------------------
# The pool declaration is fully absorbed during build; no AST node carries the
# size N. There is no ComponentPool AST class yet, so we probe by asserting the
# component body has a child node mentioning the pool. Marked xfail until B1.

POOL_SRC = """
buffer Buf { int x; }
component pss_top {
    pool [4] Buf bufp;
    bind bufp *;
}
"""


def test_pool_size_reaches_ast(parser):
    # DETOX B1: pool now builds a FieldPool node carrying the size literal.
    p = _parse_only(POOL_SRC, parser)
    pools = _find_nodes(p, "FieldPool")
    assert len(pools) == 1
    fp = pools[0]
    assert fp.getName().getId() == "bufp"
    assert fp.getType() is not None
    size = fp.getSize()
    assert size is not None and size.getValue() == 4


def test_pool_unsized_has_no_size(parser):
    # An unsized pool builds the node with size==None.
    p = _parse_only("buffer Buf { int x; } component pss_top { pool Buf bufp; }", parser)
    pools = _find_nodes(p, "FieldPool")
    assert len(pools) == 1
    assert pools[0].getSize() is None


# ---------------------------------------------------------------------------
# 2/3. covergroup + cross  ->  (no AST node today)   (DETOX Phase B2)
# ---------------------------------------------------------------------------
# Grammar accepts the inline covergroup with cross, but there is no builder and
# no Covergroup AST class, so nothing is produced.

COVERGROUP_SRC = """
component pss_top {
    action A {
        rand int x; rand int y;
        covergroup {
            cp_x : coverpoint x;
            cp_y : coverpoint y;
            cr : cross cp_x, cp_y;
        } cg_inst;
    }
}
"""


@pytest.mark.xfail(strict=True, reason="DETOX B2: no covergroup builder/AST class; node absorbed")
def test_covergroup_builds_node(parser):
    p = _parse_only(COVERGROUP_SRC, parser)
    cgs = _find_nodes(p, "Covergroup") or _find_nodes(p, "CovergroupInst")
    assert len(cgs) >= 1


# ---------------------------------------------------------------------------
# 7. fill  ->  syntax error today   (DETOX Phase C1)
# ---------------------------------------------------------------------------
# `fill` is not a keyword; the snippet is a hard parse error. When C1 adds the
# token+rule+node, this should parse and build an ActivityFill node.

FILL_SRC = """
component pss_top {
    action A { activity { fill { do B; } } }
    action B {}
}
"""


@pytest.mark.xfail(strict=True, reason="DETOX C1: 'fill' not in grammar; parse error")
def test_fill_builds_node(parser):
    p = _parse_only(FILL_SRC, parser)
    # No parse error expected once C1 lands.
    assert len(_find_nodes(p, "ActivityFill")) == 1
