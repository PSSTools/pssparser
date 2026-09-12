"""Tests for ``--stats`` rendering and flag handling (S3).

Counting itself is covered by ``test_stats.py``.
"""
import json
from io import StringIO

import pytest

from pssparser.cli.app import _build_parser
from pssparser.cli.commands import cmd_parse
from pssparser.cli.stats import (
    DECL_KEYS,
    RunStats,
    new_decl_counts,
    render_human,
    to_json,
)

MODEL_SRC = """package p {
    struct S { int a; }
}
component C {
    action A { }
}
"""


@pytest.fixture
def model(tmp_path):
    p = tmp_path / "m.pss"
    p.write_text(MODEL_SRC)
    return str(p)


def _run(files, **kw):
    out, err = StringIO(), StringIO()
    rc = cmd_parse(files if isinstance(files, list) else [files],
                   stdout=out, stderr=err, **kw)
    return rc, out.getvalue(), err.getvalue()


# -- human rendering -------------------------------------------------------

def _stats(**decls):
    s = RunStats(files=1)
    s.decls = new_decl_counts()
    s.decls.update(decls)
    return s


class TestHumanRendering:
    def test_zero_rows_are_dropped(self):
        """A model with no streams should not read a line saying so."""
        text = render_human(_stats(actions=2))
        assert "2 actions" in text
        assert "stream" not in text
        assert "resource" not in text

    def test_all_zero_reports_none(self):
        assert "declarations: none" in render_human(_stats())

    def test_pluralisation(self):
        text = render_human(_stats(actions=1, components=2, constraints=1))
        assert "1 action" in text and "1 actions" not in text
        assert "2 components" in text
        assert "1 constraint block" in text and "blocks" not in text

    def test_file_count_pluralises(self):
        s = _stats(actions=1)
        s.files = 1
        assert "1 file processed" in render_human(s)
        s.files = 3
        assert "3 files processed" in render_human(s)

    def test_timing_row_absent_when_empty(self):
        assert "timing" not in render_human(_stats(actions=1))

    def test_timing_row_present_when_populated(self):
        s = _stats(actions=1)
        s.timings_ns = {"link": 1_500_000}
        assert "link 1.5ms" in render_human(s)

    def test_diagnostics_row_absent_when_empty(self):
        assert "diagnostics" not in render_human(_stats(actions=1))


# -- JSON rendering --------------------------------------------------------

class TestJsonRendering:
    def test_every_decl_key_is_present_even_at_zero(self):
        """The opposite of the human rule, deliberately.

        A CI consumer doing ``.stats.decls.actions`` should never need a
        missing-key branch.
        """
        doc = to_json(_stats(actions=1))
        assert set(doc["decls"]) == set(DECL_KEYS)
        assert doc["decls"]["streams"] == 0

    def test_timing_key_omitted_without_timings(self):
        assert "timing_ms" not in to_json(_stats(actions=1))

    def test_timing_reported_in_milliseconds(self):
        s = _stats(actions=1)
        s.timings_ns = {"link": 2_500_000}
        assert to_json(s)["timing_ms"] == {"link": 2.5}


# -- CLI integration -------------------------------------------------------

class TestCliIntegration:
    def test_stats_absent_by_default(self, model):
        rc, _, err = _run(model)
        assert rc == 0
        assert "stats:" not in err

    def test_stats_written_to_stderr_after_the_summary(self, model):
        rc, _, err = _run(model, show_stats=True, stats_timing=False)
        assert rc == 0
        lines = [ln for ln in err.splitlines() if ln.strip()]
        assert lines[0].endswith("in 1 file")
        assert lines[1].startswith("stats:")
        assert "1 package, 1 component, 1 action, 1 struct, 1 field" in err

    def test_no_timing_output_is_byte_stable(self, model):
        _, _, first = _run(model, show_stats=True, stats_timing=False)
        _, _, second = _run(model, show_stats=True, stats_timing=False)
        assert first == second
        assert "timing" not in first

    def test_timing_included_by_default(self, model):
        _, _, err = _run(model, show_stats=True)
        assert "timing:" in err
        # The standard-library load is its own row, not folded into parse.
        assert "stdlib" in err
        assert "parse (incl. read)" in err

    def test_quiet_stats_prints_only_stats(self, model):
        rc, _, err = _run(model, show_stats=True, stats_timing=False, quiet=True)
        assert rc == 0
        assert err.startswith("stats:")
        assert "in 1 file" not in err

    def test_json_stats_is_one_document(self, model):
        rc, out, _ = _run(model, use_json=True, show_stats=True,
                          stats_timing=False)
        assert rc == 0
        doc = json.loads(out)
        assert set(doc) == {"diagnostics", "summary", "stats"}
        assert doc["stats"]["decls"]["actions"] == 1

    def test_json_has_no_stats_key_unless_asked(self, model):
        _, out, _ = _run(model, use_json=True)
        assert "stats" not in json.loads(out)

    def test_stats_does_not_change_the_exit_code(self, tmp_path):
        bad = tmp_path / "bad.pss"
        bad.write_text("struct S { int a }\n")
        without, _, _ = _run(str(bad))
        with_stats, _, err = _run(str(bad), show_stats=True, stats_timing=False)
        assert without == with_stats == 1
        # Stats are still reported for a failed run.
        assert "stats:" in err

    def test_diagnostic_histogram_reaches_the_report(self, tmp_path):
        bad = tmp_path / "bad.pss"
        bad.write_text("struct S { int a }\n")
        _, _, err = _run(str(bad), show_stats=True, stats_timing=False)
        assert "diagnostics:" in err
        assert "PSS0" in err


# -- flag plumbing ---------------------------------------------------------

class TestFlags:
    def test_stats_no_timing_implies_stats(self):
        """``--stats-no-timing`` is a variant of ``--stats``, not a modifier.

        Mirrors how ``app.main`` derives the two ``cmd_parse`` arguments.
        """
        args = _build_parser().parse_args(["--stats-no-timing", "f.pss"])
        show_stats = args.stats or args.stats_no_timing
        stats_timing = not args.stats_no_timing
        assert show_stats and not stats_timing

    def test_stats_default_off(self):
        args = _build_parser().parse_args(["f.pss"])
        assert not args.stats
        assert not args.stats_no_timing
