"""Tests for pssparser.checkers.MarkerDef."""
from __future__ import annotations

import pytest
from dataclasses import FrozenInstanceError

from pssparser.checkers import MarkerDef


def test_fields_stored():
    md = MarkerDef(id="TST001", severity="warning", summary="Test summary", detail="Details here")
    assert md.id == "TST001"
    assert md.severity == "warning"
    assert md.summary == "Test summary"
    assert md.detail == "Details here"


def test_detail_defaults_to_empty():
    md = MarkerDef(id="TST001", severity="error", summary="No detail")
    assert md.detail == ""


def test_frozen_raises_on_assignment():
    md = MarkerDef(id="TST001", severity="error", summary="Test")
    with pytest.raises(FrozenInstanceError):
        md.id = "TST999"


def test_equality_same_fields():
    md1 = MarkerDef(id="TST001", severity="error", summary="Test", detail="d")
    md2 = MarkerDef(id="TST001", severity="error", summary="Test", detail="d")
    assert md1 == md2


def test_inequality_different_fields():
    md1 = MarkerDef(id="TST001", severity="error", summary="A")
    md2 = MarkerDef(id="TST002", severity="error", summary="A")
    assert md1 != md2
