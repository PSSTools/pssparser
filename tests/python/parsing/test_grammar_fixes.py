"""Grammar false positives on legal code (symbol-resolution plan WS11).

Root causes and fix rationale: ``docs/design/symbol-resolution/H-grammar.md``.
Each fix is pinned by the LRM form it admits, plus a near miss that must still
be rejected -- by the grammar where the shape is wrong, by the linker where
only the meaning is.
"""
import pytest

from ..test_helpers import assert_marker, assert_parse_ok, parse_collect, find_markers


# ---------------------------------------------------------------------------
# 11.2 -- F2: enum domains take open ranges (7.5.2), and are no longer dropped
# (F-N3)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("domain", [
    "[..MODE_B]",
    "[MODE_B..]",
    "[MODE_A..MODE_C]",
    "[MODE_A, MODE_C]",
    "[MODE_A, MODE_B..]",
])
def test_enum_domain_forms_are_accepted(domain):
    assert_parse_ok("""
enum config_modes_e { MODE_A, MODE_B, MODE_C }
component pss_top {
  action A { rand config_modes_e in %s mode; }
}
""" % domain)


def test_enum_domain_items_resolve_in_the_enum():
    """8.4.3: the domain expects the enum, so `pkg::e_t in [A]` needs no import."""
    assert_parse_ok("""
package p { enum mode_e { MODE_A, MODE_B } }
component pss_top {
  action A { rand p::mode_e in [..MODE_B] ub; }
}
""")


@pytest.mark.parametrize("domain", ["[NOSUCH]", "[NOSUCH..]", "[..NOSUCH]", "[MODE_A..NOSUCH]"])
def test_enum_domain_unknown_item_is_reported(domain):
    """The domain used to be dropped, so a wrong name in it was never seen."""
    assert_marker("""
enum mode_e { MODE_A, MODE_B }
component pss_top { action A { rand mode_e in %s m; } }
""" % domain, marker_id="PSS002", text="'NOSUCH'")


# ---------------------------------------------------------------------------
# 11.3 -- F3: a method call on a string or aggregate literal (Ex. 10)
# ---------------------------------------------------------------------------

def test_method_call_on_string_literal():
    """LRM Ex. 10, completed with a component scope."""
    assert_parse_ok("""
component pss_top {
  exec init_down {
    list<string> parts = "abc123abcabc456".split("abc");
    int n = "a,b".split(",").size();
    string u = "abc".upper().lower();
  }
}
""")


def test_method_call_on_aggregate_literal():
    assert_parse_ok("""
component pss_top { exec init_down { int m = {1, 2, 3}.size(); } }
""")


@pytest.mark.parametrize("expr,marker_id,text", [
    ('"abc".nosuch()', "PSS002", "unknown method 'nosuch' on string"),
    ('"abc".find()', "PSS006", "expects 1 to 2 arguments"),
    ('"abc".size', "PSS006", "'size' is a method"),
    ('{1, 2}.frob()', "PSS002", "unknown method 'frob'"),
    ('"a,b".split(",").nosuch()', "PSS002", "unknown method 'nosuch'"),
])
def test_method_call_on_literal_is_checked(expr, marker_id, text):
    """The call is checked against the built-in `string` prototypes, as on a field."""
    assert_marker("""
component pss_top { exec init_down { int x = %s; } }
""" % expr, marker_id=marker_id, text=text)


def test_bool_literal_takes_no_method():
    """Only string and aggregate literals have methods; `true.x()` stays a syntax error."""
    _, markers = parse_collect("""
component pss_top { exec init_down { bool b = true.x(); } }
""")
    assert find_markers(markers, severity="error")


# ---------------------------------------------------------------------------
# 11.4 -- F26: a labelled traversal in a monitor activity (Ex. 236)
# ---------------------------------------------------------------------------

def test_labelled_do_in_monitor_activity():
    assert_parse_ok("""
component pss_top {
  action write { }
  action read { }
  monitor m {
    activity {
      w: do write;
      r: do read;
      do write;
    }
  }
}
""")


def test_labelled_handle_traversal_in_monitor_activity():
    assert_parse_ok("""
component pss_top {
  action write { }
  monitor m {
    write wr;
    activity {
      w: wr;
    }
  }
}
""")
