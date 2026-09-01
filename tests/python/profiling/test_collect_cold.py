"""Cold collection -- one subprocess per file.

Slower than the rest of the suite (a process launch per case), but the failure
modes here are not reachable in-process.
"""
from __future__ import annotations

import pytest

from pssparser.profiling.collect_cold import collect_cold, collect_cold_file

pytestmark = [pytest.mark.profiling, pytest.mark.slow]


GOOD = "component pss_top {\n    action A { rand int x; constraint x > 0; }\n}\n"

#: Invalid PSS.  The parser reports this and carries on -- it does not crash --
#: which is what makes it usable as a fixture.
BAD = "component pss_top {\n    action A { rand int ; ; }\n}\n"


def _write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


class TestColdCollection:

    def test_profiles_a_file_in_a_fresh_process(self, tmp_path):
        got = collect_cold_file(_write(tmp_path, "good.pss", GOOD), "test")
        assert got is not None
        assert got.mode == "cold"
        assert got.decisions

    def test_a_file_with_syntax_errors_still_yields_a_profile(self, tmp_path):
        """The regression that motivated writing the result to a file.

        The parser's error listener writes diagnostics to *stdout* from C++.
        While the child returned its JSON on stdout, any file with a syntax
        error came back unparseable and was silently counted as a crash --
        dropping precisely the ``parses = false`` material the cold sweep
        exists to cover, and leaving a report that claimed "0 files with
        syntax errors" over a corpus that had three.
        """
        got = collect_cold_file(_write(tmp_path, "bad.pss", BAD), "test")
        assert got is not None, "a file with syntax errors was dropped"
        assert got.syntax_errors > 0
        assert not got.parsed
        assert got.decisions, "no decisions profiled for invalid input"

    def test_reports_rule_names(self, tmp_path):
        got = collect_cold_file(_write(tmp_path, "good.pss", GOOD), "test")
        assert all(d.rule and d.rule != "<unknown>" for d in got.decisions)

    def test_atn_transitions_are_nonzero_when_cold(self, tmp_path):
        """The whole point of paying for a subprocess.

        A fresh process has an empty DFA, so prediction has to walk the ATN.
        In a warm process the same parse makes zero transitions -- see
        ``test_collect.TestDeterminism``.
        """
        got = collect_cold_file(_write(tmp_path, "good.pss", GOOD), "test")
        assert sum(d.sll_atn_transitions for d in got.decisions) > 0


class TestSweep:

    def test_reports_which_files_failed_rather_than_dropping_them(self, tmp_path):
        """A sweep that quietly covers 2 of 3 files reads as though it covered 3."""
        files = [
            (_write(tmp_path, "a.pss", GOOD), "test", True),
            (tmp_path / "missing.pss", "test", True),
            (_write(tmp_path, "b.pss", GOOD), "test", True),
        ]
        profiles, crashed = collect_cold(files)
        assert len(profiles) == 2
        assert [p.name for p in crashed] == ["missing.pss"]
