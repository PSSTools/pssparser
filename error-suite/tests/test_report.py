"""Run-file shape and the recomputability property.

The run file has to be *self-contained*: someone fixing diagnostics should be
able to read, diff and re-score it without the corpus, and every headline
number in it must be derivable from `cases[]` alone.  That last property is
tested by recomputing the metrics here.
"""
from __future__ import annotations

import json

import pytest

from pss_errsuite import report
from pss_errsuite.adapters import make_adapter
from pss_errsuite.case import collect_cases
from pss_errsuite.locate import Tolerance
from pss_errsuite.runner import Runner

REQUIRED_RUN_KEYS = {"id", "started", "duration_s", "host", "suite", "policy"}
REQUIRED_TOOL_KEYS = {"name", "version", "pss", "descriptor", "invocation",
                      "capabilities", "parse_confidence"}
REQUIRED_CASE_KEYS = {"case", "class", "title", "files", "source_sha256",
                      "expect", "status", "observations"}


@pytest.fixture(scope="module")
def document():
    from conftest import FIXTURE_CASES, SUITE_ROOT
    from pss_errsuite.descriptor import load_descriptor
    desc = load_descriptor(SUITE_ROOT / "tools" / "faketool.toml", SUITE_ROOT)
    adapter = make_adapter(desc)
    adapter.probe_version()
    runner = Runner(adapter, desc, timeout_s=3, tool_pss=desc.pss)
    try:
        runs = runner.run_all(collect_cases(FIXTURE_CASES))
    finally:
        runner.cleanup()
    return report.build_document(
        runs, desc=desc, adapter=adapter, tolerance=Tolerance("token:2"),
        severity_floor="error", suite_root=SUITE_ROOT, started="2026-01-01T00:00:00Z",
        duration_s=1.0)


def test_schema_and_top_level_shape(document):
    assert document["schema"] == "pss-errsuite/run/1"
    assert REQUIRED_RUN_KEYS <= set(document["run"])
    assert REQUIRED_TOOL_KEYS <= set(document["tool"])
    assert set(document["summary"]) == {"by_status", "by_class", "metrics",
                                        "rubric"}


def test_policy_is_recorded_so_two_runs_are_comparable(document):
    policy = document["run"]["policy"]
    assert policy["tolerance"] == "token:2"
    assert policy["severity_floor"] == "error"
    assert "rubric_version" in policy      # None until X-3b


def test_every_case_carries_what_a_reader_needs(document):
    for case in document["cases"]:
        assert REQUIRED_CASE_KEYS <= set(case), case["case"]
        assert case["source"], "source is embedded so the file stands alone"
        if case["status"] not in ("skipped", "skipped_version"):
            assert "result" in case


def test_diagnostics_are_byte_exact(document):
    """The wording *is* the object of study, so messages are never
    normalized."""
    noisy = next(c for c in document["cases"] if c["case"] == "FX-NOISY-JARGON")
    messages = [d["message"] for d in noisy["result"]["diagnostics"]]
    assert 'mismatched input \'"x"\' expecting {\'8\', ID}' in messages


def test_status_counts_sum_to_the_case_count(document):
    assert (sum(document["summary"]["by_status"].values())
            == len(document["cases"]))
    assert document["run"]["suite"]["case_count"] == len(document["cases"])


def test_metrics_are_recomputable_from_cases_alone(document):
    """If this ever fails, a metric has acquired a hidden input and the run
    file can no longer be re-scored under a different policy."""
    assert (report.compute_metrics(document["cases"])
            == document["summary"]["metrics"])


def test_every_rate_is_reported_with_its_denominator(document):
    m = document["summary"]["metrics"]
    for rate in ("detection", "localization", "false_positive",
                 "identifiability"):
        assert f"{rate}_denominator" in m


def test_skipped_cases_are_never_counted_as_misses(document):
    by_status = document["summary"]["by_status"]
    assert by_status["skipped"] >= 1 and by_status["skipped_version"] >= 1
    required = [c for c in document["cases"]
                if c["expect"]["detect"] == "required"
                and c["expect"]["kind"] != "accept"]
    counted = [c for c in required
               if c["status"] in ("detected", "detected_mislocated", "missed",
                                  "detected_wrong_severity")]
    assert document["summary"]["metrics"]["detection_denominator"] == len(counted)


def test_no_source_drops_only_the_source(document, tmp_path):
    from conftest import FIXTURE_CASES, SUITE_ROOT
    from pss_errsuite.descriptor import load_descriptor
    desc = load_descriptor(SUITE_ROOT / "tools" / "faketool.toml", SUITE_ROOT)
    adapter = make_adapter(desc)
    runner = Runner(adapter, desc, timeout_s=3, tool_pss=desc.pss)
    try:
        runs = runner.run_all(collect_cases(FIXTURE_CASES))
    finally:
        runner.cleanup()
    doc = report.build_document(
        runs, desc=desc, adapter=adapter, tolerance=Tolerance(),
        severity_floor="error", suite_root=SUITE_ROOT, started="X",
        duration_s=0.0, include_source=False)
    for case in doc["cases"]:
        assert "source" not in case
        assert case["source_sha256"], "the hash is always present"


def test_write_round_trips(document, tmp_path):
    path = tmp_path / "runs" / "x.json"
    report.write(document, path)
    assert json.loads(path.read_text()) == document
