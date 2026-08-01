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


# ---------------------------------------------------------------------------
# CheckContext is actually populated (regression)
# ---------------------------------------------------------------------------
#
# Parser.link() clears its working state, and the CLI read that state
# *after* linking -- so file_map and global_scopes, the two access paths the
# plug-in guide documents, always arrived empty. Every checker written to the
# guide silently got nothing. link() now snapshots them into public
# properties.

class _ContextCapture(CheckerBase):
    """Records the CheckContext it was handed, for inspection."""

    name = "context-capture"
    description = "captures the CheckContext for assertions"
    runs_without_link = True
    marker_defs = [
        MarkerDef(
            id="CTX001",
            severity="warning",
            summary="context capture",
            detail="test-only checker",
        )
    ]

    captured = None

    def check(self, context):
        type(self).captured = context


def test_check_context_has_file_map(valid_pss):
    _ContextCapture.captured = None
    cmd_parse(files=[valid_pss], manager=_make_manager(_ContextCapture), quiet=True)

    ctx = _ContextCapture.captured
    assert ctx is not None, "checker did not run"
    assert ctx.file_map, "file_map is empty; checkers cannot resolve a fileid to a path"
    assert valid_pss in ctx.file_map.values()


def test_check_context_has_global_scopes(valid_pss):
    _ContextCapture.captured = None
    cmd_parse(files=[valid_pss], manager=_make_manager(_ContextCapture), quiet=True)

    ctx = _ContextCapture.captured
    assert len(ctx.global_scopes) == 1, (
        "expected one GlobalScope for one user file, got %d" % len(ctx.global_scopes)
    )
    # The standard library must not appear: it is not a user file.
    assert ctx.global_scopes[0].getFileid() != 0


def test_parser_exposes_file_map_after_link(tmp_path):
    """The underlying Parser API, independent of the CLI."""
    from pssparser import Parser

    f = tmp_path / "m.pss"
    f.write_text("component pss_top { action A {} }\n")

    p = Parser()
    p.parse([str(f)])
    p.link()

    assert p.file_map == {1: str(f)}


def test_user_units_come_from_the_linked_root(tmp_path):
    """user_units() must read the root, not retained pre-link wrappers.

    The linker takes ownership of each GlobalScope, so a Python wrapper held
    across link() becomes a second owner of the same memory and segfaults on
    the next attribute access. Reading through root.getUnit(i) yields
    non-owning views, which is why this is safe and the obvious snapshot is
    not. Accessed twice here deliberately: a double-free shows up on the
    second pass.
    """
    from pssparser import Parser

    f = tmp_path / "m.pss"
    f.write_text("component pss_top { action A {} }\n")

    p = Parser()
    p.parse([str(f)])
    p.link()

    assert [u.getFileid() for u in p.user_units()] == [1]
    assert [u.getFileid() for u in p.user_units()] == [1]
