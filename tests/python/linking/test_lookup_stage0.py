"""Name-lookup fixes that keep the current structure (symbol-resolution plan
WS6.1, "stage 0").

Root causes and LRM references: ``docs/design/symbol-resolution/D-namespaces.md``
(F18, F20, F21, F23, ND-1, ND-2) and ``A-crashes.md`` (A-N2).
"""
import pytest

from ..test_helpers import assert_marker, assert_parse_ok, parse_collect, find_markers


def _codes(code):
    _, markers = parse_collect(code)
    return [(m.get("code"), m["message"]) for m in markers if m.get("severity") == "error"]


# ---------------------------------------------------------------------------
# ND-1 -- an import path resolves from where the import is written
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [
    # sibling nested package, same package statement
    """
package P {
  package bar { struct b {} }
  import bar::*;
  struct t { b f; }
}
""",
    # ... and from a second statement of the same package
    """
package P {
  package bar { struct b {} }
}
package P {
  import bar::*;
  struct t { b f; }
}
""",
])
def test_relative_import_path(code):
    assert_parse_ok(code)


# ---------------------------------------------------------------------------
# F23 -- a root-level `extend` sees root-level imports
# ---------------------------------------------------------------------------

def test_root_level_extend_uses_root_imports():
    assert_parse_ok("""
package p { struct s { rand int a; } }
import p::*;
extend struct s { constraint a > 0; }
""")


# ---------------------------------------------------------------------------
# F20 / ND-2 / A-N2 -- `::x` is the global package only
# ---------------------------------------------------------------------------

def test_global_prefix_skips_imports():
    """LRM Ex. 258: `::s` is the global `s`, not the imported `p1::s`.

    Only the global `s` has `g`, so `g == 1` checks which one was bound.
    """
    assert_parse_ok("""
const int K = 1;
package p1 { const int K = 2; struct s {} }
struct s { rand int g; }
package top {
  import p1::*;
  struct my_s : ::s { rand int x; constraint x == ::K; constraint g == 1; }
}
""")


def test_global_prefix_field_type_binds_the_global_type():
    assert_marker("""
package p1 { struct s { rand int a; } }
struct s { rand int b; }
package top {
  import p1::*;
  struct my_s { rand ::s v2; constraint v2.a == 1; }
}
""", marker_id="PSS002", text="elem a")


@pytest.mark.parametrize("decl,marker_id,name", [
    ("rand ::s v;", "PSS002", "unknown type 's'"),
    ("rand int x; constraint x == ::NOPE;", "PSS004", "NOPE"),
])
def test_global_prefix_does_not_fall_back_to_an_import(decl, marker_id, name):
    """`::s` with no global `s` used to bind the imported one; `::NOPE` was silent."""
    assert_marker("""
package p1 { struct s { rand int a; } const int NOPE = 1; }
package top {
  import p1::*;
  struct my_s { %s }
}
""" % decl, marker_id=marker_id, text=name)


def test_global_function_calls():
    """A-N2: `::p::f()` resolves `p` globally, then `f` in it."""
    assert_parse_ok("""
package p { function int f(int a) { return a; } }
function int g(int a) { return a; }
component pss_top {
  exec init_down { int x = ::p::f(1); int y = ::g(2); }
}
""")


@pytest.mark.parametrize("call,text", [
    ("::nosuch(3)", "unknown identifier 'nosuch' in the global package"),
    ("::p::nosuch2(4)", "'p' has no member named 'nosuch2'"),
])
def test_global_function_call_misses_are_reported(call, text):
    assert_marker("""
package p { function int f(int a) { return a; } }
component pss_top { exec init_down { int x = %s; } }
""" % call, marker_id="PSS002", text=text)


# ---------------------------------------------------------------------------
# F21 -- a qualified step searches supertypes
# ---------------------------------------------------------------------------

def test_qualified_step_finds_inherited_action():
    """LRM Ex. 242: `dma_der_c::xfer_a` names the action inherited from the base."""
    assert_parse_ok("""
component dma_base_c { action xfer_a { rand int i; } }
component dma_der_c : dma_base_c { }
component pss_top {
  dma_der_c d;
  action T { activity { do dma_der_c::xfer_a; } }
}
""")


def test_qualified_step_does_not_search_derived_types():
    assert_marker("""
component dma_base_c { }
component dma_der_c : dma_base_c { action mult_xfer_a { } }
component pss_top {
  dma_der_c d;
  action T { activity { do dma_base_c::mult_xfer_a; } }
}
""", marker_id="PSS002", text="mult_xfer_a")


def test_qualified_step_finds_inherited_static_const():
    assert_parse_ok("""
component base_c { static const int K = 3; }
component der_c : base_c { }
component pss_top {
  action A { rand int x; constraint x < der_c::K; }
}
""")


# ---------------------------------------------------------------------------
# F18 -- explicit beats wildcard; one declaration by two routes is one match
# ---------------------------------------------------------------------------

def test_explicit_import_beats_wildcard():
    """18.1.3 (CH17/p26b): lib2::s, imported explicitly, wins over lib1::*."""
    assert_parse_ok("""
package lib1 { struct s { rand int a; } }
package lib2 { struct s { rand int b; } }
component pss_top {
  import lib1::*;
  import lib2::s;
  action A { rand s v; constraint v.b == 1; }
}
""")


def test_same_declaration_by_two_routes_is_not_ambiguous():
    assert_parse_ok("""
package lib1 { struct s { rand int a; } }
component pss_top {
  import lib1::*;
  import lib1::s;
  action A { rand s v; constraint v.a == 1; }
}
""")


@pytest.mark.parametrize("imports,kind", [
    ("import lib1::s; import lib2::s;", "explicit"),
    ("import lib1::*; import lib2::*;", "wildcard"),
])
def test_ambiguous_import_is_reported_once(imports, kind):
    """CH17/p26: ambiguous, so nothing is imported -- and no cascade after it."""
    errs = _codes("""
package lib1 { struct s { } }
package lib2 { struct s { } }
package p {
  %s
  struct t { s f; }
}
""" % imports)
    assert errs == [("PSS017",
        "ambiguous reference to 's': more than one %s import provides it, "
        "so none does (18.1.3); qualify the name" % kind)], errs
