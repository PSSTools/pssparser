"""
Tests for PSS float32/float64 data types (LRM §7.3).

NOTE: The grammar has float_type rules and lexer tokens, but pyastbuilder
does not yet generate a DataTypeFloat AST node. These tests document
the current state: parsing succeeds but field type is None.
Once DataTypeFloat is added, update tests to verify the type class.
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
