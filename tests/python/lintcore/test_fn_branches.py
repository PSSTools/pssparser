"""Branches (lint-core-plan.md C6.5; lint-framework-plan.md S6).

`branches(n)` lists the alternatives of a `select`, `match`, `if`/`else`,
`parallel` or `schedule` as `Branch` records; `ranges(n)` folds the values a
match choice (or an `in` or `dist` range) covers into `Range` records. Records
are the library's own struct types: `b.guard`, `r.lo`, `type(b) == Branch`.
"""
import pytest

_A = ("a.pss",
      "component pss_top {\n"                                                  # 1
      "  static const int K = 4;\n"                                            # 2
      "  action Sub { rand int x; }\n"                                         # 3
      "  action A {\n"                                                         # 4
      "    rand int m;\n"                                                      # 5
      "    rand int in [..5, 10] d;\n"                                         # 6
      "    activity {\n"                                                       # 7
      "      select {\n"                                                       # 8
      "        (m > 0): do Sub;\n"                                             # 9
      "        (false): do Sub;\n"                                             # 10
      "        [2 * K]: do Sub;\n"                                             # 11
      "        (true) [0]: do Sub;\n"                                          # 12
      "      }\n"                                                              # 13
      "      match (m) {\n"                                                    # 14
      "        [1, 3..5]: do Sub;\n"                                           # 15
      "        [K..K+2]: do Sub;\n"                                            # 16
      "        [m]: do Sub;\n"                                                 # 17
      "        [9..8]: do Sub;\n"                                              # 18
      "        default: do Sub;\n"                                             # 19
      "      }\n"                                                              # 20
      "      if (m == 1) { do Sub; } else if (m == 2) { do Sub; } else { do Sub; }\n"  # 21
      "      if (m == 3) do Sub;\n"                                            # 22
      "      parallel { do Sub; do Sub; }\n"                                   # 23
      "      schedule { do Sub; { do Sub; do Sub; } }\n"                       # 24
      "    }\n"                                                                # 25
      "    exec post_solve {\n"                                                # 26
      "      match (m) { [0]: m = 1; default: m = 2; }\n"                      # 27
      "      if (m == 1) { m = 2; } else if (m == 3) { m = 4; } else { m = 5; }\n"  # 28
      "    }\n"                                                                # 29
      "    constraint { m in [1..3, 7]; dist m in [0 := 1, 2..4 :/ 2]; }\n"    # 30
      "  }\n"                                                                  # 31
      "  covergroup cg(int v) {\n"                                             # 32
      "    coverpoint v { bins lo = [0..]; }\n"                                # 33
      "  }\n"                                                                  # 34
      "}\n")


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def model():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([_A])
    root = p.link()
    (a,) = p.user_units()
    return p, root, a


def _py(v):
    t, x = v["type"], v["value"]
    if t == "list":
        return [_py(e) for e in x]
    if t == "optional_type":
        return None if x is None else _py(x)
    if t == "struct":
        return {k: _py(m) for k, m in x.items() if k != "struct"}
    if t == "node":
        return x["class"]
    return x


def _ev(hooks, model, expr, linked=True):
    p, root, a = model
    r = hooks.cel_check_node({"expr": expr}, a, model=root if linked else None)
    assert r["errors"] == [], r["errors"]
    return _py(r["values"]["expr"])


def _each(kind, expr):
    return "descendants(node).filter(d, type(d) == %s).map(n, %s)" % (kind, expr)


# ------------------------------------------------------------ branches ----

def test_select(hooks, model):
    assert _ev(hooks, model, _each("ActivitySelect", "branches(n)")) == [[
        {"node": "ActivitySelectBranch", "index": i, "guard": g, "weight": w,
         "body": "ActivityActionTypeTraversal", "is_default": False}
        for i, (g, w) in enumerate([("ExprBin", None), ("ExprBool", None),
                                    (None, "ExprBin"), ("ExprBool", "ExprUnsignedNumber")])]]


def test_guards_and_weights_fold(hooks, model):
    assert _ev(hooks, model, _each("ActivitySelect",
                                   "branches(n).map(b, const_bool(b.guard))")) == [
        [None, False, None, True]]
    assert _ev(hooks, model, _each("ActivitySelect",
                                   "branches(n).map(b, const_int(b.weight))")) == [
        [None, None, 8, 0]]


def test_match(hooks, model):
    got = _ev(hooks, model, _each("ActivityMatch", "branches(n)"))
    assert [(b["node"], b["guard"], b["is_default"]) for b in got[0]] == [
        ("ActivityMatchChoice", None, False)] * 4 + [("ActivityMatchChoice", None, True)]
    got = _ev(hooks, model, _each("ProceduralStmtMatch", "branches(n)"))
    assert [(b["node"], b["body"], b["is_default"]) for b in got[0]] == [
        ("ProceduralStmtMatchChoice", "ProceduralStmtAssignment", False),
        ("ProceduralStmtMatchChoice", "ProceduralStmtAssignment", True)]


def test_activity_if_else(hooks, model):
    # `else if` is an `else` holding the inner `if`, which has its own.
    got = _ev(hooks, model, _each("ActivityIfElse",
                                  "branches(n).map(b, [type(b.node) == type(b.body), "
                                  "b.guard != null, b.is_default])"))
    assert got == [[[True, True, False], [True, False, True]],
                   [[True, True, False], [True, False, True]],
                   [[True, True, False]]]               # no `else`: one branch
    assert _ev(hooks, model, _each("ActivityIfElse", "branches(n).map(b, type(b.node))")) == [
        ["ActivitySequence", "ActivityIfElse"], ["ActivitySequence", "ActivitySequence"],
        ["ActivityActionTypeTraversal"]]


def test_procedural_if_else_is_flat(hooks, model):
    got = _ev(hooks, model, _each("ProceduralStmtIfElse", "branches(n)"))
    assert [(b["node"], b["guard"], b["is_default"]) for b in got[0]] == [
        ("ProceduralStmtIfClause", "ExprBin", False),
        ("ProceduralStmtIfClause", "ExprBin", False),
        ("ExecScope", None, True)]


def test_parallel_and_schedule(hooks, model):
    assert _ev(hooks, model, _each("ActivityParallel", "branches(n).map(b, b.node)")) == [
        ["ActivityActionTypeTraversal", "ActivityActionTypeTraversal"]]
    # A nested block is one branch.
    assert _ev(hooks, model, _each("ActivitySchedule", "branches(n).map(b, b.node)")) == [
        ["ActivityActionTypeTraversal", "ActivitySequence"]]


def test_other_nodes_and_null(hooks, model):
    assert _ev(hooks, model, "[size(branches(node)), size(branches(%s[0].super_t))]"
               % "descendants(node).filter(d, type(d) == Action)") == [0, 0]


def test_needs_no_model(hooks, model):
    assert _ev(hooks, model, _each("ActivitySelect", "size(branches(n))"),
               linked=False) == [4]


# ---------------------------------------------------------------- records ----

def test_record_type_and_equality(hooks, model):
    assert _ev(hooks, model, _each(
        "ActivitySelect",
        "[type(branches(n)[0]) == Branch, branches(n)[0] == branches(n)[0], "
        "branches(n)[0] != branches(n)[1], has(branches(n)[0].guard), "
        "has(branches(n)[2].guard)]")) == [[True, True, True, True, False]]


def test_record_member_types_are_checked(hooks, model):
    p, root, a = model
    r = hooks.cel_check_node({"expr": "branches(node).map(b, b.nope)"}, a, model=root)
    assert [e["message"] for e in r["errors"]] == ["type 'Branch' has no field 'nope'"]
    r = hooks.cel_check_node({"expr": "branches(node).map(b, b.index + 'x')"}, a, model=root)
    assert r["errors"] and "no matching overload" in r["errors"][0]["message"]


# ----------------------------------------------------------------- ranges ----

def test_match_choice_ranges(hooks, model):
    assert _ev(hooks, model, _each("ActivityMatch", "branches(n).map(b, ranges(b.node))")) == [[
        [{"lo": 1, "hi": 1}, {"lo": 3, "hi": 5}],
        [{"lo": 4, "hi": 6}],               # through a const
        None,                               # [m]: does not fold
        [{"lo": 9, "hi": 8}],               # as written
        [],                                 # default: no values
    ]]
    assert _ev(hooks, model, _each("ProceduralStmtMatch",
                                   "branches(n).map(b, ranges(b.node))")) == [
        [[{"lo": 0, "hi": 0}], []]]


def test_a_choice_cond_and_one_range(hooks, model):
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ActivityMatchChoice "
                             "&& !d.is_default).map(c, ranges(c.cond))") == [
        [{"lo": 1, "hi": 1}, {"lo": 3, "hi": 5}], [{"lo": 4, "hi": 6}], None,
        [{"lo": 9, "hi": 8}]]
    assert _ev(hooks, model, _each("ExprOpenRangeValue", "ranges(n)"))[:2] == [
        [{"lo": 1, "hi": 1}], [{"lo": 3, "hi": 5}]]


def test_in_and_dist(hooks, model):
    assert _ev(hooks, model, _each("ExprIn", "ranges(n.rhs)")) == [
        [{"lo": 1, "hi": 3}, {"lo": 7, "hi": 7}]]
    assert _ev(hooks, model, _each("DistItem", "ranges(n.range)")) == [
        [{"lo": 0, "hi": 0}], [{"lo": 2, "hi": 4}]]


def test_open_ranges_and_bins_do_not_fold(hooks, model):
    # `int in [..5, 10]`: an open range; a bin's `[0..]` reads like `[0]`.
    assert _ev(hooks, model, _each("ExprDomainOpenRangeList", "ranges(n)")) == [None]
    assert _ev(hooks, model, "descendants(node).filter(d, type(d) == ExprOpenRangeValue "
                             "&& type(parent(d)) == CoverpointBins).map(r, ranges(r))") == [None]


def test_not_a_range(hooks, model):
    assert _ev(hooks, model, "[ranges(node), ranges(%s[0].super_t)]"
               % "descendants(node).filter(d, type(d) == Action)") == [None, None]


def test_ranges_needs_a_model(hooks, model):
    p, root, a = model
    r = hooks.cel_check_node({"expr": "ranges(node)"}, a)
    v = r["values"]["expr"]
    assert v["type"] == "error" and "needs a linked model" in v["value"]


# ------------------------------------------------------------- registry ----

def test_registered(hooks):
    reg = hooks.cel_functions()
    fns = {f["id"]: f for f in reg["functions"]}
    assert (fns["branches_node"]["group"], fns["branches_node"]["level"],
            fns["branches_node"]["result"]) == ("Branches", "L0", "list(Branch)")
    assert (fns["ranges_node"]["group"], fns["ranges_node"]["level"],
            fns["ranges_node"]["result"]) == ("Branches", "L3", "optional(list(Range))")
    recs = {r["name"]: [(m["name"], m["type"]) for m in r["members"]] for r in reg["records"]}
    assert recs["Branch"] == [("node", "node"), ("index", "int"), ("guard", "Expr"),
                              ("weight", "Expr"), ("body", "ScopeChild"),
                              ("is_default", "bool")]
    assert recs["Range"] == [("lo", "int"), ("hi", "int")]


def test_levels(factory):
    from pathlib import Path
    path = Path(__file__).parents[2] / "data" / "lint-examples" / "fn-branches.yaml"
    e = factory.mkLintEngine()
    assert e.load_rules(str(path), path.read_text()) and e.rule_diagnostics() == []
    # ranges() folds (L3); branches() alone is syntax (L0).
    assert {x["id"]: (x["level"], x["scope"]) for x in e.rules()} == {
        "TEST-BR001": ("L3", "file"), "TEST-BR002": ("L3", "file"),
        "TEST-BR003": ("L0", "file")}
