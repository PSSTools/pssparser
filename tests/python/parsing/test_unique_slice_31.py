"""
Tests for the PSS 3.1 `unique` constraint argument (P3-C2, LRM §13.1.10).

3.0 supported only the braced form.  3.1 adds a single-argument form::

    unique { a, b, c };   // these three attributes must differ
    unique arr;           // the *elements* of `arr` must differ
    unique arr[2..5];     // elements 2..5 of `arr` must differ

The two forms mean different things, and with one entry they are not
distinguishable from the operand list alone -- `unique { a }` constrains one
scalar, `unique a` constrains every element of a collection.  That is what
`is_braced` is for, and asserting on it is most of what this module does.

Slices are covered here only where they attach to a `unique` argument; the
slice node itself lives in test_slices_31.py.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []

_MODEL = """
component pss_top {
    action A {
        rand int a;
        rand int b;
        rand int c;
        rand int arr[8];
        constraint k {
            %s
        }
    }
}
"""


def _unique_stmts(body):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", _MODEL % body)])
    assert not parser.markers, [m for m in parser.markers]

    for scope in parser._files[1:]:
        for comp in scope.children():
            for action in comp.children():
                if type(action).__name__ != "Action":
                    continue
                for item in action.children():
                    if type(item).__name__ == "ConstraintBlock":
                        return [item.getConstraint(i)
                                for i in range(item.numConstraints())]
    raise AssertionError("no ConstraintBlock found")


def _last_elem(stmt, i=0):
    """The final ExprMemberPathElem of the stmt's i'th operand."""
    hid = stmt.getList(i)
    return hid.getElem(hid.numElems() - 1)


# -- braced form (unchanged from 3.0) ---------------------------------------

@pytest.mark.parametrize("body", [
    "unique { a, b };",
    "unique { a, b, c };",
    "unique { arr[0], arr[1] };",
])
def test_braced_form_parses(body):
    assert_parse_ok(_MODEL % body)


def test_braced_form_is_flagged_as_braced():
    stmt = _unique_stmts("unique { a, b, c };")[0]
    assert stmt.getIs_braced() is True
    assert stmt.numList() == 3


def test_braced_form_preserves_operand_order():
    stmt = _unique_stmts("unique { a, b, c };")[0]
    names = [stmt.getList(i).getElem(0).getId().getId()
             for i in range(stmt.numList())]
    assert names == ["a", "b", "c"]


# -- single-argument form (new in 3.1) --------------------------------------

@pytest.mark.parametrize("body", [
    "unique arr;",
    "unique arr[2..5];",
    "unique arr[2..];",
    "unique arr[..5];",
])
def test_single_argument_form_parses(body):
    assert_parse_ok(_MODEL % body)


def test_single_argument_form_is_not_flagged_as_braced():
    stmt = _unique_stmts("unique arr;")[0]
    assert stmt.getIs_braced() is False
    assert stmt.numList() == 1


def test_single_argument_form_names_the_collection():
    stmt = _unique_stmts("unique arr;")[0]
    assert stmt.getList(0).getElem(0).getId().getId() == "arr"


def test_one_element_forms_are_distinguishable():
    """
    The point of `is_braced`.  `unique { a }` and `unique a` both produce a
    one-entry list, but constrain different things -- a consumer that reads
    only the list cannot tell them apart.
    """
    braced, bare = _unique_stmts("unique { a }; unique arr;")

    assert braced.numList() == bare.numList() == 1
    assert braced.getIs_braced() is True
    assert bare.getIs_braced() is False


def test_hierarchical_id_argument():
    """The argument is a hierarchical_id, not just a plain identifier."""
    assert_parse_ok("""
    struct S { rand int items[4]; }
    component pss_top {
        action A {
            rand S s;
            constraint k { unique s.items; }
        }
    }
    """)


# -- slices on the single-argument form -------------------------------------

@pytest.mark.parametrize("body,lower,upper", [
    ("unique arr[2..5];", 2, 5),
    ("unique arr[2..];", 2, None),
    ("unique arr[..5];", None, 5),
])
def test_slice_endpoints(body, lower, upper):
    """
    `[..5]` is the case worth watching: the sole expression present is the
    *upper* bound, so an implementation keyed on expression position rather
    than on the token order gets it backwards.
    """
    stmt = _unique_stmts(body)[0]
    elem = _last_elem(stmt)

    assert elem.numSubscript() == 1
    slice_node = elem.getSubscript(0)
    assert type(slice_node).__name__ == "ExprSliceRange"

    got_lower = slice_node.getLower()
    got_upper = slice_node.getUpper()

    assert (got_lower.getValue() if got_lower is not None else None) == lower
    assert (got_upper.getValue() if got_upper is not None else None) == upper


def test_plain_index_is_not_a_slice():
    """`unique arr[3]` selects one element -- it must stay a plain subscript."""
    stmt = _unique_stmts("unique arr[3];")[0]
    subscript = _last_elem(stmt).getSubscript(0)
    assert type(subscript).__name__ != "ExprSliceRange"


def test_slice_bounds_may_be_expressions():
    """§13.1.10: the slice indexes themselves can be random."""
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int lo;
            rand int arr[8];
            constraint k { unique arr[lo..lo+2]; }
        }
    }
    """)


# -- negative cases ---------------------------------------------------------

@pytest.mark.parametrize("body", [
    "unique;",                # no argument
    "unique arr",             # no terminating semicolon
    "unique { };",            # empty brace list
    "unique { a, };",         # trailing comma
    "unique a b;",            # two bare arguments
    "unique arr[..];",        # a slice with neither endpoint
])
def test_malformed_unique_rejected(body):
    assert_parse_error(_MODEL % body)


def test_unique_still_rejects_a_bare_list_without_braces():
    """The single-argument form takes one id, not a comma-separated list."""
    assert_parse_error(_MODEL % "unique a, b;")
