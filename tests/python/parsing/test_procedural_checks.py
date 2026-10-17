"""
Procedural-statement rules checked after resolution (TaskCheckProcedural;
pssc's front-end checks F8, F9, F10, W40, F16, F17, F18 and F21).

- PSS121: a constant, or a part of one, on the left of an assignment (7.1);
  a `const` parameter changed in its function (20.2.3).
- PSS006: a constant of aggregate type passed to a non-const parameter of a
  PSS function (20.2.3, Example 291) -- beside the aggregate-literal form.
- PSS122: the sub-string operator on the left of an assignment (7.6.2).
- PSS123: a foreach's index or iterator changed in its body, or its
  collection replaced or changed by a method (20.7.8 g). An element's value
  is not the collection's "contents": Example 291 assigns `dst[i]` in
  `foreach (dst[i])`.
- PSS124: `break`/`continue` outside a loop (20.7.11 b).
- PSS125: a second `default` branch in a match (20.7.10 f, 11.4.6 f).
- PSS007: `return <value>;` in an exec block (20.7.5, ruling R21).

Every illegal case has a legal neighbour that must stay clean: most of these
are about what a name refers to, and a false positive on a legal model is
worse than the gap.
"""
import pytest

import pssparser

from ..test_helpers import _assign_codes


def codes(src):
    """(line, code) of every marker; `src` is one file."""
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        markers = p.markers
    except Exception as e:
        markers = getattr(e, "markers", None)
        if markers is None:
            raise
    return [(m["line"], m.get("code")) for m in _assign_codes(markers)]


def messages(src):
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        markers = p.markers
    except Exception as e:
        markers = e.markers
    return [(m["line"], m["col"], m.get("code"), m["message"])
            for m in _assign_codes(markers)]


def comp(body, pre=""):
    """A model whose root component holds `body`, line 4 onward."""
    return "import std_pkg::*;\n%s\ncomponent pss_top {\n%s\n}\n" % (pre, body)


# ===========================================================================
# PSS121 -- constants and const parameters (F8, F10)
# ===========================================================================

F8_DECLS = """
  struct p_s { int x; }
  static const int C = 5;
  static const array<bit[8], 3> TBL = {5, 6, 7};
  static const p_s P = {.x = 1};
"""


@pytest.mark.parametrize("stmt", [
    "C = 2;",
    "C += 2;",
    "TBL[0] = 1;",
    "P.x = 2;",
    "P = {.x = 3};",
    "pss_top::C = 2;",
])
def test_assigning_a_constant(stmt):
    src = comp(F8_DECLS + "  exec init_down { %s }" % stmt)
    assert codes(src) == [(9, "PSS121")]


def test_assigning_a_package_constant():
    src = ("package k { const int K = 1; }\n"
           "component pss_top {\n"
           "  exec init_down { k::K = 2; }\n"
           "}\n")
    assert codes(src) == [(3, "PSS121")]


def test_the_constant_is_named_where_it_is_written():
    src = comp(F8_DECLS + "  target function void run() { TBL[1] = 1; }")
    [(line, col, code, msg)] = messages(src)
    assert (line, col, code) == (9, 32, "PSS121")
    assert msg == ("an element or member of constant 'TBL' cannot be assigned: "
                   "a constant's elements are constants too (LRM 7.1)")


@pytest.mark.parametrize("stmt", [
    # Reading a constant, and writing what it initialized.
    "int y = C; y = TBL[1]; y = P.x;",
    # A local of the constant's name hides it (18.3).
    "int C; C = 2;",
    # A non-constant field of the same struct type.
    "p_s q; q.x = 2; q = P;",
])
def test_legal_neighbours_of_constant_writes(stmt):
    src = comp(F8_DECLS + "  exec init_down { %s }" % stmt)
    assert codes(src) == []


@pytest.mark.parametrize("fn,line_code", [
    ("target function int f(const int x) { x = 3; return x; }", (4, "PSS121")),
    ("function void f(const p_s s) { s.a = 1; }", (4, "PSS121")),
    ("function void f(const array<int, 2> a) { a[0] = 1; }", (4, "PSS121")),
])
def test_changing_a_const_parameter(fn, line_code):
    assert codes(comp(fn, "struct p_s { int a; }")) == [line_code]


@pytest.mark.parametrize("fn", [
    "target function int f(const int x) { int y = x; return y; }",
    "target function int f(int x) { x = 3; return x; }",
    "function void f(p_s s) { s.a = 1; }",
])
def test_legal_neighbours_of_const_parameters(fn):
    assert codes(comp(fn, "struct p_s { int a; }")) == []


# ===========================================================================
# PSS006 -- a constant passed to a non-const aggregate parameter (W40)
# ===========================================================================

EX_291 = """
  static const array<int, 3> MY_ARR = {1, 2, 3};
  static const s MY_STRUCT = {.a = 1, .b = 2};
  function void copy_array(const array<int, 3> src, array<int, 3> dst) {
    foreach (dst[i]) { dst[i] = src[i]; }
  }
  function void swap_structs(s s1, s s2) { s tmp = s1; s1 = s2; s2 = tmp; }
  function void take_int(int v) { }
  function void read_s(const s v) { }
  array<int, 3> my_arr;
  s s1, s2;
"""


@pytest.mark.parametrize("call", [
    "copy_array(my_arr, MY_ARR);",          # Example 291
    "swap_structs(s1, MY_STRUCT);",         # Example 291
])
def test_example_291(call):
    src = comp(EX_291 + "  exec init_up { %s }" % call, "struct s { int a, b; }")
    assert codes(src) == [(15, "PSS006")]


@pytest.mark.parametrize("call", [
    "copy_array(MY_ARR, my_arr);",          # Example 291: OK
    "swap_structs(s1, s2);",                # Example 291: OK
    "take_int(MY_STRUCT.a);",               # a scalar is passed by value
    "read_s(MY_STRUCT);",                   # to a const parameter
])
def test_example_291_legal(call):
    src = comp(EX_291 + "  exec init_up { %s }" % call, "struct s { int a, b; }")
    assert codes(src) == []


def test_a_const_parameter_forwarded_to_a_non_const_one():
    src = comp("  function void g(p_s s) { s.a = 1; }\n"
               "  function void h(const p_s s) { g(s); }", "struct p_s { int a; }")
    [(line, _, code, msg)] = messages(src)
    assert (line, code) == (5, "PSS006")
    assert msg == ("argument 1 of 'g' is const parameter 's', so parameter 's' "
                   "must be declared const (LRM 20.2.3)")


def test_a_const_parameter_forwarded_to_a_const_one():
    src = comp("  function void g(const p_s s) { }\n"
               "  function void h(const p_s s) { g(s); }", "struct p_s { int a; }")
    assert codes(src) == []


# ===========================================================================
# PSS122 -- the sub-string operator on the left (F9)
# ===========================================================================

@pytest.mark.parametrize("stmt", [
    's[0] = "x";',
    's[0..1] = "xy";',
    'ss[1][0] = "x";',
])
def test_assigning_a_sub_string(stmt):
    src = comp('  target function void run() { string s = "abc"; '
               'array<string, 2> ss; %s }' % stmt)
    assert codes(src) == [(4, "PSS122")]


@pytest.mark.parametrize("stmt", [
    's = "x";',
    'ss[1] = "x";',
    'string t = s[0..1];',
])
def test_legal_neighbours_of_sub_strings(stmt):
    src = comp('  target function void run() { string s = "abc"; '
               'array<string, 2> ss; %s }' % stmt)
    assert codes(src) == []


# ===========================================================================
# PSS123 -- foreach index, iterator and collection (F17)
# ===========================================================================

FE_PRE = "struct e_s { int a; }"
FE_DECLS = """  target function void run() {
    array<int, 3> w; array<int, 3> w2; list<int> l; array<e_s, 2> es; int x;
    %s
  }"""


@pytest.mark.parametrize("stmt", [
    "foreach (w[i]) { w = w2; }",
    "foreach (w[i]) { i = 2; }",
    "foreach (e : w[i]) { e = 2; }",
    "foreach (e : w[i]) { e += 2; }",
    "foreach (e : es) { e.a = 2; }",
    "foreach (e : l) { l.push_back(1); }",
    "foreach (e : l) { l.clear(); }",
    "foreach (w[i]) { foreach (w2[j]) { i = 1; } }",
    "foreach (w[i]) { if (i == 1) { w = w2; } }",
])
def test_changing_what_a_foreach_iterates(stmt):
    assert codes(comp(FE_DECLS % stmt, FE_PRE)) == [(6, "PSS123")]


@pytest.mark.parametrize("stmt", [
    # An element's value is not the collection's "contents": Example 291
    # assigns `dst[i]` in `foreach (dst[i])` (see test_example_291_legal).
    "foreach (w[i]) { w[i] = 5; }",
    "foreach (w[i]) { w[0] = 5; }",
    "foreach (e : es) { es[0].a = 2; }",
    "foreach (w[i]) { w2[i] = w[i]; }",
    "foreach (e : w[i]) { x = e + i; }",
    "foreach (e : es) { x = e.a; }",
    "foreach (e : l) { int y = e; y = 2; }",
    "foreach (w[i]) { l.push_back(w[i]); }",
    # The loop variable of a nested foreach is the inner loop's own.
    "foreach (w[i]) { foreach (w2[j]) { x = j; } }",
    # After the loop the names are free again.
    "foreach (w[i]) { x = i; } w[0] = 1;",
])
def test_legal_neighbours_of_foreach_writes(stmt):
    assert codes(comp(FE_DECLS % stmt, FE_PRE)) == []


def test_a_component_iterator_reaches_the_component():
    # The iterator is a handle: a field of the component it names is the
    # component's, not the iterator's value.
    src = ("component sub_c { int v; }\n"
           "component pss_top {\n"
           "  sub_c subs[2];\n"
           "  exec init_down { foreach (c : subs) { c.v = 1; } }\n"
           "}\n")
    assert codes(src) == []


# ===========================================================================
# PSS124 -- break/continue outside a loop (F16)
# ===========================================================================

@pytest.mark.parametrize("kw", ["break", "continue"])
def test_break_outside_a_loop(kw):
    src = comp("  target function void run() { int x; if (x == 1) { %s; } }" % kw)
    [(line, col, code, msg)] = messages(src)
    assert (line, code) == (4, "PSS124")
    assert msg.startswith("'%s' may only appear within a loop statement" % kw)


@pytest.mark.parametrize("kw", ["break", "continue"])
def test_break_in_an_exec_outside_a_loop(kw):
    assert codes(comp("  exec init_down { %s; }" % kw)) == [(4, "PSS124")]


@pytest.mark.parametrize("loop", [
    "repeat (3) { if (x == 1) { %s; } }",
    "repeat (i : 3) { %s; }",
    "while (x < 3) { x += 1; %s; }",
    "repeat { x += 1; %s; } while (x < 3);",
    "foreach (w[i]) { match (x) { [1]: %s; default: x = 2; } }",
])
@pytest.mark.parametrize("kw", ["break", "continue"])
def test_break_inside_a_loop(loop, kw):
    src = comp("  target function void run() { int x; array<int, 2> w; %s }"
               % (loop % kw))
    assert codes(src) == []


# ===========================================================================
# PSS125 -- two default branches (F18)
# ===========================================================================

def test_two_defaults_in_a_procedural_match():
    src = comp("  target function void run() { int x, y;\n"
               "    match (x) { [1]: y = 1; default: y = 2;\n"
               "      default: y = 3; } }")
    [(line, col, code, msg)] = messages(src)
    assert (line, col, code) == (6, 16, "PSS125")


def test_one_default_in_a_procedural_match():
    src = comp("  target function void run() { int x, y;\n"
               "    match (x) { [1]: y = 1; default: y = 2; } }")
    assert codes(src) == []


def test_two_defaults_in_an_activity_match():
    src = comp("  action A { }\n"
               "  action B { rand int x;\n"
               "    activity { match (x) { [1]: do A; default: do A;\n"
               "      default: do A; } } }")
    assert codes(src) == [(7, "PSS125")]


# ===========================================================================
# PSS007 -- return with a value in an exec block (F21, ruling R21)
# ===========================================================================

def test_return_with_a_value_in_an_exec():
    [(line, _, code, msg)] = messages(comp("  exec init_down { return 1; }"))
    assert (line, code) == (4, "PSS007")
    assert msg == ("an exec block returns void, so 'return' cannot take a value "
                   "(LRM 20.7.5, ruling R21)")


def test_a_bare_return_in_an_exec():
    assert codes(comp("  exec init_down { int x; if (x == 1) { return; } }")) == []
