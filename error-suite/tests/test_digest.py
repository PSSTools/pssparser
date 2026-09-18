"""The compact view of a run file.

A digest exists to be read, so the tests are mostly about what it refuses to
lose: the fact that a control failed, which diagnostic was the primary, and a
diagnostic attributed to a file other than the case's own.
"""
from __future__ import annotations

import json

from conftest import FIXTURE_CASES, SUITE_ROOT
from pss_errsuite import digest
from pss_errsuite.cli import main

TOOL = str(SUITE_ROOT / "tools" / "faketool.toml")
CASES = str(FIXTURE_CASES)


def run_file(tmp_path):
    out = tmp_path / "run.json"
    assert main(["run", "--tool", TOOL, "--cases", CASES, "--out", str(out),
                 "--timeout", "2", "-q"]) == 0
    return json.loads(out.read_text()), out


def test_a_digest_is_derived_from_the_run_file_and_much_smaller(tmp_path,
                                                                capsys):
    doc, path = run_file(tmp_path)
    small = digest.build(doc)
    assert small["schema"] == digest.SCHEMA
    assert len(small["cases"]) == len(doc["cases"])
    assert len(json.dumps(small)) < len(json.dumps(doc)) / 3
    # No source, no streams: the evidence stays in the run file.
    assert all("source" not in c and "result" not in c
               for c in small["cases"])


def test_every_field_is_copied_never_computed(tmp_path):
    """A digest must not be arguable from: if it recomputed anything it could
    disagree with the run file it came from."""
    doc, _ = run_file(tmp_path)
    for case, small in zip(doc["cases"], digest.build(doc)["cases"]):
        assert small["case"] == case["case"]
        assert small["status"] == case["status"]
        assert len(small["reported"]) == len(
            (case.get("result") or {}).get("diagnostics") or [])
        for got, want in zip(small["reported"],
                             (case.get("result") or {}).get("diagnostics")
                             or []):
            assert got["message"] == want["message"]
            assert got.get("code") == want.get("code")


def test_the_primary_diagnostic_stays_marked(tmp_path):
    doc, _ = run_file(tmp_path)
    small = {c["case"]: c for c in digest.build(doc)["cases"]}
    reported = small["FX-DETECTED"]["reported"]
    assert [d for d in reported if d.get("primary")]


def test_a_failed_control_is_never_dropped(tmp_path):
    """Without it the digest would show a diagnostic and imply it means
    something, when a failed control says it means nothing."""
    doc, _ = run_file(tmp_path)
    small = {c["case"]: c for c in digest.build(doc)["cases"]}
    assert small["FX-CONTROL-FAILED"]["control"] == "failed"


def test_a_skip_says_why(tmp_path):
    doc, _ = run_file(tmp_path)
    small = {c["case"]: c for c in digest.build(doc)["cases"]}
    assert "capability" in small["FX-SKIPPED-CAP"]["skip_reason"]


def test_spans_render_only_what_the_tool_actually_gave():
    assert digest._span({"line": 4, "col": 2}) == "4:2"
    assert digest._span({"line": 4, "col": 2, "end_col": 9}) == "4:2-9"
    assert digest._span({"line": 4, "col": 2, "end_line": 6,
                         "end_col": 9}) == "4:2-6:9"
    assert digest._span({"line": None, "col": None}) is None


def test_a_diagnostic_on_a_companion_file_is_named():
    case = {"case": "X", "class": "c", "title": "t",
            "files": ["syntax/multifile/a.pss", "syntax/multifile/_lib.pss"],
            "expect": {"kind": "error"}, "status": "detected",
            "observations": {"primary_index": 0},
            "result": {"diagnostics": [
                {"severity": "error", "message": "m", "line": 1, "col": 1,
                 "file": "/tmp/x/_lib.pss", "file_rel": "_lib.pss"}]}}
    assert digest.digest_case(case)["reported"][0]["file"] == "_lib.pss"
    case["result"]["diagnostics"][0]["file_rel"] = "a.pss"
    assert "file" not in digest.digest_case(case)["reported"][0]


def test_the_cli_writes_a_digest_and_reports_the_count(tmp_path, capsys):
    _, path = run_file(tmp_path)
    out = tmp_path / "digest.json"
    capsys.readouterr()
    assert main(["digest", str(path), "--out", str(out)]) == 0
    assert "case(s) ->" in capsys.readouterr().err
    assert json.loads(out.read_text())["schema"] == digest.SCHEMA


def test_the_cli_writes_to_stdout_without_out(tmp_path, capsys):
    _, path = run_file(tmp_path)
    capsys.readouterr()
    assert main(["digest", str(path)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"] == digest.SCHEMA


def test_a_non_run_file_is_refused(tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text('{"schema": "something/else"}')
    assert main(["digest", str(bad)]) == 2
    assert "error:" in capsys.readouterr().err


def test_the_run_file_keeps_the_verbatim_path_and_adds_a_readable_one(
        tmp_path):
    """`file` is byte-exact tool output -- a scratch path for a tool that
    prints absolute paths, a bare name for one that does not. `file_rel` is
    always the name a reader knows the case by. Neither replaces the other."""
    doc, _ = run_file(tmp_path)
    diags = [d for c in doc["cases"]
             for d in (c.get("result") or {}).get("diagnostics") or []
             if d.get("file")]
    assert diags
    for d in diags:
        assert d["file_rel"] == d["file"].rsplit("/", 1)[-1]
        assert "/" not in d["file_rel"]
