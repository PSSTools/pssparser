"""Shared fixtures for the checkers test suite."""
from __future__ import annotations

import pytest

from pssparser.checkers import CheckerBase, MarkerDef


class DummyChecker(CheckerBase):
    """Minimal checker that always emits one TST001 warning."""

    name = "dummy"
    description = "Test checker that emits one warning unconditionally"
    marker_defs = [
        MarkerDef(id="TST001", severity="warning", summary="Dummy test warning"),
    ]
    runs_without_link = False

    def check(self, context) -> None:
        if context.files:
            context.add_marker(
                code="TST001",
                file=context.files[0],
                line=1,
                col=1,
                message="dummy warning from DummyChecker",
            )


class AnotherDummyChecker(CheckerBase):
    """Second checker with a non-conflicting ID."""

    name = "another-dummy"
    description = "Second test checker"
    marker_defs = [
        MarkerDef(id="TST002", severity="info", summary="Another dummy test marker"),
    ]
    runs_without_link = True

    def check(self, context) -> None:
        if context.files:
            context.add_marker(
                code="TST002",
                file=context.files[0],
                line=1,
                col=1,
                message="another dummy marker",
            )


class ConflictingChecker(CheckerBase):
    """Checker with TST001 — conflicts with DummyChecker."""

    name = "conflicting"
    description = "Checker that re-declares TST001 for conflict testing"
    marker_defs = [
        MarkerDef(id="TST001", severity="error", summary="Conflicting marker"),
    ]

    def check(self, context) -> None:
        pass


class ErrorSeverityChecker(CheckerBase):
    """Checker that emits an error-severity marker."""

    name = "error-checker"
    description = "Emits an error-severity marker"
    marker_defs = [
        MarkerDef(id="TST003", severity="error", summary="Dummy error marker"),
    ]
    runs_without_link = False

    def check(self, context) -> None:
        if context.files:
            context.add_marker(
                code="TST003",
                file=context.files[0],
                line=1,
                col=1,
                message="dummy error",
            )


@pytest.fixture
def dummy_checker():
    return DummyChecker()


@pytest.fixture
def another_dummy_checker():
    return AnotherDummyChecker()


@pytest.fixture
def tmp_pss_file(tmp_path):
    """Write a minimal valid PSS snippet to a temporary file."""
    f = tmp_path / "test.pss"
    f.write_text(
        "component pss_top {\n"
        "    action A {}\n"
        "}\n"
    )
    return str(f)


@pytest.fixture
def tmp_invalid_pss_file(tmp_path):
    """Write intentionally broken PSS to a temporary file."""
    f = tmp_path / "broken.pss"
    f.write_text("this is not valid PSS syntax @@@@\n")
    return str(f)
