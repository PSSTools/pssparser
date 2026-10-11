"""
The lint engine's CEL standard library and function registry
(lint-core-plan.md C3.2).

Every overload in the registry has at least one case here, and each case
checks not only the value but that the call dispatched to the overload it is
written for (the eval hook's "calls" trace). A new overload without a case
fails `test_every_overload_has_a_case`.

Also: the error cases of each function, the cost classes (linear functions
charge per element, `matches` per regex step), string(double) formatting as
cel-go does it, bool(string), the optMap/optFlatMap macros, namespaced
globals, and the registry's own shape (ids, docs, levels, the profile flag).
"""
import pytest


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


@pytest.fixture(scope="module")
def registry(hooks):
    return hooks.cel_functions()["functions"]


def _eval(hooks, text, bindings=None):
    r = hooks.cel_eval(text, 0, bindings)
    assert r["ok"], r
    return r


def _plain(v):
    """A hook value as plain Python: lists of values become lists."""
    if v["type"] == "list":
        return [_plain(e) for e in v["value"]]
    if v["type"] == "map":
        return {_plain(k): _plain(x) for k, x in v["value"]}
    if v["type"] == "optional_type":
        return ("optional", None if v["value"] is None else _plain(v["value"]))
    return v["value"]


I, D, S, B = "int", "double", "string", "bool"

# (overload id, expression, expected type, expected value)
CASES = [
    ("logical_not", "!false", B, True),
    ("equals", "[1, 'a'] == [1.0, 'a']", B, True),
    ("not_equals", "{'a': 1} != {'a': 2}", B, True),
    ("less_bool", "false < true", B, True),
    ("less_int64", "1 < 2", B, True),
    ("less_int64_double", "1 < 1.5", B, True),
    ("less_double", "2.5 < 2.0", B, False),
    ("less_double_int64", "0.5 < 1", B, True),
    ("less_string", "'abc' < 'abd'", B, True),
    ("less_equals_bool", "true <= true", B, True),
    ("less_equals_int64", "3 <= 2", B, False),
    ("less_equals_int64_double", "2 <= 2.0", B, True),
    ("less_equals_double", "1.0 <= 1.0", B, True),
    ("less_equals_double_int64", "2.0 <= 1", B, False),
    ("less_equals_string", "'b' <= 'a'", B, False),
    ("greater_bool", "true > false", B, True),
    ("greater_int64", "3 > 2", B, True),
    ("greater_int64_double", "3 > 3.5", B, False),
    ("greater_double", "3.5 > 3.0", B, True),
    ("greater_double_int64", "3.5 > 3", B, True),
    ("greater_string", "'é' > 'z'", B, True),
    ("greater_equals_bool", "false >= true", B, False),
    ("greater_equals_int64", "2 >= 2", B, True),
    ("greater_equals_int64_double", "2 >= 2.5", B, False),
    ("greater_equals_double", "2.5 >= 2.5", B, True),
    ("greater_equals_double_int64", "2.5 >= 2", B, True),
    ("greater_equals_string", "'' >= ''", B, True),
    ("add_int64", "40 + 2", I, 42),
    ("add_double", "0.5 + 0.25", D, 0.75),
    ("subtract_int64", "40 - 42", I, -2),
    ("subtract_double", "1.0 - 0.25", D, 0.75),
    ("multiply_int64", "-6 * 7", I, -42),
    ("multiply_double", "1.5 * 2.0", D, 3.0),
    ("divide_int64", "-7 / 2", I, -3),
    ("divide_double", "7.0 / 2.0", D, 3.5),
    ("modulo_int64", "-7 % 3", I, -1),
    ("negate_int64", "-(1 + 1)", I, -2),
    ("negate_double", "-(0.5 + 0.5)", D, -1.0),
    ("add_string", "'ab' + 'cd'", S, "abcd"),
    ("add_list", "[1] + ['a']", "list", [1, "a"]),
    ("in_list", "2.0 in [1, 2, 3]", B, True),
    ("in_map", "'b' in {'a': 1}", B, False),
    ("index_list", "[7, 8, 9][2]", I, 9),
    ("index_list_double", "[7, 8, 9][1.0]", I, 8),
    ("index_map", "{'a': 1, 2: 'two'}[2]", S, "two"),
    ("optional_list_index_int", "optional.of([7, 8])[1]", "optional_type", ("optional", 8)),
    ("optional_map_index_value", "optional.of({'a': 1})['b']", "optional_type", ("optional", None)),
    ("list_optindex_optional_int", "[7, 8][?5]", "optional_type", ("optional", None)),
    ("map_optindex_optional_value", "{'a': 1}[?'a']", "optional_type", ("optional", 1)),
    ("optional_list_optindex_optional_int", "optional.of([7])[?0]", "optional_type",
     ("optional", 7)),
    ("optional_map_optindex_optional_value", "optional.none()[?'a']", "optional_type",
     ("optional", None)),
    ("size_list", "size([1, 2, 3])", I, 3),
    ("list_size", "[].size()", I, 0),
    ("size_map", "size({'a': 1})", I, 1),
    ("map_size", "{1: 2, 3: 4}.size()", I, 2),
    ("size_string", "size('héllo')", I, 5),
    ("string_size", "'日本'.size()", I, 2),
    ("contains_string", "'lint rules'.contains('t r')", B, True),
    ("starts_with_string", "'lint'.startsWith('lin')", B, True),
    ("ends_with_string", "'lint'.endsWith('lint rules')", B, False),
    ("matches", "matches('action_a', '^[a-z_]+$')", B, True),
    ("matches_string", "'Action'.matches('[a-z]')", B, True),
    ("int64_to_int64", "int(5)", I, 5),
    ("double_to_int64", "int(-2.9)", I, -2),
    ("string_to_int64", "int('-42')", I, -42),
    ("double_to_double", "double(2.5)", D, 2.5),
    ("int64_to_double", "double(3)", D, 3.0),
    ("string_to_double", "double('1e3')", D, 1000.0),
    ("string_to_string", "string('x')", S, "x"),
    ("int64_to_string", "string(-12)", S, "-12"),
    ("double_to_string", "string(123.456)", S, "123.456"),
    ("bool_to_string", "string(false)", S, "false"),
    ("bool_to_bool", "bool(true)", B, True),
    ("string_to_bool", "bool('f')", B, False),
    ("type", "type([1])", "type", "list"),
    ("to_dyn", "dyn(1) == 1", B, True),
    ("optional_of", "optional.of('a')", "optional_type", ("optional", "a")),
    ("optional_ofNonZeroValue", "optional.ofNonZeroValue('')", "optional_type",
     ("optional", None)),
    ("optional_none", "optional.none()", "optional_type", ("optional", None)),
    ("optional_hasValue", "optional.of(0).hasValue()", B, True),
    ("optional_value", "optional.of([1]).value()", "list", [1]),
]

# Overloads the evaluator implements itself (non-strict or lazy): checked by
# value only, since they do not appear in the call trace.
EVALUATOR_CASES = [
    ("logical_and", "(1 / 0 == 1) && false", B, False),
    ("logical_or", "true || (1 / 0 == 1)", B, True),
    ("conditional", "false ? 1 / 0 : 2", I, 2),
    ("optional_or_optional", "optional.none().or(optional.of(2))", "optional_type",
     ("optional", 2)),
    ("optional_orValue_value", "optional.of(1).orValue(1 / 0)", I, 1),
    ("select_optional_field", "{'a': 1}.?a", "optional_type", ("optional", 1)),
]


@pytest.mark.parametrize("oid,text,typ,value", CASES, ids=[c[0] for c in CASES])
def test_overload(hooks, oid, text, typ, value):
    r = _eval(hooks, text)
    assert r["result"]["type"] == typ, r["result"]
    assert _plain(r["result"]) == value
    assert oid in r["calls"], r["calls"]


@pytest.mark.parametrize("oid,text,typ,value", EVALUATOR_CASES,
                         ids=[c[0] for c in EVALUATOR_CASES])
def test_evaluator_overload(hooks, oid, text, typ, value):
    r = _eval(hooks, text)
    assert r["result"]["type"] == typ, r["result"]
    assert _plain(r["result"]) == value


def test_every_overload_has_a_case(registry):
    # CEL's standard library; the PSS library's functions have test_fn_*.py.
    covered = {c[0] for c in CASES} | {c[0] for c in EVALUATOR_CASES}
    callable_ = {f["id"] for f in registry if f["kind"] != "macro" and f["library"] == "cel"}
    assert callable_ - covered == set(), "overloads without a test case"
    assert covered - callable_ == set(), "cases for overloads that do not exist"
    assert {c[0] for c in EVALUATOR_CASES} == {f["id"] for f in registry if f["evaluator"]}


# ------------------------------------------------------------ errors ------

@pytest.mark.parametrize("text,msg", [
    ("!1", "no matching overload for '!_' applied to (int)"),
    ("1 < 'a'", "no matching overload for '_<_' applied to (int, string)"),
    ("true < 1", "no matching overload"),
    ("[1] < [2]", "no matching overload"),
    ("1 + 1.0", "no matching overload for '_+_' applied to (int, double)"),
    ("'a' + 1", "no matching overload"),
    ("[1] + 'a'", "no matching overload"),
    ("{} + {}", "no matching overload"),
    ("1.0 % 2.0", "no matching overload for '_%_' applied to (double, double)"),
    ("-'a'", "no matching overload for '-_' applied to (string)"),
    ("1 in 'abc'", "no matching overload for '@in' applied to (int, string)"),
    ("9223372036854775807 * 2", "integer overflow"),
    ("-9223372036854775807 - 1 - 1", "integer overflow"),
    ("(-9223372036854775807 - 1) / -1", "integer overflow"),
    ("(-9223372036854775807 - 1) % -1", "integer overflow"),
    ("-(-9223372036854775807 - 1)", "integer overflow"),
    ("1 / 0", "division by zero"),
    ("1 % 0", "modulus by zero"),
    ("[1][1]", "index 1 out of range for a list of size 1"),
    ("[1][-1]", "out of range"),
    ("[1][0.5]", "no matching overload for '_[_]' applied to (list, double)"),
    ("[1]['a']", "no matching overload for '_[_]' applied to (list, string)"),
    ("{'a': 1}['b']", "no such key"),
    ("'abc'[0]", "no matching overload for '_[_]' applied to (string, int)"),
    ("optional.of(1)[0]", "no matching overload for '_[_]' applied to (optional_type, int)"),
    ("size(1)", "no matching overload for 'size' applied to (int)"),
    ("1.size()", "no matching overload for 'size' applied to (int)"),
    ("'a'.contains(1)", "no matching overload for 'contains' applied to (string, int)"),
    ("contains('a', 'b')", "no matching overload for 'contains' applied to (string, string)"),
    ("[1].startsWith('a')", "no matching overload"),
    ("'a'.matches('(')", "invalid regular expression"),
    ("'a'.matches('(a)\\\\1')", "invalid regular expression"),
    ("int(1e19)", "double is out of range for int"),
    ("int(-1e19)", "double is out of range for int"),
    ("int(0.0 / 0.0)", "double is out of range for int"),
    ("int('1.5')", "cannot convert string '1.5' to int"),
    ("int('')", "cannot convert string '' to int"),
    ("int('99999999999999999999')", "cannot convert string"),
    ("int(true)", "no matching overload for 'int' applied to (bool)"),
    ("double('x')", "cannot convert string 'x' to double"),
    ("double(true)", "no matching overload"),
    ("string([1])", "no matching overload for 'string' applied to (list)"),
    ("bool('yes')", "cannot convert string 'yes' to bool"),
    ("bool(1)", "no matching overload for 'bool' applied to (int)"),
    ("optional.none().value()", "optional.none() dereference"),
    ("optional.of(1).hasValue(2)", "no matching overload for 'hasValue'"),
    ("optional.of()", "no matching overload for 'optional.of' applied to ()"),
    ("optional.none().or(1)", "no matching overload for 'or' applied to (optional_type, int)"),
    ("1.hasValue()", "no matching overload for 'hasValue' applied to (int)"),
    ("frobnicate(1)", "undeclared reference to function 'frobnicate'"),
    ("'a'.frobnicate()", "undeclared reference to function 'frobnicate'"),
    ("optional.frobnicate(1)", "undeclared reference to 'optional'"),
])
def test_function_errors(hooks, text, msg):
    r = _eval(hooks, text)
    assert r["result"]["type"] == "error", r["result"]
    assert msg in r["result"]["value"]


def test_error_operand_wins_over_dispatch(hooks):
    # A strict function never sees an error operand: the first one is the result.
    r = _eval(hooks, "size(1 / 0)")
    assert r["result"] == {"type": "error", "value": "division by zero"}
    assert r["calls"] == ["divide_int64"]


# ------------------------------------------------------------ costs -------

def _steps(hooks, text):
    return _eval(hooks, text)["steps"]


def _list(n):
    return "[" + ", ".join(["1"] * n) + "]"


def test_linear_functions_charge_per_element(hooks):
    # A literal list costs a step per element to build, whatever the function;
    # `in` adds one more per element, `size` none.
    in_10, in_110 = _steps(hooks, "2 in " + _list(10)), _steps(hooks, "2 in " + _list(110))
    size_10, size_110 = _steps(hooks, "size(%s)" % _list(10)), _steps(hooks, "size(%s)" % _list(110))
    assert (in_110 - in_10) - (size_110 - size_10) == 100
    # Concatenation: both operands' elements.
    cat = _steps(hooks, "%s + %s" % (_list(10), _list(20)))
    lit = _steps(hooks, "[%s, %s]" % (_list(10), _list(20)))
    assert cat - lit == 30


def test_linear_strings_charge_per_64_bytes(hooks):
    short = _steps(hooks, "'%s'.contains('b')" % ("a" * 10))
    long_ = _steps(hooks, "'%s'.contains('b')" % ("a" * 6400))
    assert long_ - short == 100


def test_matches_charges_regex_steps(hooks):
    short = _steps(hooks, "'%s'.matches('(a*)*b')" % ("a" * 10))
    long_ = _steps(hooks, "'%s'.matches('(a*)*b')" % ("a" * 10000))
    assert long_ - short > 100
    r = hooks.cel_eval("'%s'.matches('(a*)*b')" % ("a" * 100000), 1000)
    assert r["budget_exceeded"]


def test_constant_functions_charge_nothing_extra(hooks):
    assert _steps(hooks, "size(%s)" % _list(200)) == _steps(hooks, _list(200)) + 1


# ------------------------------------------- string(double), bool() ------

# What Go's strconv.FormatFloat(d, 'g', -1, 64) gives, which is cel-go's
# string(double).
@pytest.mark.parametrize("text,expected", [
    ("123.456", "123.456"),
    ("-4.5e-3", "-0.0045"),
    ("1e6", "1e+06"),
    ("123456.0", "123456"),
    ("999999.0", "999999"),
    ("1234567.0", "1.234567e+06"),
    ("1e-5", "1e-05"),
    ("0.0001", "0.0001"),
    ("1.5e300", "1.5e+300"),
    ("0.1 + 0.2", "0.30000000000000004"),
    ("100.0", "100"),
    ("2.0", "2"),
    ("-0.0", "-0"),
    ("0.0", "0"),
    ("5e-324", "5e-324"),
    ("1.7976931348623157e308", "1.7976931348623157e+308"),
    ("0.0 / 0.0", "NaN"),
    ("1.0 / 0.0", "+Inf"),
    ("-1.0 / 0.0", "-Inf"),
])
def test_string_of_double(hooks, text, expected):
    r = _eval(hooks, "string(%s)" % text)
    assert r["result"] == {"type": "string", "value": expected}


@pytest.mark.parametrize("text,expected", [
    (t, True) for t in ("1", "t", "T", "true", "TRUE", "True")
] + [
    (f, False) for f in ("0", "f", "F", "false", "FALSE", "False")
])
def test_bool_of_string(hooks, text, expected):
    assert _eval(hooks, "bool('%s')" % text)["result"] == {"type": "bool", "value": expected}


@pytest.mark.parametrize("text", ["tRUE", "yes", "on", " true", ""])
def test_bool_of_string_refused(hooks, text):
    assert _eval(hooks, "bool('%s')" % text)["result"]["type"] == "error"


# ------------------------------------------------ macros, namespaces ------

@pytest.mark.parametrize("text,expected", [
    ("optional.of(42).optMap(y, y + 1)", ("optional", 43)),
    ("optional.none().optMap(y, y + 1)", ("optional", None)),
    ("optional.of(1).optMap(y, 1 / 0).hasValue()", "error"),
    ("{'k': {'s': 'v'}}.?k.optFlatMap(k, k.?s)", ("optional", "v")),
    ("{'k': {}}.?k.optFlatMap(k, k.?s)", ("optional", None)),
    ("{}.?k.optFlatMap(k, k.?s)", ("optional", None)),
    ("optional.of(1).optMap(x, optional.of(2).optMap(y, x + y))", ("optional", ("optional", 3))),
    ("optional.of([1, 2]).optMap(l, l.map(x, x * 2))", ("optional", [2, 4])),
])
def test_opt_map_macros(hooks, text, expected):
    r = _eval(hooks, text)
    if expected == "error":
        assert r["result"]["type"] == "error"
    else:
        assert _plain(r["result"]) == expected


def test_opt_map_evaluates_its_target_once(hooks):
    # cel-go copies the target into the expansion; ours binds it once.
    r = _eval(hooks, "optional.of(40 + 1).optMap(y, y + 1)")
    assert r["calls"].count("add_int64") == 2
    assert _plain(r["result"]) == ("optional", 42)


@pytest.mark.parametrize("text,msg", [
    ("optional.of(1).optMap(1, 2)", "optMap() needs a simple name"),
    ("optional.of(1).optFlatMap(a.b, 2)", "optFlatMap() needs a simple name"),
])
def test_opt_map_syntax_errors(hooks, text, msg):
    r = hooks.cel_eval(text)
    assert not r["ok"] and msg in r["error"]["message"]


def test_opt_map_wrong_arity_is_an_ordinary_call(hooks):
    r = _eval(hooks, "optional.of(1).optMap(x)")
    assert "no matching overload" in r["result"]["value"] or \
        "undeclared reference" in r["result"]["value"]


def test_opt_map_hidden_name_is_not_writable(hooks):
    # The expansion's own binding (@opt) is not a name a rule can spell.
    assert not hooks.cel_parse("@opt")["ok"]


def test_namespace_shadowed_by_a_variable(hooks):
    # With `optional` bound, optional.of() is a receiver call on it.
    r = _eval(hooks, "optional.of(1)", {"optional": {"of": 1}})
    assert r["result"]["type"] == "error"
    assert "undeclared reference to function 'of'" in r["result"]["value"]


# ------------------------------------------------------- registry ---------

def test_registry_shape(registry):
    ids = [f["id"] for f in registry]
    assert len(ids) == len(set(ids))
    for f in registry:
        assert f["doc"], f["id"]
        assert f["group"], f["id"]
        assert f["display"], f["id"]
        assert f["cost"] in ("constant", "linear", "custom")
        # The standard library needs nothing but the syntax tree.
        if f["library"] == "cel":
            assert (f["level"], f["scope"]) == ("L0", "file"), f["id"]
        if f["kind"] == "macro":
            assert f["params"] == [] and f["result"] == ""
        else:
            assert f["result"], f["id"]


@pytest.mark.parametrize("oid,display", [
    ("add_int64", "int + int -> int"),
    ("logical_not", "!bool -> bool"),
    ("negate_double", "-double -> double"),
    ("in_map", "K in map(K, V) -> bool"),
    ("index_list", "list(A)[int] -> A"),
    ("map_optindex_optional_value", "map(K, V)[?K] -> optional(V)"),
    ("conditional", "bool ? A : A -> A"),
    ("contains_string", "string.contains(string) -> bool"),
    ("list_size", "list(A).size() -> int"),
    ("optional_of", "optional.of(A) -> optional(A)"),
    ("optional_none", "optional.none() -> optional(A)"),
    ("matches", "matches(string, string) -> bool"),
    ("cel_bind", "cel.bind(x, A, B) -> B"),
])
def test_registry_display(registry, oid, display):
    assert {f["id"]: f["display"] for f in registry}[oid] == display


def test_registry_receivers(registry):
    by_id = {f["id"]: f for f in registry}
    assert by_id["contains_string"]["receiver"] and by_id["contains_string"]["params"] == \
        ["string", "string"]
    assert not by_id["optional_of"]["receiver"]
    assert by_id["optional_of"]["function"] == "optional.of"
    assert by_id["optional_hasValue"]["receiver"]
    assert by_id["optional_hasValue"]["params"] == ["optional(A)"]


def test_registry_profile(registry):
    out = {f["id"] for f in registry if not f["in_profile"]}
    assert out == {"to_dyn", "index_list_double"}


def test_registry_lists_the_macros(registry):
    macros = {f["function"] for f in registry if f["kind"] == "macro"}
    assert macros == {"has", "all", "exists", "exists_one", "map", "filter", "cel.bind",
                      "optMap", "optFlatMap"}
