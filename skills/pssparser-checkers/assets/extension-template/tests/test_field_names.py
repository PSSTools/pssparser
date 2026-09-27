"""Tests for my-pss-rules.

Each test runs the real ``pssparser`` command with ``--json`` on a small
model, so it exercises exactly what a user runs.  ``--no-extensions`` plus
``--load-checker`` makes the result independent of whatever else is
installed, and works whether or not this package itself is installed (it
only has to be importable).
"""
import json
import os
import subprocess
import sys

import pytest

from pssparser.checkers import API_VERSION, CheckerManager, ExtensionRegistry

import my_pss_rules
from my_pss_rules.field_names import FieldNameLengthChecker

SPEC = "my_pss_rules.field_names:FieldNameLengthChecker"


def lint(tmp_path, source, config=None):
    """Run pssparser with this checker; return (exit code, diagnostics)."""
    (tmp_path / "model.pss").write_text(source)
    args = ["--no-extensions", "--load-checker", SPEC, "--json"]
    if config is not None:
        (tmp_path / "lint.toml").write_text(config)
        args += ["--config", "lint.toml"]
    else:
        args += ["--no-config"]
    r = subprocess.run(
        [sys.executable, "-m", "pssparser", *args, "model.pss"],
        capture_output=True, text=True, cwd=tmp_path, env=dict(os.environ))
    assert r.returncode in (0, 1), r.stderr
    # A checker that raises is reported on stderr, not as a diagnostic.
    assert "raised an exception" not in r.stderr, r.stderr
    return r.returncode, json.loads(r.stdout)["diagnostics"]


def codes(diags):
    return [d["code"] for d in diags]


def test_short_field_is_reported(tmp_path):
    rc, diags = lint(tmp_path, "struct s { rand bit[8] a; }\n")
    assert codes(diags) == ["MPR001"]
    assert (diags[0]["line"], diags[0]["col"]) == (1, 24)
    assert rc == 0  # a warning does not fail the run


def test_long_and_allowed_names_are_clean(tmp_path):
    _, diags = lint(tmp_path, "struct s { int addr; int i; }\n")
    assert codes(diags) == []


def test_option_changes_the_threshold(tmp_path):
    _, diags = lint(
        tmp_path, "struct s { int addr; }\n",
        config='[checker.field-name-length]\nmin_length = 5\n')
    assert codes(diags) == ["MPR001"]


def test_register_contributes_the_checker():
    reg = ExtensionRegistry("my-pss-rules", api_version=API_VERSION)
    my_pss_rules.register(reg)
    assert [c.name for c in reg.checkers] == ["field-name-length"]
    assert my_pss_rules.REQUIRES_API <= API_VERSION


def test_marker_ids_are_unique_and_not_core():
    m = CheckerManager()
    m.discover(load_extensions=False)
    taken = {d["id"] for d in m.list_all_markers()}
    ours = [md.id for md in FieldNameLengthChecker.marker_defs]
    assert len(ours) == len(set(ours))
    assert not taken & set(ours)
    assert not any(i.startswith("PSS") for i in ours)
