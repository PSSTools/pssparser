"""Source waivers (lint-framework-plan F2.1, source-waivers W1-W7).

The library half (``pssparser.waivers``): what each form covers, how a
waiver's ``id`` is resolved, and the hygiene markers.  The CLI half: where
waivers sit in the pipeline (after the severity map, before ``-Werror``) and
how waived findings are reported in each output format.

Most cases use LINT402 (an ``import`` after a declaration): it is in the
default profile and is raised by the linker, so it needs no lint runner.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from pssparser import Parser
from pssparser import waivers as W
from pssparser.cli.app import main


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def _codes(text):
    """``(line, code)`` of each diagnostic in JSON output."""
    doc = json.loads(text)
    return [(d["line"], d.get("code")) for d in doc["diagnostics"]]


LIB = "package lib { struct s {} }\n"


@pytest.fixture
def run_in(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    def run(src, *flags, config=None):
        (tmp_path / "m.pss").write_text(src)
        if config is not None:
            (tmp_path / ".pssparser.toml").write_text(config)
        cfg = [] if config is not None else ["--no-config"]
        return _run([*cfg, "--format", "json", *flags, "m.pss"])
    return run


# ---------------------------------------------------------------------------
# The comment pragma
# ---------------------------------------------------------------------------

def _pragmas(src):
    return [(w.selectors, w.reason, w.start[0]) for w in W.collect_pragmas("m.pss", src)]


def test_trailing_pragma_covers_its_own_line():
    assert _pragmas("struct s {}  // pssparser waive LINT402: why\n") == [
        (["LINT402"], "why", 1)]


def test_pragma_alone_covers_the_next_line_with_code():
    src = "// pssparser waive LINT402, LINT401: why\n\n// other\nstruct s {}\n"
    assert _pragmas(src) == [(["LINT402", "LINT401"], "why", 4)]


def test_pragma_without_a_reason():
    assert _pragmas("// pssparser waive LINT402\nstruct s {}\n") == [(["LINT402"], "", 2)]


@pytest.mark.parametrize("src", [
    "/* // pssparser waive LINT402: x */ struct s {}\n",
    'const string s = "// pssparser waive LINT402: x";\n',
    "// pssparser waiver LINT402: x\nstruct s {}\n",
])
def test_not_a_pragma(src):
    assert _pragmas(src) == []


# ---------------------------------------------------------------------------
# The annotation: what it covers
# ---------------------------------------------------------------------------

def _spans(src):
    p = Parser()
    p.parses([("m.pss", src)])
    p.link()
    return [(w.start, w.end) for w in W.collect(p, ["m.pss"], read=lambda f: src)]


ANN = '@lint_pkg::waive {.id = "LINT402", .reason = "r"}'


def test_element_annotation_covers_from_itself_to_the_element_end():
    src = "component C {\n  %s\n  int a;\n  int b;\n}\n" % ANN
    assert _spans(src) == [((2, 3), (3, 8))]  # a field ends after its name


def test_element_annotation_on_a_function_covers_its_body():
    src = ("component C {\n  %s\n  function void f() {\n    int a;\n  }\n}\n" % ANN)
    (start, end), = _spans(src)
    assert start == (2, 3) and end[0] == 5


def test_element_annotation_on_a_statement_covers_the_statement():
    src = ("component C { action A {} action B {\n  activity {\n    %s\n"
           "    do A;\n    do A;\n  } } }\n" % ANN)
    assert _spans(src) == [((3, 5), (4, 10))]


def test_standalone_annotation_covers_to_the_end_of_its_scope():
    src = "package p {\n  struct t {}\n  %s;\n  struct u {}\n}\nstruct v {}\n" % ANN
    (start, end), = _spans(src)
    assert start == (3, 3) and end[0] == 5


def test_standalone_annotation_at_file_scope_covers_the_rest_of_the_file():
    src = "%s;\nstruct v {}\n" % ANN
    (start, end), = _spans(src)
    assert start == (1, 1) and end[0] > 1000


def test_a_user_annotation_named_waive_is_not_a_waiver():
    src = ("package q { annotation waive { string id; string reason; } }\n"
           'component C { @q::waive {.id = "LINT402", .reason = "r"} int a; }\n')
    assert _spans(src) == []


# ---------------------------------------------------------------------------
# Matching and hygiene, end to end
# ---------------------------------------------------------------------------

def _model(waiver_line, *, pkg_body="  struct t {}\n  {w}\n  import lib::*;\n"):
    return LIB + "package p {\n" + pkg_body.replace("{w}", waiver_line) + "}\n"


@pytest.mark.parametrize("ident", [
    "LINT402", "import-after-declaration", "family:import", "LINT4",
])
def test_a_waiver_names_a_rule_by_any_selector(run_in, ident):
    rc, out, _ = run_in(_model('@lint_pkg::waive {.id = "%s", .reason = "r"}' % ident))
    assert _codes(out) == [] and rc == 0
    assert [d["code"] for d in json.loads(out)["waived"]] == ["LINT402"]


def test_pragma_waiver_end_to_end(run_in):
    src = LIB + "package p {\n  struct t {}\n  import lib::*;  // pssparser waive LINT402: vendored\n}\n"
    _, out, _ = run_in(src)
    doc = json.loads(out)
    assert doc["diagnostics"] == []
    assert doc["waived"][0]["waiver"] == {
        "form": "pragma", "id": "LINT402", "file": "m.pss", "line": 4,
        "col": 19, "reason": "vendored"}


def test_a_waiver_for_another_rule_does_not_waive(run_in):
    _, out, _ = run_in(_model('@lint_pkg::waive {.id = "LINT401", .reason = "r"}'))
    assert (5, "LINT402") in _codes(out)


def test_missing_reason_is_reported_but_the_waiver_applies(run_in):
    _, out, _ = run_in(_model('@lint_pkg::waive {.id = "LINT402"}'))
    assert _codes(out) == [(4, "PSSP205")]


def test_unknown_rule_suggests_the_nearest(run_in):
    _, out, _ = run_in(_model('@lint_pkg::waive {.id = "LINT40X", .reason = "r"}'))
    doc = json.loads(out)
    unknown = [d for d in doc["diagnostics"] if d["code"] == "PSSP203"]
    assert len(unknown) == 1 and "did you mean" in unknown[0]["message"]
    assert (5, "LINT402") in _codes(out)


def test_old_id_works_with_a_note(run_in):
    _, out, _ = run_in(_model('@lint_pkg::waive {.id = "PSS053", .reason = "r"}'))
    assert _codes(out) == [(4, "PSSP004")]


def test_unused_waiver_is_reported(run_in):
    src = LIB + "package p {\n  %s\n  struct t {}\n}\n" % (
        '@lint_pkg::waive {.id = "LINT402", .reason = "r"}')
    _, out, _ = run_in(src)
    assert _codes(out) == [(3, "PSSP202")]


def test_waiver_for_a_rule_that_did_not_run_is_not_unused(run_in):
    src = LIB + "package p {\n  %s\n  struct t {}\n}\n" % (
        '@lint_pkg::waive {.id = "LINT402", .reason = "r"}')
    _, out, _ = run_in(src, config='[severity]\nLINT402 = "off"\n')
    assert _codes(out) == []


def test_an_error_cannot_be_waived(run_in):
    src = 'component C {\n  @lint_pkg::waive {.id = "PSS002", .reason = "r"}\n  nosuch_t f;\n}\n'
    rc, out, _ = run_in(src)
    assert rc == 1
    codes = [c for _, c in _codes(out)]
    assert "PSSP204" in codes and any(c and c.startswith("PSS0") for c in codes)


def test_hygiene_markers_cannot_be_waived(run_in):
    src = LIB + "package p {\n  %s;\n  %s\n  struct t {}\n}\n" % (
        '@lint_pkg::waive {.id = "PSSP202", .reason = "r"}',
        '@lint_pkg::waive {.id = "LINT402", .reason = "r"}')
    _, out, _ = run_in(src)
    assert (4, "PSSP202") in _codes(out)


def test_waivers_on_a_failed_link_still_apply_as_pragmas(run_in):
    src = (LIB + "package p {\n  struct t {}\n  import lib::*;  // pssparser waive LINT402: v\n}\n"
           "component C { nosuch_t f; }\n")
    rc, out, _ = run_in(src)
    assert rc == 1
    assert "LINT402" not in [c for _, c in _codes(out)]


# ---------------------------------------------------------------------------
# The pipeline: severity map -> waivers -> warning policy
# ---------------------------------------------------------------------------

WAIVED = _model('@lint_pkg::waive {.id = "LINT402", .reason = "r"}')


def test_a_waiver_covers_a_rule_the_config_promoted(run_in):
    rc, out, _ = run_in(WAIVED, config='[severity]\nLINT402 = "error"\n')
    assert rc == 0 and _codes(out) == []


def test_werror_does_not_promote_a_waived_warning(run_in):
    rc, out, _ = run_in(WAIVED, "-Werror")
    assert rc == 0 and _codes(out) == []


def test_source_waivers_can_be_turned_off(run_in):
    rc, out, _ = run_in(WAIVED, config="[waivers]\nsource = false\n")
    assert _codes(out) == [(5, "LINT402")]


def test_hygiene_markers_can_be_relevelled(run_in):
    src = LIB + "package p {\n  %s\n  struct t {}\n}\n" % (
        '@lint_pkg::waive {.id = "LINT402", .reason = "r"}')
    rc, out, _ = run_in(src, config='[severity]\nPSSP202 = "error"\n')
    assert rc == 1 and _codes(out) == [(3, "PSSP202")]


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------

def test_json_keeps_waived_findings_out_of_the_counts(run_in):
    _, out, _ = run_in(WAIVED)
    doc = json.loads(out)
    assert doc["summary"]["warnings"] == 0
    assert doc["waived"][0]["code"] == "LINT402"
    assert doc["waived"][0]["waiver"]["reason"] == "r"


def test_json_has_no_waived_key_when_nothing_was_waived(run_in):
    _, out, _ = run_in(LIB)
    assert "waived" not in json.loads(out)


def test_text_output_counts_and_shows_waived(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(WAIVED)
    _, _, err = _run(["--no-config", "m.pss"])
    assert err.strip().endswith("0 errors in 1 file (1 waived)")
    assert "follows a declaration" not in err
    _, _, err = _run(["--no-config", "--show-waived", "m.pss"])
    assert "follows a declaration" in err and "[waived: r]" in err


def test_sarif_reports_a_waived_finding_as_suppressed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(WAIVED)
    _, out, _ = _run(["--no-config", "--format", "sarif", "m.pss"])
    doc = json.loads(out)
    results = doc["runs"][0]["results"]
    assert [(r["ruleId"], r["suppressions"]) for r in results] == [
        ("LINT402", [{"kind": "inSource", "justification": "r"}])]
    jsonschema = pytest.importorskip("jsonschema")
    schema = Path(__file__).parents[1] / "cli" / "data" / "sarif-2.1.0.json"
    jsonschema.validate(doc, json.loads(schema.read_text()))


def test_stats_count_waived_by_code(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(WAIVED)
    _, _, err = _run(["--no-config", "--stats-no-timing", "m.pss"])
    assert "waived:       LINT402 x1" in err


def test_github_format_omits_waived_findings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(WAIVED)
    _, out, _ = _run(["--no-config", "--format", "github", "m.pss"])
    assert out == ""


def test_lint_pkg_needs_no_import():
    p = Parser()
    p.parses([("m.pss", 'component C { %s int a; }' % ANN)])
    p.link()
    assert [m for m in p.markers if m["severity"] != "info"] == []
