"""Declarative rules in the Python registry (lint-core-plan C4.4).

Rules loaded from ``pss-rules`` files are shown to the Python side as
``MarkerDef``s (``pssparser.lint.ruleview``), registered as one
metadata-only checker, so ``--describe``, ``--explain``, ``--list-markers``,
selectors, profiles, ``[severity]``, ``[lint.rule.<name>]`` and the rule
reference all see them.  The command line loads rule files before checking
its configuration, so a configuration may name their rules.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from pssparser.checkers import CheckerManager
from pssparser.cli.app import main
from pssparser.core import Factory
from pssparser.lint import rulefiles, ruleview

REPO = Path(__file__).resolve().parents[3]

ACME = """\
pss-rules:
  defaults:
    tier: suspicious
  rules:
    - id: ACME001
      name: no-plus
      family: constraint
      summary: An addition in an expression
      message: "addition in ${node}"
      doc: |
        Additions are suspicious here.

        Write `a - -b` instead.
      lrm: ["9.1"]
      options:
        limit: { type: int, default: 3, help: The largest sum allowed }
      match: { kind: ExprBin, inside: { kind: Action } }
      where: options.limit > 1
      examples:
        - name: an addition
          code: |
            component pss_top {
              action A { int x = 1 + 2; }   // expect: ACME001
            }
        - name: no addition
          code: |
            component pss_top { }
    - id: ACME002
      name: pedantic-thing
      tier: style
      severity: error
      summary: Something pedantic
      message: m
      match: { kind: ExprBin }
"""


def _rules(text=ACME, name="acme.yaml"):
    e = Factory.inst().mkLintEngine()
    e.load_rules(name, text)
    return e.rules()


# ---------------------------------------------------------------- view ---

def test_a_rule_becomes_a_marker_def():
    md = ruleview.marker_defs(_rules())[0]
    assert (md.id, md.name, md.tier, md.family) == (
        "ACME001", "no-plus", "suspicious", "constraint")
    assert md.severity == "warning"            # the tier's default
    assert md.summary == "An addition in an expression"
    assert md.detail.startswith("Additions are suspicious here.")
    assert md.lrm == ("9.1",)
    assert (md.level, md.scope) == ("L0", "file")
    assert md.match == ("ExprBin",)
    assert md.source == "acme.yaml:5:7"
    assert md.options_schema == {
        "limit": {"type": "int", "default": 3, "help": "The largest sum allowed"}}
    assert md.is_lint and md.emittable


def test_examples_drop_their_expect_comments():
    bad, good = ruleview.marker_defs(_rules())[0].examples
    assert bad.note == "an addition"
    assert bad.code == ("component pss_top {\n  action A { int x = 1 + 2; }\n}")
    assert bad.expect == ((2, 0),)
    assert good.expect == () and good.code == "component pss_top { }"


def test_a_multi_file_example_shows_each_file_under_its_name():
    rule = {"id": "ACME009", "examples": [{"name": "two", "files": [
        {"name": "a.pss", "text": "import b::*; // expect: ACME009\n",
         "expect": [{"id": "ACME009", "line": 1, "col": 0}]},
        {"name": "b.pss", "text": "package b { }\n", "expect": []}]}]}
    ex = ruleview.marker_def(rule).examples[0]
    assert ex.code == "// a.pss\nimport b::*;\n// b.pss\npackage b { }"


def test_a_severity_override_is_kept():
    md = ruleview.marker_defs(_rules())[1]
    assert (md.tier, md.severity) == ("style", "error")


def test_refused_rules_are_left_out():
    assert [m.id for m in ruleview.marker_defs(_rules(), {"ACME001"})] == ["ACME002"]


def test_builtin_is_told_by_the_file_name():
    md = ruleview.marker_def({"id": "LINT901", "file": "pssparser:rules/a.yaml"})
    assert ruleview.is_builtin(md)
    assert not ruleview.is_builtin(ruleview.marker_defs(_rules())[0])


# ------------------------------------------------------------- manager ---

def _manager():
    m = CheckerManager()
    m.discover(load_extensions=False)
    return m


def test_the_view_joins_the_registry():
    m = _manager()
    m.add_rule_view(ruleview.marker_defs(_rules()))
    ids = [md.id for md in m.all_marker_defs()]
    assert ids[-2:] == ["ACME001", "ACME002"]
    assert m.describe_marker("no-plus")["checker"] == ruleview.CHECKER_NAME
    assert m.owner_of("ACME001") == "rule file 'acme.yaml'"
    info = [c for c in m.list_checkers() if c["name"] == ruleview.CHECKER_NAME][0]
    assert info["is_declarative"] and info["marker_ids"] == ["ACME001", "ACME002"]
    # Metadata only: never instantiated for a run.
    assert ruleview.CHECKER_NAME not in [c.name for c in m.active(None, None)]


def test_the_view_is_replaced_and_removed():
    m = _manager()
    m.add_rule_view(ruleview.marker_defs(_rules()))
    m.add_rule_view(ruleview.marker_defs(_rules(), {"ACME001"}))
    assert [md.id for md in m.all_marker_defs() if md.id.startswith("ACME")] == ["ACME002"]
    m.add_rule_view([])
    assert ruleview.CHECKER_NAME not in m.registered
    assert m.owner_of("ACME002") == ""


def test_conflicts_are_checked_before_the_view_is_added(tmp_path):
    # Loading twice with the view registered must not make the rules clash
    # with themselves: the view is never passed to conflicts().
    (tmp_path / "acme.yaml").write_text(ACME)
    m = _manager()
    for _ in range(2):
        m.add_rule_view([])
        load = rulefiles.load([rulefiles.RulePath(str(tmp_path / "acme.yaml"))],
                              m.all_marker_defs(), m.owner_of)
        assert load.refused == set() and load.diagnostics == []
        m.add_rule_view(ruleview.marker_defs(load.engine.rules(), load.refused))


# ----------------------------------------------------------------- CLI ---

def _run(*argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(list(argv))
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


@pytest.fixture
def ws(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "acme.yaml").write_text(ACME)
    (tmp_path / "m.pss").write_text("component pss_top { }\n")
    return tmp_path


EXPLAIN = """\
ACME001 no-plus
An addition in an expression

  tier:              suspicious
  family:            constraint
  analysis level:    L0
  scope:             file
  matches:           ExprBin
  defined in:        acme.yaml:5:7
  default severity:  warning
  LRM:               9.1
  fix:               none available

Additions are suspicious here.

Write `a - -b` instead.

Flagged (an addition):

    component pss_top {
      action A { int x = 1 + 2; }
    }

Not flagged (no addition):

    component pss_top { }

Options:
  limit            int          default: 3
    The largest sum allowed

Set these under [lint.rule.no-plus].
"""


def test_explain_a_declarative_rule(ws):
    rc, out, err = _run("--no-config", "--rules", "acme.yaml", "--explain", "no-plus")
    assert (rc, err) == (0, "")
    assert out == EXPLAIN


def test_describe_a_declarative_rule(ws):
    rc, out, _ = _run("--no-config", "--rules", "acme.yaml", "--describe", "ACME001")
    assert rc == 0
    assert out.startswith("ACME001  [warning]  checker: pss-rules\n"
                          "An addition in an expression\n"
                          "name: no-plus  tier: suspicious  family: constraint\n"
                          "defined in acme.yaml:5:7\n")


def test_list_markers_and_checkers(ws):
    rc, out, _ = _run("--no-config", "--rules", "acme.yaml", "--list-markers")
    assert rc == 0
    assert ["ACME002", "error", "pss-rules", "Something pedantic"] in [
        l.split(None, 3) for l in out.splitlines()]
    rc, out, _ = _run("--no-config", "--rules", "acme.yaml", "--list-checkers")
    assert "pss-rules            Declarative rules from pss-rules files [rule files]" in out


def test_without_the_rule_file_the_rule_is_unknown(ws):
    rc, _, err = _run("--no-config", "--explain", "no-plus")
    assert rc == 2 and "unknown rule 'no-plus'" in err


def test_a_query_reports_rule_file_problems(ws):
    (ws / "bad.yaml").write_text(ACME.replace("name: no-plus", "name: No_Plus"))
    rc, _, err = _run("--no-config", "--rules", "bad.yaml", "--explain", "ACME002")
    assert rc == 0
    assert "bad.yaml:6:13: error: [PSSP212]" in err


def test_selectors_and_severity_may_name_declarative_rules(ws):
    (ws / ".pssparser.toml").write_text(
        '[lint]\nrules = ["acme.yaml"]\nselect = ["ACME"]\n'
        '[severity]\nno-plus = "error"\n'
        '[lint.rule.no-plus]\nlimit = 5\n')
    rc, out, err = _run("--show-config")
    assert (rc, err) == (0, "")
    enabled = [l for l in out.splitlines() if "enabled rules:" in l][0]
    assert "ACME001-002" in enabled


def test_a_profile_enables_a_declarative_rule_by_tier(ws):
    rc, out, _ = _run("--no-config", "--rules", "acme.yaml", "--lint-profile",
                      "recommended", "--show-config")
    assert rc == 0
    enabled = [l for l in out.splitlines() if "enabled rules:" in l][0]
    assert "ACME001" in enabled                 # suspicious: in recommended
    assert "ACME002" not in enabled             # style: only in all


@pytest.mark.parametrize("toml,msg", [
    ('[lint.rule.no-plus]\nlimit = "five"\n', "option 'limit' must be of type int"),
    ('[lint.rule.no-plus]\nlimt = 5\n', "did you mean 'limit'?"),
    ('[lint]\nselect = ["ACME003"]\n', "ACME003"),
])
def test_config_naming_declarative_rules_is_checked(ws, toml, msg):
    (ws / ".pssparser.toml").write_text('[lint]\nrules = ["acme.yaml"]\n'
                                        + toml.replace("[lint]\n", ""))
    rc, _, err = _run("--show-config")
    assert rc == 2 and msg in err, err


def test_check_rules_with_a_config_that_selects_site_rules(ws):
    # The configuration is checked against a registry that holds the rules
    # --check-rules loads, so selecting them is not an unknown selector.
    (ws / ".pssparser.toml").write_text('[lint]\nrules = ["acme.yaml"]\nselect = ["ACME"]\n')
    rc, _, err = _run("--check-rules")
    assert rc == 0, err
    rc, _, err = _run("--check-rules", "acme.yaml")
    assert rc == 0, err


def test_a_parse_run_accepts_a_selected_site_rule(ws):
    rc, _, err = _run("--no-config", "--rules", "acme.yaml", "-Werror=ACME", "m.pss")
    assert rc == 0, err
    rc, _, err = _run("--no-config", "-Werror=ACME", "m.pss")
    assert rc == 2


CHECKER = (
    "from pssparser.checkers import CheckerBase, MarkerDef\n"
    "class AcmeChecker(CheckerBase):\n"
    "    name = 'acme'\n"
    "    marker_defs = [MarkerDef(id='ACME001', severity='warning', summary='python')]\n"
    "    def check(self, context):\n"
    "        pass\n"
)


def test_a_refused_rule_is_not_in_the_view(ws, monkeypatch):
    (ws / "acmechk_view.py").write_text(CHECKER)
    monkeypatch.syspath_prepend(str(ws))
    rc, out, err = _run("--no-config", "--rules", "acme.yaml", "--load-checker",
                        "acmechk_view:AcmeChecker", "--list-markers")
    assert rc == 0
    assert [l.split() for l in out.splitlines() if l.startswith("ACME001")] == [
        ["ACME001", "warning", "acme", "python"]]
    assert "[PSSP217] rule ID 'ACME001' is already the ID of marker ACME001" in err


# ------------------------------------------------------ rule reference ---

def test_the_rule_reference_documents_builtin_rule_files():
    sys.path.insert(0, str(REPO / "scripts"))
    from gen_lint_rules import render
    # As a built-in rule file would give it: a LINT ID, a pssparser: file.
    rule = dict(_rules()[0], id="LINT901", file="pssparser:rules/demo.yaml")
    text = render([ruleview.marker_def(rule)])
    entry = text[text.index(".. _lint901:"):]
    entry = entry[:entry.index("\n.. _", 1)]
    assert "**Level:** L0, file; **Defined in:** ``rules/demo.yaml``" in entry
    assert "Write ``a - -b`` instead." in entry          # Markdown, as reST
    assert "expect:" not in entry
    # Filed under its family, with the catalogue's constraint rules.
    assert text.index("Constraints\n---") < text.index(".. _lint901:")


def test_md_to_rst():
    sys.path.insert(0, str(REPO / "scripts"))
    from gen_lint_rules import md_to_rst
    assert md_to_rst("See [x](https://a.b) and `c`.\n\n```\nint x;\n```\n\nEnd.\n") == (
        "See `x <https://a.b>`_ and ``c``.\n\n.. code-block:: pss\n\n   int x;\n\nEnd.")
