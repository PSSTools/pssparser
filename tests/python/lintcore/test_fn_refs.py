"""References (lint-core-plan.md C6.3; lint-framework-plan.md S4).

`refs`, `is_read`, `is_written` and `used_only_by_itself`.

- `refs(d)` lists the identifiers naming `d` in every user file of the model,
  owned or not, from the same OccurrenceCollector bindings as `resolves_to`.
  A function's uses are its calls, which resolve to its prototype; either the
  definition or the prototype may be passed.
- `is_read`/`is_written` are by position: an assignment's or a traversal
  initializer's target is written (`+=` also reads it); a `with` constraint
  only reads.
- `refs` and `used_only_by_itself` are whole-model (L4): a rule calling them
  has scope `model`.
"""
import pytest

_A = ("a.pss",
      "component pss_top {\n"                                                     # 1
      "  int g;\n"                                                                # 2
      "  function int rec(int n) { if (n > 0) { return rec(n - 1); } return 0; }\n"  # 3
      "  function int unused_f() { return 1; }\n"                                 # 4
      "  action Sub { rand int x; rand int y; }\n"                                # 5
      "  action A {\n"                                                            # 6
      "    rand int a;\n"                                                         # 7
      "    int w;\n"                                                              # 8
      "    Sub s;\n"                                                              # 9
      "    exec post_solve {\n"                                                   # 10
      "      w = a;\n"                                                            # 11
      "      w += 1;\n"                                                           # 12
      "      s.x = 2;\n"                                                          # 13
      "    }\n"                                                                   # 14
      "    activity {\n"                                                          # 15
      "      s with { x == a; };\n"                                               # 16
      "      do Sub {.y = 3};\n"                                                  # 17
      "    }\n"                                                                   # 18
      "  }\n"                                                                     # 19
      "}\n")
_B = ("b.pss",
      "extend component pss_top {\n"
      "  exec init_down { g = 5; }\n"
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


def _ev(hooks, model, expr, linked=True):
    p, root, a, b = model
    r = hooks.cel_check_node({"expr": expr}, a, model=root if linked else None)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _field(name):
    return "descendants(node).filter(d, type(d) == Field && d.name.id == '%s')[0]" % name


def _fn(name):
    return ("descendants(node).filter(d, type(d) == FunctionDefinition "
            "&& d.proto.name.id == '%s')[0]" % name)


# ----------------------------------------------------------------- refs ----

def test_refs_in_source_order(hooks, model):
    assert _ev(hooks, model, "refs(%s).map(r, r.location.lineno)" % _field("w")) == [11, 12]
    assert _ev(hooks, model, "refs(%s).map(r, r.location.lineno)" % _field("a")) == [11, 16]


def test_refs_are_identifiers_naming_the_declaration(hooks, model):
    assert _ev(hooks, model, "refs(%s).all(r, type(r) == ExprId && resolves_to(r) == %s)"
               % (_field("x"), _field("x"))) is True


def test_refs_exclude_the_declaration_name(hooks, model):
    assert _ev(hooks, model, "size(refs(%s))" % _field("y")) == 1     # {.y = 3} only


def test_a_use_outside_the_owned_files_counts(hooks, model):
    # g's only use is in b.pss, which this check does not own.
    assert _ev(hooks, model, "refs(%s).map(r, is_owned(r))" % _field("g")) == [False]


def test_refs_of_a_function_are_its_calls(hooks, model):
    # Definition or prototype: the same calls.
    assert _ev(hooks, model, "[size(refs(%s)), size(refs(%s.proto)), size(refs(%s))]"
               % (_fn("rec"), _fn("rec"), _fn("unused_f"))) == [1, 1, 0]


def test_refs_of_null_is_empty(hooks, model):
    assert _ev(hooks, model, "refs(%s.super_t)" % _fn("rec").replace(
        "FunctionDefinition && d.proto.name.id == 'rec'", "Action && d.name.id == 'A'")) == []


def test_refs_needs_a_model(hooks, model):
    p, root, a, b = model
    r = hooks.cel_check_node({"expr": "refs(%s)" % _field("w")}, a)
    v = r["values"]["expr"]
    assert v["type"] == "error" and "needs a linked model" in v["value"]


# ------------------------------------------------- is_read, is_written ----

_ACCESS = ("descendants(node).filter(d, type(d) == ExprId && resolves_to(d) != null "
           "&& (is_read(d) || is_written(d))).map(i, string(i.location.lineno) + ':' + i.id "
           "+ (is_read(i) ? ' R' : '') + (is_written(i) ? ' W' : ''))")


def test_read_and_write_by_position(hooks, model):
    assert _ev(hooks, model, _ACCESS) == [
        "3:n R", "3:rec R", "3:n R",            # the recursive call and its argument
        "9:Sub R",                              # a type is read
        "11:w W", "11:a R",                     # w = a
        "12:w R W",                             # compound: read, then written
        "13:s R", "13:x W",                     # s.x = 2: only the last name is assigned
        "16:s R", "16:x R", "16:a R",           # with { x == a; }: a constraint reads
        "17:Sub R", "17:y W",                   # do Sub {.y = 3}: the initializer writes
    ]


def test_declaration_names_are_not_uses(hooks, model):
    assert _ev(hooks, model, "[is_read(%s.name), is_written(%s.name)]"
               % (_field("w"), _field("w"))) == [False, False]


def test_a_reference_expression_is_its_last_name(hooks, model):
    # The ExprRefPathContext for `s.x` on line 13 behaves as `x`.
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ProceduralStmtAssignment)"
                             ".map(s, [is_written(s.lhs), is_read(s.lhs)])") == [
        [True, False], [True, True], [True, False]]


def test_access_needs_no_model(hooks, model):
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ProceduralStmtAssignment)"
                             ".map(s, is_written(s.lhs))", linked=False) == [True, True, True]


def test_not_a_reference(hooks, model):
    assert _ev(hooks, model, "[is_read(node), is_written(node)]") == [False, False]


# ----------------------------------------------------- used_only_by_itself ----

def test_used_only_by_itself(hooks, model):
    assert _ev(hooks, model, "[used_only_by_itself(%s), used_only_by_itself(%s.proto),"
                             " used_only_by_itself(%s), used_only_by_itself(%s)]"
               % (_fn("rec"), _fn("rec"), _fn("unused_f"), _field("w"))) == [
        True, True, False, False]


# -------------------------------------------------------------- level ----

_RULES = """\
pss-rules:
  version: 1
  rules:
    - id: ACME001
      name: unused-field
      tier: suspicious
      summary: s
      message: "${node} is never used"
      match: { kind: Field }
      where: is_owned(node) && size(refs(node)) == 0
    - id: ACME002
      name: write-only
      tier: suspicious
      summary: s
      message: "${node} is written but never read"
      match: { kind: Field }
      where: size(refs(node)) > 0 && refs(node).all(r, !is_read(r))
"""


def test_model_scope_and_findings(factory, model):
    p, root, a, b = model
    e = factory.mkLintEngine()
    assert e.load_rules("r.yaml", _RULES) and e.rule_diagnostics() == []
    assert {x["id"]: (x["level"], x["scope"]) for x in e.rules()} == {
        "ACME001": ("L4", "model"), "ACME002": ("L4", "model")}
    r = e.run([a], {}, model=root)
    assert [(m["code"], m["line"], m["message"]) for m in r["markers"]] == [
        ("ACME002", 2, "pss_top::g is written but never read"),
        # x is assigned (s.x = 2) but also read, in the `with` constraint.
        ("ACME002", 5, "pss_top::Sub::y is written but never read")]


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    expect = {
        "is_read_node": ("L0", "file"),
        "is_written_node": ("L0", "file"),
        "refs_node": ("L4", "model"),
        "used_only_by_itself_node": ("L4", "model"),
    }
    for oid, (level, scope) in expect.items():
        f = fns[oid]
        assert (f["group"], f["level"], f["scope"], f["cost"]) == (
            "References", level, scope, "custom"), f
