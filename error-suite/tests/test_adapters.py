"""Adapters, against the fake tool only.

No real PSS tool is involved anywhere in this module, which is the point:
adapter behaviour (argv templating, timeouts, crash detection, scraping) is
testable without anyone's compiler installed.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from pss_errsuite.adapters.base import CaseOpts
from pss_errsuite.adapters.subprocess_cli import SubprocessAdapter, build_argv

OPTS = CaseOpts(timeout_s=10)


@pytest.fixture
def case_file(tmp_path):
    def _write(*directives, body="struct s { int a; }"):
        p = tmp_path / "case.pss"
        p.write_text("\n".join(f"//FAKE: {d}" for d in directives)
                     + ("\n" if directives else "") + body + "\n")
        return p
    return _write


# -- argv templating ---------------------------------------------------------

def test_standalone_files_placeholder_expands_to_many(faketool_descriptor):
    argv = build_argv(faketool_descriptor,
                      [Path("/a/one.pss"), Path("/a/two.pss")], OPTS)
    assert argv[-2:] == ["/a/one.pss", "/a/two.pss"]


def test_embedded_files_placeholder_rejects_a_multi_file_case(
        faketool_descriptor):
    desc = faketool_descriptor
    desc.argv = [a if a != "{files}" else "--src={files}" for a in desc.argv]
    with pytest.raises(ValueError, match="standalone"):
        build_argv(desc, [Path("a.pss"), Path("b.pss")], OPTS)


def test_file_argv_repeats_a_flag_before_every_file(faketool_descriptor):
    """Some tools take `-pss a.pss -pss b.pss`, not a bare list of paths."""
    desc = faketool_descriptor
    desc.file_argv = ["-pss", "{file}"]
    argv = build_argv(desc, [Path("/a/one.pss"), Path("/a/two.pss")], OPTS)
    assert argv[-4:] == ["-pss", "/a/one.pss", "-pss", "/a/two.pss"]


def test_file_argv_supports_an_attached_value(faketool_descriptor):
    """`--file=<path>` is one argv element, not two -- the substitution is on
    the element, not a positional append, so both spellings work."""
    desc = faketool_descriptor
    desc.file_argv = ["--file={file}"]
    argv = build_argv(desc, [Path("/a/one.pss"), Path("/a/two.pss")], OPTS)
    assert argv[-2:] == ["--file=/a/one.pss", "--file=/a/two.pss"]


def test_the_default_file_argv_is_a_bare_path(faketool_descriptor):
    """Every existing descriptor omits file_argv, so the default must keep
    producing exactly what it produced before this option existed."""
    assert faketool_descriptor.file_argv == ["{file}"]
    argv = build_argv(faketool_descriptor, [Path("/a/one.pss")], OPTS)
    assert argv[-1] == "/a/one.pss"


def test_file_argv_reaches_the_tool_and_its_diagnostics_come_back(
        faketool_descriptor, case_file, tmp_path):
    """End to end, not just argv assembly: the assembled command line has to be
    executable and both files have to be read.

    The argv assertion is not redundant with the templating tests above -- on
    its own, the run would still pass if `file_argv` were ignored outright,
    since a bare list of paths is also a command line faketool accepts.
    """
    desc = faketool_descriptor
    desc.file_argv = ["-pss", "{file}"]
    one = case_file('emit 1:1 error "first" code=FAKE001')
    two = tmp_path / "second.pss"
    two.write_text('//FAKE: emit 2:2 error "second" code=FAKE002\n')

    assert build_argv(desc, [one, two], OPTS)[-4:] == [
        "-pss", str(one), "-pss", str(two)]

    result = SubprocessAdapter(desc).run([one, two], OPTS)
    assert [d.message for d in result.diagnostics] == ["first", "second"]


def test_max_errors_flag_is_appended_only_when_the_case_asks(
        faketool_descriptor):
    assert "--max-errors" not in build_argv(
        faketool_descriptor, [Path("a.pss")], CaseOpts())
    argv = build_argv(faketool_descriptor, [Path("a.pss")],
                      CaseOpts(max_errors=0))
    assert argv[-2:] == ["--max-errors", "0"]


# -- regex scraping ----------------------------------------------------------

def test_regex_adapter_scrapes_location_severity_and_code(
        faketool_descriptor, case_file):
    path = case_file('emit 3:7 error "expected \';\'" code=FAKE001')
    result = SubprocessAdapter(faketool_descriptor).run([path], OPTS)
    assert result.parse_confidence == "regex"
    assert len(result.diagnostics) == 1
    d = result.diagnostics[0]
    assert (d.severity, d.line, d.col, d.code) == ("error", 3, 7, "FAKE001")
    assert d.message == "expected ';'"
    assert d.raw is not None


def test_continuation_lines_fold_into_the_primary(faketool_descriptor,
                                                  case_file):
    """A continuation is the same finding.  Counting it as a second
    diagnostic would make the tool look noisier than it is."""
    path = case_file('emit 3:7 error "duplicate name" '
                     'related=1:1:"declared here"')
    result = SubprocessAdapter(faketool_descriptor).run([path], OPTS)
    assert len(result.diagnostics) == 1
    assert "declared here" in result.diagnostics[0].message


# -- JSON ---------------------------------------------------------------------

def test_json_adapter_reads_structure_including_related(
        faketool_json_descriptor, case_file):
    path = case_file('emit 3:7 error "duplicate name" end=12 code=F1 '
                     'related=1:1:"declared here" suggestion="rename it"')
    result = SubprocessAdapter(faketool_json_descriptor).run([path], OPTS)
    assert result.parse_confidence == "structured"
    d = result.diagnostics[0]
    assert (d.line, d.col, d.end_col, d.code) == (3, 7, 12, "F1")
    assert d.suggestion == "rename it"
    assert d.related[0].label == "declared here"


def test_end_col_without_end_line_is_normalized_to_the_same_line(
        faketool_json_descriptor, case_file):
    """pssparser's --json has no `end_line` (plan §0.2).  Consumers should not
    each have to know that, and the absence is a tool limitation rather than a
    parse failure, so confidence stays structured."""
    path = case_file('emit 4:2 error "x" end=9')
    result = SubprocessAdapter(faketool_json_descriptor).run([path], OPTS)
    d = result.diagnostics[0]
    assert (d.end_line, d.end_col) == (4, 9)
    assert result.parse_confidence == "structured"


def test_unreadable_output_on_the_json_path_lowers_confidence(
        faketool_json_descriptor, case_file):
    path = case_file("garbage")
    result = SubprocessAdapter(faketool_json_descriptor).run([path], OPTS)
    assert result.diagnostics == ()
    assert result.parse_confidence == "none"


def test_silence_on_a_clean_file_keeps_full_confidence(
        faketool_json_descriptor, case_file):
    path = case_file()
    result = SubprocessAdapter(faketool_json_descriptor).run([path], OPTS)
    assert result.diagnostics == ()
    assert result.parse_confidence == "structured"


# -- failure modes -----------------------------------------------------------

def test_timeout_kills_the_tool_and_is_recorded(faketool_descriptor,
                                                case_file):
    path = case_file("hang")
    t0 = time.perf_counter()
    result = SubprocessAdapter(faketool_descriptor).run(
        [path], CaseOpts(timeout_s=1))
    assert result.timed_out is True
    assert result.exit_code is None
    assert time.perf_counter() - t0 < 20, "the kill did not take"


def test_a_signal_death_is_a_crash(faketool_descriptor, case_file):
    result = SubprocessAdapter(faketool_descriptor).run(
        [case_file("abort")], OPTS)
    assert result.crashed is True


def test_a_traceback_is_a_crash_even_with_a_normal_exit_code(
        faketool_descriptor, case_file):
    result = SubprocessAdapter(faketool_descriptor).run(
        [case_file("traceback")], OPTS)
    assert result.crashed is True


def test_a_non_zero_exit_with_diagnostics_is_not_a_crash(faketool_descriptor,
                                                         case_file):
    """Exit 1 with errors reported is a tool doing its job."""
    result = SubprocessAdapter(faketool_descriptor).run(
        [case_file('emit 3:1 error "nope"')], OPTS)
    assert result.exit_code == 1
    assert result.crashed is False
    assert result.invocation_error is None


def test_an_undeclared_exit_code_with_no_output_is_an_invocation_error(
        faketool_descriptor, case_file):
    result = SubprocessAdapter(faketool_descriptor).run(
        [case_file("exit 3")], OPTS)
    assert result.invocation_error is not None
    assert result.crashed is False


def test_a_missing_binary_is_an_invocation_error_not_an_exception(
        faketool_descriptor, case_file):
    desc = faketool_descriptor
    desc.argv = ["definitely-not-a-real-tool-xyz", "{files}"]
    result = SubprocessAdapter(desc).run([case_file()], OPTS)
    assert "could not run" in result.invocation_error
    assert result.parse_confidence == "none"


def test_output_is_truncated_but_kept(faketool_descriptor, case_file, tmp_path):
    from pss_errsuite.adapters import subprocess_cli
    path = case_file(*[f'emit 1:{i} error "{"x" * 200}"' for i in range(200)])
    result = SubprocessAdapter(faketool_descriptor).run([path], OPTS)
    assert len(result.stdout) <= subprocess_cli.CAPTURE_LIMIT + 100
    assert "truncated" in result.stdout
