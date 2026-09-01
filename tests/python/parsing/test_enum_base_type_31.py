"""
Tests for the PSS 3.1 enum base type (P3-S1, LRM §3.1, Annex B B.13).

``enum_declaration ::= enum enum_identifier [ : data_type ] { ... }``

The base type fixes the representation of the enumerators. It is optional, and
omitting it must keep behaving exactly as it did in 3.0 -- the `base_type`
accessor returns null rather than a default-constructed placeholder, so a
consumer can tell "not written" from "written as int".
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []


def _enum_decl(code, name="e"):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    for scope in parser._files[1:]:
        for child in scope.children():
            if type(child).__name__ == "EnumDecl" \
                    and child.getName().getId() == name:
                return child
    raise AssertionError("no EnumDecl %r found" % name)


# -- syntax -----------------------------------------------------------------

@pytest.mark.parametrize("base", [
    # Width is bracketed in PSS -- there is no `int<8>` form.
    #
    # `bit[7:0]` is *not* in B.13 -- it is a PSS 1.x/2.x ingestion extension
    # (D7/P7-D1), accepted everywhere an integer type may be written rather than
    # only here (P3-X5). `test_integer_width_range` in test_data_types.py covers
    # what it builds and carries the full note.
    "int", "bit", "bit[4]", "int[16]", "bit[7:0]", "int[15:0]",
])
def test_enum_with_base_type_parses(base):
    assert_parse_ok("enum e : %s { A, B, C }" % base)


def test_enum_without_base_type_still_parses():
    assert_parse_ok("enum e { A, B, C }")


def test_enum_with_base_type_and_explicit_values():
    assert_parse_ok("enum e : bit[8] { A = 0, B = 1, C = 255 }")


def test_empty_enum_with_base_type():
    assert_parse_ok("enum e : int { }")


def test_enum_with_base_type_in_package():
    assert_parse_ok("package p { enum e : bit[4] { A, B } }")


def test_enum_with_base_type_in_component():
    assert_parse_ok("component C { enum e : bit[4] { A, B } }")


# -- AST shape --------------------------------------------------------------

def test_base_type_is_absent_when_not_written():
    """
    Null, not a stand-in default. A consumer needs to distinguish "no base type
    declared" from "declared as int", because the two may imply different
    widths.
    """
    assert _enum_decl("enum e { A, B }").getBase_type() is None


def test_base_type_is_recorded():
    node = _enum_decl("enum e : int { A, B }").getBase_type()
    assert node is not None
    assert type(node).__name__ == "DataTypeInt"


@pytest.mark.parametrize("base,is_signed", [
    ("int", True),
    ("bit", False),
])
def test_base_type_signedness(base, is_signed):
    node = _enum_decl("enum e : %s { A, B }" % base).getBase_type()
    assert node.getIs_signed() is is_signed


def test_base_type_width_is_recorded():
    node = _enum_decl("enum e : bit[4] { A, B }").getBase_type()
    assert node.getWidth() is not None


def test_base_type_does_not_disturb_the_items():
    decl = _enum_decl("enum e : bit[8] { A = 0, B = 5, C }")
    names = [decl.getItem(i).getName().getId() for i in range(decl.numItems())]
    assert names == ["A", "B", "C"]
    # C follows B = 5, so it takes 6 -- the auto-numbering must still see the
    # explicit values.
    assert [decl.getItem(i).getIndex() for i in range(decl.numItems())] == [0, 5, 6]


# -- use ---------------------------------------------------------------------

def test_field_of_an_enum_with_a_base_type():
    assert_parse_ok("""
    enum e : bit[4] { A, B, C }
    struct S { e field; }
    """)


def test_enum_with_base_type_in_a_constraint():
    assert_parse_ok("""
    enum e : bit[4] { A, B, C }
    component pss_top {
        action X {
            rand e field;
            constraint c { field == e::A; }
        }
    }
    """)


# -- negative cases ---------------------------------------------------------

@pytest.mark.parametrize("decl", [
    "enum e : { A, B }",        # colon with no type
    "enum e : int A, B }",      # missing opening brace
    "enum : int { A, B }",      # missing name
    "enum e int { A, B }",      # missing colon
])
def test_malformed_enum_base_type_rejected(decl):
    assert_parse_error(decl)
