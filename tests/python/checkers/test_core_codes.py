"""Tests that C++ core marker messages are mapped to the correct PSS codes."""
from __future__ import annotations

import pytest

from pssparser.cli.commands import _assign_core_code


def _m(message, severity="error"):
    return {"message": message, "severity": severity, "file": "t.pss", "line": 1, "col": 1}


# ---------------------------------------------------------------------------
# PSS001 — syntax errors
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "expected ';' before '}'",
    "expected identifier before 'action'",
    "expected '{' or ':' before 'action'",
    "unexpected end of input; possible missing closing '}'",
    "unexpected 'action' in this context",
    "unexpected keyword 'extends' in this context",
    "unknown exec-block kind \"bad\" specified. Expect one of",
])
def test_syntax_error_mapped_to_pss001(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS001"


# ---------------------------------------------------------------------------
# PSS002 — unknown symbol
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "unknown type 'SomeUndefinedType'",
    "unknown type 'SomeUndefinedType'; did you mean 'SomeDefinedType'?",
    "unknown identifier 'badref'",
    "unknown identifier 'badref'; did you mean 'goodref'?",
    "unknown method 'nosuchmethod' on built-in type",
])
def test_unknown_symbol_mapped_to_pss002(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS002"


# ---------------------------------------------------------------------------
# PSS003 — duplicate declarations
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "duplicate declaration of 'pss_top'",
    "duplicate variable declaration my_var",
    "duplicate parameter name 'p'",
    "duplicate symbol declaration",
])
def test_duplicate_mapped_to_pss003(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS003"


# ---------------------------------------------------------------------------
# PSS004 — resolution / ref-path failures
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "failed to resolve ref-path some.path",
    "failed to resolve symbol foo",
    "root ref-path element x is not a composite scope",
])
def test_resolution_failure_mapped_to_pss004(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS004"


# ---------------------------------------------------------------------------
# PSS005 — extend-unknown
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "cannot extend unknown type 'Foo'",
    "cannot extend unknown enum 'MyEnum'",
])
def test_extend_unknown_mapped_to_pss005(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS005"


# ---------------------------------------------------------------------------
# No match — unrecognised message left without a code
# ---------------------------------------------------------------------------

def test_unrecognised_message_no_code():
    result = _assign_core_code(_m("some completely unknown internal message"))
    assert result.get("code") is None


# ---------------------------------------------------------------------------
# Existing code preserved
# ---------------------------------------------------------------------------

def test_existing_code_preserved():
    marker = {**_m("expected ';'"), "code": "PSS999"}
    assert _assign_core_code(marker)["code"] == "PSS999"


# ---------------------------------------------------------------------------
# Integration: end-to-end check that real parse errors get codes
# ---------------------------------------------------------------------------

def test_real_syntax_error_gets_pss001(tmp_path):
    from pssparser import Parser
    from pssparser.parser import ParseException
    from pssparser.cli.commands import _collect
    from pssparser.cli.diagnostics import DiagnosticCollection

    f = tmp_path / "bad.pss"
    f.write_text("component bad { action A { rand int x }")  # missing semicolon

    p = Parser()
    coll = DiagnosticCollection()
    try:
        p.parse([str(f)])
    except ParseException as exc:
        _collect(coll, getattr(exc, "markers", []), p)

    pss001 = [d for d in coll.diagnostics if d.code == "PSS001"]
    assert len(pss001) > 0


def test_real_unknown_type_gets_pss002(tmp_path):
    from pssparser import Parser
    from pssparser.parser import ParseException
    from pssparser.cli.commands import _collect
    from pssparser.cli.diagnostics import DiagnosticCollection

    f = tmp_path / "undef.pss"
    f.write_text("component pss_top { action A { UnknownType x; } }")

    p = Parser()
    coll = DiagnosticCollection()
    try:
        p.parse([str(f)])
        p.link()
    except ParseException as exc:
        _collect(coll, getattr(exc, "markers", []), p)
    _collect(coll, [], p)

    pss002 = [d for d in coll.diagnostics if d.code == "PSS002"]
    assert len(pss002) > 0
