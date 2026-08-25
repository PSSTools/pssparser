"""
Tests for PSS 3.1 soft constraints (P3-C1, LRM §13.1.12, Annex B B.14).

A soft constraint states a preference rather than a requirement: it is
discarded when it conflicts with a hard constraint, an active default
constraint, or a higher-priority soft constraint.

The solver semantics are out of scope for a parser, but one parser obligation
follows directly from them. §13.1.12 derives relative priority from *position
in the model* -- nothing in the source says "this one outranks that one" -- so
the AST must preserve declaration order exactly. `ConstraintStmt.index` is what
records it, and the ordering assertions below are the real content of this
module.

Note on lexing: `soft` is now a reserved word. Annex B spells it literally, but
Table 3 (the keyword table) omits it; we treat that as an error in the table
rather than in the BNF, consistent with how every other BNF-literal word is
handled. The consequence is a source-level break for models using `soft` as an
identifier -- see test_soft_is_a_reserved_word.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []


def _constraints(body, decl=""):
    """Parse an action whose constraint block is `body`; return its statements.

    `decl` is prepended inside the action for extra field declarations.
    """
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", """
    component pss_top {
        action A {
            rand int x;
            rand int y;
            %s
            constraint c {
                %s
            }
        }
    }
    """ % (decl, body))])
    assert not parser.markers, [m for m in parser.markers]

    for scope in parser._files[1:]:
        for comp in scope.children():
            for action in comp.children():
                if type(action).__name__ != "Action":
                    continue
                for item in action.children():
                    if type(item).__name__ == "ConstraintBlock":
                        return [item.getConstraint(i)
                                for i in range(item.numConstraints())]
    raise AssertionError("no ConstraintBlock found")


# -- syntax -----------------------------------------------------------------

@pytest.mark.parametrize("stmt", [
    "soft x > 10;",
    "soft x < 100;",
    "soft x == 5;",
    "soft x in [1..10];",
    "soft x in [1, 2, 3];",
    # NB: not `inside`. Example160 in the LRM writes `soft y inside [5..9];`,
    # but Annex B B.15 has no `inside` operator -- PSS spells set membership
    # `in`. The example contradicts the normative BNF; we follow the BNF.
    "soft x > 10 && y < 5;",
    "soft (x + y) == 20;",
])
def test_soft_constraint_parses(stmt):
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            rand int y;
            constraint c { %s }
        }
    }
    """ % stmt)


def test_soft_constraint_in_unnamed_constraint():
    """`constraint soft x > 10;` -- constraint_set admits a single item."""
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            constraint soft x > 10;
        }
    }
    """)


def test_soft_constraint_in_struct():
    assert_parse_ok("""
    struct S {
        rand int x;
        constraint c { soft x > 10; }
    }
    """)


def test_soft_constraint_in_monitor_constraint():
    """B.14 lists soft_constraint_item under monitor constraints too."""
    assert_parse_ok("""
    component pss_top {
        action A { }
        monitor M {
            A a;
            constraint c { soft 1 == 1; }
        }
    }
    """)


def test_soft_constraint_nested_in_if():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            rand int y;
            constraint c {
                if (x > 0) {
                    soft y == 1;
                } else {
                    soft y == 2;
                }
            }
        }
    }
    """)


def test_soft_constraint_nested_in_foreach():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int arr[4];
            constraint c {
                foreach (arr[i]) {
                    soft arr[i] > 0;
                }
            }
        }
    }
    """)


def test_soft_constraint_in_implication_body():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            rand int y;
            constraint c { x > 0 -> { soft y == 1; } }
        }
    }
    """)


# -- AST shape --------------------------------------------------------------

def test_soft_constraint_builds_a_soft_node():
    stmts = _constraints("soft x > 10;")
    assert [type(s).__name__ for s in stmts] == ["ConstraintStmtSoft"]


def test_soft_constraint_carries_its_expression():
    stmt = _constraints("soft x > 10;")[0]
    assert type(stmt.getExpr()).__name__ == "ExprBin"


def test_hard_and_soft_constraints_build_different_nodes():
    """A soft constraint must not degrade into a plain expression statement."""
    stmts = _constraints("x > 10; soft x < 100;")
    assert [type(s).__name__ for s in stmts] == \
        ["ConstraintStmtExpr", "ConstraintStmtSoft"]


# -- declaration order (the parser's actual obligation) ---------------------

def test_declaration_order_is_preserved():
    """
    §13.1.12 derives priority from position, so index must track source order.
    If these were reordered the model would silently mean something else.
    """
    stmts = _constraints("""
        soft x > 10;
        soft x < 100;
        soft x == 50;
    """)
    assert [s.getIndex() for s in stmts] == [0, 1, 2]


def test_soft_constraints_are_indexed_among_hard_constraints():
    """Index counts every statement in the scope, not just the soft ones."""
    stmts = _constraints("""
        x > 0;
        soft x > 10;
        y > 0;
        soft x < 100;
    """)
    kinds = [type(s).__name__ for s in stmts]
    assert kinds == ["ConstraintStmtExpr", "ConstraintStmtSoft",
                     "ConstraintStmtExpr", "ConstraintStmtSoft"]
    assert [s.getIndex() for s in stmts] == [0, 1, 2, 3]

    soft_indices = [s.getIndex() for s in stmts
                    if type(s).__name__ == "ConstraintStmtSoft"]
    assert soft_indices == [1, 3], \
        "relative order of the soft constraints was not preserved"


def test_index_distinguishes_otherwise_identical_soft_constraints():
    """
    Two soft constraints with the same expression differ only in priority, and
    priority comes only from position -- so index is the sole thing telling
    them apart.
    """
    stmts = _constraints("soft x > 10; soft x > 10;")
    assert len(stmts) == 2
    assert stmts[0].getIndex() == 0
    assert stmts[1].getIndex() == 1


# -- negative cases ---------------------------------------------------------

@pytest.mark.parametrize("stmt", [
    "soft;",              # no expression
    "soft x > 10",        # no terminating semicolon
    "soft soft x > 10;",  # doubled qualifier
])
def test_malformed_soft_constraint_rejected(stmt):
    assert_parse_error("""
    component pss_top {
        action A {
            rand int x;
            constraint c { %s }
        }
    }
    """ % stmt)


def test_soft_is_a_reserved_word():
    """
    A deliberate lexical break: `soft` cannot be an identifier any more.
    Recorded here so the cost of the Table 3 / Annex B conflict is visible
    rather than inferred from a confusing parse error downstream.
    """
    assert_parse_error("struct S { int soft; }")


def test_soft_is_not_permitted_outside_a_constraint():
    """`soft` qualifies a constraint item, not a procedural statement."""
    assert_parse_error("""
    component pss_top {
        action A {
            rand int x;
            exec post_solve { soft x > 10; }
        }
    }
    """)
