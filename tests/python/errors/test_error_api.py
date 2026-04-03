"""
Phase 4 error handling tests: structured marker API.

Verify that errors are accessible as structured data (not just
exception strings) for IDE/LLM tooling integration.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pssparser import Parser, ParseException
from pssparser.core import Factory


@pytest.fixture(autouse=True)
def ensure_factory():
    Factory.inst()


def test_markers_on_exception():
    """ParseException carries structured markers"""
    p = Parser()
    p.parses([('test.pss', 'struct S { UnknownType x; };')])
    with pytest.raises(ParseException) as exc_info:
        p.link()
    markers = exc_info.value.markers
    assert len(markers) >= 1
    assert markers[0]["severity"] == "error"
    assert "UnknownType" in markers[0]["message"]


def test_marker_has_location():
    """Each marker has file, line, col"""
    p = Parser()
    p.parses([('myfile.pss', 'struct S { UnknownType x; };')])
    with pytest.raises(ParseException) as exc_info:
        p.link()
    m = exc_info.value.markers[0]
    assert m["file"] == "myfile.pss"
    assert m["line"] == 1
    assert m["col"] >= 1


def test_multiple_markers_collected():
    """All errors collected, not just first"""
    p = Parser()
    p.parses([('test.pss', 'struct A { Bad1 x; }; struct B { Bad2 y; };')])
    with pytest.raises(ParseException) as exc_info:
        p.link()
    markers = exc_info.value.markers
    assert len(markers) >= 2
    messages = [m["message"] for m in markers]
    assert any("Bad1" in msg for msg in messages)
    assert any("Bad2" in msg for msg in messages)


def test_parser_markers_after_success():
    """Parser.markers is empty list after successful parse+link"""
    p = Parser()
    p.parses([('test.pss', 'struct S { int x; };')])
    p.link()
    assert p.markers == []


def test_parser_markers_after_error():
    """Parser.markers populated even before exception"""
    p = Parser()
    p.parses([('test.pss', 'struct S { UnknownType x; };')])
    try:
        p.link()
    except ParseException:
        pass
    assert len(p.markers) >= 1


def test_marker_severity_types():
    """Severity is a readable string, not an enum int"""
    p = Parser()
    p.parses([('test.pss', 'struct S { UnknownType x; };')])
    with pytest.raises(ParseException) as exc_info:
        p.link()
    m = exc_info.value.markers[0]
    assert m["severity"] in ("error", "warning", "info", "hint")


def test_syntax_error_marker():
    """Syntax errors also produce structured markers"""
    p = Parser()
    with pytest.raises(ParseException) as exc_info:
        p.parses([('test.pss', 'struct S { int x }')])
        p.link()
    markers = exc_info.value.markers
    assert len(markers) >= 1
    assert markers[0]["severity"] == "error"
