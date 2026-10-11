"""
The lint engine's AST reflection tables (lint-core-plan.md C1.3, D-C3).

CEL rules read AST fields by name (`node.lhs.op`), so the engine needs, for
every class, its fields and a way to read each one from a node whose class it
learns at run time. pyastbuilder's `gen-reflect` backend generates that from
ast/*.yaml, the schema the AST classes themselves come from (built into
`lint-reflect/Reflect.{h,cpp}` by src/lint/lint.cmake).

Checked three ways:
- the tables against the schema, read independently through pyastbuilder's
  own parser;
- the class ids against `NodeKind::Id`, which the engine's dispatch uses;
- a census of every corpus model through reflection against the census
  through the Cython accessors (pyastbuilder `gen-census`): two independent
  walks over every field of every node must agree.
"""
import glob
import json
import os
import re
import subprocess
import sys

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
CORPUS = os.path.join(ROOT, "packages", "pss-corpus", "curated")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def schema(hooks):
    return hooks.reflect_schema()


@pytest.fixture(scope="module")
def ast_model():
    astbuilder = pytest.importorskip("astbuilder")
    from astbuilder.ast import Ast
    from astbuilder.cmds.util import find_yaml_files
    from astbuilder.linker import Linker
    from astbuilder.parser import Parser
    ast = Ast()
    for f in find_yaml_files(os.path.join(ROOT, "ast")):
        with open(f) as fp:
            ast = Parser(ast).parse(fp)
    Linker().link(ast)
    return ast


# ------------------------------------------------------------ the tables ----

def test_classes_match_the_schema(schema, ast_model):
    classes = schema["classes"]
    assert classes[0]["name"] == ""
    assert [c["name"] for c in classes[1:]] == [c.name for c in ast_model.classes]
    by_name = {c["name"]: i for i, c in enumerate(classes)}
    for c in ast_model.classes:
        got = classes[by_name[c.name]]
        sup = c.super.target.name if c.super is not None else None
        assert (classes[got["super"]]["name"] if got["super"] else None) == sup, c.name
        assert [f["name"] for f in got["fields"]] == [d.name for d in c.data], c.name


def test_field_types(schema, ast_model):
    from astbuilder.type_list import TypeList
    from astbuilder.type_map import TypeMap
    from astbuilder.type_pointer import PointerKind, TypePointer
    from astbuilder.type_scalar import TypeScalar
    by_name = {c["name"]: c for c in schema["classes"]}
    names = [c["name"] for c in schema["classes"]]
    seen = set()
    for c in ast_model.classes:
        for d, f in zip(c.data, by_name[c.name]["fields"]):
            t = d.t
            if isinstance(t, TypeList):
                assert f["type"] == "list", (c.name, d.name)
                t = t.t
                ft = f["elem"]
            else:
                ft = f["type"]
            if isinstance(t, TypeMap):
                assert ft == "map"
            elif isinstance(t, TypeScalar):
                assert ft == {"String": "string", "Bool": "bool"}.get(
                    t.t.name, t.t.name.replace("Int", "i").replace("Uint", "u")
                    .replace("Float", "f").lower()), (c.name, d.name, ft)
            elif isinstance(t, TypePointer):
                assert ft == "node", (c.name, d.name)
                assert names[f["target"]] == t.t.target.name
                assert f["owned"] == (t.pt != PointerKind.Raw), (c.name, d.name)
            seen.add(ft)
    # Every kind of field the schema has is exercised here.
    assert {"node", "string", "bool", "i32", "enum", "struct", "list", "map"} <= seen


def test_enums_match_the_schema(schema, ast_model):
    want = [(e.name, False, [v[0] for v in e.values]) for e in ast_model.enums]
    want += [(f.name, True, list(f.values)) for f in ast_model.flags]
    assert [(e["name"], e["flags"], e["values"]) for e in schema["enums"]] == want


def test_structs_match_the_schema(schema, ast_model):
    assert [(s["name"], [f["name"] for f in s["fields"]]) for s in schema["structs"]] == \
        [(s.name, [d.name for d in s.data]) for s in ast_model.structs]


def test_ids_align_with_nodekind(schema):
    # The engine dispatches on NodeKind::Id and reads fields by reflection id;
    # the two must number the classes identically.
    with open(os.path.join(ROOT, "src", "include", "pssp", "impl", "NodeKind.h")) as fp:
        text = fp.read()
    body = re.search(r"enum class Id : uint16_t \{(.*?)\};", text, re.S).group(1)
    ids = [x.strip() for x in body.split(",") if x.strip()]
    assert ids[0] == "None"
    assert ids[1:] == [c["name"] for c in schema["classes"][1:]]


# --------------------------------------------------------------- census ----

@pytest.fixture(scope="module")
def py_census(tmp_path_factory):
    """census() from a census_gen.py generated now, from the current schema,
    rather than the committed copy under ts/scripts/generated (which may lag)."""
    pytest.importorskip("astbuilder")
    d = tmp_path_factory.mktemp("census")
    subprocess.run([sys.executable, "-m", "astbuilder", "gen-census", "-astdir",
                    os.path.join(ROOT, "ast"), "-py", str(d / "py"), "-ts", str(d / "ts")],
                   check=True, capture_output=True)
    sys.path.insert(0, str(d / "py"))
    try:
        import census_gen
    finally:
        sys.path.pop(0)
    return census_gen.census


def _compare(hooks, py_census, node, what):
    want = py_census(node)
    got = hooks.reflect_census(node)
    assert got["count"] == want["count"], what
    assert got["classes"] == want["classes"], what
    for i, (g, w) in enumerate(zip(got["records"], want["records"])):
        assert g == w, "%s: node %d (%s)" % (what, i, w[0])


def test_census_inline(hooks, py_census):
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss",
               "import std_pkg::*;\n"
               "package p { const int i = -42; const float64 f = 1.0e-9; const string s = \"x\"; }\n"
               "component pss_top {\n"
               "  function int f(int x) { int t = x; if (x > 1) { t = x + 1; } return t; }\n"
               "  action A {\n"
               "    rand int a; rand bit[8] v;\n"
               "    constraint { v in [1..4, 8]; (a > 0) -> v != 0; }\n"
               "  }\n"
               "}\n")])
    for i, u in enumerate(p._files):
        _compare(hooks, py_census, u, "unit %d" % i)
    _compare(hooks, py_census, p.link(), "linked root")


def _corpus():
    return sorted(glob.glob(os.path.join(CORPUS, "**", "*.pss"), recursive=True))


@pytest.mark.corpus
@pytest.mark.skipif(not os.path.isdir(CORPUS), reason="no pss-corpus checkout")
def test_census_corpus(hooks, py_census):
    from pssparser.parser import Parser
    files = _corpus()
    assert len(files) > 50
    stdlib_done = False
    for f in files:
        rel = os.path.relpath(f, CORPUS)
        with open(f, encoding="utf-8", errors="replace") as fp:
            text = fp.read()
        p = Parser()
        try:
            p.parses([(rel, text)])
        except Exception:
            continue
        for i, u in enumerate(p._files):
            if i == 0 and stdlib_done:
                continue            # the standard library, the same every time
            _compare(hooks, py_census, u, "%s unit %d" % (rel, i))
        stdlib_done = True
        try:
            root = p.link()
        except Exception:
            root = p._root
        if root is not None:
            _compare(hooks, py_census, root, "%s linked" % rel)
