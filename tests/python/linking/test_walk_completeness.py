"""Reference slots the resolver never walked (symbol-resolution plan WS3.3).

Each slot was silent: an undefined name there linked clean, because the
resolver's hand-written visitor for the enclosing node skipped the field.
Every test puts an undefined name in one slot and expects PSS002 on that name,
next to the legal form that must still link.  Root causes are in
``docs/design/symbol-resolution/F-reference-coverage.md`` §5 and
``E-expressions-templates.md`` (F14).
"""
import pytest

from ..test_helpers import assert_marker, assert_parse_ok, parse_collect, find_markers


def _reported(code, name, marker_id="PSS002"):
    m = assert_marker(code, marker_id=marker_id, text="'%s'" % name)
    return m


# ---------------------------------------------------------------------------
# F-N9 -- function parameter default values
# ---------------------------------------------------------------------------

def test_function_parameter_default_is_resolved():
    _reported("""
component pss_top { function void g(int p = NOSUCH) { } }
""", "NOSUCH")


def test_function_parameter_default_links():
    assert_parse_ok("""
component pss_top {
  static const int K = 3;
  function void g(int p = K) { }
}
""")


# ---------------------------------------------------------------------------
# F-N7 -- procedural `repeat` count
# ---------------------------------------------------------------------------

def test_procedural_repeat_count_is_resolved():
    _reported("""
component pss_top { exec init_up { repeat (NOSUCH) { } } }
""", "NOSUCH")


def test_procedural_repeat_index_is_not_visible_in_its_own_count():
    """`i` is declared by the loop; the count is evaluated outside it."""
    _reported("""
component pss_top { exec init_up { repeat (i : i) { } } }
""", "i")


def test_procedural_repeat_count_links():
    assert_parse_ok("""
component pss_top { int n; exec init_up { repeat (i : n) { n = i; } } }
""")


# ---------------------------------------------------------------------------
# F-N5 -- bit-slice bounds, on every path form
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("expr", [
    "x[NOSUCH:0]",
    "x[7:NOSUCH]",
    "pss_top::K[NOSUCH:0]",
])
def test_bit_slice_bounds_are_resolved(expr):
    _reported("""
component pss_top {
  static const bit[8] K = 3;
  action A { rand bit[8] x; constraint { %s == 1; } }
}
""" % expr, "NOSUCH")


def test_bit_slice_bounds_link():
    assert_parse_ok("""
component pss_top {
  static const int HI = 7;
  action A { rand bit[8] x; constraint { x[HI:0] == 1; } }
}
""")


def test_bit_slice_keeps_both_bounds():
    """`x[7:0]` was built as `x[7:7]`: the builder took both bounds from the msb."""
    import pssparser.ast as ast_mod
    root = assert_parse_ok("""
component pss_top {
  action A { rand bit[8] x; constraint { x[7:0] == 1; } }
}
""")
    bounds = []

    class _W(ast_mod.VisitorBase):
        def visitExprBitSlice(self, i):
            bounds.append((i.getLhs().getValue(), i.getRhs().getValue()))

    root.accept(_W())
    assert bounds and set(bounds) == {(7, 0)}, bounds


# ---------------------------------------------------------------------------
# Traversal subscripts and initializer values
# ---------------------------------------------------------------------------

def test_traversal_subscript_is_resolved():
    _reported("""
component pss_top {
  action A { }
  action B { A a_arr[2]; activity { a_arr[NOSUCH]; } }
}
""", "NOSUCH")


@pytest.mark.parametrize("stmt", [
    "a2 {.x = NOSUCH};",
    "do A {.x = NOSUCH};",
])
def test_traversal_initializer_value_is_resolved(stmt):
    _reported("""
component pss_top {
  action A { rand bit[4] x; }
  action B { A a2; activity { %s } }
}
""" % stmt, "NOSUCH")


def test_traversal_initializer_value_links():
    assert_parse_ok("""
component pss_top {
  action A { rand bit[4] x; }
  action B { A a2; rand bit[4] v; activity { a2 {.x = v}; do A {.x = v}; } }
}
""")


# ---------------------------------------------------------------------------
# U6 -- `import C function name;`
# ---------------------------------------------------------------------------

def test_import_function_by_name_links():
    """LRM Ex. 297 style: declare, then import by name."""
    assert_parse_ok("""
component pss_top {
  function void f(int a);
  import target C function f;
}
""")


@pytest.mark.parametrize("decl,imp,marker_id,text", [
    ("", "import C function nosuch_f;", "PSS002", "unknown function 'nosuch_f'"),
    ("int notfn;", "import C function notfn;", "PSS006", "'notfn' is not a function"),
    ("function void d() { }", "import C function d;", "PSS003", "cannot be both defined and imported"),
    ("function void g(); import C function g;", "import solve function g;", "PSS003", "already imported"),
])
def test_import_function_by_name_is_checked(decl, imp, marker_id, text):
    assert_marker("""
component pss_top {
  %s
  %s
}
""" % (decl, imp), marker_id=marker_id, text=text)


# ---------------------------------------------------------------------------
# F-N4 -- an enum's base type
# ---------------------------------------------------------------------------

def test_enum_base_type_is_resolved():
    _reported("""
enum e : nosuch_t { A, B }
component pss_top { e f; }
""", "nosuch_t")


def test_enum_base_type_resolves_in_the_enclosing_scope():
    assert_parse_ok("""
package p {
  typedef bit[8] byte_t;
  enum e : byte_t { A, B }
}
""")


# ---------------------------------------------------------------------------
# F14 (minimal) -- generic-constraint parameter types
# ---------------------------------------------------------------------------

def test_generic_constraint_parameter_type_links():
    """Used to be the internal "type 'P' is never resolved" on legal code."""
    root, markers = parse_collect("""
struct P { rand bit[8] a; }
struct S {
  constraint g(P p, bit[8] v) { p.a > v; }
  rand P pp; rand bit[8] q;
  constraint g(pp, q);
}
""")
    assert not find_markers(markers, severity="error"), markers


def test_generic_constraint_unknown_parameter_type_is_reported():
    _reported("""
struct S {
  constraint g(NoSuchType p) { p > 0; }
  rand int q;
  constraint g(q);
}
""", "NoSuchType")
