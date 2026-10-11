"""
The lint engine's CEL evaluator (lint-core-plan.md C3.1).

Every value kind (null, bool, int, double, string, list, map, optional, node,
struct, type, error) and CEL's semantics over them: commutative error
absorption in `&&`/`||`/`?:`, heterogeneous numeric equality, int64 overflow
as an error, comprehensions with early exit, the step budget, optional
chaining, node identity, and D-C6 (navigating through an unset node field is
an error value).

Reached through the private hooks `cel_eval(text, max_steps, bindings)` and,
for node values, `cel_eval_node(text, root, ...)`, which binds `node`.
"""
import pytest


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


# ------------------------------------------------------------ CEL eval ----

def _val(hooks, text):
    r = hooks.cel_eval(text)
    assert r["ok"], r
    return r["result"]["type"], r["result"]["value"]


@pytest.mark.parametrize("text,expected", [
    ("false && (1/0 == 1)", ("bool", False)),
    ("(1/0 == 1) && false", ("bool", False)),
    ("true || {}['x']", ("bool", True)),
    ("{}['x'] || true", ("bool", True)),
    ("1 == 1.0", ("bool", True)),
    ("1 < 1.5", ("bool", True)),
    ("[1, 2].map(x, x * 2)", ("list", [{"type": "int", "value": 2}, {"type": "int", "value": 4}])),
    ("[1, 2, 3].exists_one(x, x > 2)", ("bool", True)),
    ("[1, 2, 3].filter(x, x > 1).size()", ("int", 2)),
    ("size('héllo')", ("int", 5)),
    ("'abc'.matches('^a.c$')", ("bool", True)),
    ("1.0 / 0.0", ("double", "Infinity")),
    ("2.0", ("double", 2.0)),
])
def test_cel_eval_values(hooks, text, expected):
    assert _val(hooks, text) == expected


@pytest.mark.parametrize("text,msg", [
    ("9223372036854775807 + 1", "overflow"),
    ("-9223372036854775807 - 2", "overflow"),
    ("1 / 0", "division by zero"),
    ("[1][1]", "out of range"),
    ("[1][-1]", "out of range"),
    ("{'a': 1/0}", "division by zero"),
    ("1 + 1.0", "no matching overload"),
    ("x", "undeclared reference"),
])
def test_cel_eval_errors(hooks, text, msg):
    t, v = _val(hooks, text)
    assert t == "error"
    assert msg in v


def test_cel_early_exit_and_budget(hooks):
    # exists() stops at the first true element: the step count does not grow
    # with the list.
    short = hooks.cel_eval("[1, 2].exists(x, x == 1)")["steps"]
    long_ = hooks.cel_eval("[1, " + ", ".join(["2"] * 200) + "].exists(x, x == 1)")["steps"]
    assert long_ - short < 450   # the literal list's elements, not the loop
    r = hooks.cel_eval("[" + ", ".join(["1"] * 100) + "].map(x, x + 1)", 50)
    assert r["budget_exceeded"]
    assert "budget" in r["result"]["value"]


# ------------------------------------------------- error absorption -------

# Each operand is one of three outcomes; `E` is an error (1/0 == 1).
_OPERANDS = {"T": "true", "F": "false", "E": "(1/0 == 1)"}
_AND = {"TT": True, "TF": False, "TE": "E", "FT": False, "FF": False, "FE": False,
        "ET": "E", "EF": False, "EE": "E"}
_OR = {"TT": True, "TF": True, "TE": True, "FT": True, "FF": False, "FE": "E",
       "ET": True, "EF": "E", "EE": "E"}


@pytest.mark.parametrize("op,table", [("&&", _AND), ("||", _OR)])
def test_cel_error_absorption_truth_table(hooks, op, table):
    for pair, want in table.items():
        text = "%s %s %s" % (_OPERANDS[pair[0]], op, _OPERANDS[pair[1]])
        t, v = _val(hooks, text)
        if want == "E":
            assert (t, "division by zero" in v) == ("error", True), text
        else:
            assert (t, v) == ("bool", want), text


@pytest.mark.parametrize("text,expected", [
    ("true ? 1 : 1/0", ("int", 1)),
    ("false ? 1/0 : 2", ("int", 2)),
    ("!(1/0 == 1) || true", ("bool", True)),
    ("[1/0 == 1, false].exists(x, x == false)", None),   # list literal: error wins
    ("[1, 2].all(x, x / 0 == 1 || x > 0)", ("bool", True)),
    ("[0, 1].exists(x, 1 / x == 1)", ("bool", True)),     # error on 0, absorbed by 1
    ("[0, 2].exists(x, 1 / x == 1)", ("error", "division by zero")),
    ("[0, 1].all(x, 1 / x == 5)", ("bool", False)),
])
def test_cel_error_absorption_elsewhere(hooks, text, expected):
    t, v = _val(hooks, text)
    if expected is None:
        assert t == "error"
    elif expected[0] == "error":
        assert t == "error" and expected[1] in v
    else:
        assert (t, v) == expected


def test_cel_conditional_error_condition(hooks):
    t, v = _val(hooks, "(1/0 == 1) ? 1 : 2")
    assert t == "error" and "division by zero" in v
    t, v = _val(hooks, "1 ? 1 : 2")
    assert t == "error" and "no matching overload" in v


# --------------------------------------------------------- overflow -------

@pytest.mark.parametrize("text", [
    "9223372036854775807 + 1", "-9223372036854775808 - 1", "-(-9223372036854775808)",
    "4611686018427387904 * 2", "-9223372036854775808 * -1", "-9223372036854775808 / -1",
    "-9223372036854775808 % -1", "int(9.3e18)", "int(-9.3e18)",
])
def test_cel_overflow(hooks, text):
    t, v = _val(hooks, text)
    assert t == "error" and ("overflow" in v or "out of range" in v), text


@pytest.mark.parametrize("text,expected", [
    ("9223372036854775807 + 0", 9223372036854775807),
    ("-9223372036854775807 - 1", -9223372036854775808),
    ("4611686018427387903 * 2", 9223372036854775806),
    ("-9223372036854775808 / 1", -9223372036854775808),
    ("-7 / 2", -3), ("-7 % 2", -1),
])
def test_cel_no_overflow_at_the_edge(hooks, text, expected):
    assert _val(hooks, text) == ("int", expected)


# ------------------------------------------- heterogeneous equality -------

@pytest.mark.parametrize("text,expected", [
    ("1 == 1.0", True), ("1 != 1.0", False), ("1 == 1.5", False), ("2 > 1.5", True),
    ("1 in [1.0, 2.0]", True), ("1.0 in [1, 2]", True), ("2.5 in [2]", False),
    ("{1: 'a'}[1.0] == 'a'", True), ("1.0 in {1: 'a'}", True),
    ("[1, 2] == [1.0, 2.0]", True), ("{'a': 1} == {'a': 1.0}", True),
    # The int converts to double, lossily, as cel-spec's conformance tests
    # require: 2^63 - 1 rounds to 2^63.
    ("9223372036854775807 == 9223372036854775808.0", True),
    ("9223372036854775807 < 9223372036854775808.0", False),
    ("9007199254740993 == 9007199254740992.0", True),
    ("0.0 / 0.0 == 0.0 / 0.0", False), ("1 < 0.0 / 0.0", False), ("1 > 0.0 / 0.0", False),
    ("1 == 'a'", False), ("null == 0", False), ("[1] == ['1']", False),
    ("-0.0 == 0", True),
])
def test_cel_numeric_equality(hooks, text, expected):
    assert _val(hooks, text) == ("bool", expected), text


# --------------------------------------------- early exit and budget ------

def test_cel_all_stops_at_first_false(hooks):
    short = hooks.cel_eval("[0, 1].all(x, x == 1)")["steps"]
    long_ = hooks.cel_eval("[0, " + ", ".join(["1"] * 200) + "].all(x, x == 1)")["steps"]
    # The literal costs one step per element; the loop does not run past [0].
    assert long_ - short <= 201


def test_cel_budget_reported_once_exceeded(hooks):
    r = hooks.cel_eval("[1, 2, 3].map(x, [1, 2, 3].map(y, x * y))", 20)
    assert r["budget_exceeded"] and r["result"]["type"] == "error"
    assert "20 steps" in r["result"]["value"]
    r = hooks.cel_eval("[1, 2, 3].map(x, [1, 2, 3].map(y, x * y))", 1000)
    assert not r["budget_exceeded"] and r["result"]["type"] == "list"
    assert r["steps"] <= 1000


def test_cel_budget_absorbed_by_nothing(hooks):
    # The budget is not a CEL error: `||` cannot absorb it.
    r = hooks.cel_eval("true || [1, 2, 3].map(x, x).size() > 0", 3)
    assert not r["budget_exceeded"]   # short-circuits before the loop
    r = hooks.cel_eval("[1, 2, 3].map(x, x).size() > 0 || true", 3)
    assert r["budget_exceeded"] and r["result"]["type"] == "error"


# -------------------------------------------------------- bindings --------

def test_cel_bindings(hooks):
    r = hooks.cel_eval("x + y.size() + m.k[1]", bindings={"x": 1, "y": "ab", "m": {"k": [5, 6]}})
    assert r["result"] == {"type": "int", "value": 9}
    # A variable shadows a type name.
    assert hooks.cel_eval("int + 1", bindings={"int": 2})["result"]["value"] == 3
    assert hooks.cel_eval("[1].map(x, x + x)", bindings={"x": 10})["result"]["value"] == \
        [{"type": "int", "value": 2}]


# ----------------------------------------------------------- types --------

@pytest.mark.parametrize("text,expected", [
    ("type(1) == int", ("bool", True)), ("type(1.0) == double", ("bool", True)),
    ("type('') == string", ("bool", True)), ("type(true) == bool", ("bool", True)),
    ("type(null) == null_type", ("bool", True)), ("type([]) == list", ("bool", True)),
    ("type({}) == map", ("bool", True)), ("type(int) == type", ("bool", True)),
    ("type(type)", ("type", "type")), ("type(optional.none()) == optional_type", ("bool", True)),
    ("type(1) == double", ("bool", False)), ("int == int", ("bool", True)),
    ("ExprBin", ("type", "ExprBin")), ("Location", ("type", "Location")),
    ("ExprBinOp.BinOp_LogOr", ("int", 0)), ("ExprBinOp.BinOp_Eq", ("int", 17)),
    ("FieldAttr.Action", ("int", 1)), ("FieldAttr.Rand", ("int", 4)),
])
def test_cel_types_and_enum_constants(hooks, text, expected):
    assert _val(hooks, text) == expected


@pytest.mark.parametrize("text,msg", [
    ("ExprBinOp.Nope", "type 'ExprBinOp' has no member 'Nope'"),
    ("ExprBin.lhs", "type 'ExprBin' has no member 'lhs'"),
    ("NoSuchClass", "undeclared reference to 'NoSuchClass'"),
    ("int < int", "no matching overload"),
])
def test_cel_type_errors(hooks, text, msg):
    t, v = _val(hooks, text)
    assert t == "error" and msg in v


def test_cel_type_names_do_not_collide(hooks):
    # Class, struct and enum names share one namespace in expressions.
    s = hooks.reflect_schema()
    classes = {c["name"] for c in s["classes"] if c}
    enums = {e["name"] for e in s["enums"]}
    structs = {x["name"] for x in s["structs"]}
    builtin = {"bool", "int", "double", "string", "list", "map", "null_type", "type",
               "optional_type"}
    assert not (classes & enums) and not (classes & structs) and not (enums & structs)
    assert not ((classes | enums | structs) & builtin)


# ------------------------------------------------------- optionals --------

@pytest.mark.parametrize("text,expected", [
    ("optional.of(1).hasValue()", ("bool", True)),
    ("optional.none().hasValue()", ("bool", False)),
    ("optional.of(null).hasValue()", ("bool", True)),
    ("optional.ofNonZeroValue(0).hasValue()", ("bool", False)),
    ("optional.ofNonZeroValue('').hasValue()", ("bool", False)),
    ("optional.ofNonZeroValue([1]).hasValue()", ("bool", True)),
    ("optional.of(1).value()", ("int", 1)),
    ("optional.none().orValue(2)", ("int", 2)),
    ("optional.of(1).orValue(1/0)", ("int", 1)),          # argument not evaluated
    ("optional.none().or(optional.of(3)).value()", ("int", 3)),
    ("optional.of(1).or(optional.of(1/0)).value()", ("int", 1)),
    ("{'a': 1}.?a.value()", ("int", 1)),
    ("{'a': 1}.?b.hasValue()", ("bool", False)),
    ("{}.?a.b.c.hasValue()", ("bool", False)),            # none chains
    ("optional.of({'a': {'b': 2}}).a.b.value()", ("int", 2)),
    ("optional.of({'a': {}}).a.b.hasValue()", ("bool", False)),
    ("[1, 2][?1].value()", ("int", 2)),
    ("[1, 2][?2].hasValue()", ("bool", False)),
    ("[1, 2][?-1].hasValue()", ("bool", False)),
    ("{'k': 1}[?'k'].value()", ("int", 1)),
    ("optional.of([1])[0].value()", ("int", 1)),
    ("optional.of([1])[5].hasValue()", ("bool", False)),
    ("optional.none()[0].hasValue()", ("bool", False)),
    ("has({'a': optional.none()}.a)", ("bool", True)),
    ("has({'a': optional.none()}.a.b)", ("bool", False)),
    ("has({}.?a.b)", ("bool", False)),
    ("has({'a': {'b': 1}}.?a.b)", ("bool", True)),
    ("optional.none() == optional.none()", ("bool", True)),
    ("optional.of(1) == optional.of(1.0)", ("bool", True)),
    ("optional.of(1) == optional.none()", ("bool", False)),
    ("[?optional.none(), ?optional.of(1), 2]",
     ("list", [{"type": "int", "value": 1}, {"type": "int", "value": 2}])),
    ("{?'a': optional.none(), ?'b': optional.of(1)}.size()", ("int", 1)),
    ("{?'a': optional.of(1)}.a", ("int", 1)),
])
def test_cel_optionals(hooks, text, expected):
    assert _val(hooks, text) == expected, text


@pytest.mark.parametrize("text,msg", [
    ("optional.none().value()", "optional.none() dereference"),
    ("{'a': null}.?a.b", "no such key"),
    ("[?1]", "optional list element needs an optional value"),
    ("{?'a': 1}", "optional map entry needs an optional value"),
    ("optional.of(1, 2)", "optional.of"),
    ("optional.none().or(1)", "no matching overload"),
    ("optional.of(1/0)", "division by zero"),
])
def test_cel_optional_errors(hooks, text, msg):
    t, v = _val(hooks, text)
    assert t == "error" and msg in v, (text, v)


def test_cel_optional_namespace_can_be_shadowed(hooks):
    r = hooks.cel_eval("optional.of", bindings={"optional": {"of": 5}})
    assert r["result"] == {"type": "int", "value": 5}


# ----------------------------------------------------------- nodes --------

_MODEL = (
    "component pss_top {\n"
    "  action A {\n"
    "    rand int a;\n"
    "    constraint c { a > 0; }\n"
    "  }\n"
    "  action B : A { }\n"
    "}\n")

# Bound with cel.bind so the expressions below stay readable.
_PRELUDE = (
    "cel.bind(top, node.children.filter(c, type(c) == Component)[0],"
    " cel.bind(A, top.children.filter(c, type(c) == Action && c.name.id == 'A')[0],"
    " cel.bind(B, top.children.filter(c, type(c) == Action && c.name.id == 'B')[0],"
    " cel.bind(fa, A.children.filter(c, type(c) == Field)[0],"
    " cel.bind(ex, A.children.filter(c, type(c) == ConstraintBlock)[0].constraints"
    ".filter(s, type(s) == ConstraintStmtExpr).map(s, s.expr)"
    ".filter(e, type(e) == ExprBin)[0],"
    " %s)))))")


@pytest.fixture(scope="module")
def unit():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", _MODEL)])
    # The user's unit is the last; the standard library's come first.
    return p, p._files[-1]


def _node(hooks, unit, text, max_steps=0):
    r = hooks.cel_eval_node(_PRELUDE % text, unit[1], max_steps)
    assert r["ok"], r
    return r["result"]["type"], r["result"]["value"]


@pytest.mark.parametrize("text,expected", [
    ("type(node)", ("type", "GlobalScope")),
    ("type(A) == Action", ("bool", True)),
    ("A.name.id", ("string", "A")),
    ("A.location.lineno", ("int", 2)),                  # inherited (ScopeChild)
    ("A.location.linepos", ("int", 3)),
    ("type(A.location)", ("type", "Location")),
    ("A.location == A.location", ("bool", True)),
    ("A.location == B.location", ("bool", False)),
    ("fa.name.id", ("string", "a")),
    ("fa.attr == FieldAttr.Rand", ("bool", True)),
    ("type(ex) == ExprBin", ("bool", True)),
    ("ex.op == ExprBinOp.BinOp_Gt", ("bool", True)),
    ("type(ex.lhs) == ExprRefPathContext && type(ex.rhs) == ExprUnsignedNumber",
     ("bool", True)),
    ("A.children.size()", ("int", 2)),     # not the implicit `comp`
    ("A.children.exists(c, type(c) == ConstraintBlock)", ("bool", True)),
    ("A.is_abstract", ("bool", False)),
    ("A == A", ("bool", True)),                         # identity
    ("A == B", ("bool", False)),
    ("A in top.children", ("bool", True)),
    ("A in B.children", ("bool", False)),
    ("A != null", ("bool", True)),
    ("type(B.super_t) == TypeIdentifier", ("bool", True)),
])
def test_cel_node_values(hooks, unit, text, expected):
    assert _node(hooks, unit, text) == expected, text


@pytest.mark.parametrize("text,expected", [
    # proto3 presence: set node, non-empty list, non-zero scalar.
    ("has(B.super_t)", True), ("has(A.super_t)", False),
    ("has(A.children)", True), ("has(A.annotations)", False), ("has(fa.init)", False),
    ("has(A.name)", True), ("has(A.is_abstract)", False),
    ("has(fa.attr)", True), ("has(A.location)", True),
    ("has(A.location.lineno)", True),
    ("has(ex.op)", True),                                # BinOp_Gt != 0
])
def test_cel_node_has(hooks, unit, text, expected):
    assert _node(hooks, unit, text) == ("bool", expected), text


def test_cel_unset_field_d_c6(hooks, unit):
    # An unset node field reads as null ...
    assert _node(hooks, unit, "A.super_t") == ("null_type", None)
    assert _node(hooks, unit, "A.super_t == null") == ("bool", True)
    # ... and navigating through it is an error value naming both fields.
    t, v = _node(hooks, unit, "A.super_t.target")
    assert (t, v) == ("error", "field 'target' of unset 'super_t'")
    t, v = _node(hooks, unit, "has(A.super_t.target)")
    assert (t, v) == ("error", "field 'target' of unset 'super_t'")
    # && and || absorb it, as CEL absorbs any error ...
    assert _node(hooks, unit, "has(A.super_t) && A.super_t.target == null") == ("bool", False)
    assert _node(hooks, unit, "A.super_t.target == null && false") == ("bool", False)
    assert _node(hooks, unit, "!has(A.super_t) || A.super_t.target == null") == ("bool", True)
    # ... and `.?` turns it into none.
    assert _node(hooks, unit, "A.?super_t.hasValue()") == ("bool", False)
    assert _node(hooks, unit, "A.?super_t.target.hasValue()") == ("bool", False)
    assert _node(hooks, unit, "B.?super_t.hasValue()") == ("bool", True)
    assert _node(hooks, unit, "type(B.?super_t.value()) == TypeIdentifier") == ("bool", True)


@pytest.mark.parametrize("text,msg", [
    ("A.nope", "type 'Action' has no field 'nope'"),
    ("has(A.nope)", "type 'Action' has no field 'nope'"),
    ("A.?nope", "type 'Action' has no field 'nope'"),
    ("A.location.nope", "type 'Location' has no field 'nope'"),
    ("A + 1", "no matching overload for '_+_' applied to (Action, int)"),
    ("A < B", "no matching overload"),
    ("A[0]", "no matching overload"),
])
def test_cel_node_errors(hooks, unit, text, msg):
    t, v = _node(hooks, unit, text)
    assert t == "error" and msg in v, (text, v)


def test_cel_node_list_reads_charge_steps(hooks, unit):
    # Reading a list field costs a step per element, so a rule cannot walk a
    # big list for free.
    base = _node_steps(hooks, unit, "A")
    one = _node_steps(hooks, unit, "A.children.size()")
    two = _node_steps(hooks, unit, "A.children.size() + A.children.size()")
    assert two - one >= 3 + 2 and one - base >= 3


def _node_steps(hooks, unit, text):
    return hooks.cel_eval_node(_PRELUDE % text, unit[1])["steps"]


def test_cel_node_linked_root(hooks, unit):
    p, _ = unit
    root = p.link()
    # Its `children` are the linker's borrowed view of the files, which
    # reads as empty (CelNode.h); `units` are its own.
    r = hooks.cel_eval_node("node.units.size() > 0 && type(node) == RootSymbolScope", root)
    assert r["result"] == {"type": "bool", "value": True}
