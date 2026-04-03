"""
Tests for PSS address spaces and address allocation.

Tests address space syntax including:
- Address space component declarations (contiguous, transparent)
- Custom address traits
- Address regions (basic, transparent, with traits)
- Address claims in actions
- Integration with constraints and resources
- Hierarchical address space structures

Based on PSS LRM v3.0 Section 24.7-24.8 (Address Spaces and Allocation).

Note: These tests cover SYNTAX only. Runtime behavior (allocation, matching,
memory access) requires solver/execution engine and cannot be tested here.

Standard Library: Requires addr_reg_pkg (available in src/stdlib/addr_reg_pkg.pss)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Basic Address Space Tests
# ============================================================================

def test_contiguous_addr_space_basic():
    """Test basic contiguous address space declaration."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        contiguous_addr_space_c<> sys_mem;
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "my_system")
    assert comp is not None
    assert has_symbol(comp, "sys_mem")


def test_transparent_addr_space_basic():
    """Test basic transparent address space declaration."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        transparent_addr_space_c<> trans_mem;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_addr_spaces():
    """Test multiple address spaces in component."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        contiguous_addr_space_c<> sys_mem;
        contiguous_addr_space_c<> io_mem;
        transparent_addr_space_c<> rom;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_space_array():
    """Test array of address spaces."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        contiguous_addr_space_c<> memory_banks[4];
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Address Trait Tests
# ============================================================================

def test_custom_addr_trait():
    """Test custom address trait definition."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] mem_type;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_space_with_custom_trait():
    """Test address space with custom trait."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] mem_type;
        rand bit[32] latency;
    }
    
    component my_system {
        contiguous_addr_space_c<mem_trait_s> typed_mem;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_transparent_addr_space_with_trait():
    """Test transparent address space with custom trait."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[4] region_id;
    }
    
    component my_system {
        transparent_addr_space_c<mem_trait_s> trans_typed_mem;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_complex_addr_trait():
    """Test complex address trait with multiple fields."""
    pss = """
    import addr_reg_pkg::*;
    
    struct advanced_mem_trait_s : addr_trait_s {
        rand bit[8] mem_type;
        rand bit[32] base_latency_ns;
        rand bit[16] burst_size;
        rand bool cacheable;
        rand bool prefetchable;
    }
    
    component my_system {
        contiguous_addr_space_c<advanced_mem_trait_s> advanced_mem;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Address Region Tests
# ============================================================================

def test_addr_region_basic():
    """Test basic address region declaration."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        addr_region_s<> region1;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_region_with_trait():
    """Test address region with custom trait."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[4] priority;
    }
    
    component my_system {
        addr_region_s<mem_trait_s> priority_region;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_addr_regions():
    """Test multiple address regions."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        addr_region_s<> sram_region;
        addr_region_s<> dram_region;
        addr_region_s<> rom_region;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_transparent_addr_region():
    """Test transparent address region."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        transparent_addr_region_s<> fixed_region;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_transparent_region_with_trait():
    """Test transparent region with custom trait."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] region_type;
    }
    
    component my_system {
        transparent_addr_region_s<mem_trait_s> typed_fixed_region;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_region_array():
    """Test array of address regions."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        addr_region_s<> regions[8];
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Address Claim Tests
# ============================================================================

def test_addr_claim_in_action():
    """Test address claim in action."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action memory_op {
            addr_claim_s<> mem_claim;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_claim_with_size_constraint():
    """Test address claim with size constraint."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action memory_op {
            addr_claim_s<> mem_claim;
            
            constraint mem_claim.size == 1024;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_claim_with_trait():
    """Test address claim with custom trait."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] priority;
    }
    
    component my_system {
        action memory_op {
            addr_claim_s<mem_trait_s> priority_claim;
            
            constraint priority_claim.trait.priority > 5;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_claim_permanent_flag():
    """Test address claim with permanent flag."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action memory_op {
            addr_claim_s<> mem_claim;
            
            constraint mem_claim.permanent == false;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_addr_claims():
    """Test multiple address claims in action."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action dual_memory_op {
            addr_claim_s<> read_claim;
            addr_claim_s<> write_claim;
            
            constraint read_claim.size == 512;
            constraint write_claim.size == 256;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_transparent_addr_claim():
    """Test transparent address claim."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action fixed_addr_op {
            transparent_addr_claim_s<> trans_claim;
            
            constraint trans_claim.size == 512;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_transparent_claim_with_addr_constraint():
    """Test transparent claim with address constraint."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action fixed_addr_op {
            transparent_addr_claim_s<> trans_claim;
            
            constraint trans_claim.size == 512;
            constraint trans_claim.addr >= 0x1000;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_claim_array():
    """Test array of address claims."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action multi_mem_op {
            addr_claim_s<> claims[4];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Address Handle Tests (Syntax Only)
# ============================================================================

def test_addr_handle_declaration():
    """Test address handle type declaration."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        action test {
            addr_handle_t base_addr;
            addr_handle_t offset_addr;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_handle_in_struct():
    """Test address handle in struct."""
    pss = """
    import addr_reg_pkg::*;
    
    struct memory_descriptor_s {
        addr_handle_t base;
        bit[32] size;
    }
    
    component my_system {
        action test {
            memory_descriptor_s desc;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Integration Tests
# ============================================================================

def test_addr_space_with_regions_and_claims():
    """Test address space with regions and claims integration."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] mem_type;
    }
    
    component my_system {
        contiguous_addr_space_c<mem_trait_s> memory;
        
        addr_region_s<mem_trait_s> fast_region;
        addr_region_s<mem_trait_s> slow_region;
        
        action memory_op {
            addr_claim_s<mem_trait_s> mem_claim;
            
            constraint mem_claim.size == 1024;
            constraint mem_claim.trait.mem_type == 0;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_hierarchical_addr_spaces():
    """Test address spaces in hierarchical components."""
    pss = """
    import addr_reg_pkg::*;
    
    component memory_subsystem {
        contiguous_addr_space_c<> local_mem;
        addr_region_s<> cache_region;
    }
    
    component soc {
        memory_subsystem cpu_mem;
        memory_subsystem gpu_mem;
        
        contiguous_addr_space_c<> shared_mem;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_space_with_multiple_trait_types():
    """Test system with multiple trait types."""
    pss = """
    import addr_reg_pkg::*;
    
    struct fast_mem_trait_s : addr_trait_s {
        rand bit[4] cache_level;
    }
    
    struct slow_mem_trait_s : addr_trait_s {
        rand bit[16] latency_ns;
    }
    
    component my_system {
        contiguous_addr_space_c<fast_mem_trait_s> cache_mem;
        contiguous_addr_space_c<slow_mem_trait_s> dram_mem;
        
        action fast_op {
            addr_claim_s<fast_mem_trait_s> fast_claim;
        }
        
        action slow_op {
            addr_claim_s<slow_mem_trait_s> slow_claim;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_mixed_contiguous_and_transparent():
    """Test mixed contiguous and transparent address spaces."""
    pss = """
    import addr_reg_pkg::*;
    
    component my_system {
        contiguous_addr_space_c<> dynamic_mem;
        transparent_addr_space_c<> fixed_rom;
        
        addr_region_s<> dynamic_region;
        transparent_addr_region_s<> rom_region;
        
        action dynamic_op {
            addr_claim_s<> dyn_claim;
        }
        
        action fixed_op {
            transparent_addr_claim_s<> fix_claim;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_addr_space_with_actions_and_constraints():
    """Test complex address space scenario with actions and constraints."""
    pss = """
    import addr_reg_pkg::*;
    
    struct mem_trait_s : addr_trait_s {
        rand bit[8] priority;
        rand bit[4] mem_type;
    }
    
    component my_system {
        contiguous_addr_space_c<mem_trait_s> system_memory;
        
        addr_region_s<mem_trait_s> high_priority_region;
        addr_region_s<mem_trait_s> low_priority_region;
        
        action critical_op {
            addr_claim_s<mem_trait_s> mem_claim;
            
            constraint mem_claim.size == 2048;
            constraint mem_claim.trait.priority >= 7;
            constraint mem_claim.trait.mem_type == 1;
        }
        
        action normal_op {
            addr_claim_s<mem_trait_s> mem_claim;
            
            constraint mem_claim.size in [512, 1024, 2048];
            constraint mem_claim.trait.priority < 5;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.parametrize("addr_space_count", [2, 4, 6])
def test_scalability_multiple_addr_spaces(addr_space_count):
    """Test component with multiple address spaces."""
    addr_spaces = "\n".join([f"        contiguous_addr_space_c<> mem{i};" 
                              for i in range(addr_space_count)])
    
    pss = f"""
    import addr_reg_pkg::*;
    
    component my_system {{
{addr_spaces}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("region_count", [3, 6, 10])
def test_scalability_multiple_regions(region_count):
    """Test address space with multiple regions."""
    regions = "\n".join([f"        addr_region_s<> region{i};" 
                         for i in range(region_count)])
    
    pss = f"""
    import addr_reg_pkg::*;
    
    component my_system {{
{regions}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("claim_count", [2, 4, 6])
def test_scalability_multiple_claims(claim_count):
    """Test action with multiple address claims."""
    claims = "\n".join([f"            addr_claim_s<> claim{i};" 
                        for i in range(claim_count)])
    
    pss = f"""
    import addr_reg_pkg::*;
    
    component my_system {{
        action multi_claim_op {{
{claims}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("trait_field_count", [2, 5, 8])
def test_scalability_complex_trait(trait_field_count):
    """Test address trait with many fields."""
    fields = "\n".join([f"        rand bit[8] field{i};" 
                        for i in range(trait_field_count)])
    
    pss = f"""
    import addr_reg_pkg::*;
    
    struct complex_trait_s : addr_trait_s {{
{fields}
    }}
    
    component my_system {{
        contiguous_addr_space_c<complex_trait_s> complex_mem;
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None
