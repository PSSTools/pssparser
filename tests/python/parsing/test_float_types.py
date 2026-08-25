"""
Tests for PSS float32/float64 data types (LRM §7.3) and float literals.

`float32`/`float64` fields build a `DataTypeFloat` node, and float literals
build an `ExprFloatLiteral` carrying both the parsed value and the source
image. Both required a floating-point scalar kind in pyastbuilder, which the
generator originally lacked (plan item P1-G2a).
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_type_float32_in_struct(parser):
    """Parse float32 field in struct; verify field symbol exists"""
    code = """
struct sensor_data {
    float32 temperature;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "sensor_data")
    assert sym is not None
    assert has_symbol(sym, "temperature")

    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_type_float64_in_struct(parser):
    """Parse float64 field in struct; verify field symbol exists"""
    code = """
struct measurement {
    float64 precise_value;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "measurement")
    assert sym is not None
    assert has_symbol(sym, "precise_value")


def test_type_float_in_action(parser):
    """Parse float fields in action through component"""
    code = """
component pss_top {
    action Compute {
        float32 result;
        float64 accumulator;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "Compute")
    assert action is not None
    assert has_symbol(action, "result")
    assert has_symbol(action, "accumulator")


def test_type_float_in_function_params(parser):
    """Parse float as function parameter and return type"""
    code = """
component pss_top {
    function float64 compute_area(float32 width, float32 height);
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None


def test_type_float_mixed_with_other_types(parser):
    """Parse struct mixing float with int and bool types"""
    code = """
struct mixed_s {
    float32 val_f32;
    float64 val_f64;
    int     val_int;
    bool    val_bool;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "mixed_s")
    assert sym is not None
    for name in ("val_f32", "val_f64", "val_int", "val_bool"):
        assert has_symbol(sym, name), f"field {name} not found"


# ===========================================================================
# Floating-point literals (plan item P1-G2, PSS 3.1 §4.6 / Annex B B.20)
# ===========================================================================
# `floating_point_number` was a placeholder -- literally `TOK_ACTION` -- so no
# float literal of any spelling parsed. The two conforming forms are now
# implemented:
#
#   floating_point_dec_number ::= unsigned_number . unsigned_number
#   floating_point_sci_number ::= unsigned_number [ . unsigned_number ]
#                                 exp [ sign ] unsigned_number
#
# Both require a digit on each side of the '.', which is what keeps `1..2`
# lexing as a range rather than as `1.` `.2`.

from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402

# AST wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []


def _float_node(literal):
    """Parse a field initialized with `literal` and return the init node.

    The field is declared `int` rather than `float64` only because these
    assertions are about the *literal*, not the declared type; both build the
    same initializer node. `float64` fields are covered by the DataTypeFloat
    tests below.
    """
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", "struct S { int a = %s; }" % literal)])
    for scope in parser._files[1:]:
        for child in scope.children():
            if type(child).__name__ != "Struct":
                continue
            for field in child.children():
                if type(field).__name__ == "Field":
                    return field.getInit()
    raise AssertionError("no Field found for literal %r" % literal)


# -- decimal form -----------------------------------------------------------

@pytest.mark.parametrize("literal", [
    "1.0", "0.5", "3.14159", "0.0", "123.456", "1_000.5", "1.000_1",
    "10.01", "999999.999999",
])
def test_float_dec_literal_parses(literal):
    assert_parse_ok("struct S { float64 f = %s; }" % literal)


@pytest.mark.parametrize("literal", ["1.0", "0.5", "1_000.5", "3.14159"])
def test_float_dec_literal_is_not_scientific(literal):
    node = _float_node(literal)
    assert type(node).__name__ == "ExprFloatLiteral"
    assert node.getIs_scientific() is False


# -- scientific form --------------------------------------------------------

@pytest.mark.parametrize("literal", [
    "1e10", "1E10", "1e-10", "1E-10", "1e+10", "1.5e3", "1.5e+3", "1.5E-3",
    "1e0", "123.456e-7", "1_000e3", "1_000.5e-2",
])
def test_float_sci_literal_parses(literal):
    assert_parse_ok("struct S { float64 f = %s; }" % literal)


@pytest.mark.parametrize("literal", ["1e10", "1E-10", "1.5e+3", "1_000.5e-2"])
def test_float_sci_literal_is_scientific(literal):
    node = _float_node(literal)
    assert type(node).__name__ == "ExprFloatLiteral"
    assert node.getIs_scientific() is True


# -- source image is preserved ----------------------------------------------

@pytest.mark.parametrize("literal", [
    "1.0", "1.50", "1_000.5", "0.000", "1.5e+3", "1E-10", "1_000.5e-2",
])
def test_float_literal_keeps_exact_source_image(literal):
    """
    The value is stored as text, so a consumer can recover it exactly. Digit
    separators and trailing zeros would both be lost through a double.
    """
    assert _float_node(literal).getImage() == literal


def test_float_literal_value_is_recoverable_from_image():
    for literal, expected in [
        ("1.5", 1.5), ("0.5", 0.5), ("1_000.5", 1000.5),
        ("1e10", 1e10), ("1E-10", 1e-10), ("1.5e+3", 1500.0),
    ]:
        image = _float_node(literal).getImage()
        assert float(image.replace("_", "")) == expected


# -- parsed value (P1-G2a) --------------------------------------------------

@pytest.mark.parametrize("literal,expected", [
    ("1.0", 1.0),
    ("0.5", 0.5),
    ("3.14159", 3.14159),
    ("0.0", 0.0),
    ("1_000.5", 1000.5),
    ("1.000_1", 1.0001),
    ("1e10", 1e10),
    ("1E-10", 1e-10),
    ("1.5e+3", 1500.0),
    ("1_000.5e-2", 10.005),
    ("123.456e-7", 123.456e-7),
])
def test_float_literal_value(literal, expected):
    """`getValue()` carries the parsed magnitude; digit separators are stripped."""
    assert _float_node(literal).getValue() == expected


def test_float_literal_value_and_image_are_independent():
    """
    The two answer different questions and must not be conflated: `image` is
    the authority on spelling, `value` on magnitude. A double cannot reproduce
    the separators or the trailing zero.
    """
    node = _float_node("1_000.50")
    assert node.getImage() == "1_000.50"
    assert node.getValue() == 1000.5


# -- float data types (P1-G2a) ----------------------------------------------

def _field_type_node(decl):
    """Parse `struct S { <decl> }` and return the first Field's type node."""
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", "struct S { %s }" % decl)])
    for scope in parser._files[1:]:
        for child in scope.children():
            if type(child).__name__ != "Struct":
                continue
            for field in child.children():
                if type(field).__name__ == "Field":
                    return field.getType()
    raise AssertionError("no Field found for %r" % decl)


@pytest.mark.parametrize("decl,is_float64", [
    ("float32 f;", False),
    ("float64 f;", True),
    ("float32 f = 1.5;", False),
    ("float64 f = 1.0e-9;", True),
])
def test_float_field_has_float_data_type(decl, is_float64):
    node = _field_type_node(decl)
    assert type(node).__name__ == "DataTypeFloat"
    assert node.getIs_float64() is is_float64


def test_float_field_type_is_not_null():
    """
    Before DataTypeFloat existed, `float32 f;` built a Field with a null type
    and the builder logged "mkDataType returning null" -- a silently degraded
    AST rather than a parse error.
    """
    assert _field_type_node("float32 f;") is not None


# -- the '.' vs '..' hazard -------------------------------------------------

def test_integer_range_still_lexes_as_a_range():
    """
    `1..2` must lex as `1` `..` `2`, not as `1.` `.2`. The BNF's requirement of
    a digit after the '.' is what makes this unambiguous; assert it directly
    rather than trusting the lexer's longest-match behaviour.
    """
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            constraint c { x in [1..2]; }
        }
    }
    """)


def test_integer_range_list_with_multiple_ranges():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            constraint c { x in [1..2, 10..20, 100]; }
        }
    }
    """)


def test_float_range_still_parses():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            constraint c { x in [1.0..2.0]; }
        }
    }
    """)


# -- malformed forms --------------------------------------------------------

@pytest.mark.parametrize("literal", [
    "1.",     # no digits after the '.'
    ".5",     # no digits before the '.'
    "1e",     # exponent marker with no exponent
    "1.e5",   # '.' with no fractional digits
    "1e+",    # sign with no exponent digits
])
def test_malformed_float_literal_rejected(literal):
    assert_parse_error("struct S { float64 f = %s; }" % literal)


# -- end to end -------------------------------------------------------------

def test_float32_field_with_literal_initializer():
    assert_parse_ok("struct S { float32 f = 1.0; }")


def test_float64_field_with_scientific_initializer():
    assert_parse_ok("struct S { float64 f = 1.0e-9; }")


def test_float_literal_in_constraint():
    assert_parse_ok("""
    component pss_top {
        action A {
            rand int x;
            constraint c { x > 1.5; }
        }
    }
    """)


def test_multiple_float_literals_in_one_struct():
    assert_parse_ok("struct S { float64 a = 1.0; float64 b = 2.5e3; float32 c = 0.5; }")
