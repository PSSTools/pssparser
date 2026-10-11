"""
CEL expression positions in a rule file (lint-core-plan.md C2.2, risk R-3).

A CEL error offset is an offset into the scalar's decoded value; the rule
author needs a line and column in the YAML file. Every string scalar carries
a source map (src/lint/yaml/SourceMap.cpp) from value bytes to source bytes,
through quotes, escapes, folding and block indentation.

Two private hooks: `yaml_source_maps(name, text)` returns each string
scalar's value and map; `yaml_cel_parse(name, text, key)` parses every value
under `key` as CEL and reports syntax errors at their rule-file position,
which is what the rule loader (C4.1) does.
"""
import random

import pytest


@pytest.fixture(scope="module")
def hooks(factory):
    return factory._lintTestHooks()


def _cel_errors(hooks, text, key="where"):
    r = hooks.yaml_cel_parse("r.yaml", text, key)
    assert r["ok"], r
    return [(x["line"], x["col"]) if not x["ok"] else None for x in r["results"]]


# The same expression error -- the `=` of `a = b`, value offset 2 -- in
# every scalar style.
@pytest.mark.parametrize("text,where", [
    ("where: a = b\n", (1, 10)),
    ("where: 'a = b'\n", (1, 11)),
    ('where: "a = b"\n', (1, 11)),
    ("where: |\n  a = b\n", (2, 5)),
    ("where: >\n  a = b\n", (2, 5)),
    ("where: |-\n    a = b\n", (2, 7)),
    ("rules:\n  - id: X\n    where: |\n      a = b\n", (4, 9)),
    ("rules:\n- {id: X, where: \"a = b\"}\n", (2, 21)),
])
def test_same_error_in_every_style(hooks, text, where):
    assert _cel_errors(hooks, text) == [where]


@pytest.mark.parametrize("text,where", [
    # third line of a folded block: the folds before it are spaces in the value
    ("where: >\n  a &&\n  b &&\n  c = d\n", (4, 5)),
    # literal block: more-indented lines keep their extra spaces
    ("where: |\n  a &&\n    b &&\n  c = d\n", (4, 5)),
    # a blank first line in the block
    ("where: |\n\n  a = b\n", (3, 5)),
    # an explicit indentation indicator
    ("where: |1\n   a = b\n", (2, 6)),       # value "  a = b": two spaces kept
    # multi-line plain scalar
    ("where: a &&\n  b = c\n", (2, 5)),
    # quoted, folded over lines, with escapes before the error
    ('where: "\'\\t\\u00e9\' == x &&\n  b = c"\n', (2, 5)),
    ("where: 'x == ''a'' &&\n  b = c'\n", (2, 5)),
    # an escaped line break in a double-quoted scalar
    ('where: "a &&\\\n    b = c"\n', (2, 7)),
    # error at the end of the expression: just past its last source byte
    ("where: a +\n", (1, 11)),
    ("where: |\n  a +\n", (2, 6)),
    ('where: "a +"\n', (1, 12)),
])
def test_positions(hooks, text, where):
    assert _cel_errors(hooks, text) == [where]


def test_valid_expressions_report_nothing(hooks):
    assert _cel_errors(hooks, "a:\n  where: x\nb:\n  where: |\n    y > 1\n") == [None, None]


def test_columns_are_bytes(hooks):
    # Before the error, a two-byte character: columns count bytes, as every
    # PSS marker does.
    assert _cel_errors(hooks, "where: \"'é' + = 1\"\n") == [(1, 16)]


# ------------------------------------------------------------ the maps ----

def _check_map(text, s):
    """Each value byte maps to the source byte it came from: the same byte,
    or for a byte the style rewrote, a plausible origin (a backslash, a
    folded break, a quote pair)."""
    src = text.encode("utf-8")
    val = s["value"].encode("utf-8")
    m = s["map"]
    assert len(m) == len(val) + 1
    assert m == sorted(m), "the map is monotonic"
    for i, b in enumerate(val):
        o = src[m[i]]
        if o == b:
            continue
        ch = bytes([b])
        if o == ord("\\"):
            continue                    # an escape, charged to its backslash
        if ch == b" " and o in b"\r\n":
            continue                    # a folded line break
        if ch == b"\n" and o in b"\r\n":
            continue
        raise AssertionError("value byte %d %r maps to source %d %r in %r"
                             % (i, ch, m[i], bytes([o]), text))


@pytest.mark.parametrize("text", [
    "k: plain\n", "k: 'a''b'\n", 'k: "a\\"b\\\\c\\x41\\U0001F600"\n',
    "k: |\n  a\n\n  b\n", "k: |+\n  a\n\n", "k: >\n  a\n  b\n\n  c\n    d\n  e\n",
    "k: >2-\n   a\n   b\n", "- |\n  x\n- 'y'\n- \"z\"\n", "k: \"a\n\n  b\"\n",
    "k: a\n  b\n  c\n",
])
def test_maps_are_exact(hooks, text):
    r = hooks.yaml_source_maps("r.yaml", text)
    assert r["ok"], r
    for s in r["scalars"]:
        assert s["exact"], (text, s)
        _check_map(text, s)


def test_block_scalar_mark_is_its_first_content_byte(hooks):
    # rapidyaml reports column 0 for a block whose body opens with a blank
    # line; the mark is recomputed from the map.
    s = hooks.yaml_source_maps("r.yaml", "k: |\n\n  a\n")["scalars"][0]
    assert (s["line"], s["col"]) == (3, 3)


def test_real_files_map_exactly(hooks):
    import glob
    import os
    root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    files = sorted(glob.glob(os.path.join(root, "ast", "*.yaml")))
    files += sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml")))
    n = 0
    for f in files:
        with open(f, encoding="utf-8") as fp:
            text = fp.read()
        r = hooks.yaml_source_maps(f, text)
        assert r["ok"], f
        for s in r["scalars"]:
            assert s["exact"], (f, s["line"], s["value"][:40])
            _check_map(text, s)
            n += 1
    assert n > 500


def test_generated_scalars_map_exactly(hooks):
    # Random strings written by PyYAML in each style it can choose, read
    # back: every map exact and consistent with the source.
    yaml = pytest.importorskip("yaml")
    rnd = random.Random(20261010)
    alphabet = "ab =&|()'\"\\\t\né☃#:-"
    styles = [None, "'", '"', "|", ">"]
    n = 0
    for _ in range(1500):
        s = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(1, 30)))
        style = rnd.choice(styles)
        text = yaml.dump({"k": s, "j": [s]}, default_style=style, allow_unicode=True,
                         width=rnd.choice([20, 80]))
        r = hooks.yaml_source_maps("r.yaml", text)
        assert r["ok"], (text, r)
        for sc in r["scalars"]:
            if sc["value"] != s:
                continue                # a key, written in the same style
            assert sc["exact"], (text, sc)
            _check_map(text, sc)
            n += 1
    assert n > 1000
