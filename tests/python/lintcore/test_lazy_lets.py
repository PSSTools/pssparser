"""`let:` is evaluated when first read (lint-framework-plan F3.5; C8 follow-up).

A rule's lets used to be evaluated for every matched node before `where:`.
Now each is evaluated the first time `where:`, `report:` or the message
reads it, and kept for the rest of that node:

- a let nothing reads costs nothing, and its error does not matter;
- a let only the message reads is evaluated only for a finding;
- a let first read inside a comprehension sees the rule's variables, not
  the comprehension's;
- a let read twice is evaluated once.
"""
import pytest

from test_findings import _MODEL, _file, _rule


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def units():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL)])
    return p, p._files[-1]


def _run(hooks, units, *rules):
    r = hooks.lint_run("r.yaml", _file(*rules), [units[1]])
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    return r


def _steps(r, rid="ACME001"):
    return {s["rule"]: s for s in r["stats"]}[rid]["steps"]


# A let that costs a few hundred steps: descendants of the action, twice.
_COSTLY = "descendants(node).map(d, descendants(d)).map(l, size(l))"


def test_an_unread_let_costs_nothing(hooks, units):
    plain = _run(hooks, units, _rule(extra=["where: node.name.id == 'A'"]))
    unread = _run(hooks, units, _rule(extra=["let:", "  big: " + _COSTLY,
                                             "where: node.name.id == 'A'"]))
    assert _steps(unread) == _steps(plain)
    assert [f["line"] for f in unread["findings"]] == [3]


def test_an_unread_error_does_not_matter(hooks, units):
    r = _run(hooks, units, _rule(extra=["let:", "  bad: size(node.super_t.elems) > 0",
                                        "where: node.name.id == 'A'"]))
    assert r["failures"] == [] and [f["line"] for f in r["findings"]] == [3]


def test_a_message_only_let_is_evaluated_for_findings_only(hooks, units):
    # where: is false for B, so B's let is never evaluated.
    one = _run(hooks, units, _rule(message="${size(big)}",
                                   extra=["let:", "  big: " + _COSTLY,
                                          "where: node.name.id == 'A'"]))
    both = _run(hooks, units, _rule(message="${size(big)}",
                                    extra=["let:", "  big: " + _COSTLY]))
    assert len(one["findings"]) == 1 and len(both["findings"]) == 2
    assert _steps(one) < _steps(both)


def test_a_let_sees_the_rules_variables_not_a_comprehensions(hooks, units):
    # `n` is first read inside a comprehension whose variable is also
    # `node`: n is still the action's name.
    r = _run(hooks, units, _rule(message="${n}", extra=[
        "let:", "  n: node.name.id",
        "where: \"['x'].exists(node, n == 'A')\""]))
    assert [(f["line"], f["msg"]) for f in r["findings"]] == [(3, "A")]


def test_a_let_read_twice_is_evaluated_once(hooks, units):
    once = _run(hooks, units, _rule(extra=["let:", "  big: " + _COSTLY,
                                           "where: size(big) > 0"]))
    twice = _run(hooks, units, _rule(extra=["let:", "  big: " + _COSTLY,
                                            "where: size(big) > 0 && size(big) > 0"]))
    # The second read costs the read, not the evaluation.
    assert _steps(twice) - _steps(once) < 20


def test_later_lets_use_earlier_ones(hooks, units):
    r = _run(hooks, units, _rule(message="${b}", extra=[
        "let:", "  a: node.name.id", "  b: a + a",
        "where: b == 'AA'"]))
    assert [(f["line"], f["msg"]) for f in r["findings"]] == [(3, "AA")]
