"""[lint] configuration, selectors in [severity] and -W, and the info/hint
severities at the command line (plan F1.1, F1.4, F1.5, F1.6)."""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.cli.app import main

from .test_migrated_ids import PROBES

SRC = {new: src for new, _, src, _ in PROBES}


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _config(workdir, text):
    (workdir / ".pssparser.toml").write_text(text)


def _file(workdir, rule="LINT402", name="m.pss"):
    path = workdir / name
    path.write_text(SRC[rule])
    return str(path)


def _codes(out):
    return [d["code"] for d in json.loads(out)["diagnostics"]]


# -- [lint] schema --------------------------------------------------------------

@pytest.mark.parametrize("text,fragment", [
    ('[lint]\nprofil = "all"\n', "did you mean 'profile'"),
    ('[lint]\nprofile = "recomended"\n', "did you mean 'recommended'"),
    ('[lint]\nrules-version = "2026"\n', "year.release"),
    ('[lint]\nselect = "all"\n', "must be an array"),
    ('[lint]\nselect = ["unknwn-annotation"]\n', "did you mean 'unknown-annotation'"),
    ('[lint]\nignore = ["family:constrant"]\n', "family:constraint"),
    ('[lint.rule.no-such-rule]\nx = 1\n', "unknown lint rule"),
    ('[lint.rule.unknown-annotation]\nx = 1\n', "accepts no options"),
    ('[output]\nshow-hint = true\n', "did you mean 'show-hints'"),
])
def test_bad_lint_config_is_a_usage_error(workdir, text, fragment):
    _config(workdir, text)
    rc, _, err = _run([_file(workdir)])
    assert rc == 2
    assert fragment in err


def test_profile_none_in_config_hides_lint(workdir):
    _config(workdir, '[lint]\nprofile = "none"\n')
    rc, out, _ = _run(["--json", _file(workdir)])
    assert _codes(out) == []


def test_ignore_by_name(workdir):
    _config(workdir, '[lint]\nignore = ["import-after-declaration"]\n')
    _, out, _ = _run(["--json", _file(workdir)])
    assert _codes(out) == []


def test_command_line_profile_beats_config(workdir):
    _config(workdir, '[lint]\nprofile = "none"\n')
    _, out, _ = _run(["--json", "--lint-profile", "minimal", _file(workdir)])
    assert _codes(out) == ["LINT402"]


def test_no_lint_beats_config(workdir):
    _config(workdir, '[lint]\nprofile = "all"\n')
    _, out, _ = _run(["--json", "--no-lint", _file(workdir)])
    assert _codes(out) == []


def test_show_config_reports_lint(workdir):
    _config(workdir, '[lint]\nprofile = "strict"\nignore = ["LINT4"]\n')
    rc, out, _ = _run(["--show-config"])
    assert rc == 0
    assert "lint.profile" in out and "strict" in out
    assert "enabled rules: LINT301, LINT501, LINT601-602" in out


# -- selectors in [severity] ----------------------------------------------------

def test_severity_by_tier(workdir):
    _config(workdir, '[severity]\nsuspicious = "error"\n')
    rc, out, _ = _run(["--json", _file(workdir, "LINT401")])
    doc = json.loads(out)
    assert [(d["code"], d["severity"]) for d in doc["diagnostics"]] == [
        ("LINT401", "error")]
    assert rc == 1


def test_severity_most_specific_key_wins(workdir):
    _config(workdir, '[severity]\nsuspicious = "error"\nLINT401 = "info"\n')
    rc, out, _ = _run(["--json", _file(workdir, "LINT401")])
    assert json.loads(out)["diagnostics"][0]["severity"] == "info"
    assert rc == 0


def test_severity_by_family_off(workdir):
    _config(workdir, '[severity]\n"family:import" = "off"\n')
    _, out, _ = _run(["--json", _file(workdir)])
    assert _codes(out) == []


def test_a_namespace_selector_cannot_reach_core_errors(workdir):
    _config(workdir, '[severity]\nPSS = "off"\n')
    path = workdir / "bad.pss"
    path.write_text("component pss_top { action a { int x } }\n")
    rc, out, _ = _run(["--json", str(path)])
    assert rc == 1
    assert any(c.startswith("PSS0") for c in _codes(out))


# -- -W groups (F1.6) -----------------------------------------------------------

def test_werror_by_tier_names_the_group(workdir):
    rc, _, err = _run(["-Werror=portability", _file(workdir, "LINT403")])
    assert rc == 1
    assert "[-Werror=portability]" in err


def test_werror_by_family_promotes_only_its_members(workdir):
    rc, out, _ = _run(["--json", "-Werror=family:evolution",
                       _file(workdir, "LINT403")])
    assert rc == 0
    assert json.loads(out)["diagnostics"][0]["severity"] == "warning"


def test_wno_error_id_beats_a_group(workdir):
    rc, _, _ = _run(["-Werror=portability", "-Wno-error=LINT403",
                     _file(workdir, "LINT403")])
    assert rc == 0


def test_unknown_werror_selector_is_a_usage_error(workdir):
    rc, _, err = _run(["-Werror=portabilty", _file(workdir)])
    assert rc == 2
    assert "did you mean 'portability'" in err


# -- info and hint (F1.1, D-4) --------------------------------------------------

def test_info_is_counted_as_a_note(workdir):
    _config(workdir, '[severity]\nLINT402 = "info"\n')
    rc, _, err = _run([_file(workdir)])
    assert rc == 0
    assert err.rstrip().endswith("1 note in 1 file")


def test_info_is_not_promoted_by_a_bare_werror(workdir):
    _config(workdir, '[severity]\nLINT402 = "info"\n')
    rc, _, _ = _run(["-Werror", _file(workdir)])
    assert rc == 0


def test_werror_info_promotes_info(workdir):
    _config(workdir, '[severity]\nLINT402 = "info"\n')
    rc, _, err = _run(["-Werror=info", _file(workdir)])
    assert rc == 1
    assert "[-Werror=info]" in err


def test_werror_id_promotes_an_info_rule(workdir):
    _config(workdir, '[severity]\nLINT402 = "info"\n')
    rc, _, _ = _run(["-Werror=LINT402", _file(workdir)])
    assert rc == 1


def test_hint_is_hidden_and_counted_as_hidden(workdir):
    _config(workdir, '[severity]\nLINT402 = "hint"\n')
    rc, _, err = _run([_file(workdir)])
    assert rc == 0
    assert "import lib" not in err
    assert err.rstrip().endswith("0 errors in 1 file (1 hint hidden)")


def test_show_hints_prints_it(workdir):
    _config(workdir, '[severity]\nLINT402 = "hint"\n')
    rc, _, err = _run(["--show-hints", _file(workdir)])
    assert "hint:" in err
    assert "hidden" not in err


def test_hint_is_never_promoted(workdir):
    _config(workdir, '[severity]\nLINT402 = "hint"\n')
    rc, _, _ = _run(["-Werror", "-Werror=info", _file(workdir)])
    assert rc == 0


def test_json_always_carries_hints_and_counts(workdir):
    _config(workdir, '[severity]\nLINT402 = "hint"\n')
    _, out, _ = _run(["--json", _file(workdir)])
    doc = json.loads(out)
    assert _codes(out) == ["LINT402"]
    assert doc["summary"]["hints"] == 1
    assert doc["summary"]["notes"] == 0
