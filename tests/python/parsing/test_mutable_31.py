"""
Tests for the PSS 3.1 `mutable` qualifier (P3-S3, LRM §9.1.6, Annex B B.8).

``component_data_decl_qualifier ::= static const | mutable | instance``

A component is immutable once its `init_up` exec has run, since it represents
structure. `mutable` marks component data that is *not* structure and may still
change during solve-time execution.

Like `soft`, `mutable` is absent from Table 3 but spelled literally in Annex B;
it is reserved here for the same reason, which is a source break for models
using it as an identifier.

Of §9.1.6's rules, only b) is a parser-enforceable diagnostic (PSS105), and only
half of it -- see test_mutable_on_a_component_field_is_rejected and the note
above test_instance_and_mutable_cannot_both_be_written.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import (  # noqa: E402
    assert_parse_ok, assert_parse_error, assert_marker, assert_no_marker,
)
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []

# FieldAttr::Mutable -- (1 << 8). Mirrored here rather than imported because
# the flags enum is not exposed through the Python bindings as a named value.
_ATTR_MUTABLE = 1 << 8
_ATTR_STATIC = 1 << 4
_ATTR_INSTANCE = 1 << 5


def _field(code, name):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    def walk(node, depth=0):
        if node is None or depth > 20 or not hasattr(node, "numChildren"):
            return None
        for i in range(node.numChildren()):
            child = node.getChild(i)
            getter = getattr(child, "getName", None)
            if getter is not None and hasattr(child, "getAttr"):
                got = getter()
                if got is not None and got.getId() == name:
                    return child
            found = walk(child, depth + 1)
            if found is not None:
                return found
        return None

    for scope in parser._files[1:]:
        found = walk(scope)
        if found is not None:
            return found
    raise AssertionError("no field %r found" % name)


# -- syntax -----------------------------------------------------------------

@pytest.mark.parametrize("decl", [
    "mutable int total_sum;",
    "mutable bool flag;",
    "mutable string name;",
    "mutable int counters[4];",
    "mutable int total_sum = 0;",
])
def test_mutable_component_field_parses(decl):
    assert_parse_ok("component C { %s }" % decl)


def test_mutable_list_of_refs_parses():
    """Example55's second mutable field."""
    assert_parse_ok("""
    component my_comp_c { }
    component pss_top {
        mutable list<ref my_comp_c> used_comps;
    }
    """)


def test_mutable_with_an_access_modifier():
    assert_parse_ok("component C { private mutable int total; }")


def test_mutable_struct_field_parses():
    """§9.1.6 a): the qualifier propagates into an aggregate."""
    assert_parse_ok("""
    struct S { int a; int b; }
    component C { mutable S s; }
    """)


# -- AST shape --------------------------------------------------------------

def test_mutable_sets_the_attribute():
    field = _field("component C { mutable int total; }", "total")
    assert field.getAttr() & _ATTR_MUTABLE


def test_a_plain_field_does_not_carry_the_attribute():
    field = _field("component C { int total; }", "total")
    assert not (field.getAttr() & _ATTR_MUTABLE)


def test_mutable_does_not_imply_static_or_instance():
    """The three qualifiers are alternatives; only one may apply."""
    field = _field("component C { mutable int total; }", "total")
    assert not (field.getAttr() & _ATTR_STATIC)
    assert not (field.getAttr() & _ATTR_INSTANCE)


def test_other_qualifiers_are_unaffected():
    assert _field("component C { instance int a; }", "a").getAttr() & _ATTR_INSTANCE
    assert _field("component C { static const int b = 1; }", "b").getAttr() & _ATTR_STATIC


# -- PSS105: §9.1.6 b) ------------------------------------------------------

def test_mutable_on_a_component_field_is_rejected():
    """
    §9.1.6 b): a component instance is structure. Whether the fields *inside*
    it may change is decided by their own qualifiers, not by one on the
    instance.
    """
    marker = assert_marker("""
    component M { }
    component C { mutable M m; }
    """, marker_id="PSS105", severity="error")
    assert "'m'" in marker["message"]


def test_a_plain_component_field_is_accepted():
    assert_no_marker("""
    component M { }
    component C { M m; }
    """, marker_id="PSS105")


def test_mutable_on_a_scalar_field_is_accepted():
    assert_no_marker("component C { mutable int total; }", marker_id="PSS105")


def test_mutable_on_a_struct_field_is_accepted():
    """Only *component* fields are excluded, not aggregates generally."""
    assert_no_marker("""
    struct S { int a; }
    component C { mutable S s; }
    """, marker_id="PSS105")


def test_mutable_on_a_list_of_component_refs_is_accepted():
    """
    Example55 does exactly this. The restriction is on a component *instance*
    field, not on holding references to components.
    """
    assert_no_marker("""
    component my_comp_c { }
    component pss_top { mutable list<ref my_comp_c> used_comps; }
    """, marker_id="PSS105")


def test_instance_and_mutable_cannot_both_be_written():
    """
    §9.1.6 b) also forbids `mutable` on an instance reference field, but the
    grammar makes that unreachable: `mutable` and `instance` are alternatives
    of the same optional group in `component_data_decl_qualifier`. So the check
    is a syntax error, not PSS105 -- deliberately, in the same way PSS103 was
    retired for being unreachable.
    """
    assert_parse_error("""
    component M { }
    component C { instance mutable M m; }
    """)


# -- negative cases ---------------------------------------------------------

def test_mutable_is_a_reserved_word():
    """The same deliberate lexical break as `soft` -- see test_soft_constraints_31."""
    assert_parse_error("struct S { int mutable; }")


def test_mutable_is_not_permitted_on_a_struct_member():
    """`mutable` qualifies *component* data declarations only (B.8)."""
    assert_parse_error("struct S { mutable int a; }")


def test_mutable_is_not_permitted_on_an_action_field():
    assert_parse_error("""
    component pss_top {
        action A { mutable int a; }
    }
    """)


def test_mutable_is_not_permitted_with_static_const():
    """`static const` and `mutable` are alternatives, and contradictory."""
    assert_parse_error("component C { static const mutable int a = 1; }")
