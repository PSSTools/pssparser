"""Comparing code, and filtering a subtree by class (lint-framework-plan F3.5).

- `same_tree(a, b)`: two nodes are the same code -- kinds, operators, names
  and literal values, all the way down -- wherever they are and however they
  are laid out. Locations, comments, annotations and what the linker records
  are not compared. Used by self-comparison, self-assignment and
  identical-select-branches.
- `descendants(node, K)`: `descendants(node)` keeping the nodes of class `K`,
  typed `list(K)`, at one step per node visited.
- `map()` and `filter()` append in place, so their cost is linear in the
  list (C8 follow-up): a comprehension used to copy its result each step.
"""
import pytest

_SRC = ("component pss_top {\n"                                          # 1
        "  action Sub { rand bit[4] x; }\n"                               # 2
        "  action A {\n"                                                  # 3
        "    rand int x;\n"                                               # 4
        "    int arr[4];\n"                                               # 5
        "    rand bit[2] i;\n"                                            # 6
        "    exec post_solve {\n"                                         # 7
        "      x = x;\n"                                                  # 8
        "      arr[i] = arr[i];\n"                                        # 9
        "      x = this.x;\n"                                             # 10
        "      x = (x);\n"                                                # 11
        "      x = 1; x = 0x1; x = 1;\n"                                  # 12
        "    }\n"                                                         # 13
        "    activity {\n"                                                # 14
        "      select {\n"                                                # 15
        "        do Sub with { x < 5; }\n"                                # 16
        "        do Sub with {\n"                                         # 17
        "          x < 5;  // the same as the first\n"                   # 18
        "        }\n"                                                     # 19
        "        do Sub with { x < 6; }\n"                                # 20
        "        (true): do Sub;\n"                                       # 21
        "        [1]: do Sub;\n"                                          # 22
        "      }\n"                                                       # 23
        "    }\n"                                                         # 24
        "  }\n"                                                           # 25
        "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("a.pss", _SRC)])
    root = p.link()
    (unit,) = p.user_units()
    return root, unit


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _ev(hooks, model, expr):
    root, unit = model
    r = hooks.cel_check_node({"expr": expr}, unit, model=root)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


_ASSIGN = "descendants(node, ProceduralStmtAssignment)"


def test_same_tree_on_assignments(hooks, model):
    assert _ev(hooks, model, _ASSIGN + ".map(s, same_tree(s.lhs, s.rhs))") == [
        True,     # x = x
        True,     # arr[i] = arr[i]
        False,    # x = this.x: spelling counts
        True,     # x = (x): the parser keeps no parentheses
        False, False, False]


def test_literals_compare_by_value_as_written(hooks, model):
    rhs = _ASSIGN + ".map(s, s.rhs)"
    assert _ev(hooks, model, "cel.bind(r, %s, [same_tree(r[4], r[6]), same_tree(r[4], r[5])])"
               % rhs) == [True, False]


def test_select_branches_ignore_layout_and_comments(hooks, model):
    got = _ev(hooks, model, "cel.bind(s, descendants(node, ActivitySelect)[0], "
                            "cel.bind(bs, branches(s), bs.map(a, bs.filter(b, "
                            "same_tree(a.node, b.node)).map(b, b.index))))")
    # The first two are the same; a guard and a weight differ from no guard.
    assert got == [[0, 1], [0, 1], [2], [3], [4]]


def test_null(hooks, model):
    assert _ev(hooks, model, "[same_tree(null, null), same_tree(node, null), "
                             "same_tree(null, node), same_tree(node, node)]") == [
        True, False, False, True]


def test_steps_per_node_compared(hooks, model):
    root, unit = model
    small = hooks.cel_check_node({"expr": "same_tree(null, null)"}, unit, model=root)
    big = hooks.cel_check_node({"expr": "same_tree(node, node)"}, unit, model=root)
    # The same node is equal at once: identity, not a walk.
    assert big["steps"]["expr"] - small["steps"]["expr"] < 5


# -------------------------------------------------------- descendants(n, K) ----

def test_descendants_of_a_class(hooks, model):
    assert _ev(hooks, model, "descendants(node, Action).map(a, a.name.id)") == ["Sub", "A"]
    # Subclasses count, as for isa().
    assert _ev(hooks, model, "size(descendants(node, ScopeChild)) == "
                             "size(descendants(node).filter(d, d.isa(ScopeChild)))") is True


def test_descendants_of_a_class_are_typed(hooks, model):
    root, unit = model
    r = hooks.cel_check_node({"expr": "descendants(node, Field)"}, unit, model=root)
    assert r["types"]["expr"] == "list(Field)"


def test_descendants_needs_a_class(hooks, model):
    root, unit = model
    r = hooks.cel_check_node({"expr": "descendants(node, int)"}, unit, model=root)
    assert r["errors"] and "needs a node class" in r["errors"][0]["message"]


def test_descendants_of_a_class_is_cheaper(hooks, model):
    root, unit = model
    a = hooks.cel_check_node({"expr": "descendants(node, ExprId)"}, unit, model=root)
    b = hooks.cel_check_node({"expr": "descendants(node).filter(d, type(d) == ExprId)"},
                             unit, model=root)
    assert a["steps"]["expr"] * 3 < b["steps"]["expr"]


# ------------------------------------------------------------ comprehensions ----

@pytest.mark.parametrize("macro", ["filter(x, x > 0)", "map(x, x)", "map(x, x > 0, x)"])
def test_map_and_filter_are_linear(hooks, macro):
    def steps(n):
        r = hooks.cel_eval("[%s].%s" % (", ".join(str(i + 1) for i in range(n)), macro))
        assert r["ok"], r
        return r["steps"]
    # Twice the elements, about twice the steps (not four times).
    assert steps(200) - steps(100) < 1.2 * (steps(100) - steps(50)) * 2


@pytest.mark.parametrize("expr,want", [
    ("[1, 2, 3].filter(x, x > 1)", [2, 3]),
    ("[1, 2, 3].map(x, x * 2)", [2, 4, 6]),
    ("[1, 2, 3].map(x, x > 1, x * 10)", [20, 30]),
    ("[[1], [2]].map(l, l.map(x, x + 1))", [[2], [3]]),
])
def test_map_and_filter_values(hooks, expr, want):
    r = hooks.cel_eval(expr)
    assert r["ok"], r
    assert _py(r["result"]) == want


@pytest.mark.parametrize("expr", [
    "[1, 2].filter(x, x / 0 > 1)",       # a predicate that errs
    "[1, 2].map(x, x / 0)",              # an element that errs
])
def test_map_and_filter_errors(hooks, expr):
    r = hooks.cel_eval(expr)
    assert r["result"]["type"] == "error", r


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    f = fns["same_tree_node_node"]
    assert (f["group"], f["level"], f["scope"], f["cost"]) == ("Comparison", "L0", "file", "custom")
    f = fns["descendants_node_type"]
    assert (f["group"], f["level"], f["scope"], f["cost"]) == ("Navigation", "L0", "file", "custom")
