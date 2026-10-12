"""Per-path overrides, explicit hints and ``--rules-for`` on the command line
(lint-core-plan.md C7.1; lint-framework F2.5; post-readiness E3(a);
rule-authoring-requests B12).

``[[lint.overrides]]`` tables give a set of files (globs relative to the
configuration's directory) their own ``profile``, ``select``, ``ignore`` and
``rule.<name>`` options. The core engine resolves each file's rules, so a
rule off in one directory and on in another runs, and reports only where
it is on.
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.cli.app import main

ACME = """\
pss-rules:
  defaults:
    family: naming
  rules:
    - id: ACME001
      name: comp-suffix
      tier: style
      summary: Component names end in the suffix
      message: "'${node.name.id}' should end in '${options.suffix}'"
      match: { kind: Component }
      where: "!node.name.id.endsWith(options.suffix)"
      options:
        suffix: { type: string, default: "_c", help: the suffix }
      examples:
        - name: fires
          code: |
            component dma { }  // expect: ACME001
        - name: quiet
          code: |
            component dma_c { }
    - id: ACME002
      name: action-upper
      tier: suspicious
      summary: Action names are lower case
      message: "action '${node.name.id}' is not lower case"
      match: { kind: Action }
      where: "!node.name.id.matches('^[a-z_0-9]+$')"
"""

#: LINT403 (unknown annotation) is core-emitted and in every profile. Each
#: file declares its own component, `dma` plus a suffix from its path.
MODEL = """\
component dma{n} {{
  @desc_s
  action Xfer{n} {{ }}
}}
"""


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
def ws(lint_enabled, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "acme.yaml").write_text(ACME)
    for d in ("ip", "ip/legacy", "tests", "lib", "vendor/x"):
        (tmp_path / d).mkdir(parents=True, exist_ok=True)
    for n, f in enumerate(("ip/a.pss", "ip/legacy/b.pss", "tests/t.pss", "lib/l.pss",
                           "vendor/x/v.pss")):
        (tmp_path / f).write_text(MODEL.format(n=n))
    return tmp_path


def _config(ws, overrides, head='rules = ["acme.yaml"]\nselect = ["ACME"]\n'):
    (ws / ".pssparser.toml").write_text("[lint]\n" + head + overrides)


def _found(*argv, files=("ip/a.pss", "ip/legacy/b.pss", "tests/t.pss", "lib/l.pss",
                         "vendor/x/v.pss")):
    rc, out, err = _run("--format", "json", "--show-hints", *argv, *files)
    assert rc in (0, 1), err
    return sorted((d["file"], d["code"]) for d in json.loads(out)["diagnostics"]
                  if d["code"] not in ("PSSP230",))


def test_an_override_turns_rules_off_in_one_directory(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["tests/**", "vendor"]\n'
                'ignore = ["ACME", "LINT403"]\n')
    got = _found()
    assert ("tests/t.pss", "ACME001") not in got
    assert ("vendor/x/v.pss", "LINT403") not in got       # a core-emitted rule too
    assert ("ip/a.pss", "ACME001") in got and ("ip/a.pss", "LINT403") in got
    assert {f for f, _ in got} == {"ip/a.pss", "ip/legacy/b.pss", "lib/l.pss"}


def test_a_rule_on_only_in_one_directory_runs_and_reports_only_there(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["ip/legacy/*.pss"]\nselect = ["ACME002"]\n',
            head='rules = ["acme.yaml"]\n')
    assert [x for x in _found() if x[1].startswith("ACME")] == [
        ("ip/legacy/b.pss", "ACME002")]


def test_overrides_apply_in_order(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["ip/**"]\nignore = ["ACME001"]\n'
                '[[lint.overrides]]\nfiles = ["ip/legacy"]\nselect = ["comp-suffix"]\n')
    acme1 = [f for f, c in _found() if c == "ACME001"]
    assert acme1 == ["ip/legacy/b.pss", "lib/l.pss", "tests/t.pss", "vendor/x/v.pss"]


def test_library_profile_under_lib(ws):
    # library is recommended's tiers: ACME002 (suspicious) on, ACME001
    # (style) off, without the project selecting either.
    _config(ws, '[[lint.overrides]]\nfiles = ["lib/**"]\nprofile = "library"\n',
            head='rules = ["acme.yaml"]\n')
    assert [x for x in _found() if x[1].startswith("ACME")] == [("lib/l.pss", "ACME002")]


def test_override_options(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["ip/legacy/**"]\n'
                'rule.comp-suffix = { suffix = "_comp" }\n')
    rc, out, err = _run("--format", "json", "--show-hints", "ip/a.pss", "ip/legacy/b.pss")
    msgs = sorted(d["message"] for d in json.loads(out)["diagnostics"]
                  if d["code"] == "ACME001")
    assert msgs == ["[ACME001] 'dma0' should end in '_c'",
                    "[ACME001] 'dma1' should end in '_comp'"]


def test_globs_are_relative_to_the_configuration(ws, monkeypatch):
    _config(ws, '[[lint.overrides]]\nfiles = ["ip/legacy/**"]\nignore = ["ACME"]\n')
    monkeypatch.chdir(ws / "ip")
    assert [x for x in _found(files=("a.pss", "legacy/b.pss")) if x[1] == "ACME001"] == [
        ("a.pss", "ACME001")]


def test_the_command_line_beats_an_override(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["tests"]\nignore = ["ACME001"]\n')
    assert ("tests/t.pss", "ACME001") in _found("--select", "ACME001")


@pytest.mark.parametrize("table,message", [
    ('ignore = ["ACME"]\n',
     "'lint.overrides[0]' needs 'files', an array of globs"),
    ('files = "tests"\n', "'lint.overrides[0].files' must be an array"),
    ('files = ["t"]\nseverity = {}\n', "unknown key 'severity' in [[lint.overrides]]"),
    ('files = ["t"]\nprofile = "recomended"\n',
     "'lint.overrides[0].profile' names unknown profile 'recomended'; did you mean "
     "'recommended'?"),
    ('files = ["t"]\nselect = ["ACME01"]\n',
     ".pssparser.toml: 'lint.overrides[0].select' names an unknown marker or selector "
     "'ACME01'; did you mean 'ACME001'?"),
    ('files = ["t"]\nrule.comp-sufix = { suffix = "x" }\n',
     "'lint.overrides[0].rule.comp-sufix' configures an unknown lint rule; did you mean "
     "'comp-suffix'?"),
    ('files = ["t"]\nrule.comp-suffix = { prefix = "x" }\n', "prefix"),
])
def test_override_errors(ws, table, message):
    _config(ws, "[[lint.overrides]]\n" + table)
    rc, out, err = _run("ip/a.pss")
    assert rc == 2
    assert message in err, err


# -- --show-config --------------------------------------------------------

def test_show_config_for_a_file(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["tests/**"]\nignore = ["ACME"]\n')
    rc, out, err = _run("--show-config", "--for", "tests/t.pss", "--for", "ip/a.pss")
    assert rc == 0, err
    assert "lint.overrides[0]                  files = tests/**; ignore = ACME" in out
    assert "Rule files (load order):\n  acme.yaml" in out
    assert "2 rules" in out and ".pssparser.toml: lint.rules" in out
    tests, ip = out.split("For tests/t.pss (as tests/t.pss):")[1].split("For ip/a.pss")
    assert "overrides:     lint.overrides[0]" in tests and "ACME" not in tests
    assert "(no override matches)" in ip and "ACME001-002" in ip


def test_for_needs_show_config(ws):
    assert _run("--for", "x.pss")[0] == 2


# -- explicit hints (E3(a)) -----------------------------------------------

def _text(*argv):
    rc, out, err = _run(*argv)
    return err


def test_a_rule_selected_by_id_shows_its_hints(ws):
    err = _text("--no-config", "--rules", "acme.yaml", "--select", "ACME001", "ip/a.pss")
    assert "hint: [ACME001] 'dma0' should end in '_c'" in err
    assert "hidden" not in err


def test_a_rule_selected_by_tier_does_not(ws):
    err = _text("--no-config", "--rules", "acme.yaml", "--select", "style", "ip/a.pss")
    assert "ACME001" not in err
    assert "(1 hint hidden)" in err


def test_a_rule_selected_by_namespace_in_the_configuration_shows_its_hints(ws):
    _config(ws, "")
    assert "hint: [ACME001]" in _text("ip/a.pss")


# -- --rules-for (B12) -----------------------------------------------------

def test_rules_for_text(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["tests/**"]\nignore = ["ACME001", "LINT"]\n')
    rc, out, err = _run("--rules-for", "tests/new_file.pss", "--ignore", "LINT")
    assert rc == 0, err
    assert out == (
        "tests/new_file.pss: profile minimal, lint.overrides[0], 1 rule\n"
        "  ACME002 action-upper [warning] Action names are lower case  (acme.yaml:21:7)\n")


def test_rules_for_a_file_that_does_not_exist(ws):
    _config(ws, "")
    rc, out, err = _run("--rules-for", "ip/dma/not_yet.pss", "--ignore", "LINT")
    assert rc == 0, err
    assert out.splitlines()[0] == "ip/dma/not_yet.pss: profile minimal, no override, 2 rules"


def test_rules_for_json(ws):
    _config(ws, '[[lint.overrides]]\nfiles = ["ip/**"]\nrule.comp-suffix = { suffix = "_ip" }'
                '\n[severity]\nACME002 = "error"\n')
    rc, out, err = _run("--rules-for", "--format", "json", "ip/x.pss", "--ignore", "LINT")
    assert rc == 0, err
    doc = json.loads(out)
    assert doc["schema"] == "pssparser-rules/1"
    (f,) = doc["files"]
    assert (f["path"], f["rel"], f["profile"], f["overrides"]) == (
        "ip/x.pss", "ip/x.pss", "minimal", [0])
    r1, r2 = f["rules"]
    assert r1 == {
        "id": "ACME001", "name": "comp-suffix", "severity": "hint", "tier": "style",
        "family": "naming", "summary": "Component names end in the suffix",
        "source": "acme.yaml:5:7", "match": ["Component"], "doc": "",
        "options": {"suffix": "_ip"},
        "examples": [{"code": "component dma { }", "fires": True, "note": "fires"},
                     {"code": "component dma_c { }", "fires": False, "note": "quiet"}]}
    assert (r2["id"], r2["severity"]) == ("ACME002", "error")


def test_rules_for_needs_a_file(ws):
    assert _run("--rules-for")[0] == 2


def test_rules_for_parses_nothing(ws):
    (ws / "ip" / "broken.pss").write_text("component {{{")
    _config(ws, "")
    assert _run("--rules-for", "ip/broken.pss")[0] == 0
