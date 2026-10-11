"""List helpers (lint-core-plan.md C6.7; lint-rule-expressions.md §3).

`dups(list)`: the indexes of the elements equal (`==`) to an earlier one. A
`null` element is never a duplicate. Scalars and nodes are matched by key;
lists, maps, optionals, records and doubles pairwise, with CEL's `==`.
"""
import pytest


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


def _py(v):
    if v["type"] == "list":
        return [_py(e) for e in v["value"]]
    return v.get("value")


def _ev(hooks, expr):
    r = hooks.cel_eval(expr)
    assert r["ok"], r
    return _py(r["result"])


@pytest.mark.parametrize("expr,want", [
    ("dups([])", []),
    ("dups([1, 2, 3])", []),
    ("dups([1, 2, 1, 1, 3, 2])", [2, 3, 5]),
    ("dups(['a', 'b', 'a'])", [2]),
    ("dups([true, true, false, false])", [1, 3]),
    ("dups([1.0, 2.0, 1.0])", [2]),
    ("dups([0.0, -0.0])", [1]),                         # equal under ==
    ("dups([double('NaN'), double('NaN')])", []),       # NaN != NaN
    ("dups([[1], [2], [1], [1, 2]])", [2]),
    ("dups([{'a': 1}, {'a': 2}, {'a': 1}])", [2]),
    ("dups([optional.of(1), optional.none(), optional.of(1), optional.none()])", [2, 3]),
    ("dups([int, string, int])", [2]),
])
def test_values(hooks, expr, want):
    assert _ev(hooks, expr) == want


def test_steps_are_charged_per_element(hooks):
    base = hooks.cel_eval("dups([])")["steps"]
    assert hooks.cel_eval("dups([1, 2, 3, 4])")["steps"] - base >= 4
    # Pairwise kinds also pay for the comparisons.
    keyed = hooks.cel_eval("dups([[1], [2], [3], [4]])")["steps"]
    assert keyed - base >= 4 + (0 + 1 + 2 + 3)


def test_not_a_list_is_a_check_error(hooks):
    r = hooks.cel_check({"expr": "dups(1)"})
    assert [e["message"] for e in r["errors"]] == [
        "no matching overload for 'dups' applied to (int); it takes "
        "dups(list(A)) -> list(int)"]


_SRC = ("component pss_top {\n"
        "  action A { int a; int b; }\n"
        "  action T {\n"
        "    A h;\n"
        "    activity {\n"
        "      h { .a = 1, .b = 2, .a = 3 };\n"
        "      do A { .b = 1, .b = 2, .b = 3 };\n"
        "      h { .a = 1, .b = 2 };\n"
        "    }\n"
        "  }\n"
        "}\n")


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("a.pss", _SRC)])
    root = p.link()
    (unit,) = p.user_units()
    return root, unit


def _ev_node(hooks, model, expr):
    root, unit = model
    r = hooks.cel_check_node({"expr": expr}, unit, model=root)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def test_nodes_are_equal_when_the_same_node(hooks, model):
    # The initializers' targets resolve to the declarations: one per field.
    got = _ev_node(hooks, model, "descendants(node).filter(d, "
                   "type(d) == ActivityActionHandleTraversal || "
                   "type(d) == ActivityActionTypeTraversal).map(t, dups((t.isa("
                   "ActivityActionHandleTraversal) ? t.initializers : t.isa("
                   "ActivityActionTypeTraversal) ? t.initializers : []).map(i, "
                   "resolves_to(i.path))))")
    assert got == [[2], [1, 2], []]


def test_distinct_nodes_of_one_name_are_not_equal(hooks, model):
    # Each `.a` is its own ActionFieldInitializer node.
    got = _ev_node(hooks, model, "descendants(node).filter(d, type(d) == "
                   "ActionFieldInitializer).size()")
    assert got == 8
    assert _ev_node(hooks, model, "dups(descendants(node).filter(d, type(d) == "
                    "ActionFieldInitializer))") == []


def test_nulls_are_never_duplicates(hooks, model):
    # An unset field reads as null: no two of them pair up.
    assert _ev_node(hooks, model, "dups(descendants(node).filter(d, type(d) == "
                    "Action).map(a, a.super_t))") == []


def test_registered(hooks):
    fns = {f["id"]: f for f in hooks.cel_functions()["functions"]}
    f = fns["dups_list"]
    assert (f["group"], f["level"], f["scope"], f["cost"]) == (
        "Lists", "L0", "file", "custom"), f
