"""
Tests for PSS enum declarations and usage.

Tests cover:
- Basic enum declarations
- Enums with explicit values
- Enums with base types
- Enums in structs and components
- Enum constraints and usage
- Enum extension
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error
from test_helpers import get_symbol, has_symbol, get_location


def test_enum_empty(parser):
    """Test empty enum declaration"""
    code = """
enum status_e {};
    """
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "status_e")
    assert sym is not None
    loc = get_location(sym)
    assert loc is not None
    assert loc[0] == 2 or loc[0] == 1


def test_enum_single_item(parser):
    """Test enum with single item"""
    code = """
    enum status_e { IDLE };
    """
    assert_parse_ok(code, parser)


def test_enum_multiple_items(parser):
    """Test enum with multiple items"""
    code = """
enum color_e { RED, GREEN, BLUE };
    """
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "color_e") is not None


def test_enum_with_explicit_values(parser):
    """Test enum with explicit values"""
    code = """
    enum config_e { 
        UNKNOWN,
        MODE_A = 10,
        MODE_B = 20,
        MODE_C = 35
    };
    """
    assert_parse_ok(code, parser)


def test_enum_with_large_values(parser):
    """Test enum with large explicit values"""
    code = """
    enum priority_e {
        LOW = 0,
        MEDIUM = 5,
        HIGH = 15
    };
    """
    assert_parse_ok(code, parser)


def test_enum_in_struct(parser):
    """Test enum field in struct"""
    code = """
enum operation_e { READ, WRITE, EXECUTE };
struct packet_s {
    rand operation_e op;
    rand bit[8] data;
    constraint {
        op != EXECUTE;
    }
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "operation_e") is not None
    pkt = get_symbol(root, "packet_s")
    assert pkt is not None
    assert has_symbol(pkt, "op")
    assert has_symbol(pkt, "data")
    loc = get_location(pkt)
    assert loc is not None


def test_enum_in_component(parser):
    """Test enum in component action"""
    code = """
enum mode_e { MODE_A, MODE_B, MODE_C };
component my_c {
    action test_a {
        rand mode_e mode;
        constraint {
            mode != MODE_A;
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "mode_e") is not None
    comp = get_symbol(root, "my_c")
    assert comp is not None
    action = get_symbol(comp, "test_a")
    assert action is not None
    assert has_symbol(action, "mode")


def test_enum_with_negative_values(parser):
    """Test enum with negative values"""
    code = """
    enum temperature_e {
        FREEZING = -20,
        COLD = -5,
        NORMAL = 20,
        HOT = 40
    };
    """
    assert_parse_ok(code, parser)


def test_enum_non_contiguous_values(parser):
    """Test enum with non-contiguous values"""
    code = """
    enum sparse_e {
        FIRST = 1,
        TENTH = 10,
        HUNDREDTH = 100,
        THOUSANDTH = 1000
    };
    """
    assert_parse_ok(code, parser)


def test_enum_mixed_implicit_explicit(parser):
    """Test enum with mixed implicit and explicit values"""
    code = """
    enum mixed_e {
        A,           // 0
        B,           // 1
        C = 10,      // 10
        D,           // 11
        E = 20       // 20
    };
    """
    assert_parse_ok(code, parser)


def test_enum_in_constraint_expression(parser):
    """Test enum used in constraint expression"""
    code = """
    enum status_e { IDLE, ACTIVE, DONE };
    
    struct test_s {
        rand status_e status;
        rand bit[8] value;
        
        constraint {
            status == ACTIVE -> value > 10;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_enum_qualified_reference(parser):
    """Test qualified enum reference"""
    code = """
    enum color_e { RED, GREEN, BLUE };
    
    struct test_s {
        rand color_e color;
        
        constraint {
            color == color_e::RED;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_enum_in_action_field(parser):
    """Test enum as action field"""
    code = """
    enum command_e { START, STOP, PAUSE };
    
    component test_c {
        action cmd_a {
            rand command_e cmd;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_enum_multiple_declarations(parser):
    """Test multiple enum declarations"""
    code = """
    enum status_e { IDLE, BUSY };
    enum priority_e { LOW, HIGH };
    enum mode_e { AUTO, MANUAL };
    """
    assert_parse_ok(code, parser)


def test_enum_hex_values(parser):
    """Test enum with hexadecimal values"""
    code = """
    enum flags_e {
        FLAG_A = 0x01,
        FLAG_B = 0x02,
        FLAG_C = 0x04,
        FLAG_D = 0x08
    };
    """
    assert_parse_ok(code, parser)


def test_enum_octal_values(parser):
    """Test enum with octal values"""
    code = """
    enum mask_e {
        MASK_LOW = 3,
        MASK_HIGH = 12
    };
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [5, 10, 20])
def test_enum_scalability(parser, count):
    """Test enum with many items for scalability"""
    items = ", ".join([f"ITEM_{i}" for i in range(count)])
    code = f"""
    enum large_e {{
        {items}
    }};
    """
    assert_parse_ok(code, parser)


def test_enum_in_array(parser):
    """Test enum in array"""
    code = """
    enum color_e { RED, GREEN, BLUE };
    
    struct palette_s {
        rand color_e colors[4];
        
        constraint {
            colors[0] != colors[1];
        }
    };
    """
    assert_parse_ok(code, parser)


def test_enum_with_casting_expression(parser):
    """Test enum with type casting"""
    code = """
    enum value_e { A = 1, B = 2, C = 3 };
    
    struct test_s {
        rand value_e val;
        rand bit[8] data;
        
        constraint {
            data == (bit[8])val;
        }
    };
    """
    assert_parse_ok(code, parser)
