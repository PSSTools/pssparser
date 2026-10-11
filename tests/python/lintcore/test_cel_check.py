"""
The lint engine's CEL type checker (lint-core-plan.md C3.3).

Through the `cel_check` hook, which takes a small rule-shaped document
(`vars`, `bindings`, `define`, `let`, `expr`/`where`/`report`), checks it,
locates every error in the YAML text, and runs the checked expressions when
there are none.

Covered: the type of each kind of expression; unknown names, functions,
fields and enum members; wrong argument and result types; no `dyn`; the
excluded parts of CEL that only the checker can see; `1 == 1.0`; node
classes (common base, derived-class fields, narrowing after `type(x) == K`);
the comprehension nesting limit, per helper body; `define:` helpers (inlining,
hygiene, cycles with their path, misuse); shadowing; errors located in every
YAML scalar style; and that the checked expression evaluates exactly as the
unchecked one does (the standard library's cases and the node cases of
test_cel_eval.py; the CEL conformance files are test_cel_conformance.py's).
"""

import pytest

import test_cel_eval
import test_cel_stdlib


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


def _check(hooks, doc, name="check.yaml"):
    r = hooks.cel_check(doc, name)
    assert r["ok"], r
    return r


def _type(hooks, text, **doc):
    r = _check(hooks, dict(doc, expr=text, run=False))
    assert r["errors"] == [], (text, r["errors"])
    return r["types"]["expr"]


def _error(hooks, text, **doc):
    """The one error of `text`: (offset, message)."""
    r = _check(hooks, dict(doc, expr=text))
    assert len(r["errors"]) == 1, (text, r["errors"])
    e = r["errors"][0]
    return e["offset"], e["message"]


def _value(hooks, text, **doc):
    r = _check(hooks, dict(doc, expr=text))
    assert r["errors"] == [], (text, r["errors"])
    return r["values"]["expr"]


# ------------------------------------------------------------- types ------

@pytest.mark.parametrize("text,typ", [
    ("null", "null_type"), ("true", "bool"), ("1", "int"), ("1.5", "double"), ("'a'", "string"),
    ("[1, 2]", "list(int)"), ("[]", "list(?)"), ("[[1], []]", "list(list(int))"),
    ("{'a': 1}", "map(string, int)"), ("{}", "map(?, ?)"), ("{1: [true]}", "map(int, list(bool))"),
    ("1 + 2 * 3", "int"), ("1.0 / 2.0", "double"), ("'a' + 'b'", "string"),
    ("[1] + []", "list(int)"), ("[] + [1.5]", "list(double)"),
    ("1 < 2.0", "bool"), ("!true", "bool"), ("-1", "int"),
    ("true ? 1 : 2", "int"), ("[1, 2][0]", "int"), ("{'a': [1]}['a']", "list(int)"),
    ("{'a': 1}.a", "int"), ("'abc'.size()", "int"), ("size([1])", "int"),
    ("'a'.matches('b')", "bool"), ("int('1')", "int"), ("string(1.5)", "string"),
    ("type(1)", "type"), ("int", "type"), ("type(1) == int", "bool"),
    ("[1, 2].map(x, x * 2 > 1)", "list(bool)"), ("[1, 2].filter(x, x > 1)", "list(int)"),
    ("[1].all(x, x > 0)", "bool"), ("[1].exists_one(x, x > 0)", "bool"),
    ("{'a': 1}.exists(k, k == 'a')", "bool"), ("{'a': 1}.map(k, k + '!')", "list(string)"),
    ("[1, 2].map(x, x > 1, x * 10)", "list(int)"),
    ("cel.bind(x, 'a', x + x)", "string"), ("cel.bind(x, [1], x[0])", "int"),
    ("optional.of(1)", "optional(int)"), ("optional.none()", "optional(?)"),
    ("optional.of(1).value()", "int"), ("optional.none().orValue(2)", "int"),
    ("optional.of('a').or(optional.none())", "optional(string)"),
    ("{'a': 1}.?a", "optional(int)"), ("{'a': {'b': 1}}.?a.b", "optional(int)"),
    ("[1][?0]", "optional(int)"), ("[?optional.of(1), 2]", "list(int)"),
    ("{?'a': optional.of(1)}", "map(string, int)"),
    ("optional.of(1).optMap(x, x + 1)", "optional(int)"),
    ("optional.of(1).optFlatMap(x, optional.of('s'))", "optional(string)"),
    ("has({'a': 1}.a)", "bool"),
    ("ExprBinOp.BinOp_Eq", "int"), ("ExprBinOp.BinOp_Eq + 1", "int"),
    ("ExprBin", "type"), ("Location", "type"),
])
def test_types(hooks, text, typ):
    assert _type(hooks, text) == typ


@pytest.mark.parametrize("decl,typ", [
    ("int", "int"), ("list(string)", "list(string)"), ("map(string, list(int))",
     "map(string, list(int))"), ("ExprBin", "ExprBin"), ("list(Action)", "list(Action)"),
    ("Location", "Location"), ("node", "node"), ("optional(double)", "optional(double)"),
])
def test_declared_variables(hooks, decl, typ):
    assert _type(hooks, "x", vars={"x": decl}) == typ


def test_declared_variable_bad_type(hooks):
    r = hooks.cel_check({"vars": {"x": "Nonesuch"}, "expr": "x"})
    assert not r["ok"] and "unknown type 'Nonesuch'" in r["error"]["message"]


def test_binding_types_come_from_values(hooks):
    doc = {"bindings": {"n": 3, "l": [1, 2], "m": {"k": "v"}}}
    assert _type(hooks, "n + l[0]", **doc) == "int"
    assert _type(hooks, "m.k", **doc) == "string"
    assert _value(hooks, "l.map(x, x + n)", **doc)["value"] == [
        {"type": "int", "value": 4}, {"type": "int", "value": 5}]


# --------------------------------------------- unknown names, bad calls ----

@pytest.mark.parametrize("text,offset,msg", [
    ("x + 1", 0, "undeclared reference to 'x'"),
    ("1 + f(2)", 4, "undeclared reference to function 'f'"),
    ("timestamp(0)", 0, "undeclared reference to function 'timestamp'"),
    ("'a'.nope()", 0, "undeclared reference to function 'nope'"),
    ("ExprBinOp.Nope", 0, "enum 'ExprBinOp' has no member 'Nope'"),
    # A flags value is not a number (C6.8, E4).
    ("FieldAttr.Rand + 1", 0, "FieldAttr.Rand is a 'FieldAttr' flag, not a number: test a "
     "flag with has_flag(x, FieldAttr.Rand)"),
    ("int(FieldAttr.Rand)", 4, "FieldAttr.Rand is a 'FieldAttr' flag, not a number"),
    ("has_flag(4, ExprBinOp.BinOp_Eq)", 12, "ExprBinOp.BinOp_Eq is a member of enum "
     "'ExprBinOp', which is not a set of flags"),
    ("int.x", 0, "type 'int' has no member 'x'"),
    ("1 + 'a'", 0, "no matching overload for '+' applied to (int, string); it takes "
     "int + int -> int, double + double -> double, string + string -> string or "
     "list(A) + list(A) -> list(A)"),
    ("'a'.contains(1)", 0, "no matching overload for 'contains' applied to (string, int) "
     "(the first is the receiver); it takes string.contains(string) -> bool"),
    ("contains('a', 'b')", 0, "no matching overload for 'contains' applied to (string, string)"),
    ("[1] + ['a']", 0, "no matching overload for '+' applied to (list(int), list(string))"),
    ("!1", 0, "no matching overload for '!' applied to (int); it takes !bool -> bool"),
    ("1 in ['a']", 0, "no matching overload for 'in' applied to (int, list(string))"),
    ("[1]['a']", 0, "no matching overload for '[]' applied to (list(int), string)"),
    ("size(1)", 0, "no matching overload for 'size' applied to (int)"),
    ("1.x", 2, "a value of type 'int' has no field 'x'"),
    ("{1: 2}.x", 7, "cannot select 'x' from a map with 'int' keys; index it instead"),
    ("null.x", 5, "cannot select 'x' from null"),
    ("[][0].x", 6, "cannot select 'x' from a value whose type is not known"),
    ("[1].map(x, x).all(y, 1)", 21, "the condition of all() must be bool, not 'int'"),
    ("[1].exists(x, 'a')", 14, "the condition of exists() must be bool, not 'string'"),
    ("[1].exists_one(x, 2)", 18, "the condition of exists_one() must be bool, not 'int'"),
    ("[1].filter(x, x)", 14, "the condition of filter() must be bool, not 'int'"),
    ("[1].map(x, x, x)", 11, "the condition of map() must be bool, not 'int'"),
    ("1.all(x, true)", 0, "all() needs a list or a map, not 'int'"),
    ("1 && true", 0, "an operand of '&&' must be bool, not 'int'"),
    ("true || 'a'", 8, "an operand of '||' must be bool, not 'string'"),
    ("1 ? 2 : 3", 0, "the condition of '?:' must be bool, not 'int'"),
    ("true ? 1 : 'a'", 11, "the two results of '?:' must have one type, but they are "
     "'int' and 'string'"),
    ("optional.of(1).or(optional.of('a'))", 0,
     "no matching overload for 'or' applied to (optional(int), optional(string))"),
    ("optional.of(1).orValue('a')", 0,
     "no matching overload for 'orValue' applied to (optional(int), string)"),
    ("[?1]", 2, "an optional element '?e' needs an optional, not 'int'"),
    ("{?'a': 1}", 7, "an optional entry '?k: v' needs an optional value, not 'int'"),
])
def test_errors(hooks, text, offset, msg):
    off, m = _error(hooks, text)
    assert msg in m, (text, m)
    assert off == offset, (text, off, m)


def test_one_error_is_reported_once(hooks):
    # An expression already wrong does not make everything above it wrong too.
    r = _check(hooks, {"expr": "size([x].map(y, y + 1)) + 1 == 2 && true"})
    assert [e["message"] for e in r["errors"]] == ["undeclared reference to 'x'"]


def test_several_independent_errors(hooks):
    r = _check(hooks, {"expr": "x + 1 == y"})
    assert [e["message"] for e in r["errors"]] == [
        "undeclared reference to 'x'", "undeclared reference to 'y'"]


def test_errors_mean_no_values(hooks):
    r = _check(hooks, {"expr": "1 + 'a'"})
    assert "values" not in r


@pytest.mark.parametrize("text,offset,msg", [
    # A literal pattern is compiled when checked (C1.4: refused syntax is a
    # rule error, not a run-time one).
    ("'a'.matches('(?=x)')", 12, "invalid regular expression: "),
    ("matches('a', 'x\\\\1')", 13, "invalid regular expression: "),
    ("'a'.matches('[')", 12, "invalid regular expression: "),
])
def test_literal_regex_checked(hooks, text, offset, msg):
    off, m = _error(hooks, text)
    assert off == offset and m.startswith(msg) and " of the pattern)" in m, (text, m)


def test_regex_checked_and_unchecked(hooks):
    # The compiled literal gives the same answers and charges the same steps.
    for text in ["'abcabc'.matches('b(c|d)a')", "matches('xyz', '^x.z$')", "'a'.matches('b')"]:
        r = _check(hooks, {"expr": text})
        u = hooks.cel_eval(text)
        assert (r["values"]["expr"], r["steps"]["expr"]) == (u["result"], u["steps"]), text
    # A pattern that is not a literal is compiled when it runs.
    r = _check(hooks, {"bindings": {"p": "("}, "expr": "'a'.matches(p)"})
    assert r["values"]["expr"]["type"] == "error"
    assert r["values"]["expr"]["value"].startswith("invalid regular expression: ")


# ---------------------------------------------------------- no dyn ------

@pytest.mark.parametrize("text,msg", [
    ("[1, 'a']", "list elements must all have one type, but this one is 'string' and the "
     "ones before are 'int' (pss-rules has no dyn)"),
    ("[1, 2.0]", "list elements must all have one type, but this one is 'double'"),
    ("[[1], ['a']]", "this one is 'list(string)' and the ones before are 'list(int)'"),
    ("{'a': 1, 'b': 'c'}", "map values must all have one type, but this one is 'string'"),
    ("{'a': 1, 2: 3}", "map keys must all have one type, but this one is 'int'"),
    ("{1.5: 1}", "a map key must be an int, a string or a bool, not 'double'"),
    ("dyn(1)", "'dyn(A) -> A' is not supported in pss-rules"),
    ("dyn", "type 'dyn' is not supported in pss-rules"),
    ("[1, 2][1.0]", "'list(A)[double] -> A' is not supported in pss-rules"),
])
def test_no_dyn(hooks, text, msg):
    _, m = _error(hooks, text)
    assert msg in m, (text, m)


@pytest.mark.parametrize("text,msg", [
    # The parser's profile check catches the syntax; these are names, which
    # only the checker can judge.
    ("uint", "type 'uint' is not supported in pss-rules"),
    ("bytes", "type 'bytes' is not supported in pss-rules"),
    ("uint(1)", "undeclared reference to function 'uint'"),
    ("duration('1s')", "undeclared reference to function 'duration'"),
    # ... and the parser's, reported the same way.
    ("1u", "unsigned integer literals are not supported in pss-rules; use an int"),
    ("b'x'", "bytes literals are not supported in pss-rules"),
    ("M{a: 1}", "message construction ('M{...}') is not supported in pss-rules"),
])
def test_excluded_features(hooks, text, msg):
    _, m = _error(hooks, text)
    assert m == msg


# --------------------------------------------------- equality, numbers ----

@pytest.mark.parametrize("text,value", [
    ("1 == 1.0", True), ("1.0 == 1", True), ("1 != 1.5", True), ("2 != 2.0", False),
    ("1 in [1.0, 2.0]", True), ("2.0 in [1, 2]", True), ("1.0 in {1: 'a'}", True),
    ("3.0 in {1: 'a'}", False),
])
def test_equality_across_int_and_double(hooks, text, value):
    assert _value(hooks, text) == {"type": "bool", "value": value}


@pytest.mark.parametrize("text", [
    "1 + 1.0", "[1] == [1.0]", "optional.of(1) == optional.of(1.0)", "1 == 'a'", "1 == true",
])
def test_no_other_mixing(hooks, text):
    _, m = _error(hooks, text)
    assert m.startswith("no matching overload"), (text, m)


def test_null_fits_node_types(hooks):
    doc = {"vars": {"n": "ExprBin"}, "run": False}
    assert _type(hooks, "n.lhs == null", **doc) == "bool"
    assert _type(hooks, "[null, n.lhs]", **doc) == "list(Expr)"
    assert _type(hooks, "true ? null : n", **doc) == "ExprBin"
    _, m = _error(hooks, "1 == null")
    assert m.startswith("no matching overload for '==' applied to (int, null_type)")


# ---------------------------------------------------------- nodes ------

NODE = {"vars": {"node": "ExprBin", "a": "Action"}, "run": False}


@pytest.mark.parametrize("text,typ", [
    ("node", "ExprBin"),
    ("node.lhs", "Expr"),
    ("node.op", "int"),
    ("a.location", "Location"),                     # inherited, a struct
    ("a.location.lineno", "int"),
    ("node.op == ExprBinOp.BinOp_Eq", "bool"),
    ("[node.lhs, node.rhs]", "list(Expr)"),
    ("[node.lhs, node]", "list(Expr)"),             # the common base class
    ("[a, a.location]", None),
    ("true ? node : node.lhs", "Expr"),
    ("node == node.lhs", "bool"),
    ("node in [node.lhs]", "bool"),
    ("has(node.lhs)", "bool"),
    ("node.?lhs", "optional(Expr)"),
    ("type(node.lhs) == ExprBin && node.lhs.op == 0", "bool"),
    ("type(node) == ExprBin", "bool"),
    ("[node].map(n, n.lhs)", "list(Expr)"),
])
def test_node_types(hooks, text, typ):
    if typ is None:
        _, m = _error(hooks, text, **NODE)
        assert m.startswith("list elements must all have one type")
    else:
        assert _type(hooks, text, **NODE) == typ


@pytest.mark.parametrize("text,msg", [
    ("node.nope", "type 'ExprBin' has no field 'nope', nor does any class derived from it"),
    # A derived class's field needs the class tested first.
    ("node.lhs.op", "type 'Expr' has no field 'op'; ExprBin and ExprUnary have it: test the "
                    "class first, as in type(node.lhs) == ExprBin && node.lhs.op"),
    ("node.?lhs.op", "type 'Expr' has no field 'op'; ExprBin and ExprUnary have it"),
    ("has(node.lhs.op)", "type 'Expr' has no field 'op'; ExprBin and ExprUnary have it"),
    ("node.lhs.?op", "type 'Expr' has no field 'op'; ExprBin and ExprUnary have it"),
    ("a.location.nope", "type 'Location' has no field 'nope'"),
    ("has(node.nope)", "type 'ExprBin' has no field 'nope'"),
    ("node.?nope", "type 'ExprBin' has no field 'nope'"),
    ("node + 1", "no matching overload for '+' applied to (ExprBin, int)"),
    ("node < node", "no matching overload for '<' applied to (ExprBin, ExprBin)"),
    ("node == 1", "no matching overload for '==' applied to (ExprBin, int)"),
    ("a == a.location", "no matching overload for '==' applied to (Action, Location)"),
])
def test_node_errors(hooks, text, msg):
    _, m = _error(hooks, text, **NODE)
    assert msg in m, (text, m)


def test_any_node_has_no_fields(hooks):
    doc = {"vars": {"n": "node"}, "run": False}
    _, m = _error(hooks, "n.lhs", **doc)
    assert m.startswith("type 'node' has no field 'lhs'; ExprAggrMapElem, ExprBin, ")
    assert " and 6 more have it: test the class first, as in type(n) == ExprAggrMapElem && " \
           "n.lhs" in m
    assert _type(hooks, "type(n) == ExprBin && n.lhs == null", **doc) == "bool"
    _, m = _error(hooks, "n.nope", **doc)
    assert m == "type 'node' has no field 'nope', nor does any node class"


def test_derived_field_is_an_error(hooks):
    # A field only some derived classes have would be an error value on the
    # others at run time; the checker asks for the class test instead, and
    # names the classes that have it (topmost only: not each class that
    # inherits it). lint-core-plan.md C3.3, decision (a), revised.
    _, m = _error(hooks, "c.name", vars={"c": "ScopeChild"})
    assert m.startswith("type 'ScopeChild' has no field 'name'; ")
    assert "NamedScopeChild" in m and "Action" not in m
    assert m.endswith(" have it: test the class first, as in type(c) == %s && c.name"
                      % m.split("; ")[1].split(",")[0])
    _, m = _error(hooks, "c.children[0].name", vars={"c": "Action"})
    assert "as in type(x) == " in m and m.endswith(" && x.name")


@pytest.mark.parametrize("text,typ", [
    # On the right of `&&`, and in the first result of `?:`, a variable (or a
    # field path from one) that the left tested is of the tested class.
    ("type(c) == Action && c.name.id == 'A'", "bool"),
    ("Action == type(c) && c.is_abstract", "bool"),
    ("type(c) == Action ? c.name : null", "ExprId"),
    ("type(c) == Action && (true && c.is_abstract)", "bool"),
    ("type(n.lhs) == ExprBin && n.lhs.lhs != null", "bool"),
    ("l.filter(c, type(c) == Action)", "list(Action)"),
    ("l.filter(c, type(c) == Action && c.is_abstract)", "list(Action)"),
    ("l.filter(c, type(c) == Action)[0].super_t", "TypeIdentifier"),
])
def test_narrowing(hooks, text, typ):
    doc = {"vars": {"c": "ScopeChild", "n": "ExprBin", "l": "list(ScopeChild)"}, "run": False}
    assert _type(hooks, text, **doc) == typ


@pytest.mark.parametrize("text", [
    # `name` differs between ScopeChild classes, so it needs the narrowing.
    "type(c) == Action || c.name.id == ''",                     # not after ||
    "(type(c) == Action) == true && c.name.id == ''",           # not a type test
    "type(c) == Action && l.exists(c, c.name.id == '')",        # a different c
    "!(type(c) == Action) && c.name.id == ''",
    "type(c) == Action ? true : c.name.id == ''",               # not the second result
])
def test_no_narrowing(hooks, text):
    doc = {"vars": {"c": "ScopeChild", "l": "list(ScopeChild)"}, "run": False}
    r = _check(hooks, dict(doc, expr=text))
    assert [e["message"].split(";")[0] for e in r["errors"]] == [
        "type 'ScopeChild' has no field 'name'"], text


def test_narrowed_read_of_another_class_is_safe(hooks, factory):
    # A narrowed field is resolved on the narrowed class; reading it from a
    # node of another class is the by-name read's error value, never a read
    # through the wrong class.
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", test_cel_eval._MODEL)])
    doc = {"expr": test_cel_eval._PRELUDE % (
        "[A, fa].map(c, type(c) == Action ? c.is_abstract : false)")}
    r = factory._lintTestHooks().cel_check_node(doc, p._files[-1])
    assert r["errors"] == [], r
    assert r["values"]["expr"]["value"] == [
        {"type": "bool", "value": False}, {"type": "bool", "value": False}]


# ----------------------------------------------- nesting limit (Q-E3) ----

def test_nesting_two_is_fine(hooks):
    assert _type(hooks, "[[1]].all(x, x.exists(y, y > 0))") == "bool"


def test_nesting_three_is_refused(hooks):
    text = "[[[1]]].all(x, x.all(y, y.exists(z, z > 0)))"
    off, m = _error(hooks, text)
    assert off == text.index("y.exists")
    assert m == ("exists() nests comprehensions 3 deep, and at most 2 are allowed in one "
                 "expression or helper; move the inner part into a define: helper")


def test_nesting_four_is_one_error(hooks):
    r = _check(hooks, {"expr": "[[[[1]]]].all(a, a.all(b, b.all(c, c.all(d, d > 0))))"})
    assert len(r["errors"]) == 1


def test_receiver_chain_is_not_nesting(hooks):
    # The range, initial value and result run once, at the enclosing level:
    # only loop bodies nest. (Found by test_cel_differential.py.)
    assert _type(hooks, "[1].filter(a, true).filter(b, true).map(c, c).exists(d, d > 0)") == "bool"
    assert _type(hooks, "[[1]].all(x, x.filter(y, y > 0).map(y, y).exists(y, y > 0))") == "bool"
    assert _type(hooks, "[[1]].map(x, x.map(y, y)).map(l, l.all(y, y > 0))") == "list(bool)"


def test_nesting_reported_once_per_body(hooks):
    # A chain past the limit, and a second comprehension past it in the same
    # body: one error, at the first.
    text = "[[[1]]].all(x, x.all(y, y.filter(z, z > 0).exists(z, z > 0) || y.all(z, true)))"
    r = _check(hooks, {"expr": text})
    assert [e["offset"] for e in r["errors"]] == [text.index("y.filter")]
    # Each body at the limit has its own.
    text = "[[[1]]].all(x, x.all(y, y.all(z, true)) && x.all(y, y.all(z, true)))"
    r = _check(hooks, {"expr": text})
    assert [e["offset"] for e in r["errors"]] == [text.index("y.all"), text.rindex("y.all")]


def test_bind_does_not_count(hooks):
    assert _type(hooks, "cel.bind(a, 1, cel.bind(b, 2, cel.bind(c, 3, "
                        "[[1]].all(x, x.all(y, y > a + b + c)))))") == "bool"


def test_max_nesting_option(hooks):
    _, m = _error(hooks, "[[1]].all(x, x.all(y, y > 0))", max_nesting=1)
    assert "at most 1 are allowed" in m


def test_nesting_counts_per_helper_body(hooks):
    # lint-rule-expressions.md §6, LC-11-17: three levels after inlining,
    # two in each body.
    doc = {"define": {"inner(l)": "l.exists(x, [x].exists(y, y > 0))"},
           "expr": "[[[1]]].all(a, a.exists(b, inner(b)))"}
    r = _check(hooks, doc)
    assert r["errors"] == [] and r["values"]["expr"]["value"] is True
    doc["define"]["inner(l)"] = "l.exists(x, [x].exists(y, [y].all(z, z > 0)))"
    r = _check(hooks, doc)
    assert [e["at"] for e in r["errors"]] == ["define:inner(l)"]


# ----------------------------------------------------- define: helpers ----

def test_helpers_inline(hooks):
    doc = {"define": {"twice(x)": "x * 2", "k": "twice(21)",
                      "pick(a, b)": "a > b ? a : b"},
           "expr": "pick(k, twice(3)) + k"}
    r = _check(hooks, doc)
    assert r["errors"] == [] and r["types"]["expr"] == "int"
    assert r["values"]["expr"] == {"type": "int", "value": 84}


def test_helpers_are_generic(hooks):
    doc = {"define": {"first(l)": "l[0]"}, "expr": "first(['a']) + string(first([1]))"}
    assert _value(hooks, doc["expr"], define=doc["define"]) == {"type": "string", "value": "a1"}


def test_helper_argument_evaluated_once(hooks):
    # The parameter is bound once (cel.bind), not substituted: an argument
    # used three times costs its steps once.
    define = {"thrice(x)": "x + x + x"}
    big = "[" + ", ".join(["1"] * 50) + "].map(i, i).size()"
    once = _check(hooks, {"define": define, "expr": "thrice(%s)" % big})
    inline = _check(hooks, {"expr": "(%s) + (%s) + (%s)" % (big, big, big)})
    assert once["values"]["expr"] == inline["values"]["expr"] == {"type": "int", "value": 150}
    assert once["steps"]["expr"] < inline["steps"]["expr"] / 2


def test_helper_body_sees_only_its_parameters(hooks):
    # `x` is a variable of the expression that uses the helper, not of the
    # helper's body.
    r = _check(hooks, {"define": {"f(a)": "a + x"}, "expr": "[1].map(x, f(x))"})
    assert [(e["at"], e["message"]) for e in r["errors"]] == [
        ("define:f(a)", "undeclared reference to 'x'")]


def test_helper_body_sees_declared_variables_and_lets(hooks):
    doc = {"bindings": {"n": 10}, "define": {"f(a)": "a + n + d"},
           "let": {"d": "n * 2"}, "expr": "f(1)"}
    r = _check(hooks, doc)
    assert r["errors"] == [] and r["values"]["expr"] == {"type": "int", "value": 31}


def test_helper_capture_is_refused(hooks):
    # A comprehension variable named like a declared variable the helper
    # uses would capture it when the helper runs.
    r = _check(hooks, {"bindings": {"n": 1}, "define": {"f(a)": "a + n"},
                       "expr": "[2].map(n, f(n))"})
    assert [(e["at"], e["offset"], e["message"]) for e in r["errors"]] == [
        ("define:f(a)", 4, "helper 'f' uses 'n', which a variable of the same name hides "
         "where the helper is used; rename that variable")]


def test_helper_parameter_named_like_a_variable(hooks):
    # A parameter shadows a declared variable inside the body: fine.
    r = _check(hooks, {"bindings": {"n": 100}, "define": {"f(n)": "n + 1"},
                       "expr": "f(1) + n"})
    assert r["errors"] == [] and r["values"]["expr"] == {"type": "int", "value": 102}


def test_helper_type_errors_depend_on_the_arguments(hooks):
    r = _check(hooks, {"define": {"inc(x)": "x + 1"}, "expr": "inc(1) + inc('a')"})
    assert [(e["at"], e["offset"]) for e in r["errors"]] == [("define:inc(x)", 0)]
    assert r["errors"][0]["message"].startswith(
        "no matching overload for '+' applied to (string, int)")


@pytest.mark.parametrize("define,expr,at,offset,msg", [
    ({"a(x)": "a(x)"}, "a(1)", "define:a(x)", 0, "helpers call each other in a cycle: a -> a"),
    ({"a(x)": "b(x)", "b(y)": "1 + a(y)"}, "a(1)", "define:b(y)", 4,
     "helpers call each other in a cycle: a -> b -> a"),
    ({"a": "b + 1", "b": "c", "c": "a"}, "1", "define:c", 0,
     "helpers call each other in a cycle: a -> b -> c -> a"),
    ({"f(x)": "x", "size(x)": "1"}, "1", "define:size(x)", 0,
     "helper 'size' has the name of a library function, which it would hide"),
    ({"f(x, x)": "x"}, "1", "define:f(x, x)", 0, "helper 'f' has two parameters named 'x'"),
    ({"f(1)": "1"}, "1", "define:f(1)", 0, "helper 'f': '1' is not a parameter name"),
    ({"a b": "1"}, "1", "define:a b", 0, "a helper is 'name' or 'name(param, ...)', not 'a b'"),
    ({"f(x)": "b'x'"}, "1", "define:f(x)", 0, "bytes literals are not supported in pss-rules"),
])
def test_helper_errors(hooks, define, expr, at, offset, msg):
    # Reported whether or not anything uses the helper, and once.
    r = _check(hooks, {"define": define, "expr": expr})
    assert [(e["at"], e["offset"], e["message"]) for e in r["errors"]] == [(at, offset, msg)]


def test_bad_helper_used_twice_is_reported_once(hooks):
    r = _check(hooks, {"define": {"f(x)": "b'x'", "g(x)": "g(x)"},
                       "where": "f(1) == f(2) && g(1)", "report": "[f(3), g(2)]"})
    assert sorted(e["message"] for e in r["errors"]) == [
        "bytes literals are not supported in pss-rules",
        "helpers call each other in a cycle: g -> g"]


@pytest.mark.parametrize("define,expr,msg", [
    ({"f(x)": "x"}, "f(1, 2)", "helper 'f' takes 1 argument, not 2"),
    ({"f(x, y)": "x"}, "f()", "helper 'f' takes 2 arguments, not 0"),
    ({"f(x)": "x"}, "f", "'f' is a helper with parameters; call it: f(...)"),
    ({"k": "1"}, "k()", "'k' is a helper without parameters; write it without ()"),
])
def test_helper_misuse(hooks, define, expr, msg):
    r = _check(hooks, {"define": define, "expr": expr})
    assert [e["message"] for e in r["errors"]] == [msg]


def test_helper_shadowed_by_a_variable(hooks):
    # A helper used as a name is hidden by a variable of that name.
    r = _check(hooks, {"define": {"k": "'helper'"}, "expr": "[1].map(k, k + 1)"})
    assert r["errors"] == [] and r["types"]["expr"] == "list(int)"


def test_later_helper_of_a_name_wins(hooks):
    # The loader lists a rule's own helpers after the file's (C4.1).
    r = _check(hooks, "define:\n  k: '1'\nexpr: k\n")
    assert r["values"]["expr"]["value"] == 1


# -------------------------------------------------------- shadowing ------

@pytest.mark.parametrize("doc,typ,value", [
    # A comprehension variable shadows a declared one.
    ({"bindings": {"x": "s"}, "expr": "[1].map(x, x + 1)[0]"}, "int", 2),
    # A variable shadows a type name ...
    ({"bindings": {"int": 5}, "expr": "int + 1"}, "int", 6),
    ({"bindings": {"ExprBin": "v"}, "expr": "ExprBin + '!'"}, "string", "v!"),
    # ... and a namespace.
    ({"bindings": {"optional": {"of": 5}}, "expr": "optional.of"}, "int", 5),
    # A later let shadows an earlier one, and a variable.
    ({"bindings": {"a": 1}, "let": {"a": "'s'"}, "expr": "a + 't'"}, "string", "st"),
    # cel.bind shadows.
    ({"bindings": {"y": 1}, "expr": "cel.bind(y, 'b', y)"}, "string", "b"),
])
def test_shadowing(hooks, doc, typ, value):
    r = _check(hooks, doc)
    assert r["errors"] == [] and r["types"]["expr"] == typ
    assert r["values"]["expr"]["value"] == value


def test_lets_in_order(hooks):
    r = _check(hooks, {"let": {"a": "1", "b": "a + 1", "c": "[a, b]"}, "expr": "c.size()"})
    assert r["types"] == {"let:a": "int", "let:b": "int", "let:c": "list(int)", "expr": "int"}
    assert r["values"]["let:c"]["value"] == [{"type": "int", "value": 1},
                                             {"type": "int", "value": 2}]
    r = _check(hooks, {"let": {"a": "b", "b": "1"}, "expr": "a"})
    assert [(e["at"], e["message"]) for e in r["errors"]] == [
        ("let:a", "undeclared reference to 'b'")]


# --------------------------------------------- where, report, expect -----

@pytest.mark.parametrize("key,text,msg", [
    ("where", "1", "where: must be bool, but this expression is 'int'"),
    ("where", "[true]", "where: must be bool, but this expression is 'list(bool)'"),
    ("report", "node", "report: must be list(node), but this expression is 'ExprBin'"),
    ("report", "[1]", "report: must be list(node), but this expression is 'list(int)'"),
    ("report", "[a.location]", "but this expression is 'list(Location)'"),
])
def test_required_result_types(hooks, key, text, msg):
    r = _check(hooks, {"vars": {"node": "ExprBin", "a": "Action"}, key: text})
    assert len(r["errors"]) == 1 and msg in r["errors"][0]["message"]


@pytest.mark.parametrize("key,text", [
    ("where", "node.lhs != null"), ("where", "[1].exists(x, x > 0)"),
    ("report", "[node]"), ("report", "[node.lhs, node.rhs]"), ("report", "[]"),
    ("report", "[node].filter(n, n.op == ExprBinOp.BinOp_Eq)"),
])
def test_required_result_types_met(hooks, key, text):
    r = _check(hooks, {"vars": {"node": "ExprBin"}, key: text, "run": False})
    assert r["errors"] == [], r


def test_expect(hooks):
    assert _check(hooks, {"expr": "[1]", "expect": "list(int)"})["errors"] == []
    r = _check(hooks, {"expr": "[1]", "expect": "list(string)"})
    assert r["errors"][0]["message"] == (
        "expr: must be list(string), but this expression is 'list(int)'")


# --------------------------------------------- located in the YAML file ----

@pytest.mark.parametrize("doc,line,col", [
    ("expr: 1 + x\n", 1, 11),
    ("expr: '1 + x'\n", 1, 12),
    ('expr: "1 +\\\n  x"\n', 2, 3),
    ("expr: |\n  1 +\n    x\n", 3, 5),
    ("expr: >-\n  1\n  +\n\n  x\n", 5, 3),
    ("define:\n  f(a): |-\n    a +\n      x\nexpr: f(1)\n", 4, 7),
    ("let:\n  d: >\n    [1,\n     x]\nexpr: d\n", 4, 6),
])
def test_error_positions(hooks, doc, line, col):
    r = _check(hooks, doc)
    assert len(r["errors"]) == 1, r
    e = r["errors"][0]
    assert e["message"] == "undeclared reference to 'x'"
    assert (e["line"], e["col"]) == (line, col)


def test_cycle_position(hooks):
    doc = "define:\n  a(x): b(x)\n  b(y): >-\n    1 +\n    a(y)\nexpr: a(1)\n"
    r = _check(hooks, doc)
    assert [(e["at"], e["line"], e["col"], e["message"]) for e in r["errors"]] == [
        ("define:b(y)", 5, 5, "helpers call each other in a cycle: a -> b -> a")]


def test_json_document(hooks):
    # JSON is YAML; an escaped surrogate pair is one character.
    r = _check(hooks, '{"expr": "\'\\ud83d\\udc31\' + x"}', "check.json")
    assert r["errors"][0]["message"] == "undeclared reference to 'x'"
    assert r["errors"][0]["col"] == 28
    assert _check(hooks, '{"expr": "\'\\ud83d\\udc31\'.size()"}')["values"]["expr"]["value"] == 1


# ----------------------------------------------- the overloads called ----

def test_overloads_are_reported(hooks):
    r = _check(hooks, {"expr": "size('ab') + [1].size() > 1 && 'a'.contains('b')",
                       "define": {"f(x)": "x.startsWith('a')"}, "where": "f('abc')"})
    assert r["overloads"]["expr"] == [
        "logical_and", "greater_int64", "add_int64", "list_size", "size_string",
        "contains_string"]
    assert r["overloads"]["where"] == ["starts_with_string"]


def test_overloads_left_to_run_time(hooks):
    # An operand whose type is not known yet: every overload that could apply
    # is listed, and the evaluator chooses by the value.
    r = _check(hooks, {"expr": "size(optional.none().value()) == 0", "run": False})
    assert r["errors"] == []
    assert set(r["overloads"]["expr"]) >= {"size_list", "size_map", "size_string"}


def test_enum_constants_are_folded(hooks):
    # Resolved when checked: one step, no lookup.
    r = _check(hooks, {"expr": "ExprBinOp.BinOp_Eq"})
    assert r["steps"]["expr"] == 1
    assert hooks.cel_eval("ExprBinOp.BinOp_Eq")["steps"] == 2


# ------------------------------- checked and unchecked evaluate the same ---

# Cases of test_cel_stdlib.py that need dyn, so the checker refuses them.
_STDLIB_REFUSED = {
    "[1, 'a'] == [1.0, 'a']": "list elements must all have one type",
    "[1] + ['a']": "no matching overload for '+'",
    "[7, 8, 9][1.0]": "'list(A)[double] -> A' is not supported in pss-rules",
    "{'a': 1, 2: 'two'}[2]": "map keys must all have one type",
    "dyn(1) == 1": "'dyn(A) -> A' is not supported in pss-rules",
}


@pytest.mark.parametrize("oid,text", [
    (c[0], c[1]) for c in test_cel_stdlib.CASES + test_cel_stdlib.EVALUATOR_CASES])
def test_stdlib_cases_checked(hooks, oid, text):
    unchecked = hooks.cel_eval(text)
    r = _check(hooks, {"expr": text})
    if text in _STDLIB_REFUSED:
        assert _STDLIB_REFUSED[text] in r["errors"][0]["message"]
        return
    assert r["errors"] == [], r
    assert r["values"]["expr"] == unchecked["result"]
    assert r["calls"]["expr"] == unchecked["calls"]
    assert oid in r["overloads"]["expr"]


def _node_cases():
    out = []
    for name in ("test_cel_node_values", "test_cel_node_has"):
        for m in getattr(test_cel_eval, name).pytestmark:
            if m.name == "parametrize":
                out += [a[0] for a in m.args[1]]
    return out


@pytest.fixture(scope="module")
def unit():
    from pssparser.parser import Parser
    p = Parser()
    p.parses([("top.pss", test_cel_eval._MODEL)])
    return p, p._files[-1]


@pytest.mark.parametrize("text", _node_cases() + [
    "A.super_t", "A.super_t == null", "A.super_t.target", "has(A.super_t.target)",
    "has(A.super_t) && A.super_t.target == null", "A.?super_t.hasValue()",
    "A.?super_t.target.hasValue()", "type(B.?super_t.value()) == TypeIdentifier"])
def test_node_cases_checked(hooks, unit, text):
    # Node fields are read by index once checked; the values are the same.
    full = test_cel_eval._PRELUDE % text
    unchecked = hooks.cel_eval_node(full, unit[1])
    r = hooks.cel_check_node({"expr": full}, unit[1])
    assert r["errors"] == [], r
    assert r["values"]["expr"] == unchecked["result"]
    assert r["steps"]["expr"] <= unchecked["steps"]


# --------------------------------------------- qualified names (C4.1) ------

def test_qualified_variable(hooks):
    """CEL's qualified identifiers: `options.limit` names the variable
    "options.limit" when `options` is not itself a variable. A rule's options
    are declared this way (C4.1), each with its own type."""
    doc = {"bindings": {"options.limit": 3, "options.name": "x"}}
    assert _type(hooks, "options.limit", **doc) == "int"
    assert _type(hooks, "options.name", **doc) == "string"
    assert _value(hooks, "options.limit + 1", **doc) == {"type": "int", "value": 4}


def test_qualified_variable_unknown_member(hooks):
    doc = {"bindings": {"options.limit": 3}}
    assert _error(hooks, "options.limt > 0", **doc) == (
        0, "undeclared reference to 'options.limt' (declared: 'options.limit')")


def test_qualified_variable_shadowed_by_a_comprehension(hooks):
    """A variable named `options` hides the qualified names under it."""
    doc = {"bindings": {"options.limit": 3}}
    assert _error(hooks, "[{'limit': 'a'}].all(options, options.limit == 1)", **doc)[1] == \
        "no matching overload for '==' applied to (string, int); it takes A == A -> bool"
