"""The declaration enclosing a location (lint-framework-plan F2.2).

``pssparser.lint.declpath`` maps a line and column to a qualified path such as
``p::C::A::constraint c``.  Fingerprints (F2.3) hash it in place of a line
number, and SARIF reports it as each result's logical location.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from pssparser import Parser
from pssparser.checkers import CheckContext
from pssparser.cli.app import main
from pssparser.lint.declpath import (DeclPathIndex, MissingEndLocation,
                                     index_for)

ROOT = Path(__file__).resolve().parents[3]

MODEL = """\
import std_pkg::*;
package p {
  component C {
    action A {
      int x;
      constraint c { x > 0; }
      constraint { x < 9; }
      constraint { x < 8; }
      activity { do A; }
      exec post_solve { x = 1; }
      exec body { }
      exec body { }
    }
    function void f() { int a; a = 1; }

  }
  struct holder_t { int v; }
  enum e { E0, E1 }
}
extend action p::C::A { constraint { x != 3; } }
extend action p::C::A { constraint { x != 4; } }
package p { struct t {} }
package a::b { function int g(int v); }
"""


@pytest.fixture(scope="module")
def index(tmp_path_factory):
    path = tmp_path_factory.mktemp("dp") / "m.pss"
    path.write_text(MODEL)
    p = Parser()
    p.parse([str(path)])
    p.link()
    return str(path), index_for(p, [str(path)], strict=True)


def _at(index, line, text):
    """The path at the first occurrence of *text* on *line* (1-based)."""
    path, idx = index
    col = MODEL.split("\n")[line - 1].index(text) + 1
    return idx.path_at(path, line, col)


@pytest.mark.parametrize("line,text,expected", [
    (1, "import", ""),
    (2, "package", "p"),
    (3, "C", "p::C"),
    (4, "A", "p::C::A"),
    (5, "x", "p::C::A"),
    (6, "x > 0", "p::C::A::constraint c"),
    (7, "x < 9", "p::C::A::constraint"),
    (8, "x < 8", "p::C::A::constraint#2"),
    (9, "do A", "p::C::A::activity"),
    (10, "x = 1", "p::C::A::exec post_solve"),
    (11, "{", "p::C::A::exec body"),
    (12, "{", "p::C::A::exec body#2"),
    (14, "a = 1", "p::C::function f"),
    (17, "int v", "p::holder_t"),
    (18, "E1", "p::e"),
    (20, "x != 3", "extend action p::C::A::constraint"),
    (21, "x != 4", "extend action p::C::A#2::constraint"),
    (22, "struct", "p::t"),
    (23, "int v", "a::b::function g"),
])
def test_path_at(index, line, text, expected):
    assert _at(index, line, text) == expected


def test_a_location_between_declarations_is_the_enclosing_one(index):
    # Line 13 closes action A; its last column is A's, the next is C's.
    path, idx = index
    assert idx.path_at(path, 13, 5) == "p::C::A"
    assert idx.path_at(path, 13, 6) == "p::C"
    assert idx.path_at(path, 19, 1) == "p"
    assert idx.path_at(path, 19, 2) == ""


def test_chain_is_outermost_first(index):
    path, idx = index
    chain = idx.chain_at(path, 6, 22)
    assert [(s.kind, s.name) for s in chain] == [
        ("package", "p"), ("component", "C"), ("action", "A"),
        ("constraint", "constraint c")]


def test_unknown_file_has_no_path(index):
    _, idx = index
    assert idx.path_at("elsewhere.pss", 6, 22) == ""


def test_an_activity_symbol(tmp_path):
    path = tmp_path / "m.pss"
    path.write_text("component C {\n  action A {\n"
                    "    symbol s { do A; }\n    activity { s; }\n  }\n}\n")
    p = Parser()
    p.parse([str(path)])
    idx = index_for(p, [str(path)], strict=True)
    assert idx.path_at(str(path), 3, 16) == "C::A::symbol s"
    assert idx.path_at(str(path), 4, 16) == "C::A::activity"


def test_unlinked_units_are_indexed(tmp_path):
    # The path is lexical: --syntax-only, and a failed link, still have it.
    path = tmp_path / "m.pss"
    path.write_text("package p { struct s { nosuch_t v; } }\n")
    p = Parser()
    p.parse([str(path)])
    assert index_for(p, [str(path)]).path_at(str(path), 1, 25) == "p::s"


# ---------------------------------------------------------------------------
# A scope with no end location fails loudly under strict
# ---------------------------------------------------------------------------

class _Loc:
    def __init__(self, line, col):
        self.lineno, self.linepos = line, col


class Struct:
    """Stands in for an AST node whose end location was never set."""

    def __init__(self):
        self._name = type("N", (), {"getId": lambda _s: "s"})()

    def getName(self):
        return self._name

    def getLocation(self):
        return _Loc(1, 1)

    def getEndLocation(self):
        return _Loc(-1, -1)

    def getChildren(self):
        return []


class _Unit:
    def getFileid(self):
        return 1

    def getChildren(self):
        return [Struct()]


def test_missing_end_location_raises_under_strict():
    with pytest.raises(MissingEndLocation, match="Struct at m.pss:1:1"):
        DeclPathIndex([_Unit()], {1: "m.pss"}, strict=True)


def test_missing_end_location_is_recorded_otherwise():
    idx = DeclPathIndex([_Unit()], {1: "m.pss"})
    assert idx.missing_end == [("Struct", "m.pss", 1, 1)]
    assert idx.path_at("m.pss", 1, 40) == "s"
    assert idx.path_at("m.pss", 2, 1) == ""


def _corpus():
    base = ROOT / "packages" / "pss-corpus"
    files = sorted(base.glob("**/*.pss")) if base.is_dir() else []
    files += sorted((ROOT / "src" / "stdlib").glob("*.pss"))
    return files


@pytest.mark.parametrize("path", _corpus(), ids=lambda p: p.name)
def test_every_corpus_declaration_has_an_end_location(path):
    p = Parser()
    try:
        p.parse([str(path)])
    except Exception:
        pytest.skip("does not parse")
    index_for(p, [str(path)], strict=True)


# ---------------------------------------------------------------------------
# CheckContext.facts and SARIF
# ---------------------------------------------------------------------------

def test_checkcontext_facts_decl_path(tmp_path):
    path = tmp_path / "m.pss"
    path.write_text("package p {\n  struct s {\n    int v;\n  }\n}\n")
    p = Parser()
    p.parse([str(path)])
    p.link()
    units = p.user_units()
    ctx = CheckContext(root=None, files=[str(path)], global_scopes=units,
                       file_map={u.getFileid(): str(path) for u in units})
    assert ctx.facts.decl_path({"file": str(path), "line": 3, "col": 5}) == "p::s"
    assert ctx.facts.decl_path((str(path), 1, 1)) == "p"
    assert ctx.facts.decl_paths is ctx.facts.decl_paths


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def test_sarif_results_carry_logical_locations(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(
        "package lib { struct s {} }\n"
        "package p {\n  struct t {}\n  import lib::*;\n}\n"
        "import lib::*;\n")
    _, out, _ = _run(["--no-config", "--format", "sarif", "m.pss"])
    doc = json.loads(out)
    results = doc["runs"][0]["results"]
    by_line = {r["locations"][0]["physicalLocation"]["region"]["startLine"]: r
               for r in results if r.get("ruleId") == "LINT402"}
    assert by_line[4]["locations"][0]["logicalLocations"] == [
        {"name": "p", "fullyQualifiedName": "p", "kind": "namespace"}]

    jsonschema = pytest.importorskip("jsonschema")
    schema = Path(__file__).parents[1] / "cli" / "data" / "sarif-2.1.0.json"
    jsonschema.validate(doc, json.loads(schema.read_text()))


def test_sarif_logical_location_kinds(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text(
        "component C {\n  action A {\n    int x;\n"
        "    constraint c { nosuch > 0; }\n  }\n}\n")
    _, out, _ = _run(["--no-config", "--format", "sarif", "m.pss"])
    results = json.loads(out)["runs"][0]["results"]
    logical = [r["locations"][0].get("logicalLocations") for r in results
               if r.get("locations")]
    assert [{"name": "constraint c", "fullyQualifiedName": "C::A::constraint c",
             "kind": "member"}] in logical


def test_global_scope_results_have_no_logical_location(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "m.pss").write_text("struct t {}\nimport std_pkg::*;\n")
    _, out, _ = _run(["--no-config", "--format", "sarif", "m.pss"])
    results = json.loads(out)["runs"][0]["results"]
    assert results
    assert all("logicalLocations" not in loc
               for r in results for loc in r.get("locations", []))
