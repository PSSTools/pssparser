"""A `;` after a traversal is not a `select` branch (known-issues LE-6).

`inline_constraints_or_empty ::= with constraint_set | ;` (Syntax 40), so in
`do A with { x < 5; };` the trailing `;` is not part of the traversal, and
the grammar reads it as a statement of its own (`stmt_terminator`, Syntax
39). In a `select` that made it a branch that does nothing, chosen as often
as the real ones. Writing the `;` is common practice, so the builder treats
a bare `;` as a terminator. An empty branch is written `{ }`; a `;` with a
guard or a weight was written as a branch and stays one. `parallel` and
`schedule` never made a branch of a bare `;`.
"""
import pytest

_SRC = ("component pss_top {\n"
        "  action Sub { rand bit[4] x; }\n"
        "  action A {\n"
        "    rand bit[4] m;\n"
        "    activity {\n"
        "      select { do Sub with { x < 5; }; do Sub with { x > 9; }; }\n"
        "      select { do Sub; do Sub; (m > 2): ; [2]: { } }\n"
        "      parallel { do Sub with { x < 5; }; do Sub; }\n"
        "      schedule { do Sub with { x < 5; }; do Sub with { x > 1; }; }\n"
        "      select { do Sub with { x < 5; }; }\n"
        "    }\n"
        "  }\n"
        "}\n")


@pytest.fixture(scope="module")
def counts(factory):
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("a.pss", _SRC)])
    root = p.link()
    (unit,) = p.user_units()
    r = factory._lintTestHooks().cel_check_node({"expr": (
        "descendants(node).filter(d, d.isa(ActivitySelect) || d.isa(ActivityParallel)"
        " || d.isa(ActivitySchedule)).map(s, size(branches(s)))")}, unit, model=root)
    assert r["errors"] == []
    return [e["value"] for e in r["values"]["expr"]["value"]]


def test_terminators_are_not_branches(counts):
    assert counts[0] == 2


def test_a_guarded_or_braced_empty_branch_stays(counts):
    assert counts[1] == 4


def test_parallel_and_schedule(counts):
    assert counts[2:4] == [2, 2]


def test_one_traversal_and_its_terminator_is_one_branch(counts):
    assert counts[4] == 1
