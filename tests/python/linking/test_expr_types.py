"""
The front-end expression typer (TaskExprTypeCat::typeOf).

Front-end checks F1, F3, F4, F12, F29 and F30 need the type of an arbitrary
operand -- `a.b`, `a[i]`, `s[i..j]`, a call's result -- where the older
category pass followed only a bare name (known issue P3-X6c). These tests
drive the typer directly, through the private test hook
(ILintTestHooks::exprTypes): every expression a procedural statement holds,
with what the typer says its type is.

`unknown` is the safe answer, and the one a check never reports on; the
cases at the end pin where it must stay unknown.
"""
import pytest

from pssparser import Parser
from pssparser.parser import ParseException
from pssparser.core import Factory


def types_of(src):
    """{name: type} of every initialized local declaration in `src`."""
    return {r["name"]: r["type"] for r in _records(src) if r["kind"] == "init"}


_MODEL = """
import std_pkg::*;
enum col_e { RED, GREEN }
typedef bit[4] nib_t;
struct p_s { int x; bit[8] arr[4]; string s; }
typedef p_s pt;
struct g_s<type T, int N = 2> { T v; array<T, N> a; }
component sub_c { int v; function int g() { return v; } }
component pss_top {
  sub_c subs[3];
  sub_c one;
  p_s ps;
  g_s<string, 3> gs;
  static const int C = 5;
  static const array<bit[8], 3> TBL = {1, 2, 3};
  function p_s mk() { p_s r; return r; }
  function void v() { }
  target function void run(const p_s cp, nib_t n, pt z) {
    int a;
    bit[8] b;
    array<int, 3> w;
    list<string> l;
    map<string, int> m;
    set<int> st;
    string s;
    chandle h;
    float64 f;
    bool q;
    col_e e;
    %s
  }
}
"""

CASES = [
    # Literals (4.6.1): an unbased decimal is an int, a based one unsigned.
    ("16", "int"),
    ("0x10", "bit"),
    ("8'hFF", "bit"),
    ('"abc"', "string"),
    ("true", "bool"),
    ("1.5", "float"),
    ("null", "null"),
    ("{1, 2}", "an aggregate literal"),
    # Names.
    ("a", "int"),
    ("b", "bit"),
    ("q", "bool"),
    ("h", "chandle"),
    ("f", "float"),
    ("e", "enum col_e"),
    ("RED", "enum col_e"),
    ("col_e::GREEN", "enum col_e"),
    ("pss_top::C", "int"),
    ("ps", "struct p_s"),
    ("one", "component sub_c"),
    ("w", "array[3]"),
    ("l", "list"),
    ("m", "map"),
    ("st", "set"),
    # Through typedefs, and parameters.
    ("n", "bit"),
    ("z", "struct p_s"),
    ("cp.x", "int"),
    # Members, subscripts, slices and selects.
    ("ps.x", "int"),
    ("ps.arr", "array[4]"),
    ("ps.arr[1]", "bit"),
    ("ps.s[1]", "string"),
    ("w[0]", "int"),
    ("w[0..1]", "array"),
    ("l[0]", "string"),
    ("m[\"k\"]", "int"),
    ("s[0]", "string"),
    ("s[0..1]", "string"),
    ("a[3]", "bit"),
    ("a[3:0]", "bit"),
    ("TBL[1]", "bit"),
    ("subs", "array[3]"),
    ("subs[1]", "component sub_c"),
    ("subs[1].v", "int"),
    # A specialization binds its parameters.
    ("gs.v", "string"),
    ("gs.a", "array[3]"),
    ("gs.a[0]", "string"),
    # Calls: the return type, then members of it.
    ("mk()", "struct p_s"),
    ("mk().x", "int"),
    ("one.g()", "int"),
    ("v()", "void"),
    ("l.size()", "int"),
    ("s.size()", "int"),
    ("l.pop_back()", "string"),
    ('"x".upper()', "string"),
    ('"a,b".split(",")', "list"),
    # Operators.
    ("a + 1", "int"),
    ("a + b", "bit"),
    ("f + 1", "float"),
    ("a < 1", "bool"),
    ("a == 1", "bool"),
    ("!q", "bool"),
    ("-a", "int"),
    ("~b", "bit"),
    ("&b", "bit"),
    ("a << 2", "int"),
    ("q ? a : 2", "int"),
    ("a in [1..2]", "bool"),
    ("(bit[4])a", "bit"),
    ("(col_e)a", "enum col_e"),
    ("(p_s)ps", "struct p_s"),
]


def _link(src):
    """The linked root and the file's unit. A probe may well be a type error
    (`int t = ps;`): the typer is asked about it all the same."""
    p = Parser()
    p.parses([("t.pss", src)])
    try:
        root = p.link()
    except ParseException:
        root = p._root
    return root, root.getUnit(root.numUnits() - 1)


def _records(src):
    root, unit = _link(src)
    return Factory.inst()._lintTestHooks().expr_types(root, unit)


@pytest.fixture(scope="module")
def typed():
    """{probe name: type}, one model holding every case."""
    body = "\n    ".join(
        "int t%d = %s;" % (k, expr) for k, (expr, _) in enumerate(CASES))
    return {r["name"]: r["type"] for r in _records(_MODEL % body)
            if r["kind"] == "init"}


@pytest.mark.parametrize("k", range(len(CASES)), ids=[c[0] for c in CASES])
def test_type_of(typed, k):
    assert typed["t%d" % k] == CASES[k][1]


def test_the_assignment_sides_are_typed():
    got = [(r["kind"], r["type"]) for r in _records(_MODEL % "ps.x = b; w[1] = a;")
           if r["kind"] in ("lhs", "rhs")]
    assert got == [("lhs", "int"), ("rhs", "bit"), ("lhs", "int"), ("rhs", "int")]


def test_a_foreach_iterator_takes_the_element_type():
    assert types_of(_MODEL % "foreach (it : l[i]) { string t = it; }")["t"] == "string"


@pytest.mark.parametrize("body,name", [
    # A generic's own body: T is not bound there, whatever its default.
    ("struct d_s<type T = int> { T v; exec post_solve { int t = v; } }", "t"),
    ("struct d_s<type T = int> { T v; exec post_solve { int t = v + 1; } }", "t"),
])
def test_unknown_stays_unknown(body, name):
    src = "import std_pkg::*;\n%s\ncomponent pss_top { }\n" % body
    assert types_of(src)[name] == "unknown"
