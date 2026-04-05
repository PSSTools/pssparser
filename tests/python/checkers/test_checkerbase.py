"""Tests for pssparser.checkers.CheckerBase."""
from __future__ import annotations

import pytest

from pssparser.checkers import CheckerBase, MarkerDef


def test_base_check_raises_not_implemented():
    base = CheckerBase()
    with pytest.raises(NotImplementedError):
        base.check(None)


def test_concrete_subclass_can_be_instantiated():
    class MyChecker(CheckerBase):
        name = "my-checker"
        description = "Test"
        marker_defs = [MarkerDef(id="MY001", severity="warning", summary="s")]

        def check(self, context):
            pass

    checker = MyChecker()
    checker.check(None)  # should not raise


def test_runs_without_link_defaults_false():
    checker = CheckerBase()
    assert checker.runs_without_link is False


def test_subclass_marker_defs_do_not_pollute_parent():
    class ChildA(CheckerBase):
        name = "child-a"
        marker_defs = [MarkerDef(id="A001", severity="error", summary="A")]

        def check(self, context):
            pass

    class ChildB(CheckerBase):
        name = "child-b"
        marker_defs = [MarkerDef(id="B001", severity="warning", summary="B")]

        def check(self, context):
            pass

    assert "A001" not in [md.id for md in ChildB().marker_defs]
    assert "B001" not in [md.id for md in ChildA().marker_defs]
    # The base class list must remain empty
    assert CheckerBase.marker_defs == []


def test_name_defaults_to_empty_string():
    assert CheckerBase.name == ""
