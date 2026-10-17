"""Imports and the core library (lint-framework-plan F3.5).

- `import_uses(i)`: the names an import provides in its scope -- written
  unqualified, first in their path, resolving to what it imports -- in
  source order. Used by unused-import.
- `core_library_name(name)`: the core library's declaration of a name,
  qualified, or none. Used by shadows-core-library-name.
"""
import pytest

_A = ("a.pss",
      "package a_pkg {\n"                                  # 1
      "  enum mode_e { RD, WR };\n"                        # 2
      "  struct s_t { rand bit[4] v; }\n"                  # 3
      "  const int K = 3;\n"                               # 4
      "  struct own_t { s_t inner; }\n"                    # 5
      "}\n"                                                # 6
      "package b_pkg { struct t_t { } struct u_t { } }\n"  # 7
      "package outer_pkg {\n"                              # 8
      "  package inner_pkg { struct n_t { } }\n"           # 9
      "}\n"                                                # 10
      "component pss_top {\n"                              # 11
      "  import a_pkg::*;\n"                               # 12
      "  import b_pkg::t_t;\n"                             # 13
      "  import a_pkg::mode_e;\n"                          # 14
      "  import b_pkg as b;\n"                             # 15
      "  import outer_pkg::*;\n"                           # 16
      "  import std_pkg::*;\n"                             # 17
      "  s_t s;\n"                                         # 18
      "  b_pkg::t_t t;\n"                                  # 19
      "  b::u_t u;\n"                                      # 20
      "  inner_pkg::n_t n;\n"                              # 21
      "  action A {\n"                                     # 22
      "    rand bit[4] x;\n"                               # 23
      "    rand mode_e m;\n"                                # 24
      "    constraint x < K && x != s.v;\n"                # 25
      "    constraint m == RD;\n"                          # 26
      "    exec post_solve { message(LOW, \"x\"); }\n"     # 27
      "  }\n"                                              # 28
      "}\n")
_B = ("b.pss",
      "extend component pss_top {\n"
      "  a_pkg::s_t s2;\n"
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
    return root, a


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _ev(hooks, model, expr):
    root, unit = model
    r = hooks.cel_check_node({"expr": expr}, unit, model=root)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _uses(hooks, model, line):
    return _ev(hooks, model,
               "descendants(node, PackageImportStmt).filter(i, i.location.lineno == %d)"
               ".map(i, import_uses(i).map(u, string(u.location.lineno) + ':' + u.id))[0]"
               % line)


def test_wildcard_import(hooks, model):
    # s_t (a type), K (a constant), RD (an item of an enum in the package);
    # not s.v (a member reached through a value).
    assert _uses(hooks, model, 12) == ["18:s_t", "24:mode_e", "25:K", "26:RD"]


def test_explicit_import(hooks, model):
    # t_t is used only qualified, which needs no import.
    assert _uses(hooks, model, 13) == []


def test_explicit_import_of_an_enum_brings_its_items(hooks, model):
    assert _uses(hooks, model, 14) == ["24:mode_e", "26:RD"]


def test_alias(hooks, model):
    assert _uses(hooks, model, 15) == ["20:b"]


def test_nested_package(hooks, model):
    assert _uses(hooks, model, 16) == ["21:inner_pkg"]


def test_the_core_library(hooks, model):
    assert _uses(hooks, model, 17) == ["27:message", "27:LOW"]


def test_not_an_import(hooks, model):
    assert _ev(hooks, model, "import_uses(node)") == []
    assert _ev(hooks, model, "import_uses(null)") == []


def test_a_use_inside_the_package_needs_no_import(hooks):
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("c.pss",
               "import a_pkg::*;\n"
               "package a_pkg {\n"
               "  struct s_t { }\n"
               "  struct own_t { s_t inner; }\n"
               "}\n")])
    root = p.link()
    (unit,) = p.user_units()
    r = hooks.cel_check_node({"expr": "import_uses(descendants(node, PackageImportStmt)[0])"},
                             unit, model=root)
    assert r["errors"] == [] and _py(r["values"]["expr"]) == []


def test_needs_a_model(hooks, model):
    root, unit = model
    r = hooks.cel_check_node({"expr": "import_uses(descendants(node, PackageImportStmt)[0])"},
                             unit)
    assert r["values"]["expr"]["type"] == "error"


# -------------------------------------------------------- core_library_name ----

@pytest.mark.parametrize("name,want", [
    ("message", "std_pkg::message"),
    ("packed_s", "std_pkg::packed_s"),
    ("addr_handle_t", "addr_reg_pkg::addr_handle_t"),
    ("executor_c", "executor_pkg::executor_c"),
    ("LOW", None),          # an enum item is in its enum, not in std_pkg
    ("pss_top", None),
])
def test_core_library_name(hooks, model, name, want):
    got = _ev(hooks, model, "core_library_name('%s').orValue('')" % name)
    assert got == (want or "")


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    assert (fns["import_uses_node"]["group"], fns["import_uses_node"]["level"],
            fns["import_uses_node"]["scope"]) == ("Symbols", "L1", "file")
    assert fns["core_library_name_string"]["group"] == "Fields and types"
