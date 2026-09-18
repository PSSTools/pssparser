"""CLI surface and exit codes.

The exit codes encode a distinction worth keeping: `run` is a *measurement* and
exits 0 even when the tool under test missed everything (the output is the
finding); `validate` is a *gate* and exits non-zero on any corpus defect.
"""
from __future__ import annotations

import json

import pytest

from conftest import FIXTURE_CASES, SUITE_ROOT
from pss_errsuite import rubric
from pss_errsuite.cli import main

TOOL = str(SUITE_ROOT / "tools" / "faketool.toml")
CASES = str(FIXTURE_CASES)


def test_run_exits_zero_even_when_the_tool_does_badly(tmp_path, capsys):
    out = tmp_path / "run.json"
    rc = main(["run", "--tool", TOOL, "--cases", CASES, "--out", str(out),
               "--timeout", "2", "-q"])
    assert rc == 0
    doc = json.loads(out.read_text())
    assert doc["summary"]["by_status"]["missed"] >= 1


def test_run_writes_to_stdout_without_out(capsys):
    rc = main(["run", "--tool", TOOL, "--cases", CASES, "--case", "FX-CLEAN",
               "-q"])
    assert rc == 0
    doc = json.loads(capsys.readouterr().out)
    assert [c["case"] for c in doc["cases"]] == ["FX-CLEAN"]


def test_filter_selects_by_class(capsys):
    main(["run", "--tool", TOOL, "--cases", CASES, "--filter",
          "fixture.harness", "--case", "FX-CLEAN", "-q"])
    doc = json.loads(capsys.readouterr().out)
    assert len(doc["cases"]) == 1


def test_an_empty_selection_is_an_error_not_an_empty_report(capsys):
    """A filter typo must not produce a cheerful run file over zero cases."""
    assert main(["run", "--tool", TOOL, "--cases", CASES,
                 "--filter", "nope.nothing", "-q"]) == 2


def test_a_bad_descriptor_exits_two(tmp_path, capsys):
    bad = tmp_path / "bad.toml"
    bad.write_text('[tool]\nname = "x"\n')
    assert main(["run", "--tool", str(bad), "--cases", CASES, "-q"]) == 2
    assert "error:" in capsys.readouterr().err


def test_undeclared_pss_version_warns_in_the_run_file(tmp_path, capsys):
    """An absent declaration must fail in the tool's disfavour, loudly."""
    desc = tmp_path / "nover.toml"
    desc.write_text((SUITE_ROOT / "tools" / "faketool.toml").read_text()
                    .replace('pss         = "3.0"', ""))
    main(["run", "--tool", str(desc), "--cases", CASES, "--case",
          "FX-SKIPPED-VERSION", "--timeout", "2", "-q"])
    doc = json.loads(capsys.readouterr().out)
    assert doc["tool"]["pss_assumed"] is True
    assert any("declares no" in w for w in doc["run"]["warnings"])
    # …and the 3.1 case therefore runs rather than being skipped.
    assert doc["cases"][0]["status"] != "skipped_version"


def test_validate_exits_zero_on_the_shipped_corpus(capsys):
    assert main(["validate", "--cases", str(SUITE_ROOT / "cases")]) == 0


def test_validate_exits_one_on_a_broken_corpus(tmp_path, capsys):
    (tmp_path / "b.pss").write_text("//! case: X\n//! class: nope.nope\n"
                                    "//! expect: accept\npackage p { }\n")
    assert main(["validate", "--cases", str(tmp_path)]) == 1


def test_list_prints_one_line_per_case(capsys):
    assert main(["list", "--cases", str(SUITE_ROOT / "cases")]) == 0
    out = capsys.readouterr()
    assert "SYN-PUNCT-SEMI-01" in out.out
    assert "case(s)" in out.err


def test_list_filters_by_detect_level(capsys):
    main(["list", "--cases", str(SUITE_ROOT / "cases"), "--detect",
          "recommended"])
    out = capsys.readouterr().out
    assert "SYN-VOLUME-THIRTY-01" in out
    assert "SYN-PUNCT-SEMI-01" not in out


# -- compare -----------------------------------------------------------------

@pytest.fixture
def two_runs(tmp_path):
    """Two real runs of the same tool over the fixture corpus, differing only
    in `--tolerance` -- which is exactly what `compare` must refuse."""
    def _run(stem, *extra):
        out = tmp_path / f"{stem}.json"
        assert main(["run", "--tool", TOOL, "--cases", CASES, "--out",
                     str(out), "--timeout", "2", "-q", *extra]) == 0
        return out
    return _run


def test_compare_writes_both_artifacts(two_runs, tmp_path, capsys):
    a, b = two_runs("a"), two_runs("b")
    out, md = tmp_path / "compare.json", tmp_path / "compare.md"
    assert main(["compare", str(a), str(b), "--out", str(out),
                 "--md", str(md)]) == 0
    doc = json.loads(out.read_text())
    # Same tool, same policy, same corpus: no tag may claim one side did
    # better than the other.  The three that survive are the symmetric ones --
    # the fixture corpus carries deliberate skips, crashes and tool errors
    # (`incomparable`) and one case the tool does not diagnose (`both_miss`).
    counts = doc["summary"]["by_tag"]["b"]
    assert counts["agree"] > 0
    assert {t for t, n in counts.items() if n} == {"agree", "incomparable",
                                                   "both_miss"}
    assert sum(counts.values()) == doc["compare"]["shared_case_count"]
    assert "do not publish" in md.read_text()


def test_compare_refuses_runs_at_different_tolerances(two_runs, capsys):
    a = two_runs("a")
    b = two_runs("b", "--tolerance", "exact")
    assert main(["compare", str(a), str(b)]) == 2
    assert "refusing to compare" in capsys.readouterr().err


def test_compare_prints_to_stdout_without_out(two_runs, capsys):
    a, b = two_runs("a"), two_runs("b")
    capsys.readouterr()                      # drop the two run summaries
    assert main(["compare", str(a), str(b)]) == 0
    assert json.loads(capsys.readouterr().out)["schema"].startswith(
        "pss-errsuite/compare/")


# -- show --------------------------------------------------------------------

def test_show_prints_the_case_with_the_expected_line_marked(capsys):
    assert main(["show", "--cases", CASES, "FX-DETECTED"]) == 0
    out = capsys.readouterr().out
    assert "FX-DETECTED" in out
    assert ">" in out


def test_show_runs_one_case_against_a_tool(capsys):
    assert main(["show", "--cases", CASES, "FX-DETECTED", "--tool", TOOL]) == 0
    assert "faketool: detected" in capsys.readouterr().out


def test_show_reads_a_run_file_without_invoking_anything(two_runs, capsys):
    run = two_runs("a")
    assert main(["show", "--cases", CASES, "FX-DETECTED", "--run",
                 str(run)]) == 0
    assert "detected" in capsys.readouterr().out


def test_show_on_an_unknown_case_exits_two(capsys):
    assert main(["show", "--cases", CASES, "NO-SUCH-CASE"]) == 2
    assert "no case with id" in capsys.readouterr().err


# -- grade / triage ----------------------------------------------------------

@pytest.fixture
def graded_run(tmp_path):
    out = tmp_path / "run.json"
    assert main(["run", "--tool", TOOL, "--cases", CASES, "--out", str(out),
                 "--timeout", "2", "-q"]) == 0
    return out


def test_run_scores_messages_without_being_asked(graded_run):
    doc = json.loads(graded_run.read_text())
    graded = [c for c in doc["cases"] if c.get("rubric")]
    assert graded, "no case carried a rubric block"
    assert all(c["status"] in ("detected", "detected_mislocated")
               for c in graded)
    assert doc["run"]["policy"]["rubric_version"] == rubric.RUBRIC_VERSION
    assert doc["summary"]["rubric"]["graded"] == len(graded)


def test_grade_rewrites_in_place_and_is_idempotent(graded_run, capsys):
    assert main(["grade", str(graded_run), "--cache",
                 str(graded_run.parent / "cache.json")]) == 0
    once = graded_run.read_text()
    assert main(["grade", str(graded_run), "--cache",
                 str(graded_run.parent / "cache.json")]) == 0
    assert graded_run.read_text() == once
    assert "rubric v" in capsys.readouterr().err


def test_grade_reports_the_metadata_coverage_behind_the_scores(graded_run,
                                                               capsys):
    """The number that says whether a low mean is bad messages or a thin
    corpus."""
    main(["grade", str(graded_run), "--cache",
          str(graded_run.parent / "cache.json")])
    err = capsys.readouterr().err
    assert "metadata: cause" in err
    assert "n measured in brackets" in err


def test_tier_b_needs_a_name_attached_to_the_judgement(graded_run, capsys):
    assert main(["grade", str(graded_run), "--tier", "b", "--cache",
                 str(graded_run.parent / "cache.json")]) == 2
    assert "--rater" in capsys.readouterr().err


def test_tier_b_walk_records_what_a_human_said(graded_run, monkeypatch,
                                               capsys):
    answers = iter(["1", "", "", "", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    cache = graded_run.parent / "cache.json"
    assert main(["grade", str(graded_run), "--tier", "b", "--rater", "mb",
                 "--limit", "1", "--cache", str(cache)]) == 0

    doc = json.loads(graded_run.read_text())
    scored = [c for c in doc["cases"]
              if (c.get("rubric") or {}).get("tier") == "B"]
    assert len(scored) == 1
    assert scored[0]["rubric"]["d1"] == 1 and scored[0]["rubric"]["rater"] == "mb"
    assert json.loads(cache.read_text())["schema"].startswith("pss-errsuite/")

    # And a re-grade with no human in the room keeps that judgement.
    assert main(["grade", str(graded_run), "--cache", str(cache)]) == 0
    doc = json.loads(graded_run.read_text())
    assert [c["case"] for c in doc["cases"]
            if (c.get("rubric") or {}).get("tier") == "B"] == \
        [scored[0]["case"]]


def test_triage_sorts_the_work_queue_worst_first(graded_run, capsys):
    assert main(["triage", str(graded_run), "--notes"]) == 0
    out = capsys.readouterr()
    rows = [l for l in out.out.splitlines() if l and not l.startswith(" ")]
    # Ascending D1 -- not ascending composite.  A `detected` case whose
    # message is about the wrong thing outranks a good message missing a
    # fix-it, however the two composites happen to fall.
    firsts = [r.split()[1][0] for r in rows]   # the d1 column
    order = [9 if c == "-" else int(c) for c in firsts]
    assert order == sorted(order), "D1 does not lead the queue"
    assert "worst first" in out.err


def test_triage_lists_the_metadata_backfill_queue(graded_run, capsys):
    assert main(["triage", str(graded_run), "--missing", "cause"]) == 0
    out = capsys.readouterr()
    assert "D1 is unmeasured for them, not bad" in out.err
    assert "FX-MISLOCATED" in out.out


def test_compare_refuses_two_different_rubric_versions(two_runs, tmp_path,
                                                       capsys):
    """Design §5.6: scores from different anchors are never compared -- a
    rubric edit would otherwise read as a change in message quality."""
    a, b = two_runs("a"), two_runs("b")
    doc = json.loads(b.read_text())
    doc["run"]["policy"]["rubric_version"] = "99"
    b.write_text(json.dumps(doc))
    assert main(["compare", str(a), str(b)]) == 2
    err = capsys.readouterr().err
    assert "rubric version" in err and "not on the same scale" in err
