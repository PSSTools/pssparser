"""
Tests for PSS 3.1 range slices (P3-E1 `in` + array_slice, P3-E2 string slices).

Annex B B.19 defines two rules with *identical* syntax::

    array_slice  ::= expression .. expression | expression .. | .. expression
    string_slice ::= expression .. expression | expression .. | .. expression

Which one a bracketed range is depends on the type of the operand, which is not
known while parsing.  Both therefore build a single neutral `ExprSliceRange`,
and the operand type is what classifies it downstream.  (`bit_slice`, spelled
`[msb : lsb]`, *is* syntactically distinct and remains `ExprBitSlice`.)

Two things this module pins that are easy to get wrong:

**The range end used to be discarded.**  `member_path_elem_index` already
accepted `[a..b]` before 3.1, but the builder read only `expression(0)` --
`s[1..3]` built a plain subscript of `1`, with a `TODO` where the upper bound
should have been.  Silent, and indistinguishable from `s[1]` in the AST.

**A slice is not an index.**  `arr[1]` selects an element, `arr[1..3]` selects a
sub-collection.  Both arrive as entries in the same subscript list, so a
resolver that does not check gives `arr[1..3].f` the same meaning as
`arr[1].f`.  It now reports PSS107 instead.
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


def _first_slice(code):
    """Parse `code` and return the first ExprSliceRange found, or None."""
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    found = []

    # No visited-set: each accessor call returns a *fresh* Python wrapper, so
    # `id()` is not a stable node identity and freed ids get reused -- keying a
    # visited-set on it prunes the walk at random. The depth bound is what
    # keeps this terminating.
    # Reflective rather than a hand-listed set of accessors: a slice can turn
    # up under a constraint operand, a procedural assignment, an `in`
    # expression or a ref path, and enumerating those routes by name gets
    # silently stale as the AST grows. `numX()`/`getX(i)` and zero-argument
    # `getX()` cover every generated accessor.
    def walk(node, depth=0):
        if node is None or depth > 60:
            return

        if type(node).__name__ == "ExprSliceRange":
            found.append(node)
            return

        for name in dir(node):
            if not name.startswith("num"):
                continue
            # The generator's singular-accessor convention: `numChildren` ->
            # `getChild`, `numItems` -> `getItem`, `numSubscript` ->
            # `numSubscript`. Getting the "ren" case wrong silently stops the
            # walk at the first scope, since `getChildren` takes no index.
            single = "get" + name[3:]
            if single.endswith("ren"):
                single = single[:-3]
            elif single.endswith("s"):
                single = single[:-1]
            if not hasattr(node, single):
                continue
            try:
                count = getattr(node, name)()
            except Exception:
                continue
            for i in range(count):
                try:
                    child = getattr(node, single)(i)
                except Exception:
                    break
                walk(child, depth + 1)

        for name in dir(node):
            if not name.startswith("get") or name in ("getParent",):
                continue
            try:
                child = getattr(node, name)()
            except Exception:
                continue
            if child is not None and child is not node \
                    and type(child).__module__ == type(node).__module__:
                walk(child, depth + 1)

    for scope in parser._files[1:]:
        walk(scope)
    return found[0] if found else None


def _bounds(slice_node):
    lower, upper = slice_node.getLower(), slice_node.getUpper()
    return (lower.getValue() if lower is not None else None,
            upper.getValue() if upper is not None else None)


# ===========================================================================
# The slice node
# ===========================================================================

_ARR_MODEL = """
component pss_top {
    action A {
        rand int arr[8];
        constraint c { unique arr%s; }
    }
}
"""


@pytest.mark.parametrize("spelling,expected", [
    ("[1..3]", (1, 3)),
    ("[1..]", (1, None)),
    ("[..3]", (None, 3)),
])
def test_slice_carries_both_endpoints(spelling, expected):
    node = _first_slice(_ARR_MODEL % spelling)
    assert node is not None, "no ExprSliceRange built for %s" % spelling
    assert _bounds(node) == expected


def test_range_end_is_not_discarded():
    """
    The regression this module exists for: `[1..3]` and `[1]` must not produce
    the same AST.  Before 3.1 support they did.
    """
    sliced = _first_slice(_ARR_MODEL % "[1..3]")
    assert sliced is not None
    assert sliced.getUpper() is not None, "upper bound was dropped"

    assert _first_slice(_ARR_MODEL % "[1]") is None, \
        "a plain index must not build a slice node"


def test_a_slice_needs_at_least_one_endpoint():
    assert_parse_error(_ARR_MODEL % "[..]")


# ===========================================================================
# P3-E1 -- `in` with an array slice
# ===========================================================================
#
# B.15: `expression in collection_expression [ [ array_slice ] ]`.
#
# The trailing bracket is not spelled separately in the grammar because a
# hierarchical_id already absorbs it: `arr[2..5]` parses as a ref path whose
# last element carries a slice subscript.  Adding a second overlapping way to
# match the same brackets would be an ambiguity ANTLR resolves silently -- one
# source spelling, two possible AST shapes.
#
# The gap this leaves is a slice applied to a collection_expression that is not
# a ref path (`x in f()[1..3]`, `x in [1,2,3][0..1]`).  Those remain rejected;
# test_slice_on_a_non_ref_path_collection_is_not_supported records it rather
# than leaving it to be discovered.

_IN_MODEL = """
component pss_top {
    action A {
        rand int x;
        rand int arr[8];
        constraint c { x in %s; }
    }
}
"""


@pytest.mark.parametrize("collection", [
    "arr", "arr[2..5]", "arr[2..]", "arr[..5]",
])
def test_in_expression_accepts_a_sliced_collection(collection):
    assert_parse_ok(_IN_MODEL % collection)


def test_in_expression_slice_reaches_the_ast():
    node = _first_slice(_IN_MODEL % "arr[2..5]")
    assert node is not None
    assert _bounds(node) == (2, 5)


def test_in_expression_with_open_range_list_still_parses():
    """The other `in` form -- `in [ open_range_list ]` -- is untouched."""
    assert_parse_ok(_IN_MODEL % "[1..3]")
    assert_parse_ok(_IN_MODEL % "[1, 2, 3]")


def test_slice_on_a_non_ref_path_collection_is_not_supported():
    """
    A known, deliberate gap: the slice is absorbed by the ref path, so a
    collection expression that is not a ref path cannot carry one.  Written as
    a passing test of current behaviour, not an xfail, because the behaviour is
    a choice (avoid a silent grammar ambiguity), not a defect to be fixed.
    """
    assert_parse_error("""
    component pss_top {
        action A {
            rand int x;
            function list<int> f();
            constraint c { x in f()[1..3]; }
        }
    }
    """)


# ===========================================================================
# P3-E2 -- string slices
# ===========================================================================

_STR_MODEL = """
struct S {
    string s;
    string t;
    exec init_up {
        t = s%s;
    }
}
"""


@pytest.mark.parametrize("spelling", ["[1..3]", "[1..]", "[..3]"])
def test_string_slice_parses(spelling):
    assert_parse_ok(_STR_MODEL % spelling)


def test_string_slice_builds_the_same_node_as_an_array_slice():
    """
    Deliberate: array and string slices are syntactically identical, and the
    parser cannot tell them apart without the operand's type.  One node is the
    only shape it can honestly produce.
    """
    from_string = _first_slice(_STR_MODEL % "[1..3]")
    from_array = _first_slice(_ARR_MODEL % "[1..3]")

    assert from_string is not None and from_array is not None
    assert type(from_string).__name__ == type(from_array).__name__


def test_bit_slice_is_still_a_distinct_node():
    """`[msb : lsb]` is spelled differently and stays ExprBitSlice."""
    assert_parse_ok("""
    struct S {
        bit[16] v;
        bit[8] b;
        exec init_up { b = v[7:0]; }
    }
    """)
    assert _first_slice("""
    struct S {
        bit[16] v;
        bit[8] b;
        exec init_up { b = v[7:0]; }
    }
    """) is None, "a bit slice must not build an ExprSliceRange"


# ===========================================================================
# PSS107 -- member selection on a slice
# ===========================================================================

_ELEM_MODEL = """
struct E { int f; }
component pss_top {
    action A {
        rand E arr[8];
        constraint c { %s == 0; }
    }
}
"""


def test_member_selection_on_an_index_is_permitted():
    assert_no_marker(_ELEM_MODEL % "arr[1].f", marker_id="PSS107")


@pytest.mark.parametrize("path", [
    "arr[1..3].f", "arr[1..].f", "arr[..3].f",
])
def test_member_selection_on_a_slice_is_rejected(path):
    marker = assert_marker(_ELEM_MODEL % path,
                           marker_id="PSS107", severity="error")
    assert "arr" in marker["message"]


def test_slice_without_member_selection_is_permitted():
    """The slice itself is fine -- only selecting *through* it is not."""
    assert_no_marker("""
    component pss_top {
        action A {
            rand int x;
            rand int arr[8];
            constraint c { x in arr[1..3]; }
        }
    }
    """, marker_id="PSS107")


def test_slice_member_selection_reports_the_sliced_name():
    """
    The diagnostic names the collection, not the missing member: the member is
    not misspelled, it is unreachable through a slice.
    """
    marker = assert_marker(_ELEM_MODEL % "arr[1..3].nope", marker_id="PSS107")
    assert "slice of 'arr'" in marker["message"]
