"""Declarative rules run from the command line (lint-core-plan.md C5.4).

The ``pss-rules`` checker runs the enabled rules in the core engine; its
findings then go through the same selection, ``[severity]``, waivers,
baseline and output formats as any checker's.
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.cli.app import main

RULES = """\
pss-rules:
  rules:
    - id: ACME001
      name: action-upper
      tier: suspicious
      summary: Action names start upper-case
      message: "action '${node.name.id}' should start with ${options.first}"
      match: { kind: Action }
      where: "!node.name.id.startsWith(options.first)"
      options:
        first: { type: string, default: "A", help: The first letter }
    - id: ACME002
      name: every-field
      tier: style
      summary: Every field
      message: "field ${node}"
      match: { kind: Field }
"""

MODEL = """\
component pss_top {
  action A { }
  action b { }
}
"""


def _main(args):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(args)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def _run(args, select=("ACME001",), ignore=(), extra=""):
    """Runs with a configuration in the rules' directory that loads
    acme.yaml and selects *select* (selection is configuration-only)."""
    tmp = _run.tmp
    cfg = tmp / "pssparser.toml"
    cfg.write_text('[lint]\nrules = ["acme.yaml"]\n'
                   f"select = {json.dumps(list(select))}\n"
                   f"ignore = {json.dumps(list(ignore))}\n" + extra)
    return _main(["--config", str(cfg)] + args)


@pytest.fixture
def files(tmp_path):
    rules = tmp_path / "acme.yaml"
    rules.write_text(RULES)
    model = tmp_path / "m.pss"
    model.write_text(MODEL)
    _run.tmp = tmp_path
    return tmp_path, str(rules), str(model)


def _json(args, **kw):
    rc, out, err = _run(args + ["--format", "json"], **kw)
    assert out, err
    return rc, json.loads(out)


def _codes(doc):
    return [(d["code"], d["line"]) for d in doc["diagnostics"]]


def test_a_rule_given_with_rules_fires(lint_enabled, files):
    tmp, rules, model = files
    cfg = tmp / "select-only.toml"
    cfg.write_text('[lint]\nselect = ["ACME001"]\n')
    rc, out, err = _main(["--config", str(cfg), "--rules", rules, model])
    assert rc == 0
    assert "m.pss:3:10: warning: [ACME001] action 'b' should start with A" in err


def test_not_enabled_by_the_default_profile(lint_enabled, files):
    _, rules, model = files
    rc, doc = _json([model], select=())
    assert _codes(doc) == []


def test_profile_enables_by_tier(lint_enabled, files):
    _, rules, model = files
    rc, doc = _json(["--lint-profile", "recommended", model], select=())
    # suspicious is in `recommended`; style is not.
    assert _codes(doc) == [("ACME001", 3)]


def test_select_by_namespace_and_name(lint_enabled, files):
    _, rules, model = files
    _, doc = _json([model], select=("ACME",))
    assert _codes(doc) == [("ACME001", 3)]   # ACME002: the model has no fields
    _, doc = _json([model], select=("action-upper",))
    assert _codes(doc) == [("ACME001", 3)]


def test_ignore_wins(lint_enabled, files):
    _, rules, model = files
    _, doc = _json([model], select=("ACME",), ignore=("action-upper",))
    assert _codes(doc) == []


def test_options_from_the_config(lint_enabled, files):
    tmp, rules, model = files
    rc, out, err = _run([model], extra='[lint.rule.action-upper]\nfirst = "b"\n')
    assert "action 'A' should start with b" in err
    assert "action 'b'" not in err


def test_severity_map_applies(lint_enabled, files):
    tmp, rules, model = files
    rc, out, err = _run([model], extra='[severity]\naction-upper = "error"\n')
    assert rc == 1
    assert "error: [ACME001]" in err


def test_a_waiver_suppresses(lint_enabled, files):
    tmp, rules, _ = files
    model = tmp / "w.pss"
    model.write_text("component pss_top {\n"
                     "  action b { }   // pssparser waive ACME001: legacy name\n"
                     "}\n")
    rc, doc = _json([str(model)])
    assert _codes(doc) == []


def test_a_baseline_records_and_accepts(lint_enabled, files):
    tmp, rules, model = files
    base = tmp / "base.json"
    rc, out, err = _run(["--write-baseline", str(base), model])
    assert rc == 0, err
    entries = json.loads(base.read_text())
    assert "ACME001" in json.dumps(entries)
    _, doc = _json(["--baseline", str(base), model])
    assert _codes(doc) == []


def test_sarif_carries_the_rule(lint_enabled, files):
    _, rules, model = files
    rc, out, _ = _run(["--format", "sarif", model])
    sarif = json.loads(out)
    run = sarif["runs"][0]
    assert [r["ruleId"] for r in run["results"]] == ["ACME001"]
    assert "ACME001" in [r["id"] for r in run["tool"]["driver"]["rules"]]


def test_no_lint_runs_nothing(files):
    # conftest sets PSSPARSER_NO_LINT=1: no declarative rule runs.
    _, rules, model = files
    _, doc = _json([model])
    assert _codes(doc) == []


def test_gate_on_a_link_error(lint_enabled, files):
    tmp, rules, _ = files
    model = tmp / "bad.pss"
    model.write_text("component pss_top { action b : Missing { } }\n")
    rc, doc = _json([str(model)])
    assert rc == 1
    codes = [d["code"] for d in doc["diagnostics"]]
    assert "ACME001" not in codes
    (skip,) = [d for d in doc["diagnostics"] if d["code"] == "PSSP230"]
    assert skip["severity"] == "info"
    assert skip["message"] == "[PSSP230] lint skipped: 1 error"


def test_gate_on_a_parse_error(lint_enabled, files):
    tmp, rules, _ = files
    model = tmp / "bad.pss"
    model.write_text("component pss_top { action b { }\n")
    rc, doc = _json([str(model)])
    assert rc == 1
    assert "PSSP230" in [d["code"] for d in doc["diagnostics"]]


def test_no_gate_note_without_enabled_rules(lint_enabled, files):
    # Nothing would have run, so nothing was skipped.
    tmp, rules, _ = files
    model = tmp / "bad.pss"
    model.write_text("component pss_top { action b : Missing { } }\n")
    _, doc = _json([str(model)], select=())
    assert "PSSP230" not in [d["code"] for d in doc["diagnostics"]]


def test_rule_failure_is_reported(lint_enabled, tmp_path):
    _run.tmp = tmp_path
    rules = tmp_path / "acme.yaml"
    rules.write_text("""\
pss-rules:
  rules:
    - id: ACME003
      name: base-elems
      tier: suspicious
      summary: s
      message: m
      match: { kind: Action }
      where: size(node.super_t.elems) > 0
""")
    model = tmp_path / "m.pss"
    model.write_text(MODEL)
    rc, doc = _json([str(model)], select=("ACME003",))
    assert rc == 0
    (d,) = doc["diagnostics"]
    assert (d["code"], d["severity"], d["line"]) == ("PSSP220", "warning", 2)
    assert "rule ACME003 (base-elems) failed in its where at Action 'pss_top::A'" in d["message"]


def test_stats_breakdown(lint_enabled, files):
    _, rules, model = files
    rc, out, err = _run(["--stats-no-timing", model], select=("ACME",))
    assert rc == 0
    tail = err[err.index("stats:"):]
    assert tail == (
        "stats: 1 file processed\n"
        "  declarations: 1 component, 2 actions\n"
        "  diagnostics:  ACME001 x1\n"
        "  lint rules:\n"
        "    ACME001: 2 matches, 1 finding, 16 steps\n"
        "    ACME002: 0 matches, 0 findings, 0 steps\n")


def test_stats_json(lint_enabled, files):
    _, rules, model = files
    _, doc = _json(["--stats-no-timing", model])
    assert doc["stats"]["lint_rules"] == [
        {"id": "ACME001", "matches": 2, "findings": 1, "steps": 16, "errors": 0}]


def test_stats_timing_has_a_lint_phase(lint_enabled, files):
    _, rules, model = files
    _, doc = _json(["--stats", model])
    assert "lint" in doc["stats"]["timing_ms"]
    assert "ms" in doc["stats"]["lint_rules"][0]
