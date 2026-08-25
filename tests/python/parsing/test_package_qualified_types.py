"""
Tests for package-qualified type identifiers (known issue P2-A5a).

`pkg::Type` never resolved: `TaskResolveRef::visitTypeIdentifier` walks the
elements after the root through `TaskResolveFieldRef`, whose `visitSymbolScope`
was an empty stub.  A package is an ordinary `ISymbolScope`, so the lookup
silently produced nothing and the reference was left unresolved -- with no
marker anywhere except an annotation, which reported it as ``PSS101``.

The silence is why this went unnoticed for so long, so the tests below check
both halves: that a good reference resolves, *and* that a bad one is now
reported rather than ignored.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


# ---------------------------------------------------------------------------
# A qualified reference resolves
# ---------------------------------------------------------------------------

def test_qualified_struct():
    pss = """
    package p { struct S { int a; } }
    component pss_top { p::S s; }
    """
    assert_no_marker(pss, severity="error")


def test_qualified_struct_member_resolves_through_it():
    """The reference is not merely accepted -- it yields a usable scope."""
    pss = """
    package p { struct S { int a; } }
    component pss_top {
        p::S s;
        exec init_up { int x = s.a; }
    }
    """
    assert_no_marker(pss, severity="error")


def test_nested_package():
    pss = """
    package p::q { struct S { int a; } }
    component pss_top { p::q::S s; }
    """
    assert_no_marker(pss, severity="error")


def test_qualified_enum_type():
    pss = """
    package p { enum E { A, B } }
    component pss_top { p::E e; }
    """
    assert_no_marker(pss, severity="error")


def test_qualified_templated_type():
    pss = """
    package p { struct S<type T> { int a; } }
    component pss_top { p::S<int> s; }
    """
    assert_no_marker(pss, severity="error")


def test_qualified_super_type():
    pss = """
    package p { struct B { int a; } }
    package q { struct D : p::B { int b; } }
    """
    assert_no_marker(pss, severity="error")


def test_qualified_function_parameter_type():
    pss = """
    package p { struct S { int a; } }
    package q { function void g(p::S s); }
    """
    assert_no_marker(pss, severity="error")


# ---------------------------------------------------------------------------
# A bad qualified reference is now reported instead of ignored
# ---------------------------------------------------------------------------

def test_unknown_member_of_a_package_is_reported():
    pss = """
    package p { struct S { int a; } }
    component pss_top { p::Nope s; }
    """
    assert_marker(pss, marker_id="PSS002",
                  text="unknown type 'Nope' in 'p'")


def test_the_message_names_the_whole_qualifying_prefix():
    """`in 'p'` would point at the wrong scope for a nested package."""
    pss = """
    package p::q { struct S { int a; } }
    component pss_top { p::q::Nope s; }
    """
    assert_marker(pss, marker_id="PSS002",
                  text="unknown type 'Nope' in 'p::q'")


def test_unknown_root_package_is_still_reported_as_before():
    pss = """
    component pss_top { nosuchpkg::S s; }
    """
    assert_marker(pss, marker_id="PSS002", text="unknown type 'nosuchpkg'")
