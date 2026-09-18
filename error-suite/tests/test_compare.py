"""Comparison (design §7).

Every test here builds its run files by hand.  `compare` is pure -- run files
in, comparison out -- so involving a real tool would only make the tests slower
and the expectations less exact.  The one thing that cannot be faked is the
refusal to join runs measured under different policies, and that gets its own
tests because the failure it prevents is a silently wrong number.
"""
from __future__ import annotations

import json

import pytest

from pss_errsuite import compare as C
from pss_errsuite.report import SCHEMA as RUN_SCHEMA

SOURCE = "//! case: X\nstruct s {\n    int a\n}\n"


def case_doc(cid="C-1", *, status="detected", kind="error", detect="required",
             cls="syntax.punct", count=1, message="expected ';'", line=3,
             col=10, rubric=None, source=SOURCE):
    """One `cases[]` entry, shaped exactly as `report.case_document` writes it."""
    doc = {
        "case": cid,
        "class": cls,
        "title": "a case",
        "source": source,
        "expect": {"kind": kind, "detect": detect, "count": 1},
        "status": status,
        "observations": {"error_count": count,
                         "primary_index": 0 if message else None},
        "result": {"diagnostics": (
            [{"severity": "error", "message": message, "file": "c.pss",
              "line": line, "col": col}] if message else [])},
    }
    if kind != "accept":
        doc["expect"]["at"] = {"line": 3, "col": 10}
    if rubric is not None:
        doc["rubric"] = {"composite": rubric}
    return doc


def run_doc(cases, *, name="toola", tolerance="token:2",
            severity_floor="error", revision="git:abc123"):
    return {
        "schema": RUN_SCHEMA,
        "run": {"suite": {"revision": revision, "case_count": len(cases)},
                "policy": {"tolerance": tolerance,
                           "severity_floor": severity_floor,
                           "rubric_version": None},
                "warnings": []},
        "tool": {"name": name, "version": "1.0", "pss": "3.1",
                 "descriptor": f"{name}.toml", "parse_confidence": "structured"},
        "summary": {"metrics": {"detection_rate": 0.9,
                                "detection_denominator": 10,
                                "localization_rate": 1.0,
                                "localization_denominator": 9}},
        "cases": cases,
    }


@pytest.fixture
def write_run(tmp_path):
    def _write(stem, doc):
        path = tmp_path / f"{stem}.json"
        path.write_text(json.dumps(doc), encoding="utf-8")
        return path
    return _write


def tag_of(document, cid):
    for c in document["cases"]:
        if c["case"] == cid:
            return c["divergence"]
    raise AssertionError(f"{cid} not in the comparison")


# -- the tag table (design §7) ----------------------------------------------

@pytest.mark.parametrize("a,b,expected", [
    (dict(status="detected"), dict(status="detected"), C.AGREE),
    (dict(status="missed", message=None),
     dict(status="detected"), C.WE_MISS),
    (dict(status="detected"),
     dict(status="missed", message=None), C.WE_CATCH),
    (dict(status="missed", message=None),
     dict(status="missed", message=None), C.BOTH_MISS),
    (dict(status="detected_mislocated"),
     dict(status="detected"), C.WE_MISLOCATE),
    (dict(status="detected"),
     dict(status="detected_mislocated"), C.THEY_MISLOCATE),
    # `wrong_severity` is a degraded diagnostic, not a miss -- it folds onto
    # the location-quality axis, below `mislocated`.
    (dict(status="detected_wrong_severity"),
     dict(status="detected_mislocated"), C.WE_MISLOCATE),
    (dict(status="detected_wrong_severity"),
     dict(status="missed", message=None), C.WE_CATCH),
    (dict(status="detected", count=5), dict(status="detected", count=1),
     C.WE_NOISIER),
    (dict(status="detected", count=1), dict(status="detected", count=5),
     C.THEY_NOISIER),
    # One extra error is within tolerance: recovery strategies differ.
    (dict(status="detected", count=2), dict(status="detected", count=1),
     C.AGREE),
    (dict(status="control_failed"), dict(status="detected"), C.INCOMPARABLE),
    (dict(status="detected"), dict(status="skipped"), C.INCOMPARABLE),
    (dict(status="detected"), dict(status="crash"), C.INCOMPARABLE),
    (dict(status="detected"), dict(status="tool_error"), C.INCOMPARABLE),
    (dict(status="clean", kind="accept", message=None),
     dict(status="clean", kind="accept", message=None), C.AGREE),
    (dict(status="spurious", kind="accept"),
     dict(status="clean", kind="accept", message=None), C.WE_NOISIER),
    (dict(status="clean", kind="accept", message=None),
     dict(status="spurious", kind="accept"), C.THEY_NOISIER),
    (dict(status="detected", rubric=2.0), dict(status="detected", rubric=2.5),
     C.WE_VAGUER),
    (dict(status="detected", rubric=2.9), dict(status="detected", rubric=2.4),
     C.THEY_VAGUER),
    # Below the 0.25 threshold: not a meaningful difference.
    (dict(status="detected", rubric=2.5), dict(status="detected", rubric=2.4),
     C.AGREE),
])
def test_every_tag(write_run, a, b, expected):
    kind = a.get("kind", "error")
    left = write_run("a", run_doc([case_doc(**a)], name="a"))
    right = write_run("b", run_doc([case_doc(**{"kind": kind, **b})], name="b"))
    assert tag_of(C.compare([left, right]), "C-1") == expected


def test_the_rubric_axis_is_inert_without_scores(write_run):
    """Tier A lands in X-3b.  Until then an absent score must read as
    `unscored`, never as a bad score -- otherwise every case in every
    comparison would be tagged `we_vaguer` the moment one tool is graded."""
    left = write_run("a", run_doc([case_doc()], name="a"))
    right = write_run("b", run_doc([case_doc(rubric=3.0)], name="b"))
    doc = C.compare([left, right])
    assert tag_of(doc, "C-1") == C.AGREE
    assert doc["cases"][0]["rubric"] == "unscored"

    md = C.render_markdown(doc)
    assert "Unscored" in md
    assert "not** a finding" in md


def test_a_case_diverging_on_two_axes_is_counted_once(write_run):
    """Tags partition the shared cases, so the summary column has to sum to
    the shared case count -- a case that is both mislocated and noisier must
    not appear in two rows."""
    left = write_run("a", run_doc(
        [case_doc(status="detected_mislocated", count=9)], name="a"))
    right = write_run("b", run_doc([case_doc()], name="b"))
    doc = C.compare([left, right])
    counts = doc["summary"]["by_tag"]["b"]
    assert counts[C.WE_MISLOCATE] == 1
    assert sum(counts.values()) == doc["compare"]["shared_case_count"] == 1


# -- refusals ----------------------------------------------------------------

@pytest.mark.parametrize("key,value", [("tolerance", "exact"),
                                       ("severity_floor", "warning")])
def test_runs_measured_under_different_policies_are_refused(write_run, key,
                                                            value):
    left = write_run("a", run_doc([case_doc()], name="a"))
    right = write_run("b", run_doc([case_doc()], name="b", **{key: value}))
    with pytest.raises(C.CompareError) as e:
        C.compare([left, right])
    assert key in str(e.value)
    # The message has to say what to do about it, not just that it refused.
    assert "Re-run" in str(e.value)


def test_a_file_that_is_not_a_run_file_is_refused(write_run, tmp_path):
    left = write_run("a", run_doc([case_doc()], name="a"))
    junk = tmp_path / "junk.json"
    junk.write_text('{"schema": "something/else"}')
    with pytest.raises(C.CompareError, match="not a pss-errsuite/run"):
        C.compare([left, junk])


def test_one_run_file_is_refused(write_run):
    with pytest.raises(C.CompareError, match="at least two"):
        C.compare([write_run("a", run_doc([case_doc()]))])


# -- joining -----------------------------------------------------------------

def test_three_way_compare_tags_each_pair_against_the_baseline(write_run):
    a = write_run("a", run_doc([case_doc(status="missed", message=None)],
                               name="a"))
    b = write_run("b", run_doc([case_doc()], name="b"))
    c = write_run("c", run_doc([case_doc(status="missed", message=None)],
                               name="c"))
    doc = C.compare([a, b, c])
    case = doc["cases"][0]
    assert case["tags"] == {"b": C.WE_MISS, "c": C.BOTH_MISS}
    # Ambiguous with three runs, so it is simply not written.
    assert "divergence" not in case
    # `we_miss` against *any* run is still a case we miss.
    assert [c["case"] for c in C.cases_tagged(doc, C.WE_MISS)] == ["C-1"]


def test_cases_missing_from_one_run_are_excluded_and_reported(write_run):
    a = write_run("a", run_doc([case_doc("C-1"), case_doc("C-2")], name="a"))
    b = write_run("b", run_doc([case_doc("C-1")], name="b"))
    doc = C.compare([a, b])
    assert doc["compare"]["shared_case_count"] == 1
    assert doc["only_in"] == {"a": ["C-2"]}
    assert any("not present in every run" in w
               for w in doc["compare"]["warnings"])


def test_two_runs_of_the_same_tool_get_distinct_labels(write_run, tmp_path):
    """The X-3 exit criterion is two pssparser descriptors compared, so equal
    file stems have to stay addressable."""
    a = tmp_path / "x" / "pssparser.json"
    b = tmp_path / "y" / "pssparser.json"
    for path in (a, b):
        path.parent.mkdir()
        path.write_text(json.dumps(run_doc([case_doc()])))
    doc = C.compare([a, b])
    assert [r["label"] for r in doc["compare"]["runs"]] == ["pssparser",
                                                            "pssparser#2"]


def test_a_differing_corpus_revision_warns_but_does_not_refuse(write_run):
    a = write_run("a", run_doc([case_doc()], name="a", revision="git:aaa"))
    b = write_run("b", run_doc([case_doc()], name="b", revision="git:bbb"))
    doc = C.compare([a, b])
    assert any("revision" in w for w in doc["compare"]["warnings"])


# -- Markdown ----------------------------------------------------------------

def test_markdown_carries_the_banner_and_the_high_value_list(write_run):
    a = write_run("a", run_doc([case_doc(status="missed", message=None)],
                               name="a"))
    b = write_run("b", run_doc([case_doc(message="missing ';'")], name="b"))
    doc = C.compare([a, b])
    md = C.render_markdown(doc, source_of=C.source_lookup(
        [json.loads(p.read_text()) for p in (a, b)]))

    assert C.BANNER in md
    assert "## Cases we miss (1)" in md
    # The source is quoted, so the reader can judge the case without opening it.
    assert "int a" in md
    assert "missing ';'" in md
    # Every section heading is present even when empty, so a missing section
    # means a rendering bug rather than "nothing to report".
    for heading in ("Divergences", "Wording study", "Neither tool diagnoses",
                    "Error-count divergences", "Incomparable"):
        assert f"## {heading}" in md


def test_markdown_says_why_each_case_was_incomparable(write_run):
    """An `incomparable` count alone can hide a third of the corpus being
    skipped; the reason is what distinguishes that from a crash."""
    skipped = case_doc(status="skipped", message=None)
    skipped["skip_reason"] = "tool does not declare capability 'max_errors'"
    a = write_run("a", run_doc([case_doc()], name="a"))
    b = write_run("b", run_doc([skipped], name="b"))
    md = C.render_markdown(C.compare([a, b]))
    assert "## Incomparable (1)" in md
    assert "max_errors" in md


def test_markdown_reports_count_divergence_without_calling_it_wrong(write_run):
    a = write_run("a", run_doc([case_doc(count=21)], name="a"))
    b = write_run("b", run_doc([case_doc(count=50)], name="b"))
    md = C.render_markdown(C.compare([a, b]))
    assert "## Error-count divergences (1)" in md
    assert "| 21 | 50 |" in md
    assert "not a verdict" in md


def test_the_readme_quotes_the_banner_verbatim():
    """The banner is the one part of the output that is a *policy*, so the
    README has to show the exact text.  Quoting it by hand would let the two
    drift, and a drifted banner is one someone edits out without noticing what
    it was for."""
    from conftest import SUITE_ROOT
    assert C.BANNER in (SUITE_ROOT / "README.md").read_text(encoding="utf-8")


def test_markdown_without_sources_still_renders(write_run):
    """`run --no-source` drops case text; the report degrades to messages."""
    stripped = case_doc(status="missed", message=None)
    del stripped["source"]
    a = write_run("a", run_doc([stripped], name="a"))
    b = write_run("b", run_doc([case_doc()], name="b"))
    md = C.render_markdown(C.compare([a, b]))
    assert "## Cases we miss (1)" in md
    assert "```pss" not in md
