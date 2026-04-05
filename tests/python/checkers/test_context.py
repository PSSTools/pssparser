"""Tests for pssparser.checkers.CheckContext."""
from __future__ import annotations

import pytest

from pssparser.checkers import CheckContext, MarkerDef


def _make_context(marker_defs=None):
    index = {}
    for md in (marker_defs or []):
        index[md.id] = md
    return CheckContext(root=None, files=["test.pss"], global_scopes=[], _marker_index=index)


def test_add_marker_appends_to_markers():
    md = MarkerDef(id="TST001", severity="warning", summary="Test")
    ctx = _make_context([md])
    ctx.add_marker(code="TST001", file="test.pss", line=1, col=1, message="hello")
    assert len(ctx._markers) == 1


def test_add_marker_dict_has_expected_keys():
    md = MarkerDef(id="TST001", severity="warning", summary="Test")
    ctx = _make_context([md])
    ctx.add_marker(code="TST001", file="test.pss", line=5, col=10, message="msg")
    m = ctx._markers[0]
    assert "severity" in m
    assert "message" in m
    assert "file" in m
    assert "line" in m
    assert "col" in m
    assert "code" in m


def test_severity_taken_from_marker_def_when_not_provided():
    md = MarkerDef(id="TST001", severity="warning", summary="Test")
    ctx = _make_context([md])
    ctx.add_marker(code="TST001", file="test.pss", line=1, col=1, message="msg")
    assert ctx._markers[0]["severity"] == "warning"


def test_explicit_severity_overrides_marker_def():
    md = MarkerDef(id="TST001", severity="warning", summary="Test")
    ctx = _make_context([md])
    ctx.add_marker(code="TST001", file="test.pss", line=1, col=1, message="msg", severity="error")
    assert ctx._markers[0]["severity"] == "error"


def test_add_marker_unknown_code_raises_value_error():
    ctx = _make_context()
    with pytest.raises(ValueError, match="TST999"):
        ctx.add_marker(code="TST999", file="test.pss", line=1, col=1, message="bad")


def test_message_includes_code_prefix():
    md = MarkerDef(id="TST001", severity="info", summary="Test")
    ctx = _make_context([md])
    ctx.add_marker(code="TST001", file="test.pss", line=1, col=1, message="the message")
    assert "[TST001]" in ctx._markers[0]["message"]
    assert "the message" in ctx._markers[0]["message"]
