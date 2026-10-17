"""Constants (lint-core-plan.md C6.4; lint-framework-plan.md S2).

`const_int` and `const_bool`: the linker's constant folder (TaskEvalExpr), as
`lib::ConstEval` narrows it. A reference folds only through a `const` field
or a bound template value parameter; anything else is `optional.none()`, and
so is an integer that `int` cannot hold. They never raise (except without a
linked model).

A bound template parameter belongs to a specialization, which no rule can
reach yet: `resolves_to` gives the generic template. C6.8's `type_decl` is
where that case gets its test.
"""
import pytest

_A = ("a.pss",
      "package p {\n"                                       # 1
      "  const int K = 3;\n"                                # 2
      "  const bool B = (K > 2);\n"                         # 3
      "  enum e_t { E0, E1 = 5 }\n"                         # 4
      "  struct T<int W = 4> {\n"                           # 5
      "    rand bit[W] v;\n"                                # 6
      "    constraint { v < W; }\n"                         # 7
      "  }\n"                                               # 8
      "}\n"                                                 # 9
      "component pss_top {\n"                               # 10
      "  int nc = 7;\n"                                     # 11
      "  static const int SK = p::K * 2;\n"                 # 12
      "  action A {\n"                                      # 13
      "    rand int x;\n"                                   # 14
      "    p::T<8> t8;\n"                                   # 15
      "    constraint {\n"                                  # 16
      "      x == 1 + 2;\n"                                 # 17
      "      x != p::K;\n"                                  # 18
      "      x != SK;\n"                                    # 19
      "      x != nc;\n"                                    # 20
      "      x != p::E1;\n"                                 # 21
      "      x != (p::B ? 1 : 0);\n"                        # 22
      "      x < 72'hFFFFFFFFFFFFFFFFFF;\n"                 # 23
      "      x < 64'hFFFFFFFFFFFFFFFF;\n"                   # 24
      "      x < 64'h7FFFFFFFFFFFFFFF;\n"                   # 25
      "      x != (7 / 0);\n"                               # 26
      "      true;\n"                                       # 27
      "      1 == 2;\n"                                     # 28
      "    }\n"                                             # 29
      "  }\n"                                               # 30
      "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    from pssparser.parser import ParseException
    p = Parser()
    p.parses([_A])
    try:
        root = p.link()
    except ParseException as e:
        # Line 26's `7 / 0` is kept on purpose -- const_int must not fold it
        # -- and is an error now (PSS139, LRM 8.5.1). Nothing else is.
        assert [m["line"] for m in e.markers if m["severity"] == "error"] == [26]
        root = p._root
    (a,) = p.user_units()
    return p, root, a


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    if v["type"] == "optional_type":
        return None if v["value"] is None else _py(v["value"])
    return v.get("value")


def _ev(hooks, model, expr, linked=True):
    p, root, a = model
    r = hooks.cel_check_node({"expr": expr}, a, model=root if linked else None)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


# The constraint statements of action A, in order (lines 17-28).
_STMTS = ("enclosing(descendants(node).filter(d, type(d) == Field && d.name.id == 'x')[0],"
          " Action)")
_A_STMTS = ("descendants(node).filter(d, type(d) == ConstraintStmtExpr"
            " && enclosing(d, Action) != null)")


def _rhs(fn):
    return _A_STMTS + ".map(s, type(s.expr) == ExprBin ? %s(s.expr.rhs) : %s(s.expr))" % (fn, fn)


def test_const_int_through_references(hooks, model):
    assert _ev(hooks, model, _rhs("const_int")) == [
        3,          # 1 + 2
        3,          # p::K, a const field in a package
        6,          # SK = p::K * 2, a static const field
        None,       # nc: not const
        None,       # p::E1: an enum item is not an int
        1,          # (p::B ? 1 : 0), through a const bool
        None,       # 72 bits: wider than int
        None,       # 64'hFFFF...: unsigned above INT64_MAX
        2 ** 63 - 1,
        None,       # 7 / 0 does not fold
        1,          # `true`: the whole statement
        2,          # the rhs of 1 == 2
    ]


def test_a_non_constant_reference_does_not_fold(hooks, model):
    assert _ev(hooks, model, _A_STMTS + ".map(s, const_int(s.expr))")[:2] == [None, None]


def test_const_bool(hooks, model):
    got = _ev(hooks, model, _A_STMTS + ".map(s, const_bool(s.expr))")
    assert got[-2:] == [True, False]
    assert set(got[:-2]) == {None}       # x == ..., x != ...: x is not constant


def test_const_bool_is_only_boolean(hooks, model):
    # 1 + 2 folds, but to an int.
    assert _ev(hooks, model, _A_STMTS + ".map(s, type(s.expr) == ExprBin ? "
                             "const_bool(s.expr.rhs) : optional.none())")[0] is None


def test_a_declaration_folds_to_its_value(hooks, model):
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == Field)"
                             ".map(f, [f.name.id, string(const_int(f).orValue(-1))])") == [
        ["K", "3"], ["B", "1"], ["v", "-1"], ["nc", "-1"], ["SK", "6"], ["x", "-1"],
        ["t8", "-1"]]


def test_unbound_template_parameter_does_not_fold(hooks, model):
    # In the generic template, W's default (4) is not its value.
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ConstraintStmtExpr"
                             " && enclosing(d, Struct) != null)"
                             ".map(s, type(s.expr) == ExprBin ? const_int(s.expr.rhs) "
                             ": optional.none())") == [None]
    assert _ev(hooks, model, "descendants(node).filter(d, d.isa(TemplateValueParamDecl))"
                             ".map(t, const_int(t))") == [None]


def test_null_and_non_expressions(hooks, model):
    assert _ev(hooks, model, "[const_int(node), const_int(%s.super_t)]" % _STMTS) == [
        None, None]


def test_needs_a_model(hooks, model):
    p, root, a = model
    r = hooks.cel_check_node({"expr": "const_int(node)"}, a)
    v = r["values"]["expr"]
    assert v["type"] == "error" and "needs a linked model" in v["value"]


_RULES = """\
pss-rules:
  version: 1
  rules:
    - id: ACME001
      name: constant-constraint
      tier: suspicious
      summary: s
      message: "this constraint is always ${const_bool(node.expr).value()}"
      match: { kind: ConstraintStmtExpr }
      where: const_bool(node.expr).hasValue()
"""


def test_level_and_run(factory, model):
    p, root, a = model
    e = factory.mkLintEngine()
    assert e.load_rules("r.yaml", _RULES) and e.rule_diagnostics() == []
    assert [(x["level"], x["scope"]) for x in e.rules()] == [("L3", "file")]
    r = e.run([a], {}, model=root)
    assert [(m["line"], m["message"]) for m in r["markers"]] == [
        (27, "this constraint is always true"), (28, "this constraint is always false")]


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    for oid in ("const_int_node", "const_bool_node"):
        f = fns[oid]
        assert (f["group"], f["level"], f["scope"], f["cost"]) == (
            "Constants", "L3", "file", "constant"), f
