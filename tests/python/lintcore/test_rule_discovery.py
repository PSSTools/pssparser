"""Where rule files come from (lint-core-plan C4.3; pss-rules-format §6.2).

The built-in files embedded in the core, ``[lint] rules`` (relative to the
config file), ``--rules``, and ``--check-rules``.  The core decides whether a
file in a named directory is a rule file (``probe_rules``); the Python host
lists directories, reads files, and reports.
"""
from __future__ import annotations

import io
import json
import os
import re
import runpy
import sys
from pathlib import Path

import pytest

from pssparser.cli.app import main
from pssparser.core import Factory
from pssparser.lint import rulefiles
from pssparser.lint.rulefiles import RulePath, RulePathError

REPO = Path(__file__).resolve().parents[3]


def _rule(id, name):
    return (f"    - id: {id}\n      name: {name}\n      summary: s\n"
            f"      message: m\n      match: {{ kind: ExprBin }}\n")


def rule_file(*rules):
    """A clean site rule file with *rules*, each ``(id, name)``."""
    return ("pss-rules:\n  defaults:\n    tier: style\n  rules:\n"
            + "".join(_rule(i, n) for i, n in rules))


def engine():
    return Factory.inst().mkLintEngine()


# ---------------------------------------------------------------- probe ---

@pytest.mark.parametrize("text,kind", [
    (rule_file(("ACME001", "a")), "rule-file"),
    ('{"pss-rules": {"rules": []}}', "rule-file"),
    ("pss-rules: {}\n", "rule-file"),
    ("", "empty"),
    ("# only a comment\n", "empty"),
    ("- a\n- b\n", "not-mapping"),
    ("42\n", "not-mapping"),
    ("name: x\nsteps: []\n", "no-key"),
    ("pss_rules:\n  rules: []\n", "no-key"),        # the typo --verbose exposes
    ("a: [\n", "not-yaml"),
    # Not valid YAML, but a rule file: loading it reports the YAML errors
    # rather than the directory listing skipping it in silence.
    ("pss-rules:\n  rules: [\n", "rule-file"),
    ('{"pss-rules": {\n', "rule-file"),
    ("x: 1\nx: 2\npss-rules: {}\n", "rule-file"),   # a duplicate key
])
def test_probe(text, kind):
    assert engine().probe_rules(text) == kind


# ------------------------------------------------------------- built-in ---

def test_the_build_embeds_every_file_in_rules():
    files = [p for p in (REPO / "rules").iterdir() if p.suffix in (".yaml", ".yml")]
    assert engine().num_builtin_rule_files == len(files)


def test_the_builtin_rules_load_without_a_diagnostic():
    e = engine()
    assert e.load_builtin_rules() == e.num_builtin_rule_files
    assert e.rule_diagnostics() == []
    assert all(r["id"].startswith("LINT") for r in e.rules())


def test_builtin_rules_load_once():
    e = engine()
    e.load_builtin_rules()
    assert e.load_builtin_rules() == 0


def _generator():
    return runpy.run_path(str(REPO / "src" / "lint" / "rules" / "mk_builtin_rules.py"),
                          run_name="mk_builtin_rules")


def _embedded(cpp):
    """``{name: bytes}`` back out of the generated source."""
    arrays = {int(i): bytes(int(b) for b in re.findall(r"\d+", body)[:-1])
              for i, body in re.findall(r"file_(\d+)\[\] = \{(.*?)\};", cpp, re.S)}
    table = re.findall(r'\{"([^"]+)", file_(\d+), (\d+)\}', cpp)
    out = {}
    for name, i, size in table:
        assert len(arrays[int(i)]) == int(size)
        out[name] = arrays[int(i)]
    return out


def test_the_generator_embeds_the_bytes_in_name_order(tmp_path):
    (tmp_path / "naming.yaml").write_bytes(b'pss-rules:\n  x: ")"\\ \xc3\xa9\n')
    (tmp_path / "decl.yml").write_text("pss-rules: {}\n")
    (tmp_path / "README.md").write_text("not a rule file\n")
    (tmp_path / "sub.yaml").mkdir()
    cpp = _generator()["generate"](str(tmp_path))
    got = _embedded(cpp)
    assert list(got) == ["pssparser:rules/decl.yml", "pssparser:rules/naming.yaml"]
    assert got["pssparser:rules/naming.yaml"] == (tmp_path / "naming.yaml").read_bytes()
    assert "{nullptr, nullptr, 0}" in cpp


def test_the_generator_handles_no_rules_directory(tmp_path):
    cpp = _generator()["generate"](str(tmp_path / "absent"))
    assert _embedded(cpp) == {}
    assert "{nullptr, nullptr, 0}" in cpp


# ---------------------------------------------------------- expand/load ---

def test_a_directory_is_listed_not_recursively_and_in_name_order(tmp_path):
    d = tmp_path / "rules"
    (d / "deeper").mkdir(parents=True)
    (d / "b.yaml").write_text(rule_file(("ACME002", "b")))
    (d / "a.yml").write_text(rule_file(("ACME001", "a")))
    (d / "c.json").write_text(json.dumps({"pss-rules": {"defaults": {"tier": "style"}, "rules": [
        {"id": "ACME003", "name": "c", "summary": "s", "message": "m",
         "match": {"kind": "ExprBin"}}]}}))
    (d / "notes.txt").write_text(rule_file(("ACME004", "d")))       # not examined
    (d / "deeper" / "e.yaml").write_text(rule_file(("ACME005", "e")))
    (d / "ci.yaml").write_text("steps: []\n")
    (d / "empty.yaml").write_text("")
    load = rulefiles.load([RulePath(str(d))])
    assert [os.path.basename(f) for f in load.files] == ["a.yml", "b.yaml", "c.json"]
    assert [r["id"] for r in load.engine.rules()
            if not r["file"].startswith("pssparser:")] == ["ACME001", "ACME002", "ACME003"]
    assert [(os.path.basename(p), why) for p, why in load.skipped] == [
        ("ci.yaml", "no top-level 'pss-rules' key"), ("empty.yaml", "the file is empty")]
    assert load.diagnostics == []


def test_a_named_file_that_is_not_a_rule_file_is_an_error(tmp_path):
    f = tmp_path / "ci.yaml"
    f.write_text("steps: []\n")
    load = rulefiles.load([RulePath(str(f))])
    assert [(d["code"], d["severity"]) for d in load.diagnostics] == [("PSSP210", "error")]
    assert "no top-level 'pss-rules' key" in load.diagnostics[0]["message"]
    assert load.skipped == []


def test_a_broken_rule_file_in_a_directory_is_loaded_not_skipped(tmp_path):
    (tmp_path / "bad.yaml").write_text("pss-rules:\n  rules: [\n")
    load = rulefiles.load([RulePath(str(tmp_path))])
    assert [d["code"] for d in load.diagnostics] == ["PSSP218"]
    assert load.skipped == []


def test_a_missing_path_is_a_usage_error(tmp_path):
    with pytest.raises(RulePathError, match=r"\.pssparser\.toml: lint\.rules: rule path "
                                            r".*nope does not exist"):
        rulefiles.load([RulePath(str(tmp_path / "nope"), ".pssparser.toml: lint.rules")])


def test_a_file_that_is_not_utf8_is_a_usage_error(tmp_path):
    (tmp_path / "x.yaml").write_bytes(b"pss-rules: \xff\n")
    with pytest.raises(RulePathError, match="not UTF-8"):
        rulefiles.load([RulePath(str(tmp_path / "x.yaml"))])


def test_a_file_reached_twice_loads_once(tmp_path):
    (tmp_path / "a.yaml").write_text(rule_file(("ACME001", "a")))
    load = rulefiles.load([RulePath(str(tmp_path)), RulePath(str(tmp_path / "a.yaml"))])
    assert len(load.files) == 1 and load.diagnostics == []


def test_load_order_decides_which_duplicate_is_refused(tmp_path):
    (tmp_path / "first.yaml").write_text(rule_file(("ACME001", "a")))
    (tmp_path / "second.yaml").write_text(rule_file(("ACME001", "b")))
    load = rulefiles.load([RulePath(str(tmp_path / "second.yaml")),
                           RulePath(str(tmp_path / "first.yaml"))])
    (d,) = load.diagnostics
    assert d["code"] == "PSSP217" and d["file"].endswith("first.yaml")
    assert d["related"][0]["file"].endswith("second.yaml")


def test_a_clash_with_an_extension_marker_is_reported_and_refused(tmp_path):
    from pssparser.checkers import MarkerDef

    (tmp_path / "a.yaml").write_text(rule_file(("ACME001", "a"), ("ACME002", "b")))
    mdefs = [MarkerDef(id="ACME001", severity="warning", summary="s")]
    load = rulefiles.load([RulePath(str(tmp_path / "a.yaml"))], mdefs,
                          owner_of=lambda mid: "checker 'acme'")
    (d,) = load.diagnostics
    assert d["message"] == ("[PSSP217] rule ID 'ACME001' is already the ID of marker "
                            "ACME001, declared by checker 'acme'")
    assert load.refused == {"ACME001"}


# ------------------------------------------------------------------ CLI ---

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
    """A project: ``m.pss``, and ``lint/rules/`` named by ``.pssparser.toml``
    in ``cfg/`` (so config-relative paths are tested)."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text("component pss_top { }\n")
    rules = tmp_path / "cfg" / "lint" / "rules"
    rules.mkdir(parents=True)
    (rules / "acme.yaml").write_text(rule_file(("ACME001", "a")))
    (rules / "ci.yaml").write_text("steps: []\n")
    (tmp_path / "cfg" / ".pssparser.toml").write_text('[lint]\nrules = ["lint/rules"]\n')
    return tmp_path


def test_config_paths_are_relative_to_the_config_file(ws):
    rc, out, _ = _run("--config", "cfg/.pssparser.toml", "--show-config")
    assert rc == 0
    assert re.search(r"lint\.rules\s+cfg/lint/rules\s+cfg/\.pssparser\.toml", out)


def test_rules_flag_adds_after_the_config(ws):
    (ws / "extra.yaml").write_text(rule_file(("ACME001", "dup")))
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "--rules", "extra.yaml",
                      "--check-rules")
    assert rc == 1
    # --rules loads after the config's entries, so its copy is the one refused.
    assert "extra.yaml:5:11: error: [PSSP217] rule ID 'ACME001' is already" in err
    rc, out, _ = _run("--config", "cfg/.pssparser.toml", "--rules", "extra.yaml",
                      "--show-config")
    assert re.search(r"lint\.rules\s+cfg/lint/rules, extra\.yaml\s+"
                     r"cfg/\.pssparser\.toml \+ command line", out)


def test_check_rules_clean_is_0(ws):
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "--check-rules")
    assert rc == 0
    assert err.endswith("0 errors in 1 file\npssparser: 1 rule loaded from 1 file\n")
    assert "skipped" not in err


def test_check_rules_verbose_lists_skipped_files(ws):
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "--check-rules", "-v")
    assert rc == 0
    assert ("pssparser: skipped cfg/lint/rules/ci.yaml: no top-level 'pss-rules' key"
            in err)


def test_check_rules_errors_are_1(ws):
    (ws / "bad.yaml").write_text("pss-rules:\n  rules:\n    - id: acme1\n")
    rc, _, err = _run("--no-config", "--check-rules", "bad.yaml")
    assert rc == 1
    assert "bad.yaml:3:11: error: [PSSP212]" in err


def test_check_rules_paths_replace_the_configured_ones(ws):
    (ws / "other.yaml").write_text(rule_file(("ACME001", "a")))
    # The configured file also declares ACME001; naming PATHs checks only those.
    rc, _, _ = _run("--config", "cfg/.pssparser.toml", "--check-rules", "other.yaml")
    assert rc == 0


@pytest.mark.parametrize("argv,msg", [
    (("--no-config", "--check-rules"), "has no rule files to check"),
    (("--no-config", "--check-rules", "nope.yaml"),
     "--check-rules: rule path nope.yaml does not exist"),
])
def test_check_rules_usage_errors_are_2(ws, argv, msg):
    rc, _, err = _run(*argv)
    assert rc == 2 and msg in err


def test_check_rules_json(ws):
    (ws / "bad.yaml").write_text("pss-rules:\n  rules: 3\n")
    rc, out, _ = _run("--no-config", "--check-rules", "--format", "json", "bad.yaml")
    assert rc == 1
    doc = json.loads(out)
    assert [(d["code"], d["file"], d["line"]) for d in doc["diagnostics"]] == [
        ("PSSP210", "bad.yaml", 2)]


def test_a_parse_run_reports_rule_file_errors(ws):
    (ws / "cfg" / "lint" / "rules" / "bad.yaml").write_text(
        rule_file(("ACME001", "again")))
    rc, out, _ = _run("--config", "cfg/.pssparser.toml", "--format", "json", "m.pss")
    assert rc == 1
    assert [d["code"] for d in json.loads(out)["diagnostics"]] == ["PSSP217"]


def test_a_parse_run_with_clean_rules_is_0(ws):
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "m.pss")
    assert rc == 0 and "skipped" not in err
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "-v", "m.pss")
    assert rc == 0 and "pssparser: skipped cfg/lint/rules/ci.yaml" in err


def test_a_parse_run_with_a_missing_rule_path_is_2(ws):
    rc, _, err = _run("--no-config", "--rules", "nope", "m.pss")
    assert rc == 2
    assert "error: --rules: rule path nope does not exist" in err


def test_lint_rules_must_be_an_array_of_strings(ws):
    (ws / ".pssparser.toml").write_text('[lint]\nrules = "lint/rules"\n')
    rc, _, err = _run("--check-rules")
    assert rc == 2 and "'lint.rules' must be an array" in err


CHECKER = (
    "from pssparser.checkers import CheckerBase, MarkerDef\n"
    "class AcmeChecker(CheckerBase):\n"
    "    name = 'acme'\n"
    "    marker_defs = [MarkerDef(id='ACME001', severity='warning', summary='s')]\n"
    "    def check(self, context):\n"
    "        pass\n"
)


def test_a_rule_that_takes_an_extension_id_is_refused(ws, monkeypatch):
    (ws / "acmechk.py").write_text(CHECKER)
    monkeypatch.syspath_prepend(str(ws))
    rc, _, err = _run("--config", "cfg/.pssparser.toml", "--load-checker",
                      "acmechk:AcmeChecker", "--check-rules")
    assert rc == 1
    assert ("[PSSP217] rule ID 'ACME001' is already the ID of marker ACME001, "
            "declared by checker 'acme'" in err)
