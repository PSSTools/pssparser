"""Baselines (lint-framework-plan F2.4).

``--write-baseline`` records a run's lint findings; ``--baseline`` (or
``[lint] baseline``) then reports only the findings it does not record.

Most cases use LINT402 (an ``import`` after a declaration): it is in the
default profile and is raised by the linker, so it needs no lint runner.  It
has no extent, so its fingerprint covers the ``import`` keyword only, and
every LINT402 in one declaration has the same fingerprint -- which makes it
the natural test of ``count``.
"""
from __future__ import annotations

import io
import json
import os
import sys

import pytest

from pssparser.cli.app import main
from pssparser.lint import baseline as B


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def _model(n=2, q=0):
    """*n* late imports in package ``p``, and *q* in package ``q``."""
    src = "package lib { struct s {} }\npackage p {\n  struct t {}\n"
    src += "  import lib::*;\n" * n
    src += "}\n"
    if q:
        src += "package q {\n  struct u {}\n" + "  import lib::*;\n" * q + "}\n"
    return src


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """A workspace: ``m.pss`` and a runner that returns the JSON document."""
    monkeypatch.chdir(tmp_path)

    class W:
        path = tmp_path

        def write(self, src, name="m.pss"):
            (tmp_path / name).write_text(src)

        def run(self, *flags, files=("m.pss",), fmt="json"):
            cfg = [] if (tmp_path / ".pssparser.toml").exists() else ["--no-config"]
            rc, out, err = _run([*cfg, "--format", fmt, *flags, *files])
            doc = json.loads(out) if fmt in ("json", "sarif") and out else None
            return rc, doc, err

    return W()


def _codes(doc):
    return [(d["line"], d.get("code")) for d in doc["diagnostics"]]


# ---------------------------------------------------------------------------
# Writing and reading
# ---------------------------------------------------------------------------

def test_write_then_read_reports_nothing(ws):
    ws.write(_model(2))
    rc, _, err = ws.run("--write-baseline", "base.json", fmt="text")
    assert rc == 0
    assert "recorded 2 findings in base.json" in err
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert rc == 0
    assert doc["diagnostics"] == []
    assert [d["code"] for d in doc["baselined"]] == ["LINT402", "LINT402"]
    assert doc["summary"]["warnings"] == 0


def test_the_file_is_sorted_and_one_entry_per_line(ws):
    ws.write(_model(1, q=1))
    ws.run("--write-baseline", "base.json")
    text = (ws.path / "base.json").read_text()
    lines = text.splitlines()
    assert lines[0] == "{"
    assert lines[1] == '  "schema": "pssparser-baseline/1",'
    entries = [ln for ln in lines if ln.lstrip().startswith('{"code"')]
    assert len(entries) == 2
    assert entries == sorted(entries)
    doc = json.loads(text)
    assert doc["rules-version"] is None
    assert {e["file"] for e in doc["entries"]} == {"m.pss"}
    # Reading gives each entry the line it is on.
    assert [e.line for e in B.load(str(ws.path / "base.json")).entries] == [
        lines.index(ln) + 1 for ln in entries]


def test_text_output_counts_baselined_findings(ws):
    ws.write(_model(2))
    ws.run("--write-baseline", "base.json")
    rc, _, err = ws.run("--baseline", "base.json", fmt="text")
    assert rc == 0
    assert err.strip() == "0 errors in 1 file (2 baselined)"


def test_rules_version_pin_is_recorded(ws):
    ws.write(_model(1))
    (ws.path / ".pssparser.toml").write_text('[lint]\nrules-version = "2026.1"\n')
    ws.run("--write-baseline", "base.json")
    assert json.loads((ws.path / "base.json").read_text())["rules-version"] == "2026.1"


# ---------------------------------------------------------------------------
# Matching
# ---------------------------------------------------------------------------

def test_a_new_finding_is_reported(ws):
    ws.write(_model(2))
    ws.run("--write-baseline", "base.json")
    ws.write(_model(2, q=1))
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert _codes(doc) == [(9, "LINT402")]   # the one in package q
    assert len(doc["baselined"]) == 2


def test_count_three_recorded_four_found_reports_one(ws):
    ws.write(_model(3))
    ws.run("--write-baseline", "base.json")
    assert [e["count"] for e in json.loads(
        (ws.path / "base.json").read_text())["entries"]] == [3]
    ws.write(_model(4))
    rc, doc, _ = ws.run("--baseline", "base.json")
    # Nothing tells the four apart, so the last in source order is new.
    assert _codes(doc) == [(7, "LINT402")]


def test_a_finding_survives_edits_above_it(ws):
    ws.write(_model(1))
    ws.run("--write-baseline", "base.json")
    ws.write("// a header\n\n" + _model(1).replace("struct t {}", "struct t {}\n  struct t2 {}"))
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert doc["diagnostics"] == []
    assert len(doc["baselined"]) == 1


def test_minus_werror_does_not_promote_a_baselined_finding(ws):
    ws.write(_model(1))
    ws.run("--write-baseline", "base.json")
    rc, doc, _ = ws.run("--baseline", "base.json", "-Werror")
    assert rc == 0 and doc["diagnostics"] == []
    ws.write(_model(1, q=1))
    rc, doc, _ = ws.run("--baseline", "base.json", "-Werror")
    assert rc == 1 and _codes(doc) == [(8, "LINT402")]


def test_a_waived_finding_is_not_recorded(ws):
    ws.write(_model(1).replace(
        "  import lib::*;", "  import lib::*;  // pssparser waive LINT402: ok"))
    rc, _, err = ws.run("--write-baseline", "base.json", fmt="text")
    assert "recorded 0 findings" in err
    assert json.loads((ws.path / "base.json").read_text())["entries"] == []


# ---------------------------------------------------------------------------
# Stale entries
# ---------------------------------------------------------------------------

def test_a_fixed_finding_makes_its_entry_stale(ws):
    ws.write(_model(1, q=1))
    ws.run("--write-baseline", "base.json")
    ws.write(_model(1))
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert rc == 0
    (stale,) = doc["diagnostics"]
    assert stale["code"] == "PSSP206"
    assert stale["severity"] == "info"
    assert stale["file"] == "base.json"
    text = (ws.path / "base.json").read_text().splitlines()
    assert '"m.pss"' in text[stale["line"] - 1]
    assert "its finding is no longer reported (LINT402 in m.pss)" in stale["message"]
    assert doc["summary"]["files"] == 1   # the baseline is not a model file


def test_a_partly_fixed_entry_says_how_many(ws):
    ws.write(_model(3))
    ws.run("--write-baseline", "base.json")
    ws.write(_model(1))
    _, doc, _ = ws.run("--baseline", "base.json")
    (stale,) = doc["diagnostics"]
    assert "2 of its 3 findings are no longer reported" in stale["message"]


def test_no_stale_entry_for_a_file_not_checked(ws):
    ws.write(_model(1))
    ws.write(_model(1).replace("package p", "package p2").replace(
        "package lib", "package lib2").replace("lib::", "lib2::"), name="o.pss")
    ws.run("--write-baseline", "base.json", files=("m.pss", "o.pss"))
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert doc["diagnostics"] == []


def test_no_stale_entry_for_a_rule_that_did_not_run(ws):
    ws.write(_model(1))
    ws.run("--write-baseline", "base.json")
    rc, doc, _ = ws.run("--baseline", "base.json", "--no-lint")
    assert doc["diagnostics"] == []


def test_stale_entries_can_be_turned_off(ws):
    ws.write(_model(1, q=1))
    ws.run("--write-baseline", "base.json")
    ws.write(_model(1))
    (ws.path / ".pssparser.toml").write_text('[severity]\nPSSP206 = "off"\n')
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert doc["diagnostics"] == []


# ---------------------------------------------------------------------------
# What a baseline never covers
# ---------------------------------------------------------------------------

ERROR_MODEL = "package p { struct s { int a } }\n"


def test_writing_is_refused_when_the_model_has_errors(ws):
    ws.write(ERROR_MODEL)
    rc, _, err = ws.run("--write-baseline", "base.json", fmt="text")
    assert rc == 1
    assert not (ws.path / "base.json").exists()
    assert err.rstrip().splitlines()[-1].startswith(
        "error: not writing the baseline base.json: the model has errors")


def test_a_core_error_is_never_matched(ws):
    ws.write(_model(1))
    ws.run("--write-baseline", "base.json")
    ws.write(ERROR_MODEL)
    _, doc, _ = ws.run("--baseline", "base.json")
    (err,) = [d for d in doc["diagnostics"] if d["severity"] == "error"]
    # Forge an entry for the error itself: it still is not matched.
    data = json.loads((ws.path / "base.json").read_text())
    data["entries"] = [{"code": err["code"], "file": "m.pss",
                        "fingerprint": err["fingerprint"], "count": 1}]
    (ws.path / "base.json").write_text(json.dumps(data))
    rc, doc, _ = ws.run("--baseline", "base.json")
    assert rc == 1
    assert [d["code"] for d in doc["diagnostics"]] == [err["code"]]
    assert "baselined" not in doc


@pytest.mark.parametrize("code,expected", [
    ("LINT402", True), ("LINT403", True), ("PSSP202", False), ("PSS001", False),
    (None, False),
])
def test_eligible(code, expected):
    from pssparser.checkers.core_checker import CoreChecker
    from pssparser.checkers.selectors import _is_core_error

    defs = {md.id: md for md in CoreChecker.marker_defs}

    class D:
        pass
    d = D()
    d.code, d.fingerprint = code, "f"
    assert B.eligible(d, lambda c: _is_core_error(defs[c])) is expected


# ---------------------------------------------------------------------------
# Malformed baselines
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,why", [
    ("not json", "invalid JSON"),
    ("[]", "expected a JSON object"),
    ('{"schema": "x", "entries": []}', "'schema' is 'x'"),
    ('{"schema": "pssparser-baseline/1"}', "'entries' must be an array"),
    ('{"schema": "pssparser-baseline/1", "entries": [{"code": "LINT402"}]}',
     "entry 1 has no 'file' string"),
    ('{"schema": "pssparser-baseline/1", "entries": [{"code": "A", "file": "m",'
     ' "fingerprint": "f", "count": 0}]}', "'count' must be a positive integer"),
])
def test_a_malformed_baseline_is_a_usage_error(ws, text, why):
    ws.write(_model(1))
    (ws.path / "base.json").write_text(text)
    rc, out, err = _run(["--no-config", "--baseline", "base.json", "m.pss"])
    assert rc == 2
    assert out == ""
    assert err.startswith("error: base.json")
    assert why in err


def test_a_missing_baseline_is_a_usage_error(ws):
    ws.write(_model(1))
    rc, _, err = _run(["--no-config", "--baseline", "nope.json", "m.pss"])
    assert rc == 2
    assert "baseline file not found: nope.json" in err


# ---------------------------------------------------------------------------
# Paths, configuration and flags
# ---------------------------------------------------------------------------

def test_paths_are_relative_to_the_baseline(ws, monkeypatch):
    os.makedirs(ws.path / "src")
    os.makedirs(ws.path / "ci")
    ws.write(_model(2), name="src/m.pss")
    ws.run("--write-baseline", "ci/base.json", files=("src/m.pss",))
    doc = json.loads((ws.path / "ci" / "base.json").read_text())
    assert [e["file"] for e in doc["entries"]] == ["../src/m.pss"]
    # The same baseline from another working directory.
    monkeypatch.chdir(ws.path / "src")
    rc, out, _ = _run(["--no-config", "--format", "json",
                       "--baseline", "../ci/base.json", "m.pss"])
    assert rc == 0 and json.loads(out)["diagnostics"] == []


def test_config_baseline_is_relative_to_the_config_file(ws, monkeypatch):
    os.makedirs(ws.path / "ci")
    os.makedirs(ws.path / "sub")
    ws.write(_model(1))
    (ws.path / ".pssparser.toml").write_text('[lint]\nbaseline = "ci/base.json"\n')
    rc, _, err = ws.run("--write-baseline", "ci/base.json", fmt="text")
    assert rc == 0 and "in ci/base.json" in err
    ws.write(_model(1, q=1))
    monkeypatch.chdir(ws.path / "sub")
    rc, out, _ = _run(["--format", "json", "../m.pss"])
    assert _codes(json.loads(out)) == [(8, "LINT402")]


def test_no_baseline_reports_everything(ws):
    ws.write(_model(1))
    (ws.path / ".pssparser.toml").write_text('[lint]\nbaseline = "base.json"\n')
    ws.run("--write-baseline", "base.json")
    _, doc, _ = ws.run()
    assert doc["diagnostics"] == []
    _, doc, _ = ws.run("--no-baseline")
    assert _codes(doc) == [(4, "LINT402")]


def test_write_baseline_never_overwrites_a_source_file(ws):
    ws.write(_model(1))
    rc, _, err = ws.run("--write-baseline", "m.pss", fmt="text")
    assert rc == 2
    assert "would overwrite the source file m.pss" in err
    assert (ws.path / "m.pss").read_text() == _model(1)


def test_write_baseline_conflicts_with_baseline(ws):
    ws.write(_model(1))
    rc, _, err = ws.run("--write-baseline", "a.json", "--baseline", "b.json",
                        fmt="text")
    assert rc == 2 and "conflicts" in err


def test_show_config_reports_the_baseline(ws):
    (ws.path / ".pssparser.toml").write_text('[lint]\nbaseline = "ci/b.json"\n')
    rc, out, _ = _run(["--show-config"])
    assert rc == 0
    row = [ln for ln in out.splitlines() if "lint.baseline" in ln]
    assert row and "ci/b.json" in row[0] and ".pssparser.toml" in row[0]


def test_config_rejects_a_non_string_baseline(ws):
    (ws.path / ".pssparser.toml").write_text("[lint]\nbaseline = 3\n")
    ws.write(_model(1))
    rc, _, err = _run(["m.pss"])
    assert rc == 2 and "lint.baseline" in err


def test_an_old_id_in_a_baseline_matches_its_successor(tmp_path):
    path = tmp_path / "b.json"
    path.write_text(json.dumps({"schema": B.SCHEMA, "entries": [
        {"code": "PSS104", "file": "m.pss", "fingerprint": "f", "count": 1}]}))
    doc = B.load(str(path), aliases={"PSS104": "LINT601"})
    assert [e.code for e in doc.entries] == ["LINT601"]


# ---------------------------------------------------------------------------
# Output formats
# ---------------------------------------------------------------------------

def test_sarif_baseline_state_and_fingerprints(ws):
    ws.write(_model(1))
    ws.run("--write-baseline", "base.json")
    ws.write(_model(1, q=1))
    rc, doc, _ = ws.run("--baseline", "base.json", fmt="sarif")
    results = doc["runs"][0]["results"]
    states = sorted((r["locations"][0]["physicalLocation"]["region"]["startLine"],
                     r["baselineState"]) for r in results)
    assert states == [(4, "unchanged"), (8, "new")]
    assert all(set(r["partialFingerprints"]) == {"pssparser/v1"} for r in results)

    jsonschema = pytest.importorskip("jsonschema")
    from pathlib import Path
    schema = Path(__file__).parents[1] / "cli" / "data" / "sarif-2.1.0.json"
    jsonschema.validate(doc, json.loads(schema.read_text()))


def test_sarif_without_a_baseline_has_fingerprints_but_no_state(ws):
    ws.write(_model(1))
    _, doc, _ = ws.run(fmt="sarif")
    (result,) = doc["runs"][0]["results"]
    assert "partialFingerprints" in result and "baselineState" not in result


def test_json_without_a_baseline_is_unchanged(ws):
    ws.write(_model(1))
    _, doc, _ = ws.run()
    assert "fingerprint" not in doc["diagnostics"][0]
    assert "baselined" not in doc


def test_stats_count_baselined_findings(ws):
    ws.write(_model(2))
    ws.run("--write-baseline", "base.json")
    _, doc, _ = ws.run("--baseline", "base.json", "--stats-no-timing")
    assert doc["stats"]["baselined_by_code"] == {"LINT402": 2}
    _, _, err = ws.run("--baseline", "base.json", "--stats-no-timing", fmt="text")
    assert "  baselined:    LINT402 x2" in err
