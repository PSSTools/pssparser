"""Runner: isolation, skips, controls, parallelism, determinism."""
from __future__ import annotations

import json
import shutil

import pytest

from pss_errsuite.adapters import make_adapter
from pss_errsuite.case import CaseFormatError, collect_cases
from pss_errsuite.classify import (CLEAN, CONTROL_FAILED, DETECTED, SKIPPED,
                                   SKIPPED_VERSION)
from pss_errsuite.runner import Runner


def run_fixtures(desc, fixture_cases, **kw):
    kw.setdefault("tool_pss", desc.pss)
    runner = Runner(make_adapter(desc), desc, timeout_s=kw.pop("timeout", 3),
                    **kw)
    try:
        return {r.case.case_id: r
                for r in runner.run_all(collect_cases(fixture_cases))}
    finally:
        runner.cleanup()


@pytest.fixture(scope="module")
def runs():
    """One pass over the fixture corpus, shared by every test that only reads
    it.  The corpus deliberately contains a hang and a crash, so re-running it
    per test costs seconds for no information.  Built from scratch rather than
    from the per-test descriptor fixture, which tests are free to mutate."""
    from pss_errsuite.descriptor import load_descriptor
    from conftest import FIXTURE_CASES, SUITE_ROOT
    desc = load_descriptor(SUITE_ROOT / "tools" / "faketool.toml", SUITE_ROOT)
    return run_fixtures(desc, FIXTURE_CASES)


def test_every_status_is_reachable(runs):
    """The fixture corpus exists to exercise the whole vocabulary; if a status
    becomes unreachable, the classifier has drifted from the design."""
    seen = {r.status for r in runs.values()}
    expected = {"detected", "detected_mislocated", "detected_wrong_severity",
                "missed", "clean", "spurious", "control_failed", "crash",
                "timeout", "tool_error", "skipped", "skipped_version"}
    assert expected <= seen, f"unreachable: {sorted(expected - seen)}"


def test_capability_skip_is_not_a_miss(runs):
    run = runs["FX-SKIPPED-CAP"]
    assert run.status == SKIPPED
    assert "json_output" in run.skip_reason
    assert run.result is None, "a skipped case must not invoke the tool"


def test_version_skip_says_both_versions(runs):
    run = runs["FX-SKIPPED-VERSION"]
    assert run.status == SKIPPED_VERSION
    assert "3.1" in run.skip_reason and "3.0" in run.skip_reason


def test_declaring_a_newer_version_makes_the_case_run(faketool_descriptor,
                                                      fixture_cases):
    runs = run_fixtures(faketool_descriptor, fixture_cases, tool_pss="3.1")
    assert runs["FX-SKIPPED-VERSION"].status == DETECTED


def test_control_failure_is_recorded_rather_than_scored(runs):
    run = runs["FX-CONTROL-FAILED"]
    assert run.status == CONTROL_FAILED
    assert run.control_status == "failed"
    assert run.control_error_count == 1
    # The tool *did* report the defect -- that is exactly why the case has to
    # be excluded rather than counted as a detection.
    assert run.result.diagnostics


def test_a_passing_control_is_recorded_too(runs):
    run = runs["FX-DETECTED"]
    assert run.status == DETECTED and run.control_status == CLEAN


def test_lints_are_attached_as_observations(runs):
    run = runs["FX-NOISY-JARGON"]
    assert "G3-jargon" in run.observations.lints
    assert run.observations.error_count == 4
    assert run.observations.noise == 3


# -- isolation ---------------------------------------------------------------

def test_cases_are_never_run_in_the_corpus(tmp_path, faketool_descriptor,
                                           fixture_cases):
    """A tool that drops artifacts beside its input must not touch `cases/`.
    A corpus that mutates when you measure it is not a corpus."""
    work = tmp_path / "cases"
    shutil.copytree(fixture_cases, work)
    before = {p: p.read_bytes() for p in sorted(work.rglob("*"))
              if p.is_file()}
    run_fixtures(faketool_descriptor, work)
    after = {p: p.read_bytes() for p in sorted(work.rglob("*"))
             if p.is_file()}
    assert before == after


def test_scratch_is_removed_on_cleanup(faketool_descriptor, fixture_cases):
    runner = Runner(make_adapter(faketool_descriptor), faketool_descriptor,
                    timeout_s=3)
    root = runner.scratch_root
    assert root.is_dir()
    runner.cleanup()
    assert not root.exists()


# -- parallelism and determinism ---------------------------------------------

def _statuses(desc, cases, jobs):
    return {cid: r.status
            for cid, r in run_fixtures(desc, cases, jobs=jobs).items()}


def test_parallel_and_serial_agree(faketool_descriptor, fixture_cases):
    assert (_statuses(faketool_descriptor, fixture_cases, 1)
            == _statuses(faketool_descriptor, fixture_cases, 4))


def test_two_runs_are_identical_modulo_timing(faketool_descriptor,
                                              fixture_cases, suite_root):
    """Everything except wall time and the run timestamp must be byte-identical
    across runs, or a run-file diff is unreadable."""
    from pss_errsuite import report
    from pss_errsuite.locate import Tolerance

    def once():
        runner = Runner(make_adapter(faketool_descriptor), faketool_descriptor,
                        timeout_s=3)
        try:
            runs = runner.run_all(collect_cases(fixture_cases))
        finally:
            runner.cleanup()
        doc = report.build_document(
            runs, desc=faketool_descriptor, adapter=make_adapter(
                faketool_descriptor),
            tolerance=Tolerance(), severity_floor="error",
            suite_root=suite_root, started="FIXED", duration_s=0.0)
        return doc

    a, b = once(), once()
    for doc in (a, b):
        for case in doc["cases"]:
            case["observations"]["duration_s"] = 0
            if case.get("result"):
                case["result"]["duration_s"] = 0
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


# -- tool directives addressed to the tool being run ----------------------
#
# A `<tool>.<key>` the suite does not consume is only a warning in `validate`,
# which cannot know whose namespace it is looking at.  The runner can: these
# directives were addressed to the tool it is running, so not understanding
# one is an error.  `pssparser.max-errors:` was ignored across the whole
# corpus until this existed -- every volume case measured the default cap.

def _runner_for(desc):
    return Runner(make_adapter(desc), desc, timeout_s=1)


def _case_with(write_case, header):
    return write_case(
        "opt.pss",
        f"//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
        f"{header}package p {{ }}\n")


def test_max_errors_reaches_the_runner_in_either_spelling(
        faketool_descriptor, write_case):
    runner = _runner_for(faketool_descriptor)
    name = faketool_descriptor.name
    try:
        for spelling in ("max-errors", "max_errors"):
            case = _case_with(write_case, f"//! {name}.{spelling}: 3\n")
            assert runner._max_errors_for(case) == 3
    finally:
        runner.cleanup()


def test_an_unconsumed_directive_for_this_tool_is_an_error(
        faketool_descriptor, write_case):
    runner = _runner_for(faketool_descriptor)
    case = _case_with(write_case,
                      f"//! {faketool_descriptor.name}.nonsense: 1\n")
    try:
        with pytest.raises(CaseFormatError, match="no reader consumes"):
            runner._max_errors_for(case)
    finally:
        runner.cleanup()


def test_another_tool_s_directive_is_left_alone(
        faketool_descriptor, write_case):
    """The same directive under a namespace we are not running is ignored --
    otherwise onboarding a third-party tool would break every case it has
    annotated."""
    runner = _runner_for(faketool_descriptor)
    case = _case_with(write_case, "//! vendorx.nonsense: 1\n")
    try:
        assert runner._max_errors_for(case) is None
    finally:
        runner.cleanup()


def test_a_non_integer_max_errors_is_an_error_not_a_silent_default(
        faketool_descriptor, write_case):
    runner = _runner_for(faketool_descriptor)
    case = _case_with(write_case,
                      f"//! {faketool_descriptor.name}.max_errors: many\n")
    try:
        with pytest.raises(CaseFormatError, match="expected an integer"):
            runner._max_errors_for(case)
    finally:
        runner.cleanup()
