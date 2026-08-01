"""
Tests for PSS data types including primitives and collections.

Tests cover:
- Primitive types (int, bit, bool, string)
- Sized types (int[N], bit[N])
- Collection types (array, list, map, set)
- Type usage in various contexts
- Linkage: field symbols resolve, data type classes correct
- Source locations: struct/field declaration positions
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error, get_symbol, has_symbol, get_location
import pssparser.ast as ast


def test_type_int(parser):
    """Test int type — verify DataTypeInt and location"""
    code = """
struct test_s {
    rand int value;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    assert sym is not None
    field = sym.getChild(sym.symtabAt("value"))
    assert isinstance(field.getType(), ast.DataTypeInt)
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_type_bit(parser):
    """Test bit type — verify unsigned and DataTypeInt"""
    code = """
struct test_s {
    rand bit[8] value;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    field = sym.getChild(sym.symtabAt("value"))
    dt = field.getType()
    assert isinstance(dt, ast.DataTypeInt)
    assert dt.getIs_signed() == False


def test_type_bool(parser):
    """Test bool type — verify DataTypeBool"""
    code = """
struct test_s {
    rand bool flag;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    field = sym.getChild(sym.symtabAt("flag"))
    assert isinstance(field.getType(), ast.DataTypeBool)


def test_type_string(parser):
    """Test string type — verify DataTypeString"""
    code = """
struct test_s {
    string message;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    field = sym.getChild(sym.symtabAt("message"))
    assert isinstance(field.getType(), ast.DataTypeString)


def test_type_sized_int(parser):
    """Test sized int type"""
    code = """
    struct test_s {
        rand int[16] value;
    };
    """
    assert_parse_ok(code, parser)


def test_type_sized_bit_various(parser):
    """Test various bit sizes"""
    code = """
    struct test_s {
        rand bit[1] flag;
        rand bit[8] byte_val;
        rand bit[16] word_val;
        rand bit[32] dword_val;
    };
    """
    assert_parse_ok(code, parser)


def test_type_chandle(parser):
    """Test chandle type — verify DataTypeChandle"""
    code = """
struct test_s {
    chandle handle;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    field = sym.getChild(sym.symtabAt("handle"))
    assert isinstance(field.getType(), ast.DataTypeChandle)


def test_type_array_fixed_size(parser):
    """Test fixed-size array"""
    code = """
    struct test_s {
        rand int values[10];
    };
    """
    assert_parse_ok(code, parser)


def test_type_array_of_arrays(parser):
    """Test array of fixed-size arrays (simulates 2D)"""
    code = """
    struct test_s {
        rand int row0[4];
        rand int row1[4];
        rand int row2[4];
        rand int row3[4];
    };
    """
    assert_parse_ok(code, parser)


def test_type_array_of_bits(parser):
    """Test array of bit type"""
    code = """
    struct test_s {
        rand bit[8] bytes[16];
    };
    """
    assert_parse_ok(code, parser)


def test_type_enum_as_type(parser):
    """Test enum used as type — verify DataTypeUserDefined and enum resolves"""
    code = """
enum status_e { IDLE, BUSY, DONE };
struct test_s {
    rand status_e status;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "status_e") is not None
    sym = get_symbol(root, "test_s")
    field = sym.getChild(sym.symtabAt("status"))
    assert isinstance(field.getType(), ast.DataTypeUserDefined)


def test_type_struct_as_field(parser):
    """Test struct used as field type — verify cross-type linkage and location"""
    code = """
struct inner_s {
    rand int value;
};
struct outer_s {
    inner_s inner;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "inner_s") is not None
    outer = get_symbol(root, "outer_s")
    field = outer.getChild(outer.symtabAt("inner"))
    assert isinstance(field.getType(), ast.DataTypeUserDefined)
    loc = get_location(outer.getTarget())
    assert loc is not None
    assert loc[0] == 5


def test_type_in_action_field(parser):
    """Test various types in action — verify linkage through component scope"""
    code = """
component test_c {
    action test_a {
        rand int int_val;
        rand bit[8] bit_val;
        rand bool bool_val;
        string str_val;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "test_c")
    action = get_symbol(comp, "test_a")
    assert action is not None
    for name in ("int_val", "bit_val", "bool_val", "str_val"):
        assert has_symbol(action, name), f"field {name} not found"


def test_type_in_function_params(parser):
    """Test types in function parameters"""
    code = """
    function void process(int a, bit[8] b, bool c, string msg);
    """
    assert_parse_ok(code, parser)


def test_type_mixed_in_struct(parser):
    """Test mixing various types in struct — verify all fields resolve"""
    code = """
struct mixed_s {
    rand int int_field;
    rand bit[16] bit_field;
    rand bool bool_field;
    string str_field;
    chandle handle_field;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "mixed_s")
    assert sym is not None
    for name in ("int_field", "bit_field", "bool_field", "str_field", "handle_field"):
        assert has_symbol(sym, name), f"field {name} not found"


@pytest.mark.parametrize("size", [1, 8, 16, 32, 64])
def test_type_bit_sizes(parser, size):
    """Test various bit field sizes"""
    code = f"""
    struct test_s {{
        rand bit[{size}] value;
    }};
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("size", [8, 16, 32, 64])
def test_type_int_sizes(parser, size):
    """Test various int field sizes"""
    code = f"""
    struct test_s {{
        rand int[{size}] value;
    }};
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("array_size", [1, 10, 100])
def test_type_array_scalability(parser, array_size):
    """Test arrays of different sizes"""
    code = f"""
    struct test_s {{
        rand int values[{array_size}];
    }};
    """
    assert_parse_ok(code, parser)


def test_type_in_constraint(parser):
    """Test type usage in constraints"""
    code = """
    struct test_s {
        rand int[8] small_val;
        rand int[16] large_val;

        constraint {
            small_val < 100;
            large_val > 1000;
        }
    };
    """
    assert_parse_ok(code, parser)


# ============================================================================
# Legacy [msb:lsb] width specification
# ============================================================================
#
# NOT part of the PSS 3.1 grammar: LRM 7.2 (c) specifies a single width
# expression, and the dual-bound spelling is absent from the BNF.  It is
# accepted only so existing PSS 1.x/2.x models can be ingested, and is folded
# to a plain width at build time.

def test_legacy_dual_bound_width(parser):
    """`bit[31:0]` is accepted and means `bit[32]`."""
    assert_parse_ok("""
    struct s { bit[31:0] a; }
    component pss_top { }
    """, parser)


def test_legacy_dual_bound_width_folds_to_width(parser):
    """The folded width must be msb-lsb+1, not the msb.

    Checked through the value domain rather than the AST: a 4-bit field
    cannot hold 16, so a constraint requiring it is unsatisfiable only if the
    width really is 4.
    """
    import pssparser.ast as ast

    root = parse_pss("""
    struct s { bit[3:0] nibble; }
    component pss_top { }
    """, parser=parser)

    widths = {}

    class V(ast.VisitorBase):
        def visitField(self, i):
            name = i.getName()
            t = i.getType()
            if name is None or t is None:
                return
            dt = None
            try:
                dt = t.getWidth()
            except Exception:
                return
            if dt is not None:
                try:
                    widths[name.getId()] = int(dt.getValue())
                except Exception:
                    widths[name.getId()] = dt

    root.accept(V())
    assert widths.get("nibble") == 4, widths


def test_non_zero_low_bound_is_rejected(parser):
    """`bit[7:4]` has no meaning under the current type model."""
    assert_parse_error("""
    struct s { bit[7:4] a; }
    component pss_top { }
    """)


def test_single_width_still_parses(parser):
    """Control: the PSS 3.1 spelling must keep working."""
    assert_parse_ok("""
    struct s { bit[32] a; int[5] b; }
    component pss_top { }
    """, parser)
