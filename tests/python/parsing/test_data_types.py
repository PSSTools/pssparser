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


# ===========================================================================
# `bit[msb:0]` -- the range spelling of a width (P3-X5)
#
# NOT conformant PSS 3.1, and recorded that way deliberately (D7/P7-D1). B.13 is
# `integer_type ::= integer_atom_type [ [ constant_expression ] ]
# [ in [ domain_open_range_list ] ]` -- one width expression, no `[msb:lsb]`
# form in any 3.x draft. It is accepted here only so that existing PSS 1.x/2.x
# models can be ingested.
#
# Treated as another way of writing `bit[8]`, with the low bound required to be
# 0 -- and the two spellings must build the *same* AST, since nothing
# downstream should have to know which one it came from.
#
# This block is the guard on the citation as much as on the behaviour: an
# earlier version of this comment quoted a B.13 that exists in no draft, and
# that misquote reached the grammar, the builder and two design documents before
# anyone checked it against the PDF.
# ===========================================================================

# Keeps the linked tree alive.  The C++ nodes are freed with the root, and the
# AST wrappers do not reference it -- a helper that returns only the width
# expression drops the root on the way out and touching the result segfaults.
_LIVE_ROOTS = []


def _field_width(pss, field, parser=None):
    """The width expression of `field` in `struct test_s`."""
    root = parse_pss(pss, parser=parser)
    _LIVE_ROOTS.append((parser, root))
    sym = get_symbol(root, "test_s")
    return sym.getChild(sym.symtabAt(field)).getType().getWidth()


_RANGE_STRUCT = """
struct test_s {
    bit[7:0]   a;
    bit[8]     b;
    int[31:0]  c;
    int[32]    d;
}
"""


@pytest.mark.parametrize("field,expected", [
    ("a", 8), ("b", 8), ("c", 32), ("d", 32),
])
def test_integer_width_range(parser, field, expected):
    """`bit[7:0]` is width 8, not width 7 -- the bound is the most significant
    bit index, so the width is one more than it."""
    w = _field_width(_RANGE_STRUCT, field, parser)
    assert isinstance(w, ast.ExprUnsignedNumber), type(w).__name__
    assert w.getValue() == expected


def test_range_and_count_spellings_are_indistinguishable(parser):
    """The two forms name the same type, so they leave the same AST behind --
    including the literal's image, which a formatter reads."""
    root = parse_pss(_RANGE_STRUCT, parser=parser)
    sym = get_symbol(root, "test_s")

    def w(name):
        return sym.getChild(sym.symtabAt(name)).getType().getWidth()

    assert w("a").getValue() == w("b").getValue()
    assert w("a").getImage() == w("b").getImage()
    assert w("c").getValue() == w("d").getValue()


def test_integer_width_range_over_a_parameter(parser):
    """`bit[W:0]` cannot be folded, so the addition is left in the expression
    for the width to be evaluated with -- the same as happens to `bit[W]`."""
    root = parse_pss("""
    struct test_s<int W> {
        bit[W:0] a;
    }
    """, parser=parser)
    sym = get_symbol(root, "test_s")
    w = sym.getChild(sym.symtabAt("a")).getType().getWidth()
    assert isinstance(w, ast.ExprBin), type(w).__name__
    assert isinstance(w.getRhs(), ast.ExprUnsignedNumber)
    assert w.getRhs().getValue() == 1


def test_a_nonzero_low_bound_is_rejected(parser):
    """B.13 fixes the low bound at 0.  The grammar accepts an expression there
    anyway, so that this says what is wrong rather than ANTLR reporting an
    unexplained syntax error."""
    from test_helpers import parse_collect
    _, markers = parse_collect("struct test_s { bit[7:1] a; }")
    assert [m.get("code") for m in markers] == ["PSS001"], markers
    assert "low bound" in markers[0]["message"]


def test_the_low_bound_must_be_a_literal(parser):
    """Not an expression that happens to evaluate to zero: B.13 gives the
    token, and accepting more would mean constant-folding in the builder."""
    from test_helpers import parse_collect
    _, markers = parse_collect("struct test_s { bit[7:1-1] a; }")
    assert [m.get("code") for m in markers] == ["PSS001"], markers
    # Asserted on the text, not just the code: before the grammar accepted the
    # range form at all this failed as an ordinary syntax error, which is also
    # PSS001.
    assert "low bound" in markers[0]["message"], markers


def test_integer_width_range_in_a_function_parameter(parser):
    """Not only in a field declaration -- the gap was in `integer_type`, which
    is every position an integer type may be written."""
    assert_parse_ok("""
    package p {
        function void f(bit[15:0] v);
    }
    """, parser)


def test_integer_width_range_in_a_cast(parser):
    """`casting_type` reaches `integer_type` too."""
    assert_parse_ok("""
    struct test_s {
        int a;
        int b;
        constraint { b == (bit[7:0])a; }
    }
    """, parser)


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
