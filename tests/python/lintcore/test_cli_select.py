"""``--select`` / ``--ignore`` on the command line (linter-post-readiness E2).

A rule file's rules run only once something selects them.  These flags do it
without a configuration file, as a layer over ``[lint] select`` / ``ignore``:
a rule that a command-line selector matches is decided by the command line.
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
    tier: style
    family: naming
  rules:
    - id: ACME001
      name: action-lower
      summary: Action names are lower case
      message: "action '${node.name.id}' is not lower case"
      match: { kind: Action }
      where: "!node.name.id.matches('^[a-z_0-9]+$')"
    - id: ACME002
      name: field-prefix
      summary: Fields start with m_
      message: "field '${node.name.id}' does not start with 'm_'"
      match: { kind: Field }
      where: "!node.name.id.startsWith('m_')"
"""

MODEL = """\
component pss_top {
  action Xfer {
    rand bit[8] x;
  }
}
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
    (tmp_path / "m.pss").write_text(MODEL)
    return tmp_path


def _codes(*argv):
    # The rules are style tier, so they report hints, hidden by default.
    rc, out, err = _run("--format", "json", "--show-hints", *argv, "m.pss")
    assert rc == 0, err
    return sorted(d["code"] for d in json.loads(out)["diagnostics"])


def test_site_rules_are_off_without_a_selector(ws):
    assert _codes("--no-config", "--rules", "acme.yaml") == []


def test_select_runs_a_namespace_with_no_config_file(ws):
    assert _codes("--no-config", "--rules", "acme.yaml", "--select", "ACME") == [
        "ACME001", "ACME002"]


def test_select_by_name_and_repeated(ws):
    assert _codes("--no-config", "--rules", "acme.yaml",
                  "--select", "action-lower", "--select", "ACME002") == [
        "ACME001", "ACME002"]


def test_ignore_beats_select(ws):
    assert _codes("--no-config", "--rules", "acme.yaml",
                  "--select", "ACME", "--ignore", "ACME002") == ["ACME001"]


def test_a_more_specific_select_beats_a_broad_ignore(ws):
    assert _codes("--no-config", "--rules", "acme.yaml",
                  "--select", "ACME002", "--ignore", "ACME") == ["ACME002"]


def test_command_line_select_beats_a_configured_ignore(ws):
    (ws / ".pssparser.toml").write_text(
        '[lint]\nrules = ["acme.yaml"]\nignore = ["ACME001"]\n')
    assert _codes() == []
    assert _codes("--select", "ACME001") == ["ACME001"]


def test_command_line_ignore_beats_a_configured_select(ws):
    (ws / ".pssparser.toml").write_text(
        '[lint]\nrules = ["acme.yaml"]\nselect = ["ACME"]\n')
    assert _codes() == ["ACME001", "ACME002"]
    assert _codes("--ignore", "ACME001") == ["ACME002"]


def test_select_adds_to_the_configured_select(ws):
    (ws / ".pssparser.toml").write_text(
        '[lint]\nrules = ["acme.yaml"]\nselect = ["ACME001"]\n')
    assert _codes("--select", "ACME002") == ["ACME001", "ACME002"]


@pytest.mark.parametrize("flag", ["--select", "--ignore"])
def test_an_unknown_selector_is_exit_2(ws, flag):
    rc, _, err = _run("--no-config", "--rules", "acme.yaml", flag, "BOGUS", "m.pss")
    assert rc == 2
    assert f"command line: '{flag}' names an unknown marker or selector 'BOGUS'" in err


def test_show_config_attributes_the_command_line(ws):
    (ws / ".pssparser.toml").write_text(
        '[lint]\nrules = ["acme.yaml"]\nselect = ["ACME001"]\n')
    rc, out, err = _run("--select", "ACME002", "--ignore", "ACME001", "--show-config")
    assert rc == 0, err
    rows = {line.split()[0]: line for line in out.splitlines() if line.strip()}
    assert "ACME001, ACME002" in rows["lint.select"]
    assert rows["lint.select"].rstrip().endswith(".pssparser.toml + command line")
    assert "ACME001" in rows["lint.ignore"]
    assert rows["lint.ignore"].rstrip().endswith("command line")
