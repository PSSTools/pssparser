"""Kind tests and navigation (lint-core-plan.md C6.1; lint-rule-expressions.md §3).

`isa`, `parent`, `ancestors`, `enclosing`, `children`, `descendants`,
`siblings` and `index_of`. Parent links come from the run's library context,
which indexes every file before any rule runs, so navigation sees nodes
the walk has not reached yet and nodes of other files.

Two kinds of node are not children (Walker.h):
- an element of a list that does not own it: the linker lists an `extend`'s
  members in a template's body that way;
- the builder's implicit `comp` handle (a FieldCompRef without a location)
  in every action.

Each function also has a rule with examples in
tests/data/lint-examples/fn-navigation.yaml, which the WASM parity fixture
runs.
"""
import pytest

_MODEL = (
    "component pss_top {\n"                         # 1
    "  int cf;\n"                                   # 2
    "  action A {\n"                                # 3
    "    rand int a;\n"                             # 4
    "    rand int b;\n"                             # 5
    "    constraint c { a > b + 1; b < 4; }\n"      # 6
    "  }\n"                                         # 7
    "  action B : A { }\n"                          # 8
    "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def unit():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL)])
    return p, p._files[-1]


def _py(v):
    """A cel_check value as Python: lists and scalars; a type as its name."""
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _check(hooks, root, expr, **doc):
    doc = dict(doc, expr=expr)
    return hooks.cel_check_node(doc, root)


def _ev(hooks, unit, expr, **doc):
    r = _check(hooks, unit[1], expr, **doc)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _errors(hooks, unit, expr):
    return [e["message"] for e in _check(hooks, unit[1], expr)["errors"]]


# Bindings used below (each a let:, so `expr` can name them).
_LETS = {
    "let": {
        "top": "node.children.filter(c, type(c) == Component)[0]",
        "act": "descendants(node).filter(d, type(d) == Action)[0]",
        "fa": "descendants(node).filter(d, type(d) == Field && d.name.id == 'a')[0]",
        "fb": "descendants(node).filter(d, type(d) == Field && d.name.id == 'b')[0]",
        "bin": "descendants(node).filter(d, type(d) == ExprBin)[0]",
    }
}


def _lev(hooks, unit, expr):
    return _ev(hooks, unit, expr, **_LETS)


# ------------------------------------------------------------- isa ----

def test_isa_exact_and_base_classes(hooks, unit):
    assert _lev(hooks, unit, "[act.isa(Action), act.isa(TypeScope), act.isa(ScopeChild),"
                             " act.isa(Field)]") == [True, True, True, False]


def test_isa_differs_from_type_equality(hooks, unit):
    # type() is the exact class; isa follows `super:`.
    assert _lev(hooks, unit, "[type(act) == TypeScope, act.isa(TypeScope)]") == [False, True]


def test_isa_narrows_after_and(hooks, unit):
    # `name` is NamedScope's: without narrowing, a ScopeChild has none.
    assert _ev(hooks, unit, "node.children.filter(c, c.isa(NamedScope) && c.name.id != '')"
                            ".map(c, c.isa(Component) ? c.name.id : '')") == ["pss_top"]


def test_isa_needs_a_node_class(hooks, unit):
    (msg,) = _errors(hooks, unit, "node.isa(int)")
    assert "isa() needs a node class" in msg and "'int'" in msg


def test_isa_class_must_be_written_out(hooks, unit):
    (msg,) = _errors(hooks, unit, "node.isa(type(node))")
    assert "isa() needs a node class" in msg


def test_isa_unknown_class(hooks, unit):
    (msg,) = _errors(hooks, unit, "node.isa(Actoin)")
    assert "undeclared reference to 'Actoin'" in msg


# ---------------------------------------------------- parent, ancestors ----

def test_parent_of_root_is_null(hooks, unit):
    assert _ev(hooks, unit, "parent(node) == null") is True


def test_parent_of_declaration_and_operand(hooks, unit):
    assert _lev(hooks, unit, "[type(parent(fa)) == Action, parent(fa) == act,"
                             " parent(top) == node, parent(bin.lhs) == bin]") == [True] * 4


def test_ancestors_nearest_first(hooks, unit):
    assert _lev(hooks, unit, "ancestors(fa).map(x, type(x))") == [
        "Action", "Component", "GlobalScope"]
    assert _lev(hooks, unit, "ancestors(fa)[0] == parent(fa)") is True


def test_ancestors_of_root_is_empty(hooks, unit):
    assert _ev(hooks, unit, "ancestors(node)") == []


def test_ancestors_of_deep_expression(hooks, unit):
    # b + 1, inside a > b + 1, inside the constraint statement, ...
    assert _lev(hooks, unit, "ancestors(bin.rhs).map(x, type(x))") == [
        "ExprBin", "ConstraintStmtExpr", "ConstraintBlock", "Action", "Component",
        "GlobalScope"]


# ------------------------------------------------------------ enclosing ----

def test_enclosing_nearest(hooks, unit):
    assert _lev(hooks, unit, "[enclosing(bin, Action) == act, enclosing(fa, Component) == top]") \
        == [True, True]


def test_enclosing_matches_derived_classes(hooks, unit):
    # The nearest TypeScope above a field is its action.
    assert _lev(hooks, unit, "enclosing(fa, TypeScope) == act") is True


def test_enclosing_excludes_the_node_itself(hooks, unit):
    assert _lev(hooks, unit, "enclosing(act, Action) == null") is True


def test_enclosing_result_has_the_class(hooks, unit):
    r = _check(hooks, unit[1], "enclosing(fa, Action).name.id", **_LETS)
    assert r["types"]["expr"] == "string"
    assert _py(r["values"]["expr"]) == "A"


def test_enclosing_none_is_null(hooks, unit):
    assert _lev(hooks, unit, "enclosing(fa, ExecBlock) == null") is True


def test_enclosing_navigating_through_none_is_an_error(hooks, unit):
    r = _check(hooks, unit[1], "enclosing(fa, ExecBlock).kind", **_LETS)
    assert r["errors"] == []
    assert r["values"]["expr"]["type"] == "error"


def test_enclosing_needs_a_node_class(hooks, unit):
    (msg,) = _errors(hooks, unit, "enclosing(node, int)")
    assert "enclosing() needs a node class" in msg
    (msg,) = _errors(hooks, unit, "enclosing(node, 'Action')")
    assert "no matching overload for 'enclosing'" in msg


# -------------------------------------------------- children, descendants ----

def test_children_in_source_order(hooks, unit):
    # The action's items, then its name: base class fields first.
    assert _lev(hooks, unit, "children(act).map(x, type(x))") == [
        "Field", "Field", "ConstraintBlock", "ExprId"]


def test_children_leave_out_references(hooks, unit):
    # B's super_t is a child (a TypeIdentifier it owns); the action it names is not.
    assert _ev(hooks, unit,
               "descendants(node).filter(d, type(d) == Action && has(d.super_t))"
               ".map(b, children(b).map(x, type(x)))") == [
        ["ExprId", "TypeIdentifier"]]


def test_descendants_pre_order(hooks, unit):
    assert _lev(hooks, unit, "descendants(bin).map(x, type(x))") == [
        "ExprRefPathContext", "ExprHierarchicalId", "ExprMemberPathElem", "ExprId",
        "ExprBin", "ExprRefPathContext", "ExprHierarchicalId", "ExprMemberPathElem",
        "ExprId", "ExprUnsignedNumber"]


def test_descendants_exclude_the_node(hooks, unit):
    assert _lev(hooks, unit, "descendants(fa).exists(x, x == fa)") is False
    assert _lev(hooks, unit, "descendants(node).exists(x, x == fa)") is True


def test_descendants_charge_a_step_per_element(hooks, unit):
    small = _check(hooks, unit[1], "size(descendants(node)) >= 0")
    n = _ev(hooks, unit, "size(descendants(node))")
    (s1,) = small["steps"].values()
    tiny = _check(hooks, unit[1], "size([]) >= 0")
    (s0,) = tiny["steps"].values()
    assert s1 - s0 >= n


# ------------------------------------------------------ siblings, index_of ----

def test_siblings_and_index_in_a_list(hooks, unit):
    assert _lev(hooks, unit, "[index_of(fa), index_of(fb)]") == [0, 1]
    assert _lev(hooks, unit, "siblings(fb).map(x, type(x))") == [
        "Field", "ConstraintBlock"]
    assert _lev(hooks, unit, "siblings(fa).exists(x, x == fa)") is False


def test_constraint_items_are_siblings(hooks, unit):
    assert _lev(hooks, unit, "[index_of(parent(bin)), size(siblings(parent(bin)))]") == [0, 1]


def test_single_field_has_no_siblings(hooks, unit):
    assert _lev(hooks, unit, "[index_of(bin.lhs), size(siblings(bin.lhs))]") == [-1, 0]


def test_root_has_no_siblings(hooks, unit):
    assert _ev(hooks, unit, "[index_of(node), size(siblings(node))]") == [-1, 0]


# ------------------------------------------ nodes that are not children ----

def test_implicit_comp_is_not_a_child(hooks, unit):
    # The builder puts a `comp` FieldCompRef first in every action.
    assert _lev(hooks, unit, "descendants(node).exists(d, d.isa(FieldCompRef))") is False
    assert _lev(hooks, unit, "act.children.exists(c, c.isa(FieldCompRef))") is False
    assert _lev(hooks, unit, "index_of(fa)") == 0


def _linked(*files):
    from pssparser.parser import Parser
    p = Parser()
    p.parses(list(files))
    p.link()
    return p, p.user_units()


_TEMPLATE = ("t.pss", "package p {\n  struct S<int W=4> {\n    rand bit[W] a;\n  }\n}\n")
_EXTEND = ("e.pss", "extend struct p::S {\n  rand int x;\n}\n"
                    "component pss_top { p::S<> s; }\n")


def test_extend_member_belongs_to_the_extend(hooks):
    p, (t, e) = _linked(_TEMPLATE, _EXTEND)
    r = hooks.cel_check_node({"expr": "descendants(node).filter(d, type(d) == Struct)"
                                      ".map(s, s.children.map(c, type(c)))"}, t)
    assert r["errors"] == [], r
    # The linker lists x in S's body too, without owning it.
    assert _py(r["values"]["expr"]) == [["Field"]]


_RUN_RULE = """\
pss-rules:
  version: 1
  rules:
    - id: ACME001
      name: r
      tier: style
      summary: s
      message: "${node.name.id} in ${parent(node)}, ${size(ancestors(node))} deep"
      match: { kind: %s }
"""


def test_run_reports_extend_member_in_its_own_file(hooks):
    p, units = _linked(_TEMPLATE, _EXTEND)
    r = hooks.lint_run("r.yaml", _RUN_RULE % "Field", units)
    assert r["diagnostics"] == []
    assert [(f["line"], f["msg"]) for f in r["findings"]] == [
        (3, "a in p::S, 3 deep"), (2, "x in extend struct p::S, 2 deep"),
        (4, "s in pss_top, 2 deep")]


def test_run_never_matches_the_implicit_comp(hooks, unit):
    r = hooks.lint_run("r.yaml", _RUN_RULE % "FieldCompRef", [unit[1]])
    assert r["diagnostics"] == []
    assert r["findings"] == [] and r["stats"][0]["matches"] == 0


# ---------------------------------------------------------- across files ----

def test_parent_across_files(hooks):
    # The run indexes every file before the first runs, so a rule in the
    # first file can navigate nodes of the second.
    p, units = _linked(("a.pss", "component pss_top {\n  action A { }\n}\n"),
                       ("b.pss", "package q {\n  struct T { rand int f; }\n}\n"))
    rule = _RUN_RULE.replace("message: \"${node.name.id} in ${parent(node)}, "
                             "${size(ancestors(node))} deep\"",
                             "message: \"${node.name.id}\"") \
        % "Action" + "      where: size(ancestors(node)) == 2\n"
    r = hooks.lint_run("r.yaml", rule, units)
    assert r["diagnostics"] == [] and [f["msg"] for f in r["findings"]] == ["A"]


# ------------------------------------------------------------- registry ----

def test_registered_with_group_level_and_cost(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    expect = {
        "node_isa": ("Kind tests", "constant"),
        "parent_node": ("Navigation", "constant"),
        "ancestors_node": ("Navigation", "custom"),
        "enclosing_node_type": ("Navigation", "custom"),
        "children_node": ("Navigation", "custom"),
        "descendants_node": ("Navigation", "custom"),
        "siblings_node": ("Navigation", "custom"),
        "index_of_node": ("Navigation", "custom"),
    }
    for oid, (group, cost) in expect.items():
        f = fns[oid]
        assert (f["group"], f["cost"], f["level"], f["scope"], f["library"]) == (
            group, cost, "L0", "file", "pss"), f
