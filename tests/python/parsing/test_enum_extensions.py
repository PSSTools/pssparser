"""
Tests for PSS enum extensions (v3.0 feature).

Tests enum type extension capability introduced in PSS v3.0:
- Basic enum extensions
- Multiple extensions of same enum
- Extensions with explicit values
- Enum extensions across packages
- Extended enums in constraints

Based on PSS LRM v3.0 Section 20.2.4 (Enumeration type extensions).

Limitations:
- Cannot test runtime value behavior (parser-only tests)
- Cannot test enum extension resolution across actual multi-file projects
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Basic Enum Extension Tests
# ============================================================================

def test_enum_extension_basic():
    """Test basic enum extension."""
    pss = """
enum config_modes_e {MODE_A, MODE_B}
extend enum config_modes_e {MODE_C, MODE_D}
    """
    root = parse_pss(pss)
    sym = get_symbol(root, "config_modes_e")
    assert sym is not None


def test_enum_extension_with_values():
    """Test enum extension with explicit values."""
    pss = """
    enum config_modes_e {MODE_A=10, MODE_B=20}
    
    extend enum config_modes_e {MODE_C=30, MODE_D=50}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_empty_base():
    """Test extending enum declared without initial items."""
    pss = """
    enum mem_block_tag_e { }
    
    extend enum mem_block_tag_e {A_MEM, B_MEM}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_enum_extensions():
    """Test multiple extensions of same enum."""
    pss = """
    enum mem_block_tag_e {SYS_MEM}
    
    extend enum mem_block_tag_e {DDR}
    extend enum mem_block_tag_e {SRAM, FLASH}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_in_package():
    """Test enum extension in package context."""
    pss = """
    enum device_type_e {CPU, GPU}
    
    package my_pkg {
        extend enum device_type_e {DSP, FPGA}
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_multiple_packages():
    """Test enum extensions across multiple packages."""
    pss = """
    enum interrupt_type_e {IRQ, FIQ}
    
    package pkg1 {
        extend enum interrupt_type_e {NMI}
    }
    
    package pkg2 {
        extend enum interrupt_type_e {SMI, ABORT}
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Enum Extensions with Different Value Patterns
# ============================================================================

def test_enum_extension_sequential_values():
    """Test enum extension with sequential values."""
    pss = """
    enum priority_e {LOW=0, MEDIUM=1, HIGH=2}
    
    extend enum priority_e {CRITICAL=3, URGENT=4}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_sparse_values():
    """Test enum extension with sparse/non-contiguous values."""
    pss = """
    enum error_code_e {SUCCESS=0, ERROR=1}
    
    extend enum error_code_e {WARNING=100, FATAL=500}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_negative_values():
    """Test enum extension with negative values."""
    pss = """
    enum status_e {NORMAL=0, ERROR=-1}
    
    extend enum status_e {CRITICAL=-10, WARNING=-2}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_mixed_auto_explicit():
    """Test enum extension mixing auto and explicit values."""
    pss = """
    enum mode_e {A, B, C}
    
    extend enum mode_e {D, E=100, F}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Extended Enums in Usage Contexts
# ============================================================================

def test_extended_enum_in_struct():
    """Test extended enum used in struct."""
    pss = """
    enum color_e {RED, GREEN}
    
    extend enum color_e {BLUE, YELLOW}
    
    struct MyStruct {
        color_e primary_color;
        color_e secondary_color;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_extended_enum_in_action():
    """Test extended enum used in action."""
    pss = """
    enum operation_e {READ, WRITE}
    
    extend enum operation_e {EXECUTE, DELETE}
    
    component MyComponent {
        action my_action {
            rand operation_e op;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_extended_enum_in_constraint():
    """Test extended enum in constraint."""
    pss = """
    enum level_e {L0, L1}
    
    extend enum level_e {L2, L3}
    
    component MyComponent {
        action my_action {
            rand level_e level;
            
            constraint level in [L1, L2, L3];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_extended_enum_as_function_param():
    """Test extended enum as function parameter."""
    pss = """
    enum command_e {START, STOP}
    
    extend enum command_e {PAUSE, RESUME}
    
    component MyComponent {
        function void execute(command_e cmd) {
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_extended_enum_as_function_return():
    """Test extended enum as function return type."""
    pss = """
    enum state_e {IDLE, BUSY}
    
    extend enum state_e {ERROR, DONE}
    
    component MyComponent {
        function state_e get_state() {
            return IDLE;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Enum Extensions with Type Specifications
# ============================================================================


def test_multiple_enums_with_extensions():
    """Test multiple enums each with extensions."""
    pss = """
    enum type_a_e {A1, A2}
    enum type_b_e {B1, B2}
    
    extend enum type_a_e {A3, A4}
    extend enum type_b_e {B3, B4}
    extend enum type_a_e {A5}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_in_nested_package():
    """Test enum extension in nested package structure."""
    pss = """
    enum base_e {ITEM1, ITEM2}
    
    package outer {
        extend enum base_e {ITEM3}
        
        package inner {
            extend enum base_e {ITEM4, ITEM5}
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_enum_extension_with_struct_usage():
    """Test extended enum with comprehensive struct usage."""
    pss = """
    enum protocol_e {TCP, UDP}
    
    extend enum protocol_e {SCTP, DCCP}
    
    struct packet_s {
        rand protocol_e proto;
        bit[16] port;
        
        constraint proto != UDP;
    }
    
    component MyComponent {
        action send_packet {
            rand packet_s pkt;
            
            constraint pkt.proto in [TCP, SCTP];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.parametrize("extension_count", [2, 4, 6])
def test_scalability_multiple_extensions(extension_count):
    """Test enum with multiple extensions."""
    extensions = "\n".join([f"    extend enum base_e {{ITEM{i}}}" 
                           for i in range(extension_count)])
    
    pss = f"""
    enum base_e {{START}}
    
{extensions}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("item_count", [3, 6, 10])
def test_scalability_extension_items(item_count):
    """Test enum extension with many items."""
    items = ", ".join([f"ITEM{i}" for i in range(item_count)])
    
    pss = f"""
    enum base_e {{INITIAL}}
    
    extend enum base_e {{{items}}}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("enum_count", [3, 5, 8])
def test_scalability_multiple_enums_extended(enum_count):
    """Test multiple enums each with extensions."""
    enums = "\n".join([f"""    enum type{i}_e {{BASE{i}}}
    extend enum type{i}_e {{EXT{i}}}""" for i in range(enum_count)])
    
    pss = f"""
{enums}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None
