"""The bundled lint extension (plan F1.12)."""
from __future__ import annotations

import io
import sys

from pssparser.checkers import CheckerManager
from pssparser.cli.app import main


def _list_extensions():
    out = io.StringIO()
    old = sys.stdout
    sys.stdout = out
    try:
        main(["--list-extensions"])
    finally:
        sys.stdout = old
    return out.getvalue()


def test_discovered_when_enabled(lint_enabled):
    m = CheckerManager()
    m.discover()
    info = {e["name"]: e for e in m.list_extensions()}
    assert info["lint"]["bundled"] is True
    assert info["lint"]["dist"] == "pssparser"


def test_absent_under_no_lint():
    # conftest sets PSSPARSER_NO_LINT=1
    m = CheckerManager()
    m.discover()
    assert "lint" not in {e["name"] for e in m.list_extensions()}


def test_present_under_no_extensions(lint_enabled, monkeypatch):
    monkeypatch.setenv("PSSPARSER_NO_EXTENSIONS", "1")
    m = CheckerManager()
    m.discover(load_extensions=False)
    assert "lint" in {e["name"] for e in m.list_extensions()}


def test_list_extensions_marks_it_bundled(lint_enabled):
    assert "(bundled with pssparser)" in _list_extensions()


def test_core_emitted_lint_does_not_need_the_extension(tmp_path):
    """PSSPARSER_NO_LINT skips the runner rules only; the nine core-emitted
    LINT warnings still report under the default profile."""
    src = tmp_path / "m.pss"
    src.write_text("compile if (1) struct q {}\n")
    err = io.StringIO()
    old = sys.stderr
    sys.stderr = err
    try:
        rc = main(["--no-config", str(src)])
    finally:
        sys.stderr = old
    assert rc == 0
    assert "without enclosing braces is deprecated" in err.getvalue()


def test_zero_rules_leave_the_output_unchanged(lint_enabled, tmp_path):
    src = tmp_path / "m.pss"
    src.write_text("component pss_top { action a { } }\n")

    def run():
        err = io.StringIO()
        old = sys.stderr
        sys.stderr = err
        try:
            rc = main(["--no-config", "--lint-profile", "recommended", str(src)])
        finally:
            sys.stderr = old
        return rc, err.getvalue()

    assert run() == (0, "0 errors in 1 file\n")
