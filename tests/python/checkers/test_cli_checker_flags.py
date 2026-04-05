"""Tests for the new CLI checker flags."""
from __future__ import annotations

import io
import sys
import pytest

from pssparser.cli.app import main


def _run(argv, *, stdin=None):
    """Run main() with captured stdout/stderr; return (exit_code, stdout, stderr)."""
    out = io.StringIO()
    err = io.StringIO()
    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        code = main(argv)
    finally:
        sys.stdout, sys.stderr = old_out, old_err
    return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# --list-checkers
# ---------------------------------------------------------------------------

def test_list_checkers_exit_zero():
    code, out, _ = _run(["--list-checkers"])
    assert code == 0


def test_list_checkers_shows_core():
    _, out, _ = _run(["--list-checkers"])
    assert "core" in out


def test_list_checkers_no_files_needed():
    code, _, _ = _run(["--list-checkers"])
    assert code == 0


# ---------------------------------------------------------------------------
# --list-markers
# ---------------------------------------------------------------------------

def test_list_markers_exit_zero():
    code, _, _ = _run(["--list-markers"])
    assert code == 0


def test_list_markers_shows_pss001():
    _, out, _ = _run(["--list-markers"])
    assert "PSS001" in out


def test_list_markers_shows_pss002():
    _, out, _ = _run(["--list-markers"])
    assert "PSS002" in out


def test_list_markers_shows_columns():
    _, out, _ = _run(["--list-markers"])
    assert "ID" in out
    assert "SEV" in out
    assert "CHECKER" in out
    assert "SUMMARY" in out


# ---------------------------------------------------------------------------
# --describe
# ---------------------------------------------------------------------------

def test_describe_known_id_exit_zero():
    code, _, _ = _run(["--describe", "PSS001"])
    assert code == 0


def test_describe_known_id_shows_summary():
    _, out, _ = _run(["--describe", "PSS001"])
    assert "PSS001" in out


def test_describe_known_id_shows_detail():
    _, out, _ = _run(["--describe", "PSS001"])
    # The PSS001 detail text contains "parser"
    assert "parser" in out.lower() or "syntax" in out.lower()


def test_describe_unknown_id_exit_two():
    code, _, _ = _run(["--describe", "UNKNOWNXXX"])
    assert code == 2


def test_describe_unknown_id_error_message():
    _, _, err = _run(["--describe", "UNKNOWNXXX"])
    assert "error" in err.lower() or "unknown" in err.lower()


# ---------------------------------------------------------------------------
# No source files, no query flag
# ---------------------------------------------------------------------------

def test_no_files_no_query_exit_two():
    code, _, _ = _run([])
    assert code == 2


# ---------------------------------------------------------------------------
# --checker and --no-checker with source files (basic smoke test)
# ---------------------------------------------------------------------------

def test_checker_flag_with_valid_file(tmp_path):
    pss = tmp_path / "valid.pss"
    pss.write_text("component pss_top {\n    action A {}\n}\n")
    code, _, _ = _run(["--checker", "core", str(pss)])
    # 'core' is is_builtin so active() returns nothing; no errors -> exit 0
    assert code == 0


def test_no_checker_flag_unknown_silently_ignored(tmp_path):
    pss = tmp_path / "valid.pss"
    pss.write_text("component pss_top {\n    action A {}\n}\n")
    code, _, _ = _run(["--no-checker", "nonexistent-checker", str(pss)])
    assert code == 0


# ---------------------------------------------------------------------------
# --load-checker
# ---------------------------------------------------------------------------

def test_load_checker_invalid_spec_exits_two():
    code, _, err = _run(["--load-checker", "badspec"])
    assert code == 2
    assert "error" in err.lower()


def test_load_checker_then_list(tmp_path, monkeypatch):
    mod = tmp_path / "mychk.py"
    mod.write_text(
        "from pssparser.checkers import CheckerBase, MarkerDef\n"
        "class MyChecker(CheckerBase):\n"
        "    name = 'my-loaded-checker'\n"
        "    marker_defs = [MarkerDef(id='MLC001', severity='warning', summary='s')]\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    code, out, _ = _run(["--load-checker", "mychk:MyChecker", "--list-checkers"])
    assert code == 0
    assert "my-loaded-checker" in out
