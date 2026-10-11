"""The lint walk and dispatch (lint-core-plan.md C5.1; pss-rules-format.md §3.2).

`lint_walk` loads a rule file and walks the given GlobalScopes with it,
reporting every (rule, node) match in walk order without evaluating
`where:`. Each match carries the node's ancestors, nearest first, read back
from the parent map the walk records.
"""
import pytest

_MODEL = (
    "component pss_top {\n"                 # 1
    "  int cf;\n"                           # 2
    "  action A {\n"                        # 3
    "    rand int a;\n"                     # 4
    "    constraint c { a > 0; }\n"         # 5
    "    activity { }\n"                    # 6
    "  }\n"                                 # 7
    "  action B : A { }\n"                  # 8
    "}\n")

_OTHER = (
    "component other_c {\n"
    "  action C { rand int c; }\n"
    "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def units():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL), ("other.pss", _OTHER)])
    # The standard library's unit comes first, then the files in order.
    return p, p._files[-2], p._files[-1]


def _rules(*rules):
    """A rule file from (id, match) pairs; `match` is YAML flow text."""
    out = ["pss-rules:", "  version: 1", "  defaults: { tier: style }", "  rules:"]
    for i, (rid, match) in enumerate(rules):
        out += ["    - id: %s" % rid,
                "      name: rule-%d" % i,
                "      summary: s",
                "      message: m",
                "      match: %s" % match]
    return "\n".join(out) + "\n"


def _walk(hooks, units, *rules, roots=None):
    r = hooks.lint_walk("r.yaml", _rules(*rules), roots or [units[1]])
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    return r


def _hits(r):
    return [(m["rule"], m["kind"], m["line"]) for m in r["matches"]]


def test_dispatch_order_is_walk_order_then_load_order(hooks, units):
    r = _walk(hooks, units,
              ("ACME002", "{ kind: Field }"),
              ("ACME001", "{ kind: [Action, Field] }"))
    # Pre-order over the tree; at one node, rules in the order they loaded.
    assert _hits(r) == [
        ("ACME002", "Field", 2), ("ACME001", "Field", 2),
        ("ACME001", "Action", 3),
        ("ACME002", "Field", 4), ("ACME001", "Field", 4),
        ("ACME001", "Action", 8),
    ]


def test_rule_matching_two_kinds_fires_once_per_node(hooks, units):
    # Action derives from TypeScope: naming both must not fire twice.
    r = _walk(hooks, units, ("ACME001", "{ kind: [TypeScope, Action] }"))
    hits = _hits(r)
    assert len(hits) == len(set(hits))
    assert ("ACME001", "Action", 3) in hits
    assert ("ACME001", "Component", 1) in hits


def test_subclasses_match(hooks, units):
    r = _walk(hooks, units, ("ACME001", "{ kind: Expr }"))
    kinds = {m["kind"] for m in r["matches"]}
    assert {"ExprBin", "ExprId", "ExprUnsignedNumber", "ExprRefPathContext"} <= kinds
    assert "Field" not in kinds


def test_inside(hooks, units):
    r = _walk(hooks, units, ("ACME001", "{ kind: Field, inside: { kind: Action } }"))
    # The component's field `cf` is not inside an action.
    assert _hits(r) == [("ACME001", "Field", 4)]


def test_inside_with_stop(hooks, units):
    r = _walk(hooks, units,
              ("ACME001", "{ kind: ExprBin, inside: { kind: Component, stop: Action } }"),
              ("ACME002", "{ kind: ExprBin, inside: { kind: ConstraintBlock, stop: Action } }"),
              ("ACME003", "{ kind: ExprBin, inside: { kind: Action, stop: Action } }"))
    # ACME001: the search stops at the action before reaching the component.
    # ACME003: a stop kind's node is tested first, so the nearest action counts.
    assert [m["rule"] for m in r["matches"]] == ["ACME002", "ACME003"]


def test_not_inside(hooks, units):
    r = _walk(hooks, units,
              ("ACME001", "{ kind: Field, not_inside: { kind: Action } }"),
              ("ACME002", "{ kind: Field, not_inside: { kind: Action, stop: Field } }"))
    # A stop kind that is never an ancestor bounds nothing.
    assert _hits(r) == [("ACME001", "Field", 2), ("ACME002", "Field", 2)]


def test_not_inside_bounded_by_stop(hooks, units):
    # A stop below the excluded kind hides it: `int` fields' types are
    # searched up to their Field, never reaching the action.
    r = _walk(hooks, units,
              ("ACME001", "{ kind: DataTypeInt, not_inside: { kind: Action, stop: Field } }"))
    assert [m["ancestors"][1] for m in r["matches"]] == ["Component", "Action"]


def test_parent_map(hooks, units):
    r = _walk(hooks, units, ("ACME001", "{ kind: ExprBin }"))
    (m,) = r["matches"]
    assert m["ancestors"] == ["ConstraintStmtExpr", "ConstraintBlock", "Action",
                              "Component", "GlobalScope"]


def test_root_is_visited_and_has_no_parent(hooks, units):
    r = _walk(hooks, units, ("ACME001", "{ kind: GlobalScope }"))
    assert [(m["kind"], m["ancestors"]) for m in r["matches"]] == [("GlobalScope", [])]


def _census(hooks, unit):
    """The census's node count, less what the walk leaves out: each action's
    implicit `comp` (a FieldCompRef and, unlinked, its name; Walker::implicit)."""
    c = hooks.reflect_census(unit)
    return c["count"] - 2 * c["classes"].get("FieldCompRef", 0)


def test_each_owned_node_is_visited_once(hooks, units):
    # The census walks the same owned children: the counts agree, so a
    # reference (B's base type, resolved to A) is not followed.
    r = _walk(hooks, units, ("ACME001", "{ kind: Action }"))
    assert r["visited"] == _census(hooks, units[1])
    assert [m["line"] for m in r["matches"]] == [3, 8]


def test_node_not_owned_by_the_run_is_not_visited(hooks, units):
    rule = ("ACME001", "{ kind: Action }")
    only_top = _walk(hooks, units, rule)
    both = _walk(hooks, units, rule, roots=[units[1], units[2]])
    assert [m["line"] for m in only_top["matches"]] == [3, 8]
    assert [m["line"] for m in both["matches"]] == [3, 8, 2]
    assert both["visited"] == (_census(hooks, units[1])
                               + _census(hooks, units[2]))
    # The standard library's unit is never a root, so nothing in it fires.
    assert all(m["ancestors"][-1] == "GlobalScope" for m in both["matches"])


def test_root_given_twice_is_walked_once(hooks, units):
    r = _walk(hooks, units, ("ACME001", "{ kind: Action }"), roots=[units[1], units[1]])
    assert [m["line"] for m in r["matches"]] == [3, 8]


def test_no_rules_still_walks(hooks, units):
    r = hooks.lint_walk("r.yaml", "pss-rules:\n  version: 1\n  rules: []\n", [units[1]])
    assert r["matches"] == []
    assert r["visited"] == _census(hooks, units[1])


def test_deep_expression_does_not_recurse(hooks):
    # The walk is iterative: a long chain of binary operators is fine.
    from pssparser.parser import Parser
    p = Parser()
    chain = " + ".join(["1"] * 3000)
    p.parses([("deep.pss", "component pss_top { int x = %s; }\n" % chain)])
    r = hooks.lint_walk("r.yaml", _rules(("ACME001", "{ kind: ExprBin }")), [p._files[-1]])
    assert len(r["matches"]) == 2999
