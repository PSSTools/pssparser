"""
The lint engine's YAML layer (lint-core-plan.md C1.2; pss-rules-format.md §6.1).

rapidyaml parses; `src/lint/yaml/YamlDoc.cpp` types scalars by the YAML 1.2
core schema, gives every node a 1-based line and column, refuses what rule
files must not contain, and expands aliases within a budget. Reached through
the private test hook `yaml_load(name, text)`, which returns the converted
tree as JSON. `ts/test/lintcore-parity.test.ts` checks the WASM build gives
the same text.
"""
import pytest


@pytest.fixture(scope="module")
def load(factory):
    hooks = factory._lintTestHooks()
    return lambda text, name="r.yaml": hooks.yaml_load(name, text)


def _root(r):
    assert r["ok"], r
    return r["root"]


def _members(r):
    return {m["key"]: m["value"] for m in _root(r)["members"]}


def _where(n):
    return (n["line"], n["col"])


# ------------------------------------------------------------- typing ----

@pytest.mark.parametrize("text,kind,value", [
    # The YAML 1.1 booleans are strings: the `on:` trap (format §6.1).
    ("on", "string", "on"), ("off", "string", "off"), ("yes", "string", "yes"),
    ("no", "string", "no"), ("y", "string", "y"), ("Off", "string", "Off"),
    ("true", "bool", True), ("True", "bool", True), ("TRUE", "bool", True),
    ("false", "bool", False), ("tRUE", "string", "tRUE"),
    ("~", "null", None), ("null", "null", None), ("Null", "null", None), ("NULL", "null", None),
    ("nUll", "string", "nUll"),
    ("0", "int", 0), ("-17", "int", -17), ("+3", "int", 3), ("007", "int", 7),
    ("0x10", "int", 16), ("0xff", "int", 255), ("0o17", "int", 15),
    ("0x", "string", "0x"), ("0o8", "string", "0o8"), ("0b101", "string", "0b101"),
    ("9223372036854775807", "int", 9223372036854775807),
    ("-9223372036854775808", "int", -9223372036854775808),
    ("1e3", "float", 1000.0), ("1.5", "float", 1.5), (".5", "float", 0.5), ("5.", "float", 5.0),
    ("-1.5e-2", "float", -0.015), ("1e", "string", "1e"), (".", "string", "."),
    (".inf", "float", "Infinity"), ("-.Inf", "float", "-Infinity"), ("+.INF", "float", "Infinity"),
    (".nan", "float", "NaN"), ("-.nan", "string", "-.nan"),
    ("1_000", "string", "1_000"), ("1.2.3", "string", "1.2.3"), ("12:30", "string", "12:30"),
    ("'1'", "string", "1"), ('"true"', "string", "true"), ("''", "string", ""),
])
def test_core_schema_typing(load, text, kind, value):
    v = _members(load("k: %s\n" % text))["k"]
    assert (v["kind"], v.get("value")) == (kind, value)


def test_empty_value_is_null(load):
    assert _members(load("k:\n"))["k"]["kind"] == "null"


def test_only_plain_scalars_are_typed(load):
    m = _members(load("a: '1'\nb: \"1\"\nc: |\n  1\n"))
    assert [m[k]["kind"] for k in "abc"] == ["string"] * 3
    assert m["c"]["value"] == "1\n"


@pytest.mark.parametrize("text", ["9223372036854775808", "-9223372036854775809",
                                  "0x8000000000000000", "0o1000000000000000000000"])
def test_integer_out_of_range(load, text):
    r = load("k: %s\n" % text)
    assert not r["ok"]
    assert "out of the 64-bit range" in r["error"]["message"]
    assert _where(r["error"]) == (1, 4)


def test_empty_document_is_null(load):
    assert _root(load(""))["kind"] == "null"
    assert _root(load("# only a comment\n"))["kind"] == "null"


def test_json_goes_through_the_same_path(load):
    m = _members(load('{"pss-rules": 1, "rules": [{"id": "A", "on": true, "x": null}]}', "r.json"))
    assert m["pss-rules"] == {**m["pss-rules"], "kind": "int", "value": 1}
    rule = {x["key"]: x["value"] for x in m["rules"]["items"][0]["members"]}
    assert rule["id"]["style"] == "double-quoted"
    assert (rule["on"]["kind"], rule["x"]["kind"]) == ("bool", "null")
    assert _where(rule["on"]) == (1, 46)
    # A quoted key or value is marked at its first content character.
    assert _where(m["rules"]["items"][0]["members"][0]["key_mark"]) == (1, 30)
    assert _where(rule["id"]) == (1, 36)


# ------------------------------------------------------------- marks ----

def test_marks_block_map_and_flow_seq(load):
    m = _members(load("a: 1\nbb: [x, 'y']\n"))
    assert _where(m["a"]) == (1, 4)
    items = m["bb"]["items"]
    assert [_where(i) for i in items] == [(2, 6), (2, 10)]
    assert [i["style"] for i in items] == ["plain", "single-quoted"]
    assert m["bb"]["style"] == "flow"


def test_marks_nested(load):
    text = ("rules:\n"
            "  - id: A\n"
            "    match:\n"
            "      kind: [ExprBin, ExprUnary]\n"
            "    where: \"x\"\n"
            "  - {id: B, where: y}\n")
    rules = _members(load(text))["rules"]
    a = {x["key"]: x for x in rules["items"][0]["members"]}
    assert _where(a["id"]["key_mark"]) == (2, 5)
    assert _where(a["id"]["value"]) == (2, 9)
    kinds = {x["key"]: x["value"] for x in a["match"]["value"]["members"]}["kind"]
    assert [_where(i) for i in kinds["items"]] == [(4, 14), (4, 23)]
    assert _where(a["where"]["value"]) == (5, 13)     # inside the quotes
    b = {x["key"]: x for x in rules["items"][1]["members"]}
    assert rules["items"][1]["style"] == "flow"
    assert [_where(b[k]["value"]) for k in ("id", "where")] == [(6, 10), (6, 20)]


def test_marks_containers(load):
    # A container value is marked where it starts, not at its key (rapidyaml
    # reports the key's location for both).
    m = _members(load("rules:\n  - id: A\nm:\n  a: 1\nf: {k: [1]}\ns:\n- 1\n"))
    assert _where(m["rules"]) == (2, 3)                  # the '-'
    assert _where(m["rules"]["items"][0]) == (2, 5)      # the first key
    assert _where(m["m"]) == (4, 3)
    assert _where(m["f"]) == (5, 4)                      # the '{'
    assert _where(m["f"]["members"][0]["value"]) == (5, 8)
    assert _where(m["s"]) == (7, 1)


def test_alias_value_is_marked_at_its_anchor(load):
    # The expanded copy carries the anchored text's position: that is where
    # the content a diagnostic would talk about is written.
    m = _members(load("b: &x {k: 1}\nu: *x\n"))
    assert _where(m["u"]) == _where(m["b"]) == (1, 7)


def test_marks_offsets_are_bytes(load):
    # Two-byte characters before the value: col counts bytes, as offset does.
    text = "k: 'é'\nv: 1\n"
    m = _members(load(text))
    assert m["v"]["offset"] == text.encode("utf-8").index(b"1")
    assert _where(m["v"]) == (2, 4)


@pytest.mark.parametrize("text,style,value", [
    ("k: |\n  a\n  b\n", "literal", "a\nb\n"),
    ("k: |-\n  a\n", "literal", "a"),
    ("k: |+\n  a\n\n", "literal", "a\n\n"),
    ("k: >\n  a\n  b\n\n  c\n", "folded", "a b\nc\n"),
    ("k: >-\n  a\n  b\n", "folded", "a b"),
    ("k: |2\n   a\n", "literal", " a\n"),
])
def test_block_scalars(load, text, style, value):
    v = _members(load(text))["k"]
    assert (v["kind"], v["style"], v["value"]) == ("string", style, value)
    # F-4: a block scalar's mark is the start of its first content line, not
    # the indented text; C2.2 maps expression offsets inside it.
    assert v["line"] == 2


def test_multiline_plain_scalar_folds(load):
    v = _members(load("k: a\n  b\n"))["k"]
    assert (v["kind"], v["value"], _where(v)) == ("string", "a b", (1, 4))


# ------------------------------------------------------------ refusals ----

@pytest.mark.parametrize("text,line,col,msg", [
    ("x: !!str 1\n", 1, 10, "tags"),
    ("x: !custom 1\n", 1, 12, "tags"),
    ("!!str k: 1\n", 1, 7, "tags"),          # at the key
    ("a: 1\n---\nb: 2\n", 3, 1, "one YAML document"),
    ("a: b: c\n", 1, 7, "two colons"),
    ("a:\n  - x\n - y\n", 3, 1, "indentation"),
    ("[" * 100 + "]" * 100, 1, 65, "nests too deeply"),
    ("{a: 1\n", None, None, "YAML syntax error"),
    ("k: \"abc\n", None, None, "YAML syntax error"),
])
def test_refused(load, text, line, col, msg):
    r = load(text)
    assert not r["ok"]
    assert msg in r["error"]["message"]
    if line is not None:
        assert _where(r["error"]) == (line, col)
    else:
        assert r["error"]["line"] >= 1


def test_duplicate_key_reports_both_lines(load):
    r = load("rules:\n  - id: A\n    where: x\n    id: B\n")
    assert not r["ok"]
    e = r["error"]
    assert e["message"] == "duplicate key 'id' (first defined on line 2)"
    assert _where(e) == (4, 5)
    assert _where(e["related"]) == (2, 5)


def test_duplicate_key_in_flow_map(load):
    r = load("k: {a: 1, a: 2}\n")
    assert not r["ok"]
    assert (_where(r["error"]), _where(r["error"]["related"])) == ((1, 11), (1, 5))


def test_nesting_limit_edge(load):
    assert load("[" * 64 + "]" * 64)["ok"]
    assert not load("[" * 65 + "]" * 65)["ok"]


def test_very_deep_input_does_not_crash(load):
    r = load("[" * 100000 + "]" * 100000)
    assert not r["ok"]


# ------------------------------------------------------------- aliases ----

def test_aliases_resolved(load):
    m = _members(load("b: &x {k: 1}\nu: *x\nm:\n  <<: *x\n  j: 2\n"))
    assert [x["key"] for x in m["u"]["members"]] == ["k"]
    assert [x["key"] for x in m["m"]["members"]] == ["k", "j"]


def test_scalar_alias(load):
    m = _members(load("a: &v 0x10\nb: *v\n"))
    assert (m["b"]["kind"], m["b"]["value"]) == ("int", 16)


def test_alias_bomb_refused(load):
    # "Billion laughs": each level is nine aliases to the previous one.
    lines = ["a: &a [1,1,1,1,1,1,1,1,1]"]
    for prev, cur in zip("abcdefgh", "bcdefghi"):
        lines.append("%s: &%s [%s]" % (cur, cur, ",".join(["*" + prev] * 9)))
    assert load("\n".join(lines[:5]) + "\n")["ok"]               # ~66k nodes
    r = load("\n".join(lines) + "\n")                             # ~430M nodes
    assert not r["ok"]
    assert "aliases expand this file to more than 100000 nodes" in r["error"]["message"]


def test_undefined_alias(load):
    r = load("a: *nope\n")
    assert not r["ok"]
    assert "YAML syntax error" in r["error"]["message"]


def test_error_after_error_leaves_the_layer_usable(load):
    assert not load("a: b: c\n")["ok"]
    assert not load("[" * 1000)["ok"]
    assert _members(load("a: 1\n"))["a"]["value"] == 1


# ---------------------------------------------------------- real files ----

def test_real_files_load(load):
    import glob
    import os
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    files = sorted(glob.glob(os.path.join(root, "ast", "*.yaml")))
    assert files
    for f in files:
        with open(f, encoding="utf-8") as fp:
            assert load(fp.read(), os.path.basename(f))["ok"], f
