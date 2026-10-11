"""
The lint engine's CEL parser (lint-core-plan.md C2.1, D-C1).

A hand-written recursive-descent parser for the full CEL expression syntax,
producing the canonical CEL AST (operators as calls `_+_`, `@in`, `_?_:_`,
...; macros expanded to comprehensions, as the spec does). Features outside
the pss-rules profile parse and are then rejected by a separate profile check
with a precise message. Reached through the private hook `cel_parse(text)`.

The conformance expressions (tests/data/cel-conformance/, cel-spec v0.25.3)
check coverage and, through an unparse round-trip, the tree's shape.
"""
import glob
import json
import math
import os

import pytest

CONFORMANCE = os.path.join(os.path.dirname(__file__), "..", "..", "data", "cel-conformance")

#: Conformance tests whose expression is outside CEL's expression syntax as
#: this parser takes it, each with the reason.
SYNTAX_SKIPS = {
    # none: every expression in the imported files parses (block_ext, the only
    # syntax this parser refuses, is not imported).
}


@pytest.fixture(scope="module")
def parse(factory):
    hooks = factory._lintTestHooks()
    return hooks.cel_parse


def _ok(parse, text):
    r = parse(text)
    assert r["ok"], (text, r)
    return r["ast"]


# ------------------------------------------------------------- unparse ----

_BINARY = {
    "_||_": "||", "_&&_": "&&", "_==_": "==", "_!=_": "!=", "_<_": "<", "_<=_": "<=",
    "_>_": ">", "_>=_": ">=", "_+_": "+", "_-_": "-", "_*_": "*", "_/_": "/", "_%_": "%",
    "@in": "in",
}


def _str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch in '"\\':
            out.append("\\" + ch)
        elif o < 0x20 or o == 0x7f or 0xd800 <= o <= 0xdfff:
            out.append("\\x%02x" % o if o < 0x80 else "\\u%04x" % o)
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _ident(name):
    """A field name, backquoted unless it is a plain identifier. Reserved
    words (`if`, ...) may be selected unquoted; the literal and operator
    keywords may not."""
    ok = name and (name[0].isalpha() or name[0] == "_") and all(
        c.isalnum() or c == "_" for c in name) and name.isascii() \
        and name not in ("in", "true", "false", "null")
    return name if ok else "`%s`" % name


def unparse(e, src):
    """CEL text for a parsed tree: every operand parenthesised, so precedence
    is explicit. A comprehension is a macro the parser expanded; its own
    source text stands for it (`src[begin:end]`)."""
    k = e["k"]
    if k == "const":
        t, v = e["type"], e["value"]
        if t == "null":
            return "null"
        if t == "bool":
            return "true" if v else "false"
        if t == "int":
            return str(v)
        if t == "uint":
            return "%du" % v
        if t == "double":
            if isinstance(v, str):
                return None             # inf/nan have no literal
            r = repr(float(v))
            return r if ("." in r or "e" in r) else r + ".0"
        if t == "string":
            return _str(v)
        if t == "bytes":
            return 'b"%s"' % "".join("\\x" + v[i:i + 2] for i in range(0, len(v), 2))
    if k == "ident":
        return e["name"]

    def p(x):
        u = unparse(x, src)
        return None if u is None else "(%s)" % u

    def all_of(*parts):
        return None if any(x is None for x in parts) else parts

    if k == "select":
        o = p(e["operand"])
        if o is None:
            return None
        s = "%s.%s" % (o, _ident(e["field"]))
        return "has(%s)" % s if e["test_only"] else s
    if k == "call":
        fn, args = e["fn"], e["args"]
        a = [p(x) for x in args]
        if any(x is None for x in a):
            return None
        if "target" not in e:
            if fn in _BINARY:
                return "%s %s %s" % (a[0], _BINARY[fn], a[1])
            if fn == "!_":
                return "!" + a[0]
            if fn == "-_":
                return "-" + a[0]
            if fn == "_?_:_":
                return "%s ? %s : %s" % tuple(a)
            if fn == "_[_]":
                return "%s[%s]" % (a[0], unparse(args[1], src))
            if fn == "_[?_]":
                return "%s[?%s]" % (a[0], unparse(args[1], src))
            if fn == "_?._":
                return "%s.?%s" % (a[0], _ident(args[1]["value"]))
            return "%s(%s)" % (fn, ", ".join(unparse(x, src) for x in args))
        t = p(e["target"])
        if t is None:
            return None
        return "%s.%s(%s)" % (t, fn, ", ".join(unparse(x, src) for x in args))
    if k == "list":
        opt = set(e["optional"])
        el = [unparse(x, src) for x in e["elems"]]
        if any(x is None for x in el):
            return None
        return "[%s]" % ", ".join(("?" if i in opt else "") + x for i, x in enumerate(el))
    if k in ("map", "struct"):
        parts = []
        for ent in e["entries"]:
            v = unparse(ent["value"], src)
            key = unparse(ent["key"], src) if "key" in ent else _ident(ent["field"])
            if v is None or key is None:
                return None
            parts.append("%s%s: %s" % ("?" if ent["optional"] else "", key, v))
        body = "{%s}" % ", ".join(parts)
        return body if k == "map" else e["name"] + body
    if k == "comprehension":
        return src.encode("utf-8")[e["begin"]:e["end"]].decode("utf-8")
    raise AssertionError("unknown node %r" % k)


def shape(e):
    """The tree without ids and positions."""
    if isinstance(e, dict):
        return {k: shape(v) for k, v in e.items() if k not in ("id", "begin", "end")}
    if isinstance(e, list):
        return [shape(x) for x in e]
    return e


def _sexpr(e):
    """A compact rendering, for shape assertions."""
    k = e["k"]
    if k == "const":
        v = e["value"]
        return {True: "true", False: "false", None: "null"}.get(v, repr(v)) \
            if v is None or isinstance(v, bool) else repr(v)
    if k == "ident":
        return e["name"]
    if k == "select":
        return ("has(%s.%s)" if e["test_only"] else "%s.%s") % (_sexpr(e["operand"]), e["field"])
    if k == "call":
        args = [_sexpr(a) for a in e["args"]]
        t = (_sexpr(e["target"]) + ".") if "target" in e else ""
        return "%s%s(%s)" % (t, e["fn"], ", ".join(args))
    if k == "list":
        return "[%s]" % ", ".join(_sexpr(a) for a in e["elems"])
    if k == "map":
        return "{%s}" % ", ".join("%s: %s" % (_sexpr(x["key"]), _sexpr(x["value"]))
                                  for x in e["entries"])
    if k == "comprehension":
        return "comp(%s in %s)" % (e["iter_var"], _sexpr(e["iter_range"]))
    return k


# ---------------------------------------------- precedence/associativity ----

@pytest.mark.parametrize("text,shape_", [
    # precedence, loosest first: ?: || && relations(== != < <= > >= in) + - * / % unary member
    ("a ? b : c || d", "_?_:_(a, b, _||_(c, d))"),
    ("a || b && c", "_||_(a, _&&_(b, c))"),
    ("a && b == c", "_&&_(a, _==_(b, c))"),
    ("a == b < c", "_<_(_==_(a, b), c)"),       # one relation level, left-associative
    ("a < b + c", "_<_(a, _+_(b, c))"),
    ("a + b * c", "_+_(a, _*_(b, c))"),
    ("a * -b", "_*_(a, -_(b))"),
    ("-a.b", "-_(a.b)"),
    ("!a.b()", "!_(a.b())"),
    ("a in b == c", "_==_(@in(a, b), c)"),
    # associativity
    ("a - b - c", "_-_(_-_(a, b), c)"),
    ("a / b * c", "_*_(_/_(a, b), c)"),
    ("a == b != c", "_!=_(_==_(a, b), c)"),
    ("a < b < c", "_<_(_<_(a, b), c)"),
    ("a ? b : c ? d : e", "_?_:_(a, b, _?_:_(c, d, e))"),
    ("a ? (b ? c : d) : e", "_?_:_(a, _?_:_(b, c, d), e)"),
    ("!!a", "!_(!_(a))"),
    ("--a", "-_(-_(a))"),
    # member chains
    ("a.b[1].c(d)", "_[_](a.b, 1).c(d)"),
    ("a.b.c", "a.b.c"),
    ("f(a).g(b)", "f(a).g(b)"),
    ("(a + b).c", "_+_(a, b).c"),
    ("a.?b.c", "_?._(a, 'b').c"),
    ("a[?0][1]", "_[_](_[?_](a, 0), 1)"),
])
def test_precedence_and_associativity(parse, text, shape_):
    assert _sexpr(_ok(parse, text)) == shape_


def test_long_logical_chain_is_balanced(parse):
    # 5000 terms parse because the chain is built balanced (as cel-go does);
    # it stays a left fold semantically, which commutativity makes moot.
    ast = _ok(parse, " || ".join(["a"] * 5000))
    depth = 0
    while ast.get("k") == "call":
        ast = ast["args"][0]
        depth += 1
    assert depth <= 14


# ------------------------------------------------------------- literals ----

@pytest.mark.parametrize("text,type_,value", [
    ("0", "int", 0), ("42", "int", 42), ("0x2A", "int", 42), ("0X2a", "int", 42),
    ("9223372036854775807", "int", 9223372036854775807),
    ("-9223372036854775808", "int", -9223372036854775808),
    ("-0x8000000000000000", "int", -9223372036854775808),
    ("42u", "uint", 42), ("42U", "uint", 42), ("0x2Au", "uint", 42),
    ("18446744073709551615u", "uint", 18446744073709551615),
    ("1.5", "double", 1.5), ("1e3", "double", 1000.0), ("1E-3", "double", 0.001),
    (".5", "double", 0.5), ("5.", None, None), ("1.5e+2", "double", 150.0), ("-1.5", "double", -1.5),
    ("1e999", "double", "Infinity"),
    ("true", "bool", True), ("false", "bool", False), ("null", "null", None),
    # strings
    ("'a'", "string", "a"), ('"a"', "string", "a"), ("''", "string", ""),
    ("'''a'b''c'''", "string", "a'b''c"), ('"""a\nb"""', "string", "a\nb"),
    ("'\\a\\b\\f\\n\\r\\t\\v\\\\\\'\\\"\\`\\?'", "string", "\a\b\f\n\r\t\v\\'\"`?"),
    ("'\\x41\\101\\u00e9\\U0001F600'", "string", "AAé😀"),
    ("'é😀'", "string", "é😀"),
    ("r'\\d\\n'", "string", "\\d\\n"), ("R\"\\x\"", "string", "\\x"),
    ("r'''a\\'''", "string", "a\\"), ("r\"\"\"\\\"\"\"", "string", "\\"),
    # bytes: hex in the hook's JSON
    ("b'ab'", "bytes", "6162"), ("b'\\xff\\377'", "bytes", "ffff"), ("b'é'", "bytes", "c3a9"),
    ("B'\\u00e9'", None, None), ("br'\\x'", "bytes", "5c78"), ("rb'\\x'", "bytes", "5c78"),
])
def test_literals(parse, text, type_, value):
    r = parse(text)
    if type_ is None:
        assert not r["ok"], r
        return
    assert r["ok"], r
    assert (r["ast"]["k"], r["ast"]["type"], r["ast"]["value"]) == ("const", type_, value)


@pytest.mark.parametrize("text,msg", [
    ("9223372036854775808", "out of range"),
    ("-9223372036854775809", "out of range"),
    ("18446744073709551616u", "out of range"),
    ("'\\q'", "invalid escape"),
    ("'\\x4'", "escape"),
    ("'\\u00e'", "escape"),
    ("'\\ud800'", "not a valid Unicode code point"),
    ("'\\U00110000'", "not a valid Unicode code point"),
    ("'abc", "unterminated"),
    ("'a\nb'", "unterminated"),
    ("'''abc", "unterminated"),
    ("b'\\u00e9'", "bytes"),
])
def test_bad_literals(parse, text, msg):
    r = parse(text)
    assert not r["ok"]
    assert msg in r["error"]["message"], r


# ----------------------------------------------------------------- macros ----

def _comp(ast):
    assert ast["k"] == "comprehension", ast
    return ast


@pytest.mark.parametrize("text,init,cond,step,result", [
    ("l.all(x, p)", "true", "@not_strictly_false(@result)", "_&&_(@result, p)", "@result"),
    ("l.exists(x, p)", "false", "@not_strictly_false(!_(@result))", "_||_(@result, p)", "@result"),
    ("l.exists_one(x, p)", "0", "true", "_?_:_(p, _+_(@result, 1), @result)", "_==_(@result, 1)"),
    ("l.existsOne(x, p)", "0", "true", "_?_:_(p, _+_(@result, 1), @result)", "_==_(@result, 1)"),
    ("l.map(x, f)", "[]", "true", "_+_(@result, [f])", "@result"),
    ("l.map(x, p, f)", "[]", "true", "_?_:_(p, _+_(@result, [f]), @result)", "@result"),
    ("l.filter(x, p)", "[]", "true", "_?_:_(p, _+_(@result, [x]), @result)", "@result"),
])
def test_macro_expansion(parse, text, init, cond, step, result):
    c = _comp(_ok(parse, text))
    assert (c["iter_var"], c["accu_var"], _sexpr(c["iter_range"])) == ("x", "@result", "l")
    got = tuple(_sexpr(c[k]) for k in ("accu_init", "loop_cond", "loop_step", "result"))
    assert got == (init, cond, step, result)


def test_has_macro(parse):
    ast = _ok(parse, "has(a.b.c)")
    assert (ast["k"], ast["test_only"], ast["field"]) == ("select", True, "c")
    assert _sexpr(ast["operand"]) == "a.b"


def test_cel_bind(parse):
    c = _comp(_ok(parse, "cel.bind(v, 1 + 1, v * v)"))
    assert (c["iter_var"], c["accu_var"]) == ("#unused", "v")
    assert _sexpr(c["iter_range"]) == "[]"
    assert (_sexpr(c["accu_init"]), _sexpr(c["loop_cond"]), _sexpr(c["result"])) == \
        ("_+_(1, 1)", "false", "_*_(v, v)")


@pytest.mark.parametrize("text,offset,msg", [
    ("has(a)", 4, "has()"),
    ("has(f())", 4, "has()"),
    ("has(a[0])", 4, "has()"),
    ("l.filter(1, p)", 9, "simple name"),
    ("l.all(a.b, p)", 6, "simple name"),
    ("cel.bind(a.b, 1, 2)", 9, "simple name"),
])
def test_macro_misuse(parse, text, offset, msg):
    r = parse(text)
    assert not r["ok"], r
    assert msg in r["error"]["message"], r
    assert r["error"]["offset"] == offset, r


@pytest.mark.parametrize("text", [
    # A macro is a name *and* an argument count (and receiver style); anything
    # else is an ordinary call, left for the checker to reject (as cel-go).
    "all(l, p)", "x.has(y)", "l.all(x)", "l.all(x, p, q)", "has(a.b, c)", "cel.bind(v, 1)",
    "l.map(x)", "l.exists()",
])
def test_non_macro_calls_stay_calls(parse, text):
    assert _ok(parse, text)["k"] == "call"


# ---------------------------------------------------------- aggregates ----

def test_aggregates(parse):
    assert _sexpr(_ok(parse, "[]")) == "[]"
    assert _sexpr(_ok(parse, "[1, 2,]")) == "[1, 2]"
    m = _ok(parse, "{'a': 1, 2: [x],}")
    assert _sexpr(m) == "{'a': 1, 2: [x]}"
    lst = _ok(parse, "[?a, b, ?c]")
    assert lst["optional"] == [0, 2]
    mp = _ok(parse, "{?'k': v}")
    assert mp["entries"][0]["optional"] is True


# --------------------------------------------------------------- errors ----

@pytest.mark.parametrize("text,offset,msg", [
    ("1 +", 3, "expected an expression, found the end of the input"),
    ("a = b", 2, "use '=='"),
    ("f(1,)", 4, "trailing ','"),
    ("if", 0, "reserved word"),
    ("a ? b ? c : d : e", 6, "expected ':'"),     # the then-branch is not a full Expr
    ("x.all(1, true)", 6, "simple name"),
    ("9223372036854775808", 0, "out of range"),
    ("'abc", 0, "unterminated"),
    ("'\\q'", 1, "invalid escape"),
    ("a b", 2, "unexpected"),
    ("(a", 2, "to close '('"),
    ("[1, 2", 5, "']'"),
    ("{1: 2", 5, "'}'"),
    ("{1}", 2, "':'"),
    ("a.", 2, "expected a field or method name after '.'"),
    ("a ? b", 5, "':'"),
    ("`a`", 0, "quoted identifier"),
    ("a.`b c`", 2, None),
    ("#", 0, "unexpected character"),
    ("(" * 70 + "1" + ")" * 70, 64, "nests too deeply"),
    # A tall tree is reported at the operator that made it one level too tall:
    # the 256th '+' (offset 511), the 256th '.'.
    ("+".join(["a"] * 300), 511, "too deeply nested"),
    ("x" + ".f" * 300, 511, "too deeply nested"),
    ("x" + "[0]" * 300, 766, "too deeply nested"),
])
def test_syntax_errors(parse, text, offset, msg):
    r = parse(text)
    if msg is None:
        assert r["ok"], r              # a quoted field name may hold any text
        return
    assert not r["ok"], r
    assert msg in r["error"]["message"], r
    assert r["error"]["offset"] == offset, r


def test_nesting_limit_edge(parse):
    # The limit counts nested expressions, the innermost included: 63 sets of
    # parentheses around `1` is 64 levels, 64 lists (the innermost empty) too.
    assert parse("(" * 63 + "1" + ")" * 63)["ok"]
    assert not parse("(" * 64 + "1" + ")" * 64)["ok"]
    assert parse("[" * 64 + "]" * 64)["ok"]
    assert not parse("[" * 65 + "]" * 65)["ok"]
    assert parse("+".join(["a"] * 256))["ok"]


def test_reserved_words_as_field_names(parse):
    # Reserved words cannot be identifiers, but can be selected (cel-spec
    # parse conformance: `{'if': 1}.if`).
    assert _sexpr(_ok(parse, "a.if")) == "a.if"
    assert _sexpr(_ok(parse, "a.if()")) == "a.if()"
    # `in` is an operator token, not a reserved identifier: not selectable.
    assert "keyword" in parse("a.in")["error"]["message"]


def test_offsets_are_bytes(parse):
    ast = _ok(parse, "'é' + x")
    assert (ast["args"][1]["begin"], ast["args"][1]["end"]) == (7, 8)


# -------------------------------------------------------------- profile ----

@pytest.mark.parametrize("text,msg", [
    ("b'x'", "bytes literals"),
    ("1u", "unsigned integer"),
    ("pkg.Msg{f: 1}", "message construction"),
    ("m.all(k, v, true)", "two-variable comprehensions"),
    (".a.b", "absolute names"),
])
def test_profile_rejects(parse, text, msg):
    r = parse(text)
    assert r["ok"]
    assert msg in r["profile_errors"][0]["message"]


def test_profile_accepts(parse):
    assert _ok_profile(parse, "l.exists(x, x.matches('a') && has(x.f) && x in [1])")


def _ok_profile(parse, text):
    r = parse(text)
    return r["ok"] and not r["profile_errors"]


def test_message_name_is_qualified(parse):
    assert _ok(parse, "a.b.M{}")["name"] == "a.b.M"
    assert _ok(parse, ".a.M{}")["name"] == ".a.M"


# ---------------------------------------------------------- conformance ----

def _conformance():
    out = []
    for f in sorted(glob.glob(os.path.join(CONFORMANCE, "*.json"))):
        with open(f, encoding="utf-8") as fp:
            d = json.load(fp)
        for t in d["tests"]:
            out.append(("%s/%s/%s" % (d["source"].split(".")[0], t["section"], t["name"]), t["expr"]))
    return out


def test_conformance_expressions_parse(parse):
    cases = _conformance()
    assert len(cases) > 1000
    bad = [(cid, e, parse(e)["error"]) for cid, e in cases
           if cid not in SYNTAX_SKIPS and not parse(e)["ok"]]
    assert not bad, bad[:5]


def test_conformance_unparse_round_trip(parse):
    # unparse(parse(e)) parses to the same tree, ids and positions aside.
    n = 0
    bad = []
    for cid, e in _conformance():
        r = parse(e)
        if not r["ok"]:
            continue
        u = unparse(r["ast"], e)
        if u is None:
            continue                    # an inf/nan constant: no literal for it
        r2 = parse(u)
        if not r2["ok"] or shape(r2["ast"]) != shape(r["ast"]):
            bad.append((cid, e, u))
        n += 1
    assert n > 1000
    assert not bad, bad[:5]
