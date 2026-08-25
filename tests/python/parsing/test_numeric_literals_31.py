"""
Numeric literal forms required by PSS 3.1 Annex B B.20 (plan item P1-G1).

Three gaps in the pre-3.1 lexer, all of which silently rejected conforming PSS:

* ``bin_number`` (``0b1010``) had no token at all
* ``hex_number`` accepted only lowercase ``0x``, not ``0X``
* ``oct_number`` rejected the ``_`` digit separator every other base allowed

Parsing alone is not sufficient coverage here: a literal that parses to the
*wrong value* is worse than one that fails to parse, so each positive case
asserts the value carried into the AST rather than just that the parse
survived.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402

from pssparser import Parser  # noqa: E402


# AST node wrappers do NOT keep their owning Parser alive: once the Parser is
# collected the underlying C++ nodes are freed and touching a wrapper segfaults
# the interpreter. Hold every parser used by a probe for the life of the module.
_LIVE_PARSERS = []


def _literal_node(literal: str):
    """Parse `int a = <literal>;` and return the initializer expression node."""
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", "struct S { int a = %s; }" % literal)])

    # The pre-link AST is where literals are observable; children() does not
    # descend into field initializers, so reach the Field and ask directly.
    for scope in parser._files[1:]:
        for child in scope.children():
            if type(child).__name__ != "Struct":
                continue
            for field in child.children():
                if type(field).__name__ == "Field":
                    return field.getInit()
    raise AssertionError("no Field found for literal %r" % literal)


def assert_literal_value(literal: str, expected: int, check_image: bool = True):
    """Assert `literal` parses and reaches the AST with `expected` value."""
    node = _literal_node(literal)
    assert node is not None, "literal %r produced no initializer node" % literal
    assert node.getValue() == expected, \
        "literal %r evaluated to %d, expected %d" % (
            literal, node.getValue(), expected)
    if check_image:
        assert node.getImage() == literal, \
            "literal %r lost its source image (got %r)" % (
                literal, node.getImage())


# =============================================================================
# Binary literals -- entirely new in this change
# =============================================================================

@pytest.mark.parametrize("literal,expected", [
    ("0b0", 0),
    ("0b1", 1),
    ("0b1010", 10),
    ("0B1010", 10),
    ("0b11111111", 255),
    ("0b1010_1010", 0xAA),
    ("0B1111_0000_1111_0000", 0xF0F0),
    ("0b0000_0001", 1),
])
def test_binary_literal_value(literal, expected):
    assert_literal_value(literal, expected)


def test_binary_literal_in_enum():
    assert_parse_ok("enum Flags { A = 0b0001, B = 0b0010, C = 0b0100 }")


def test_binary_literal_in_constraint():
    assert_parse_ok("""
        component pss_top {
            action A {
                rand bit[8] v;
                constraint c { v == 0b1010_1010; }
            }
        }
    """)


@pytest.mark.parametrize("literal", [
    "0b",       # no digits
    "0b2",      # 2 is not a binary digit
    "0b_1",     # separator may not lead the digit sequence
    "0B",
])
def test_malformed_binary_literal_rejected(literal):
    assert_parse_error("struct S { int a = %s; }" % literal)


def test_binary_does_not_shadow_bare_zero():
    """
    ``OCT_LITERAL`` matches a bare ``0``, so it overlaps the ``0b`` prefix.
    ANTLR's longest-match rule resolves this, but the resolution is worth
    pinning: both forms must keep working, whatever their lexer order.
    """
    assert_literal_value("0", 0)
    assert_literal_value("0b1010", 10)


# =============================================================================
# Hex literals -- uppercase 0X was rejected
# =============================================================================

@pytest.mark.parametrize("literal,expected", [
    ("0xff", 255),
    ("0XFF", 255),
    ("0Xff", 255),
    ("0xFF", 255),
    ("0xDEAD_BEEF", 0xDEADBEEF),
    ("0XDEAD_BEEF", 0xDEADBEEF),
    ("0x0", 0),
    ("0X1234_5678", 0x12345678),
])
def test_hex_literal_value(literal, expected):
    assert_literal_value(literal, expected)


@pytest.mark.parametrize("literal", ["0x", "0X", "0xg", "0x_1"])
def test_malformed_hex_literal_rejected(literal):
    assert_parse_error("struct S { int a = %s; }" % literal)


# =============================================================================
# Octal literals -- the '_' separator was rejected
# =============================================================================

@pytest.mark.parametrize("literal,expected", [
    ("0", 0),
    ("07", 7),
    ("0777", 0o777),
    ("0_777", 0o777),
    ("07_7_7", 0o777),
    ("0123_456", 0o123456),
])
def test_octal_literal_value(literal, expected):
    assert_literal_value(literal, expected)


@pytest.mark.parametrize("literal", ["08", "09", "0778"])
def test_non_octal_digit_rejected(literal):
    """8 and 9 are not octal digits -- these must not silently truncate."""
    assert_parse_error("struct S { int a = %s; }" % literal)


# =============================================================================
# Regression: the forms that already worked must keep working
# =============================================================================

@pytest.mark.parametrize("literal,expected", [
    ("1", 1),
    ("42", 42),
    ("1_000", 1000),
    ("1_000_000", 1000000),
])
def test_decimal_literal_value(literal, expected):
    assert_literal_value(literal, expected)


@pytest.mark.parametrize("literal,expected", [
    ("8'hFF", 255),
    ("8'hF_F", 255),
    ("4'b1010", 10),
    ("4'B1010", 10),
    ("8'o777", 0o777),
    ("8'd99", 99),
    ("'hFF", 255),
    ("'b1010", 10),
])
def test_based_literal_value(literal, expected):
    """Based literals share the digit-separator handling being changed here."""
    # Image is checked separately below -- sized forms currently lose their
    # width prefix.
    assert_literal_value(literal, expected, check_image=False)


@pytest.mark.parametrize("literal", ["8'hFF", "4'b1010", "16'd99"])
@pytest.mark.xfail(strict=True, reason=(
    "P1-G1 follow-up: AstBuilderInt::visitNumber sets the literal image from "
    "the BASED_*_LITERAL token alone, dropping the width prefix, so a sized "
    "based literal reconstructs as \"'hFF\" rather than \"8'hFF\". Value and "
    "width are correct; only the source image is lossy."))
def test_sized_based_literal_keeps_full_image(literal):
    node = _literal_node(literal)
    assert node.getImage() == literal


@pytest.mark.parametrize("literal,expected", [
    ("'hFF", 255),
    ("'b1010", 10),
    ("'o777", 0o777),
    ("'d99", 99),
])
def test_unsized_based_literal_keeps_image(literal, expected):
    """Unsized based literals have no prefix to lose, so the image is exact."""
    assert_literal_value(literal, expected)


@pytest.mark.parametrize("literal,width", [
    ("8'hFF", 8),
    ("16'hFF", 16),
    ("32'hDEADBEEF", 32),
])
def test_based_literal_width(literal, width):
    node = _literal_node(literal)
    assert node.getWidth() == width
