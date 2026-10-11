"""Purity (lint-core-plan.md C6.6; lint-framework S7).

`is_pure(n)`: whether a function is pure, as PSS114 decides it for a call in a
template string -- the two share `functionPurity()` (src/FunctionPurity.h).
`n` is a call (its `ExprMemberPathElem`, or the whole path) or a function
declaration.

Each case is checked both ways: the call in a template string, where PSS114
reports a non-pure callee, and the same call in an `exec`, where `is_pure`
must say the opposite of what PSS114 did.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


def _link(text):
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("a.pss", text)])
    root = p.link()
    (unit,) = p.user_units()
    return root, unit


def _ev(hooks, model, expr):
    root, unit = model
    r = hooks.cel_check_node({"expr": expr}, unit, model=root)
    assert r["errors"] == [], r["errors"]
    v = r["values"]["expr"]
    return [e["value"] for e in v["value"]] if v["type"] == "list" else v["value"]


def _pss114(decls, call):
    from test_helpers import parse_collect
    _, markers = parse_collect(
        decls + 'component pss_top { %s action A { exec body C = """{{%s}}"""; } }'
        % (_HANDLES, call))
    errors = [m for m in markers if m["severity"] == "error"]
    assert all(m.get("code") == "PSS114" for m in errors), errors
    return bool(errors)


def _calls(hooks, decls, call):
    # [is_pure(element with the arguments), is_pure(whole path)]. The
    # component's own exec names its handles without `comp.`.
    model = _link(decls + "component pss_top { %s exec post_solve { int v; v = %s; } }"
                  % (_HANDLES, call.replace("comp.", "")))
    elem = _ev(hooks, model, "descendants(node).filter(d, type(d) == ExprMemberPathElem "
               "&& has(d.params)).map(d, is_pure(d))")
    path = _ev(hooks, model, "descendants(node).filter(d, d.isa(ExprRefPath) && "
               "descendants(d).exists(e, type(e) == ExprMemberPathElem && has(e.params)))"
               ".map(d, is_pure(d))")
    return elem, path


_HANDLES = "PC pc; D d; P q;"

_DECLS = """
package p {
  pure function int scaled(int x) { return x * 2; }
  function int bumped(int x) { return x + 1; }
}
pure component PC {
  function int f(int a);
}
component D : PC { function int h(int a); }
component P {
  pure function int proto_only(int a);
  function int plain(int a);
}
extend component PC { function int added(int a); }
"""


@pytest.mark.parametrize("call,pure", [
    ("p::scaled(1)", True),             # declared pure, with a body
    ("p::bumped(1)", False),
    ("comp.q.proto_only(1)", True),     # declared pure, prototype only
    ("comp.q.plain(1)", False),
    ("comp.pc.f(1)", True),             # a pure component's function
    ("comp.d.f(1)", True),              # inherited from it: pure where declared
    ("comp.d.h(1)", False),             # deriving does not make D pure
    ("comp.pc.added(1)", True),         # an extension re-homes into PC
])
def test_agrees_with_pss114(hooks, call, pure):
    assert _pss114(_DECLS, call) is (not pure)
    elem, path = _calls(hooks, _DECLS, call)
    assert elem == [pure], elem
    assert path == [pure], path


def test_declarations(hooks):
    model = _link(_DECLS + "component pss_top { }")
    got = _ev(hooks, model, "descendants(node).filter(d, type(d) == FunctionPrototype)"
              ".map(d, d.name.id + '=' + string(is_pure(d)))")
    assert sorted(got) == sorted([
        "scaled=true", "bumped=false", "f=true", "h=false",
        "proto_only=true", "plain=false", "added=true"]), got


def test_any_declaration_saying_pure_is_enough(hooks):
    # A prototype and a separate definition are one function.
    model = _link("component pss_top {\n"
                  "  pure function int k(int a);\n"
                  "  function int k(int a) { return a; }\n"
                  "}\n")
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == FunctionPrototype)"
               ".map(d, is_pure(d))") == [True, True]


def test_a_library_function(hooks):
    model = _link("import std_pkg::*;\n"
                  "component pss_top { exec post_solve { message(LOW, \"x\"); } }\n")
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ExprMemberPathElem "
               "&& has(d.params)).map(d, d.id.id + '=' + string(is_pure(d)))") == ["message=false"]


@pytest.mark.parametrize("expr", [
    "is_pure(null)",
    "is_pure(node)",
    # A reference to something that is not a function: a field, a local.
    "descendants(node).filter(d, d.isa(ExprRefPath)).exists(d, is_pure(d))",
    "descendants(node).filter(d, type(d) == Field).exists(d, is_pure(d))",
])
def test_false_for_what_is_not_a_function(hooks, expr):
    model = _link("component pss_top { int x; exec post_solve { int v; v = x; } }")
    assert _ev(hooks, model, expr) is False


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    f = fns["is_pure_node"]
    assert (f["group"], f["level"], f["scope"], f["cost"]) == (
        "Functions", "L1", "file", "constant"), f
