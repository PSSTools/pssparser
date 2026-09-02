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
    # The leaf of a static-rooted path, once it is resolved at all
    "'p' has no member named 'nosuch_f'",
    # The same failure reached through an unqualified path -- `f().zzz`
    "Failed to find elem zzz",
    "Failed to find elem nosuchmeth",
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
    # Function redeclaration, which does not start with the word "duplicate"
    "function 'f' is already defined",
    "function 'f' cannot be both defined and imported",
    "function 'f' is already imported",
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
    # The same failure below the root, which reports without the "root" prefix
    "ref-path element a is not a composite scope",
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

def test_real_syntax_error_gets_a_pss02x_code(tmp_path):
    """A missing ';' is PSS020 (expected specific punctuation) since E-3
    classified the syntax sub-band; the marker carries its own code (from
    C++), it is not recovered from _assign_core_code's PSS001 pattern."""
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

    pss020 = [d for d in coll.diagnostics if d.code == "PSS020"]
    assert len(pss020) > 0


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


# ---------------------------------------------------------------------------
# PSS006 — call argument count
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "too few arguments to 'f': expected 2, got 1",
    "too many arguments to 'f': expected 1, got 2",
    "too few arguments to 'f': expected at least 1, got 0",
    "too many arguments to 'f': expected at most 2, got 3",
    # The callee is not a function, or its parameter list is malformed
    "'x' is not a function",
    "parameter 'b' has no default, but follows 'a' which does",
    "argument 1 of 'f' is a string, but parameter 'a' is numeric",
])
def test_call_arity_mapped_to_pss006(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS006"


# ---------------------------------------------------------------------------
# PSS007 — return statement vs. declared return type
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "'f' returns void, so 'return' cannot take a value",
    "'f' has a return type, so 'return' must supply a value",
    "'f' returns void, so its result cannot be used as a value",
])
def test_return_mismatch_mapped_to_pss007(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS007"


# ---------------------------------------------------------------------------
# PSS008 — function qualifiers used where the LRM disallows them
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "parameter 'a' of 'f' is declared output, so 'f' may only be imported,"
        " not defined in PSS",
    "parameter 'a' of 'f' is declared inout, so 'f' may only be imported,"
        " not defined in PSS",
    "'f' is declared pure, so it cannot return void",
    "'f' is declared pure, so parameter 'a' cannot be output",
])
def test_qualifier_misuse_mapped_to_pss008(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS008"


# ---------------------------------------------------------------------------
# PSS009 — declarations of one function that disagree with each other
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("msg", [
    "declarations of 'f' disagree about the return type",
    "declarations of 'f' disagree about the return type: one returns void"
        " and the other does not",
    "declarations of 'f' disagree about the number of parameters (1 and 2)",
    "declarations of 'f' disagree about the type of parameter 1 ('a')",
    "declarations of 'f' disagree about the direction of parameter 1 ('a')",
    "declarations of 'f' disagree about what kind of parameter 1 ('a') is",
    "declarations of 'f' disagree about whether parameter 2 ('args')"
        " is varargs",
    # Not a "disagreement" -- respecifying an identical default violates LRM
    # 20.2.4 c too -- so it needs its own pattern for the same code.
    "parameter 1 ('a') of 'f' is given a default value by more than one"
        " declaration; only one declaration may give it",
])
def test_declaration_disagreement_mapped_to_pss009(msg):
    assert _assign_core_code(_m(msg))["code"] == "PSS009"
