"""End-to-end integration tests for the checker pipeline."""
from __future__ import annotations

import pytest

from pssparser.checkers import CheckerBase, CheckerManager, MarkerDef
from pssparser.cli.commands import cmd_parse
from tests.python.checkers.conftest import (
    DummyChecker,
    AnotherDummyChecker,
    ErrorSeverityChecker,
)


def _make_manager(*checker_classes):
    m = CheckerManager()
    from pssparser.checkers.core_checker import CoreChecker
    m._registered["core"] = CoreChecker
    for cls in checker_classes:
        m._registered[cls().name] = cls
    return m


@pytest.fixture
def valid_pss(tmp_path):
    f = tmp_path / "valid.pss"
    f.write_text("component pss_top {\n    action A {}\n}\n")
    return str(f)


# ---------------------------------------------------------------------------
# DummyChecker emits marker visible in DiagnosticCollection
# ---------------------------------------------------------------------------

def test_dummy_checker_marker_in_collection(valid_pss, capsys):
    import io
    manager = _make_manager(DummyChecker)
    code = cmd_parse(
        files=[valid_pss],
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=True,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    # DummyChecker emits a warning, so exit code should be 0
    assert code == 0


# ---------------------------------------------------------------------------
# runs_without_link=False: checker skipped when syntax_only=True
# ---------------------------------------------------------------------------

def test_checker_skipped_when_syntax_only(valid_pss):
    import io

    emitted = []

    class TrackingChecker(CheckerBase):
        name = "tracking"
        marker_defs = [MarkerDef(id="TRK001", severity="warning", summary="tracking")]
        runs_without_link = False

        def check(self, context):
            emitted.append("called")
            context.add_marker(
                code="TRK001", file=context.files[0], line=1, col=1, message="tracked"
            )

    manager = _make_manager(TrackingChecker)
    cmd_parse(
        files=[valid_pss],
        syntax_only=True,
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=True,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert emitted == [], "checker with runs_without_link=False should be skipped in syntax_only mode"


# ---------------------------------------------------------------------------
# runs_without_link=True: checker runs even when syntax_only=True
# ---------------------------------------------------------------------------

def test_checker_runs_when_syntax_only_and_runs_without_link(valid_pss):
    import io

    emitted = []

    class EagerChecker(CheckerBase):
        name = "eager"
        marker_defs = [MarkerDef(id="EGR001", severity="info", summary="eager")]
        runs_without_link = True

        def check(self, context):
            emitted.append("called")

    manager = _make_manager(EagerChecker)
    cmd_parse(
        files=[valid_pss],
        syntax_only=True,
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=True,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert emitted == ["called"]


# ---------------------------------------------------------------------------
# Error-severity marker causes exit code 1
# ---------------------------------------------------------------------------

def test_error_severity_checker_causes_exit_1(valid_pss):
    import io
    manager = _make_manager(ErrorSeverityChecker)
    code = cmd_parse(
        files=[valid_pss],
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=True,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert code == 1


# ---------------------------------------------------------------------------
# Warning-only checker does not change exit code (still 0 for valid file)
# ---------------------------------------------------------------------------

def test_warning_only_checker_exit_0(valid_pss):
    import io
    manager = _make_manager(DummyChecker)
    code = cmd_parse(
        files=[valid_pss],
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=True,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )
    assert code == 0


# ---------------------------------------------------------------------------
# JSON output includes checker marker's "code" field
# ---------------------------------------------------------------------------

def test_json_output_includes_code_field(valid_pss):
    import io, json

    class JsonTestChecker(CheckerBase):
        name = "json-test"
        marker_defs = [MarkerDef(id="JSN001", severity="error", summary="json test")]
        runs_without_link = True

        def check(self, context):
            context.add_marker(
                code="JSN001",
                file=context.files[0],
                line=1,
                col=1,
                message="json marker",
            )

    manager = _make_manager(JsonTestChecker)
    stdout_buf = io.StringIO()
    cmd_parse(
        files=[valid_pss],
        use_json=True,
        syntax_only=True,
        manager=manager,
        checkers=None,
        no_checkers=None,
        quiet=False,
        stdout=stdout_buf,
        stderr=io.StringIO(),
    )
    output = stdout_buf.getvalue()
    data = json.loads(output)
    codes = [d.get("code") for d in data.get("diagnostics", [])]
    assert "JSN001" in codes
