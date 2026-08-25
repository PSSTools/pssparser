"""
Tests for PSS 3.1 multi-dimensional arrays (P3-S2, LRM §11.3.2, Annex B).

3.1 spells `{ array_dim }` (zero or more) where the 3.0 parser had `array_dim?`
in four productions: `object_ref_field`, `procedural_data_instantiation` and
both positions of `monitor_instantiation`. `data_instantiation` and
`action_handle_array_instance` were already correct.

Dimensions are not stored as a list on the field. They nest: `int a[3][2]`
builds `array<array<int,2>,3>`, which is how the parser has always represented
a single dimension and needs no AST change.

**Ordering is the thing to get right.** §11.3.2 Example87 declares
`A a_arr[3][2]` and states that `a_arr[1]` is a *sub-array of two handles*, so
the leftmost dimension is the outermost. Because each dimension is applied by
wrapping the type built so far, they must be applied right to left. Two call
sites disagreed about this before 3.1 support -- `action_handle_array_instance`
went right to left and `data_instantiation` went left to right, so
`int a[3][2]` built the transposed type. Both now share one helper.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []


def _field_type(code, field_name):
    """Return the declared type node of `field_name`, searching recursively."""
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    def walk(node, depth=0):
        if node is None or depth > 20 or not hasattr(node, "numChildren"):
            return None
        for i in range(node.numChildren()):
            child = node.getChild(i)
            name = getattr(child, "getName", None)
            if name is not None and hasattr(child, "getType"):
                got = name()
                if got is not None and got.getId() == field_name:
                    return child.getType()
            found = walk(child, depth + 1)
            if found is not None:
                return found
        return None

    for scope in parser._files[1:]:
        found = walk(scope)
        if found is not None:
            return found
    raise AssertionError("no field %r found" % field_name)


def _array_shape(type_node):
    """Unwrap nested `array<elem, size>` types into a list of dimensions.

    Returns the sizes outermost-first, so `int a[3][2]` gives [3, 2] -- the
    same order they are written.
    """
    dims = []
    node = type_node
    while node is not None and type(node).__name__ == "DataTypeUserDefined":
        tid = node.getType_id()
        elem = tid.getElem(tid.numElems() - 1)
        if elem.getId().getId() != "array":
            break
        params = elem.getParams()
        assert params is not None and params.numValues() == 2, \
            "array<> without two template parameters"
        # TemplateParamExprValue / TemplateParamTypeValue both expose the
        # payload as getValue(); the parameter's position is what says which.
        dims.append(params.getValue(1).getValue().getValue())
        node = params.getValue(0).getValue()
    return dims


# ===========================================================================
# The four productions that gained `*`
# ===========================================================================

def test_object_ref_field_multidim():
    """`input`/`output` flow-object reference fields."""
    assert_parse_ok("""
    buffer B { }
    component pss_top {
        action A {
            input B b[2][3];
            output B c[4][5][6];
        }
    }
    """)


def test_resource_ref_field_multidim():
    """`lock`/`share` share the object_ref_field production."""
    assert_parse_ok("""
    resource R { }
    component pss_top {
        action A {
            lock R r[2][3];
        }
    }
    """)


def test_procedural_data_instantiation_multidim():
    assert_parse_ok("""
    struct S {
        exec init_up {
            int a[2][3];
        }
    }
    """)


def test_monitor_instantiation_multidim():
    assert_parse_ok("""
    component pss_top {
        action A { }
        monitor M { A a; }
        monitor N { M m[2][3]; }
    }
    """)


def test_monitor_instantiation_multidim_in_a_list():
    """Both `array_dim` positions of monitor_instantiation, not just the first."""
    assert_parse_ok("""
    component pss_top {
        action A { }
        monitor M { A a; }
        monitor N { M m[2][3], n[4][5]; }
    }
    """)


# ===========================================================================
# The two that were already correct
# ===========================================================================

def test_data_instantiation_multidim():
    assert_parse_ok("struct S { int a[2][3]; }")


def test_action_handle_array_multidim():
    assert_parse_ok("""
    component pss_top {
        action A { }
        action entry { A a_arr[3][2]; }
    }
    """)


# ===========================================================================
# Dimension order
# ===========================================================================

@pytest.mark.parametrize("decl,expected", [
    ("int a[4];", [4]),
    ("int a[3][2];", [3, 2]),
    ("int a[2][3];", [2, 3]),
    ("int a[1][2][3];", [1, 2, 3]),
])
def test_data_instantiation_dimension_order(decl, expected):
    """
    The regression this module exists for. `data_instantiation` applied
    dimensions left to right, producing the transposed type -- wrong for every
    non-square declaration and accidentally right for square ones.
    """
    assert _array_shape(_field_type("struct S { %s }" % decl, "a")) == expected


def test_action_handle_dimension_order():
    """
    §11.3.2 Example87: given `A a_arr[3][2]`, `a_arr[1]` is a sub-array of two
    handles. So the outermost dimension is 3, the leftmost as written.
    """
    code = """
    component pss_top {
        action A { }
        action entry { A a_arr[3][2]; }
    }
    """
    assert _array_shape(_field_type(code, "a_arr")) == [3, 2]


def test_the_two_declaration_forms_agree_on_order():
    """
    They used to disagree: one applied dimensions right to left and the other
    left to right, so the same shape written two ways built two different
    types.
    """
    data = _array_shape(_field_type("struct S { int a[3][2]; }", "a"))

    handle = _array_shape(_field_type("""
    component pss_top {
        action A { }
        action entry { A a[3][2]; }
    }
    """, "a"))

    assert data == handle == [3, 2]


def test_square_dimensions_do_not_distinguish_the_orders():
    """
    Documents why the ordering defect stayed hidden: with equal dimensions both
    orders build the same type, so any test using `[2][2]` proves nothing.
    """
    assert _array_shape(_field_type("struct S { int a[2][2]; }", "a")) == [2, 2]


# ===========================================================================
# Use and negative cases
# ===========================================================================

def test_multidim_element_access():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int a[3][2];
            constraint c { a[1][0] == 5; }
        }
    }
    """)


def test_multidim_action_handle_subarray_traversal():
    """Example87: a sub-array may be traversed as a whole."""
    assert_parse_ok("""
    component pss_top {
        action A { }
        action entry {
            A a_arr[3][2];
            activity {
                a_arr[2][0];
                a_arr[1];
                a_arr;
            }
        }
    }
    """)


def test_single_dimension_still_parses():
    assert_parse_ok("struct S { int a[4]; }")


def test_no_dimension_still_parses():
    assert_parse_ok("struct S { int a; }")


@pytest.mark.parametrize("decl", [
    "int a[2][;",      # unterminated second dimension
    "int a[][2];",     # empty dimension
    "int a[2]3];",     # missing bracket
])
def test_malformed_dimensions_rejected(decl):
    assert_parse_error("struct S { %s }" % decl)
