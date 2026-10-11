"""Symbols (lint-core-plan.md C6.2; lint-rule-expressions.md §3).

`decl_path`, `resolves_to`, `is_owned` and `in_library`.

- `decl_path` ports lint/declpath.py. Python's `DeclPathIndex` is the oracle:
  every corpus file's scopes must get the same paths from both
  (`test_decl_paths_match_python`).
- `resolves_to` reads the linker's bindings through OccurrenceCollector,
  collected once per run, the first time a rule asks. It needs the linked
  model: `LintEngine.run(..., model=)`; without one, rules at L1 and above
  are not run.
- A node renders in a message as its declaration path (format §3.4).
"""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]

_A = ("a.pss",
      "import std_pkg::*;\n"                   # 1
      "package p {\n"                          # 2
      "  struct S { rand int v; }\n"           # 3
      "}\n")
_B = ("b.pss",
      "import p::*;\n"                         # 1
      "import addr_reg_pkg::*;\n"              # 2
      "component pss_top {\n"                  # 3
      "  action A {\n"                         # 4
      "    rand S s;\n"                        # 5
      "    rand int x;\n"                      # 6
      "    addr_handle_t h;\n"                 # 7
      "    constraint { x == s.v; }\n"         # 8
      "    exec post_solve { x = 1; }\n"       # 9
      "    exec body { }\n"                    # 10
      "    exec body { }\n"                    # 11
      "  }\n"                                  # 12
      "  action B : A { }\n"                   # 13
      "  function void f() { int loc; loc = 1; }\n"   # 14
      "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([_A, _B])
    root = p.link()
    a, b = p.user_units()
    return p, root, a, b


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _ev(hooks, model, expr, unit=None, linked=True):
    p, root, a, b = model
    r = hooks.cel_check_node({"expr": expr}, unit or b, model=root if linked else None)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _of(kind, cond="true"):
    """The nodes of a class under `node`, by a condition."""
    return "descendants(node).filter(d, type(d) == %s && %s)" % (kind, cond)


# ------------------------------------------------------------ decl_path ----

def test_decl_path_of_declarations(hooks, model):
    assert _ev(hooks, model, _of("Action") + ".map(x, decl_path(x))") == [
        "pss_top::A", "pss_top::B"]
    assert _ev(hooks, model, _of("Field") + ".map(x, decl_path(x))") == [
        "pss_top::A::s", "pss_top::A::x", "pss_top::A::h"]


def test_decl_path_numbers_repeats(hooks, model):
    assert _ev(hooks, model, _of("ExecBlock") + ".map(x, decl_path(x))") == [
        "pss_top::A::exec post_solve", "pss_top::A::exec body", "pss_top::A::exec body#2"]
    assert _ev(hooks, model, _of("ConstraintBlock") + ".map(x, decl_path(x))") == [
        "pss_top::A::constraint"]


def test_decl_path_of_a_non_declaration_is_its_enclosing_one(hooks, model):
    assert _ev(hooks, model, _of("ExprBin") + ".map(x, decl_path(x))") == [
        "pss_top::A::constraint"]


def test_decl_path_inside_a_function_is_the_function(hooks, model):
    # A local variable is not a scope: it takes its function's path.
    assert _ev(hooks, model, "descendants(node).filter(d, d.isa(ProceduralStmtDataDeclaration))"
                             ".map(x, decl_path(x))") == ["pss_top::function f"]


def test_decl_path_of_root_is_empty(hooks, model):
    assert _ev(hooks, model, "decl_path(node)") == ""


def test_decl_path_of_package_member_in_another_file(hooks, model):
    # Navigation reaches a.pss through the model: its parent links are made
    # when first asked for.
    assert _ev(hooks, model, _of("Field", "d.name.id == 's'")
               + ".map(f, decl_path(resolves_to(f.type)))") == ["p::S"]


def _corpus():
    base = ROOT / "packages" / "pss-corpus"
    files = sorted(base.glob("**/*.pss")) if base.is_dir() else []
    files += sorted((ROOT / "src" / "stdlib").glob("*.pss"))
    return files


@pytest.mark.parametrize("path", _corpus(), ids=lambda p: p.name)
def test_decl_paths_match_python(hooks, path):
    """C++ decl_path vs lint/declpath.py, on every scope of every corpus file
    that parses (linked when it links)."""
    from pssparser import Parser
    from pssparser.lint.declpath import index_for
    p = Parser()
    try:
        p.parse([str(path)])
    except Exception:
        pytest.skip("does not parse")
    try:
        p.link()
    except Exception:
        pass
    unit = (p.user_units() or p._files)[-1]

    def flat(scopes, out):
        for s in scopes:
            out.append((s.start[0], s.start[1], s.path))
            flat(s.children, out)
        return out

    python = sorted(flat(index_for(p, [str(path)]).scopes(str(path)), []))
    cpp = sorted((d["line"], d["col"], d["path"]) for d in hooks.decl_paths(unit))
    assert cpp == python


def test_decl_paths_on_the_declpath_model(hooks, tmp_path):
    # The model test_declpath.py checks path_at on, scope by scope.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "declpath_tests", ROOT / "tests" / "python" / "lint" / "test_declpath.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from pssparser import Parser
    p = Parser()
    p.parses([("m.pss", mod.MODEL)])
    p.link()
    paths = [d["path"] for d in hooks.decl_paths(p.user_units()[-1])]
    for want in ("p::C::A::constraint c", "p::C::A::constraint#2", "p::C::A::exec body#2",
                 "p::C::function f", "extend action p::C::A#2", "a::b::function g", "p::t"):
        assert want in paths, (want, paths)


# ---------------------------------------------------------- resolves_to ----

def test_resolves_to_an_identifier_and_a_path(hooks, model):
    # x == s.v: `x` is A's field; `s.v` is S's field v (the last name). `loc`
    # is f's local, whose path is f's.
    assert _ev(hooks, model, _of("ExprRefPathContext") + ".map(r, decl_path(resolves_to(r)))") \
        == ["pss_top::A::x", "p::S::v", "pss_top::A::x", "pss_top::function f"]


def test_resolves_to_a_type(hooks, model):
    assert _ev(hooks, model, _of("Field") + ".filter(f, resolves_to(f.type) != null)"
                             ".map(f, decl_path(resolves_to(f.type)))") == [
        "p::S", "addr_reg_pkg::addr_handle_t"]
    assert _ev(hooks, model, _of("Action", "has(d.super_t)")
               + ".map(x, decl_path(resolves_to(x.super_t)))") == ["pss_top::A"]


def test_resolves_to_is_identity(hooks, model):
    # Both `x`s name one declaration.
    assert _ev(hooks, model, "size(%s.map(r, resolves_to(r)).filter(d, type(d) == Field "
                             "&& d.name.id == 'x'))" % _of("ExprRefPathContext")) == 2
    assert _ev(hooks, model, "%s[0] == %s[2]" % (
        _of("ExprRefPathContext") + ".map(r, resolves_to(r))",
        _of("ExprRefPathContext") + ".map(r, resolves_to(r))")) is True


def test_resolves_to_a_non_reference_is_null(hooks, model):
    assert _ev(hooks, model, _of("ExprBin") + ".map(e, resolves_to(e) == null)") == [True]
    assert _ev(hooks, model, _of("Field", "d.name.id == 'x'")
               + ".map(f, resolves_to(f.type) == null)") == [True]     # int


def test_resolves_to_needs_a_model(hooks, model):
    p, root, a, b = model
    r = hooks.cel_check_node({"expr": _of("ExprRefPathContext") + ".map(r, resolves_to(r))"},
                             b)
    assert r["errors"] == []
    v = r["values"]["expr"]
    assert v["type"] == "error" and "needs a linked model" in v["value"]


# --------------------------------------------------- is_owned, in_library ----

def test_owned_and_library(hooks, model):
    # cel_check_node owns only b.pss.
    got = _ev(hooks, model, _of("Field") + ".filter(f, resolves_to(f.type) != null)"
                                 ".map(f, [is_owned(f), is_owned(resolves_to(f.type)),"
                                 " in_library(resolves_to(f.type))])")
    assert got == [[True, False, False], [True, False, True]]


def test_root_is_owned_and_not_library(hooks, model):
    assert _ev(hooks, model, "[is_owned(node), in_library(node)]") == [True, False]


# ---------------------------------------------------------------- runs ----

_RULES = """\
pss-rules:
  version: 1
  rules:
    - id: ACME001
      name: lib-type
      tier: style
      summary: s
      message: "${node} has a library type, ${resolves_to(node.type)}"
      match: { kind: Field }
      where: has(node.type) && in_library(resolves_to(node.type))
    - id: ACME002
      name: decl
      tier: style
      summary: s
      message: "${node}"
      match: { kind: ExecBlock }
"""


def _engine(factory):
    e = factory.mkLintEngine()
    assert e.load_rules("r.yaml", _RULES)
    assert e.rule_diagnostics() == []
    return e


def test_run_with_model(factory, model):
    p, root, a, b = model
    r = _engine(factory).run([b], {}, model=root)
    assert r["problems"] == []
    assert [(m["code"], m["line"], m["message"]) for m in r["markers"]] == [
        ("ACME001", 7, "pss_top::A::h has a library type, addr_reg_pkg::addr_handle_t"),
        ("ACME002", 9, "pss_top::A::exec post_solve"),
        ("ACME002", 10, "pss_top::A::exec body"),
        ("ACME002", 11, "pss_top::A::exec body#2")]


def test_run_without_model_leaves_out_symbol_rules(factory, model):
    p, root, a, b = model
    r = _engine(factory).run([b], {})
    assert r["problems"] == ["rule ACME001 needs a linked model (level L1); not run"]
    assert {m["code"] for m in r["markers"]} == {"ACME002"}


def test_rule_levels(factory):
    levels = {x["id"]: (x["level"], x["scope"]) for x in _engine(factory).rules()}
    assert levels == {"ACME001": ("L1", "file"), "ACME002": ("L0", "file")}


def test_message_renders_a_local_by_its_name(hooks, model):
    # Inside a function, a local's path is the function's: it shows its name.
    p, root, a, b = model
    r = hooks.lint_run("r.yaml", _RULES.replace("kind: ExecBlock",
                                                "kind: ProceduralStmtDataDeclaration"),
                       [b], enabled=["ACME002"], model=root)
    assert [f["msg"] for f in r["findings"]] == ["loc"]


# ------------------------------------------------------------- registry ----

def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    expect = {
        "decl_path_node": ("L0", "custom"),
        "resolves_to_node": ("L1", "constant"),
        "is_owned_node": ("L0", "constant"),
        "in_library_node": ("L0", "constant"),
    }
    for oid, (level, cost) in expect.items():
        f = fns[oid]
        assert (f["group"], f["level"], f["scope"], f["cost"], f["library"]) == (
            "Symbols", level, "file", cost, "pss"), f


# ------------------------------------------------------------------ null ----

def test_null_is_no_node(hooks, model):
    # resolves_to(int) is null; the predicates take null as "no node", and
    # resolves_to passes it through, so a chain needs no has() first.
    assert _ev(hooks, model, _of("Field", "d.name.id == 'x'")
               + ".map(f, [is_owned(resolves_to(f.type)), in_library(resolves_to(f.type)),"
                 " resolves_to(resolves_to(f.type)) == null])") == [[False, False, True]]
    assert _ev(hooks, model, _of("Action", "!has(d.super_t)")
               + ".map(x, resolves_to(x.super_t) == null)") == [True]


def test_decl_path_of_null_is_an_error(hooks, model):
    r = hooks.cel_check_node({"expr": _of("Field", "d.name.id == 'x'")
                              + ".map(f, decl_path(resolves_to(f.type)))"},
                             model[3], model=model[1])
    assert r["values"]["expr"]["type"] == "error"
