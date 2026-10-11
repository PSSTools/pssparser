"""Rule failures, the step budget and the gate (lint-core-plan.md C5.3;
lint-rule-expressions.md §5; lint-framework.md L8.1).

A rule whose `where:`, `report:` or message evaluates to an error, or that
uses up its step budget for a file, is one PSSP220/PSSP221 failure naming
the rule and the node, and is skipped for the rest of that file. Lint does
not run on a model with errors: one PSSP230 marker says so.
"""
import pytest

from test_findings import _MODEL, _file, _rule

_OTHER = (
    "component other_c {\n"                 # 1
    "  action C { }\n"                      # 2
    "  action D { }\n"                      # 3
    "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def units():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL), ("other.pss", _OTHER)])
    return p, p._files[-2], p._files[-1]


def _run(hooks, roots, *rules, **kw):
    r = hooks.lint_run("r.yaml", _file(*rules), roots, **kw)
    assert r["loaded"] and r["diagnostics"] == [], r["diagnostics"]
    return r


def _stats(r):
    return {s["rule"]: s for s in r["stats"]}


# Unset in A (no base), set in B: an error at A only.
_BAD_WHERE = "where: size(node.super_t.elems) > 0"


def test_an_erroring_rule_does_not_stop_the_others(hooks, units):
    r = _run(hooks, [units[1]],
             _rule("ACME001", extra=[_BAD_WHERE]),
             _rule("ACME002", message="${node}"))
    assert [(f["id"], f["msg"]) for f in r["findings"]] == [
        ("ACME002", "pss_top::A"), ("ACME002", "pss_top::B")]
    (f,) = r["failures"]
    assert (f["id"], f["rule"], f["in"], f["severity"]) == ("PSSP220", "ACME001", "where", "warning")
    assert (f["line"], f["col"]) == (3, 3)
    assert f["msg"].startswith("rule ACME001 (rule-acme001) failed in its where at Action 'pss_top::A': ")
    assert "super_t" in f["msg"]
    assert f["msg"].endswith("; the rule is skipped for the rest of this file")
    s = _stats(r)
    # Skipped after A: B is never evaluated.
    assert (s["ACME001"]["matches"], s["ACME001"]["errors"]) == (1, 1)
    assert (s["ACME002"]["matches"], s["ACME002"]["errors"]) == (2, 0)


def test_a_failure_is_per_file(hooks, units):
    # The rule fails once in each file that has an erroring node, and runs
    # again from the start of the next file.
    r = _run(hooks, [units[1], units[2]], _rule("ACME001", extra=[_BAD_WHERE]))
    assert [(f["rule"], f["line"]) for f in r["failures"]] == [("ACME001", 3), ("ACME001", 2)]
    s = _stats(r)["ACME001"]
    assert (s["matches"], s["errors"]) == (2, 2)


def test_report_error_fails_the_rule(hooks, units):
    r = _run(hooks, [units[1]], _rule(extra=["report: '[node.super_t.elems[0]]'"]))
    assert r["findings"] == []
    (f,) = r["failures"]
    assert (f["id"], f["in"], f["line"]) == ("PSSP220", "report", 3)


def test_message_error_keeps_the_finding_and_ends_the_file(hooks, units):
    # A's message fails (no base): its finding stands with `?`, and B is not
    # evaluated.
    r = _run(hooks, [units[1]], _rule(message="${node} base ${size(node.super_t.elems)}"))
    assert [f["msg"] for f in r["findings"]] == ["pss_top::A base ?"]
    (f,) = r["failures"]
    assert (f["in"], f["line"]) == ("message", 3)
    assert _stats(r)["ACME001"]["matches"] == 1


def test_let_error_fails_only_through_its_use(hooks, units):
    r = _run(hooks, [units[1]], _rule(message="${node}", extra=[
        "let:",
        "  base: node.super_t.elems",
        "where: \"node.name.id == 'B'\""]))
    assert [f["msg"] for f in r["findings"]] == ["pss_top::B"]
    assert r["failures"] == []


def _cost(hooks, units, rule):
    """Steps one evaluation of `rule` costs on each Field, with no budget."""
    r = _run(hooks, [units[1]], rule)
    s = r["stats"][0]
    assert s["matches"] == 3 and s["steps"] % 3 == 0
    return s["steps"] // 3


# A literal message: every step is the where:'s.
_FIELD = _rule(match="{ kind: Field }", message="f",
               extra=["where: node.name.id.size() > 0"])


def test_budget_trips_at_a_known_step_count(hooks, units):
    k = _cost(hooks, units, _FIELD)
    assert k > 0
    # Exactly enough for the three fields: no failure.
    r = _run(hooks, [units[1]], _FIELD, max_steps=3 * k)
    assert [f["line"] for f in r["findings"]] == [2, 4, 5]
    assert r["failures"] == []
    # One step short: the third field trips it.
    r = _run(hooks, [units[1]], _FIELD, max_steps=3 * k - 1)
    assert [f["line"] for f in r["findings"]] == [2, 4]
    (f,) = r["failures"]
    assert (f["id"], f["rule"], f["in"], f["line"]) == ("PSSP221", "ACME001", "where", 5)
    assert f["msg"] == (
        "rule ACME001 (rule-acme001) used its budget of %d evaluation steps for this "
        "file, in its where at Field 'pss_top::A::b'; the rule is skipped for the rest of this file"
        % (3 * k - 1))
    s = r["stats"][0]
    # Steps are counted up to the budget, not past it.
    assert (s["steps"], s["errors"], s["error_in"]) == (3 * k - 1, 1, "where")


def test_budget_is_per_file(hooks, units):
    # A rule on Action costs the same at every action: two actions per file
    # fit a budget of two evaluations in each file, though not in the run.
    rule = _rule(message="${node}", extra=["where: node.name.id.size() > 0"])
    r = _run(hooks, [units[1]], rule)
    k = r["stats"][0]["steps"] // 2
    r = _run(hooks, [units[1], units[2]], rule, max_steps=2 * k)
    assert [f["msg"] for f in r["findings"]] == [
        "pss_top::A", "pss_top::B", "other_c::C", "other_c::D"]
    assert r["failures"] == []
    assert r["stats"][0]["steps"] == 4 * k


def test_budget_shared_by_a_rules_expressions(hooks, units):
    # let, where and the message all draw on one budget: a budget too small
    # for the message trips there, and the finding is kept.
    rule = _rule(match="{ kind: Field }", message="${n + n}", extra=[
        "let:",
        "  n: node.name.id",
        "where: n.size() > 0"])
    r = _run(hooks, [units[1]], rule)
    per = r["stats"][0]["steps"] // 3
    r = _run(hooks, [units[1]], rule, max_steps=per - 1)
    assert [f["msg"] for f in r["findings"]] == ["?"]
    (f,) = r["failures"]
    assert (f["id"], f["in"]) == ("PSSP221", "message")


def test_budget_trips_in_a_let(hooks, units):
    rule = _rule(match="{ kind: Field }", extra=[
        "let:",
        "  n: node.name.id + node.name.id + node.name.id",
        "where: n.size() > 0"])
    r = _run(hooks, [units[1]], rule, max_steps=2)
    assert r["findings"] == []
    (f,) = r["failures"]
    assert (f["id"], f["in"], f["line"]) == ("PSSP221", "let", 2)


def test_a_disabled_rule_is_never_evaluated(hooks, units):
    r = _run(hooks, [units[1]],
             _rule("ACME001", extra=[_BAD_WHERE]),
             _rule("ACME002", message="${node}"),
             enabled=["ACME002"])
    assert r["failures"] == []
    s = _stats(r)
    assert (s["ACME001"]["matches"], s["ACME001"]["steps"], s["ACME001"]["ns"]) == (0, 0, 0)
    assert s["ACME002"]["matches"] == 2 and s["ACME002"]["steps"] > 0
    assert len(r["findings"]) == 2


def test_none_enabled(hooks, units):
    r = _run(hooks, [units[1]], _rule("ACME001"), enabled=[])
    assert r["findings"] == [] and r["stats"][0]["matches"] == 0


def test_time_is_recorded(hooks, units):
    r = _run(hooks, [units[1]], _rule())
    assert r["stats"][0]["ns"] > 0


def test_gate_trips_on_a_link_error(hooks):
    from pssparser.parser import Parser, ParseException
    p = Parser()
    p.parses([("bad.pss", "component pss_top { action A : Missing { } }\n")])
    with pytest.raises(ParseException):
        p.link()
    errors = sum(1 for m in p.markers if m["severity"] == "error")
    assert errors == 1
    # The caller counts the errors (C5.4 wires this): nothing is walked.
    r = _run(hooks, [], _rule(), gate_errors=errors)
    assert r["skipped"] == {"id": "PSSP230", "severity": "info",
                            "msg": "lint skipped: 1 error", "line": -1}
    assert r["findings"] == [] and r["stats"][0]["matches"] == 0


def test_gate_counts_errors(hooks, units):
    r = _run(hooks, [units[1]], _rule(), gate_errors=3)
    assert r["skipped"]["msg"] == "lint skipped: 3 errors"


def test_no_errors_no_gate(hooks, units):
    r = _run(hooks, [units[1]], _rule())
    assert r["skipped"] is None and len(r["findings"]) == 2


def test_markers_are_defined():
    from pssparser.checkers.core_checker import CoreChecker
    defs = {d.id: d for d in CoreChecker().marker_defs}
    assert (defs["PSSP220"].name, defs["PSSP220"].severity) == ("rule-evaluation-error", "warning")
    assert (defs["PSSP221"].name, defs["PSSP221"].severity) == ("rule-budget-exceeded", "warning")
    assert (defs["PSSP230"].name, defs["PSSP230"].severity) == ("lint-skipped", "info")
