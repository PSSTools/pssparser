"""
Tests for calling something that is not a function (PSS006, known issue P3-X6b).

``TaskResolveRefs::checkCallArity`` reaches a path element that carries an
argument list but whose target is not a function scope, and reports it.  The
test is broad: anything that resolved to a non-function is reported, including
a type used as a call (``S(1)``).  Only an unresolved target is left alone,
because that has already been diagnosed where the name was written.

The message names the callee but *not* what it is instead -- ``'f' is not a
function``, not ``...; it is a field``.  The finer wording lives in
``TaskCheckCallArgs::valueKind``, which is no longer wired into path
resolution; the two checkers were merged onto this one so that a bad call
draws one error rather than two.  The silent cases at the bottom pin the
boundary.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


# ---------------------------------------------------------------------------
# The three kinds of value that are reported
# ---------------------------------------------------------------------------

def test_calling_a_field():
    pss = """
    component pss_top {
        int f;
        exec init_up { f(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="'f' is not a function")


def test_calling_a_local_variable():
    pss = """
    component pss_top {
        exec init_up { int v; v(); }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="'v' is not a function")


def test_calling_a_function_parameter():
    pss = """
    package p {
        function void h(int x) { x(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="'x' is not a function")


def test_calling_a_struct_member():
    """The check runs on every path element, not just the root."""
    pss = """
    package p {
        struct s { int f; }
        component pss_top {
            exec init_up { s v; v.f(1); }
        }
    }
    """
    assert_marker(pss, marker_id="PSS006",
                  text="'f' is not a function")


def test_calling_a_component_instance():
    pss = """
    component c { }
    component pss_top {
        c inst;
        exec init_up { inst(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="'inst' is not a function")


def test_calling_a_string_variable():
    """A string field has methods, but is not itself callable."""
    pss = """
    component pss_top {
        string s;
        exec init_up { s(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="'s' is not a function")


def test_calling_a_collection_variable():
    pss = """
    component pss_top {
        exec init_up { list<int> l; l(1); }
    }
    """
    assert_marker(pss, marker_id="PSS006", text="'l' is not a function")


# ---------------------------------------------------------------------------
# Real calls stay silent -- especially the ones that resolve unusually
# ---------------------------------------------------------------------------

def test_plain_function_call_is_silent():
    pss = """
    package p {
        function void g(int a);
        component pss_top { exec init_up { g(1); } }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_method_call_is_silent():
    pss = """
    component c { function void g(); }
    component pss_top {
        c inst;
        exec init_up { inst.g(); }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_string_method_call_is_silent():
    """String methods resolve through a name allow-list (P3-X6d), not here."""
    pss = """
    component pss_top {
        exec init_up { string s = "ab"; int n = s.size(); }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_collection_method_call_is_silent():
    pss = """
    component pss_top {
        exec init_up { list<int> l; l.push_back(1); }
    }
    """
    assert_no_marker(pss, marker_id="PSS006")


def test_core_library_call_is_silent():
    pss = """
    component pss_top { exec init_up { print("hi"); } }
    """
    assert_no_marker(pss, severity="error")
