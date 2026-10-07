"""The rule test harness itself (plan F1.11), against a toy rule."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pssparser.checkers import CheckerBase, MarkerDef
from pssparser.checkers.markerdef import Example
from pssparser.checkers.testing import (
    FixtureError,
    check_examples,
    check_fixture,
    check_fixture_dir,
    check_messages,
    parse_expectations,
    run_rules,
)

import pssparser.ast as pss_ast


class ToyRule(CheckerBase):
    """Flags an action named ``bad``."""

    name = "toy-rule"
    marker_defs = [
        MarkerDef(
            id="TOY001", severity="", summary="action named 'bad'",
            name="toy-bad-action", tier="suspicious", family="decl",
            examples=(
                Example(code="component pss_top {\n  action bad { }\n}\n",
                        expect=((2, 3),)),
                Example(code="component pss_top {\n  action good { }\n}\n"),
            ),
        ),
    ]

    def check(self, context):
        class V(pss_ast.VisitorBase):
            def visitAction(self, node):
                if node.getName().getId() == "bad":
                    loc = node.getLocation()
                    context.add_marker(
                        code="TOY001", file=context.files[0], line=loc.lineno,
                        col=loc.linepos, message="action named 'bad'")
                super().visitAction(node)

        for gs in context.global_scopes:
            gs.accept(V())


def _fixture(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return str(path)


SRC = "component pss_top {\n  action bad { }\n}\n"


def test_run_rules_reports_only_the_selected_rule(tmp_path):
    path = _fixture(tmp_path, "m.pss", SRC)
    diags = run_rules([path], ["toy-bad-action"], checkers=[ToyRule])
    assert [(d["code"], d["line"], d["col"]) for d in diags] == [("TOY001", 2, 3)]


def test_a_lint_rule_not_selected_does_not_report(tmp_path):
    path = _fixture(tmp_path, "m.pss", SRC)
    assert run_rules([path], [], checkers=[ToyRule]) == []


def test_passing_fixture(tmp_path):
    path = _fixture(tmp_path, "l01.pss", "// expect: TOY001 @ 3:3\n" + SRC)
    assert check_fixture(path, ["TOY001"], checkers=[ToyRule]).ok


def test_missing_expectation_fails(tmp_path):
    path = _fixture(tmp_path, "l01.pss", "// expect: none\n" + SRC)
    result = check_fixture(path, ["TOY001"], checkers=[ToyRule])
    assert result.unexpected == [("TOY001", 3, 3)]


def test_expected_finding_not_reported_fails(tmp_path):
    path = _fixture(tmp_path, "l01.pss",
                    "// expect: TOY001 @ 3:3, TOY001 @ 4:1\n" + SRC)
    result = check_fixture(path, ["TOY001"], checkers=[ToyRule])
    assert result.missing == [("TOY001", 4, 1)]


def test_column_must_match_exactly(tmp_path):
    path = _fixture(tmp_path, "l01.pss", "// expect: TOY001 @ 3:4\n" + SRC)
    result = check_fixture(path, ["TOY001"], checkers=[ToyRule])
    assert not result.ok


def test_malformed_expectation_names_file_and_line(tmp_path):
    with pytest.raises(FixtureError, match=r"f\.pss:2: malformed"):
        parse_expectations("// ok\n// expect: TOY001 at 3\n", "f.pss")


def test_expect_none_with_findings_is_malformed():
    with pytest.raises(FixtureError):
        parse_expectations("// expect: none\n// expect: TOY001 @ 1:1\n")


def test_fixture_dir_reports_every_failing_file(tmp_path):
    _fixture(tmp_path, "l01.pss", "// expect: none\n" + SRC)
    _fixture(tmp_path, "ok_01.pss", "// expect: none\ncomponent pss_top { }\n")
    with pytest.raises(AssertionError, match="l01.pss") as info:
        check_fixture_dir(str(tmp_path), ["TOY001"], checkers=[ToyRule])
    assert "ok_01.pss" not in str(info.value)


def test_empty_fixture_dir_is_an_error(tmp_path):
    with pytest.raises(AssertionError, match="no fixture files"):
        check_fixture_dir(str(tmp_path))


def test_check_examples_runs_documented_examples():
    check_examples(ToyRule)


def test_check_examples_catches_a_wrong_example():
    class Wrong(ToyRule):
        marker_defs = [MarkerDef(
            id="TOY001", severity="warning", summary="s",
            examples=(Example(code=SRC, expect=((1, 1),)),))]

    with pytest.raises(AssertionError, match="expected"):
        check_examples(Wrong)


def test_check_messages():
    assert check_messages([{"message": "[TOY001] fine", "code": "TOY001"}]) == []
    problems = check_messages([{"message": "two\nlines", "code": None}])
    assert problems


def test_the_example_extension_passes_through_the_harness():
    """The extension-author path: a third-party checker and its fixtures."""
    root = Path(__file__).resolve().parents[3] / "examples" / "pss_naming_checker"
    sys.path.insert(0, str(root / "src"))
    try:
        from pss_naming.checker import NamingConventionChecker
    finally:
        sys.path.remove(str(root / "src"))
    check_fixture_dir(str(root / "tests" / "lint"), checkers=[NamingConventionChecker])
