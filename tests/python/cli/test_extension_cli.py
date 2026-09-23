"""CLI-level tests for extension discovery: --list-extensions, --no-extensions,
and how extension-load failures reach the diagnostic stream (X4).
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.checkers import (
    CHECKER_GROUP,
    EXTENSION_GROUP,
    NO_EXTENSIONS_ENV,
)
from pssparser.checkers import manager as manager_mod
from pssparser.cli.app import main

from tests.python.checkers.test_extensions import FakeEP, make_checker, make_module


def _run(argv):
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


@pytest.fixture
def eps(monkeypatch):
    groups = {EXTENSION_GROUP: [], CHECKER_GROUP: []}
    monkeypatch.setattr(
        manager_mod, "_entry_points", lambda group: list(groups.get(group, []))
    )
    monkeypatch.delenv(NO_EXTENSIONS_ENV, raising=False)
    return groups


@pytest.fixture
def valid_pss(tmp_path):
    f = tmp_path / "valid.pss"
    f.write_text("component pss_top {\n    action A {}\n}\n")
    return str(f)


def _extension(name, checker_name, marker_id, *, description="", **kw):
    def register(reg):
        reg.description = description
        reg.add_checker(make_checker(checker_name, marker_id))
    return FakeEP(name, make_module(name.replace("-", "_"), register=register), **kw)


# ---------------------------------------------------------------------------
# --list-extensions
# ---------------------------------------------------------------------------

def test_list_extensions_with_none_installed(eps):
    code, out, _ = _run(["--list-extensions"])
    assert code == 0
    assert "No checker extensions installed" in out


def test_list_extensions_needs_no_source_files(eps):
    code, _, _ = _run(["--list-extensions"])
    assert code == 0


def test_list_extensions_output(eps):
    eps[EXTENSION_GROUP] = [
        _extension("acme-rules", "acme-naming", "ACM001",
                   description="Acme house rules",
                   dist="acme-pss-rules", version="2.3.0"),
        _extension("zeta-rules", "zeta-flow", "ZET001",
                   description="Zeta flow rules", dist="zeta-rules", version="0.1.0"),
    ]
    code, out, _ = _run(["--list-extensions"])
    assert code == 0
    assert out == (
        "Installed extensions (2):\n"
        "  acme-rules 2.3.0 [acme-pss-rules]\n"
        "    Acme house rules\n"
        "    checkers: acme-naming\n"
        "  zeta-rules 0.1.0\n"
        "    Zeta flow rules\n"
        "    checkers: zeta-flow\n"
    )


def test_list_extensions_marks_a_legacy_entry_point(eps):
    eps[CHECKER_GROUP] = [FakeEP("legacy", make_checker("legacy", "LEG001"))]
    _, out, _ = _run(["--list-extensions"])
    assert "single-checker entry point" in out


# ---------------------------------------------------------------------------
# --no-extensions
# ---------------------------------------------------------------------------

def test_no_extensions_hides_extension_checkers(eps):
    eps[EXTENSION_GROUP] = [_extension("acme-rules", "acme-naming", "ACM001")]

    _, with_ext, _ = _run(["--list-checkers"])
    assert "acme-naming" in with_ext

    _, without, _ = _run(["--no-extensions", "--list-checkers"])
    assert "acme-naming" not in without
    assert "core" in without


def test_no_extensions_suppresses_a_load_failure(eps):
    eps[EXTENSION_GROUP] = [
        FakeEP("broken", None, raises=ImportError("nope"))
    ]
    _, _, err = _run(["--list-checkers"])
    assert "PSS030" in err

    _, _, err = _run(["--no-extensions", "--list-checkers"])
    assert "PSS030" not in err


def test_no_extensions_env_var_is_honoured(eps, monkeypatch):
    eps[EXTENSION_GROUP] = [_extension("acme-rules", "acme-naming", "ACM001")]
    monkeypatch.setenv(NO_EXTENSIONS_ENV, "1")
    _, out, _ = _run(["--list-checkers"])
    assert "acme-naming" not in out


# ---------------------------------------------------------------------------
# Load failures on the query paths
# ---------------------------------------------------------------------------

def test_query_path_reports_load_failure_on_stderr(eps):
    eps[EXTENSION_GROUP] = [
        FakeEP("broken", None, dist="broken-dist", raises=ImportError("nope"))
    ]
    code, out, err = _run(["--list-checkers"])
    assert code == 0                      # the query still answers
    assert "PSS030" in err
    assert "broken-dist" in err
    # The report goes to stderr only; stdout carries the query's answer.
    # (PSS030 itself appears in stdout as one of core's marker IDs, which is
    # why this asserts on the failure text rather than on the bare code.)
    assert "broken-dist" not in out
    assert "failed to import" not in out


def test_describe_documents_the_new_band(eps):
    for code_id in ("PSS030", "PSS031", "PSS032", "PSS033"):
        rc, out, _ = _run(["--describe", code_id])
        assert rc == 0
        assert code_id in out


def test_list_markers_includes_the_new_band(eps):
    _, out, _ = _run(["--list-markers"])
    for code_id in ("PSS030", "PSS031", "PSS032", "PSS033"):
        assert code_id in out


# ---------------------------------------------------------------------------
# Load failures on the parse path
# ---------------------------------------------------------------------------

def test_load_failure_is_a_diagnostic_on_the_parse_path(eps, valid_pss):
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    code, _, err = _run([valid_pss])
    # A warning does not fail the run.
    assert code == 0
    assert "PSS030" in err
    # Rendered as a tool-level diagnostic: no file:line:col prefix.
    assert "pssparser: warning:" in err
    assert "<pssparser>:0:0" not in err


def test_load_failure_does_not_inflate_the_file_count(eps, valid_pss):
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    _, _, err = _run([valid_pss])
    assert "in 1 file" in err


def test_load_failure_appears_in_json(eps, valid_pss):
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    code, out, _ = _run(["--json", valid_pss])
    doc = json.loads(out)
    entry = next(d for d in doc["diagnostics"] if d.get("code") == "PSS030")
    assert entry["severity"] == "warning"
    assert doc["summary"]["warnings"] == 1
    assert doc["summary"]["files"] == 1


def test_werror_promotes_a_load_failure(eps, valid_pss):
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    code, _, err = _run(["-Werror", valid_pss])
    assert code == 1
    assert "error:" in err


def test_werror_code_promotes_a_load_failure(eps, valid_pss):
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    code, _, _ = _run(["-Werror=PSS030", valid_pss])
    assert code == 1


def test_duplicate_marker_id_fails_the_run(eps, valid_pss):
    eps[EXTENSION_GROUP] = [
        _extension("aaa-first", "first-checker", "DUP001"),
        _extension("zzz-second", "second-checker", "DUP001"),
    ]
    code, _, err = _run([valid_pss])
    assert code == 1                      # PSS033 is an error
    assert "PSS033" in err
    assert "aaa-first" in err and "zzz-second" in err


def test_a_load_failure_still_reports_on_a_failed_parse(eps, tmp_path):
    """The early-return paths must not drop the extension diagnostic."""
    bad = tmp_path / "bad.pss"
    bad.write_text("this is not valid PSS @@@@\n")
    eps[EXTENSION_GROUP] = [FakeEP("broken", None, raises=ImportError("nope"))]
    code, _, err = _run([str(bad)])
    assert code == 1
    assert "PSS030" in err


# ---------------------------------------------------------------------------
# An installed extension's checkers actually run
# ---------------------------------------------------------------------------

def test_an_extension_checker_runs_by_default(eps, valid_pss):
    """The point of the whole feature: installed means active, no flags."""
    from pssparser.checkers import CheckerBase, MarkerDef

    class Noisy(CheckerBase):
        name = "noisy"
        description = "emits one marker per run"
        marker_defs = [MarkerDef(id="NOI001", severity="warning", summary="noise")]
        runs_without_link = True

        def check(self, context):
            context.add_marker(
                code="NOI001", file=context.files[0], line=1, col=1,
                message="noisy checker ran",
            )

    def register(reg):
        reg.add_checker(Noisy)

    eps[EXTENSION_GROUP] = [
        FakeEP("noisy-ext", make_module("noisy_ext", register=register))
    ]

    code, _, err = _run([valid_pss])
    assert code == 0
    assert "noisy checker ran" in err

    # ...and --no-extensions turns it off again.
    _, _, err = _run(["--no-extensions", valid_pss])
    assert "noisy checker ran" not in err
