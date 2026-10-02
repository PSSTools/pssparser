"""Every constraint statement is located (pssc request P2, widened).

pssc asked for `dist` only, because it reports locations only for the
statements it refuses. Probing showed that expression, `if`, implication and
`foreach` statements had no location either. Only `unique`, `soft` and the
two `default` forms did. The builder now locates every statement a constraint
body item adds, from the item's first token through its last.
"""
import inspect
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import pssparser.ast as P  # noqa: E402
from test_helpers import parse_collect  # noqa: E402

#: class name -> (constraint body text, column of its first token).
#: Each is put on line 6 of _model.
CASES = {
    "ConstraintStmtExpr": "x < 3;",
    "ConstraintStmtImplication": "x > 1 -> y == 2;",
    "ConstraintStmtIf": "if (x > 1) { y == 2; } else { y == 1; }",
    "ConstraintStmtForeach": "foreach (arr[i]) { arr[i] < 3; }",
    "ConstraintStmtForall": "forall (a_it: A) { a_it.v < 4; }",
    "ConstraintStmtUnique": "unique { x, y };",
    "ConstraintStmtSoft": "soft x == 3;",
    "ConstraintStmtDist": "dist x in [0..3 := 1, 4 := 5];",
    "ConstraintStmtDefault": "default x == 3;",
    "ConstraintStmtDefaultDisable": "default disable x;",
}

#: Not statements a constraint body holds on its own.
NOT_A_STATEMENT = {
    "ConstraintStmt", "ConstraintScope", "ConstraintBlock",
    "GenericConstraintDeclBool", "ConstraintStmtField",
}

_ROOTS = []


def _model(body, multiline=False):
    if multiline:
        body = body.replace(" ", "\n            ", 1)
    return ("component pss_top {\n"
            "    action A { rand int v; }\n"
            "    action T {\n"
            "        rand int x; rand int y; rand int arr[4];\n"
            "        constraint c1 {\n"
            f"            {body}\n"
            "        }\n"
            "        activity { do A; }\n"
            "    }\n"
            "}\n")


def _first_stmt(src):
    root, markers = parse_collect(src)
    assert root is not None, markers
    _ROOTS.append(root)

    def find(n):
        if type(n).__name__ == "ConstraintBlock":
            return n
        if hasattr(n, "numChildren"):
            for i in range(n.numChildren()):
                r = find(n.getChild(i))
                if r is not None:
                    return r
        if hasattr(n, "getTarget") and type(n).__name__ == "SymbolTypeScope":
            return find(n.getTarget())
        return None

    def comp_children(n):
        return [n.getChild(i) for i in range(n.numChildren())]

    for c in comp_children(root):
        if type(c).__name__ == "SymbolTypeScope" and c.getName() == "pss_top":
            for a in comp_children(c):
                if type(a).__name__ == "SymbolTypeScope" and a.getName() == "T":
                    blk = find(a)
                    return blk.getConstraint(0)
    raise AssertionError("constraint c1 not found")


def _classes():
    return sorted(n for n, c in vars(P).items()
                  if inspect.isclass(c) and issubclass(c, P.ConstraintStmt))


def test_every_constraint_statement_is_accounted_for():
    missing = [n for n in _classes() if n not in CASES and n not in NOT_A_STATEMENT]
    assert not missing, f"constraint statements with no location case: {missing}"


@pytest.mark.parametrize("name", sorted(CASES))
def test_a_constraint_statement_is_located(name):
    stmt = _first_stmt(_model(CASES[name]))
    assert type(stmt).__name__ == name
    loc, end = stmt.getLocation(), stmt.getEndLocation()
    assert (loc.lineno, loc.linepos) == (6, 13), name
    assert end is not None and end.lineno == 6, name


@pytest.mark.parametrize("name", ["ConstraintStmtDist", "ConstraintStmtExpr",
                                  "ConstraintStmtIf", "ConstraintStmtForeach"])
def test_the_end_location_reaches_the_last_line(name):
    stmt = _first_stmt(_model(CASES[name], multiline=True))
    assert stmt.getLocation().lineno == 6
    assert stmt.getEndLocation().lineno == 7, name


def test_nested_statements_are_located():
    stmt = _first_stmt(_model("if (x > 1) { y == 2; } else { y == 1; x < 2; }"))
    for branch in (stmt.getTrue_c(), stmt.getFalse_c()):
        for i in range(branch.numConstraints()):
            c = branch.getConstraint(i)
            assert c.getLocation().lineno == 6, type(c).__name__
            assert c.getLocation().linepos > 13
