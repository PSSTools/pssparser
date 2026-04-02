"""
Executor tests for PSS parser.

Tests executor declarations, executor groups, traits, claims, and executor assignment patterns.
Based on PSS LRM v3.0 Section 24.6 (Executors).

Test categories:
- Basic executor declarations
- Executor traits (custom properties)
- Executor groups (grouping executors)
- Executor claims in actions
- Trait-constrained assignments
- Executor+resource combinations

Limitations:
- Executor standard library (executor_pkg) not available in parser
- Must define executor_trait_s, executor_c, executor_group_c locally
- Cannot test exec init_down/init_up blocks (require execution context)
- Cannot test actual executor assignment logic (requires solver)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


def test_executor_base_definitions():
    """Test basic executor type definitions."""
    pss = """
package executor_pkg {
    struct executor_trait_s { }
    struct empty_executor_trait_s : executor_trait_s { }
    component executor_base_c { }
}
    """
    root = parse_pss(pss)
    pkg = get_symbol(root, "executor_pkg")
    assert pkg is not None
    assert has_symbol(pkg, "executor_trait_s")
    assert has_symbol(pkg, "executor_base_c")


def test_executor_component_template():
    """Test executor_c template component."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct empty_executor_trait_s : executor_trait_s { }
        
        component executor_base_c { }
        
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_group_component():
    """Test executor group component declaration."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct empty_executor_trait_s : executor_trait_s { }
        
        component executor_base_c { }
        
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
        
        component executor_group_c {
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_custom_executor_trait():
    """Test custom executor trait with fields."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct my_core_trait_s : executor_trait_s {
            rand int cluster_id;
            rand bit[8] core_id;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_struct():
    """Test executor claim struct declaration."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct empty_executor_trait_s : executor_trait_s { }
        
        struct executor_claim_s {
            rand empty_executor_trait_s trait;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_instantiation():
    """Test basic executor instantiation in component."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        executor_c cpu1;
        executor_c cpu2;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_array():
    """Test executor array declaration."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        executor_c cores[8];
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_group_instantiation():
    """Test executor group instantiation."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
        component executor_group_c { }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        executor_c cores[4];
        executor_group_c all_cores;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_in_action():
    """Test executor claim field in action."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        struct executor_claim_s {
            rand empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        action compute {
            rand executor_claim_s ec;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_with_custom_trait():
    """Test executor claim with custom trait."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct my_core_trait_s : executor_trait_s {
            rand int cluster_id;
        }
        
        struct executor_claim_s {
            rand my_core_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        action compute {
            rand executor_claim_s core;
            
            constraint core.trait.cluster_id in [0..3];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_with_implication():
    """Test executor claim with implication constraint."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct my_core_trait_s : executor_trait_s {
            rand int cluster_id;
        }
        
        struct executor_claim_s {
            rand my_core_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        action compute {
            rand bit[8] priority;
            rand executor_claim_s core;
            
            constraint priority > 10 -> core.trait.cluster_id == 0;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_executors_in_component():
    """Test multiple executor types in component."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
        component executor_group_c { }
    }
    
    import executor_pkg::*;
    
    component soc {
        executor_c cpu_cores[4];
        executor_c gpu_cores[2];
        executor_c dsp;
        
        executor_group_c all_compute;
        executor_group_c cpu_group;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_in_hierarchical_component():
    """Test executors in hierarchical components."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component cluster {
        executor_c cores[2];
    }
    
    component soc {
        cluster cluster0;
        cluster cluster1;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_trait_with_multiple_fields():
    """Test executor trait with multiple field types."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        
        struct advanced_trait_s : executor_trait_s {
            rand int cluster_id;
            rand bit[8] core_id;
            rand bit[2] privilege_level;
            rand bool has_fpu;
            rand bit[32] frequency_mhz;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_in_multiple_actions():
    """Test executor claims in multiple actions."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        struct executor_claim_s {
            rand empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        action task_a {
            rand executor_claim_s ec;
        }
        
        action task_b {
            rand executor_claim_s ec;
        }
        
        action task_c {
            rand executor_claim_s ec;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_claim_array():
    """Test array of executor claims (simulated)."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        struct executor_claim_s {
            rand empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component my_chip {
        action parallel_compute {
            rand executor_claim_s claims[4];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_executor_with_inheritance():
    """Test executor component inheritance."""
    pss = """
    package executor_pkg {
        struct executor_trait_s { }
        struct empty_executor_trait_s : executor_trait_s { }
        component executor_base_c { }
        component executor_c : executor_base_c {
            empty_executor_trait_s trait;
        }
    }
    
    import executor_pkg::*;
    
    component specialized_executor_c : executor_c {
        bit[8] custom_id;
    }
    
    component my_chip {
        specialized_executor_c special_core;
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# Scalability tests

@pytest.mark.parametrize("executor_count", [2, 4, 8])
def test_scalability_multiple_executors(executor_count):
    """Test component with multiple executors."""
    executors = "\n".join([f"        executor_c core{i};" for i in range(executor_count)])
    
    pss = f"""
    package executor_pkg {{
        struct executor_trait_s {{ }}
        struct empty_executor_trait_s : executor_trait_s {{ }}
        component executor_base_c {{ }}
        component executor_c : executor_base_c {{
            empty_executor_trait_s trait;
        }}
    }}
    
    import executor_pkg::*;
    
    component my_chip {{
{executors}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("trait_field_count", [2, 5, 10])
def test_scalability_trait_fields(trait_field_count):
    """Test executor trait with many fields."""
    fields = "\n".join([f"            rand int field{i};" for i in range(trait_field_count)])
    
    pss = f"""
    package executor_pkg {{
        struct executor_trait_s {{ }}
        
        struct complex_trait_s : executor_trait_s {{
{fields}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("action_count", [3, 6, 10])
def test_scalability_executor_claims(action_count):
    """Test multiple actions with executor claims."""
    actions = "\n".join([f"""        action task{i} {{
            rand executor_claim_s ec;
        }}""" for i in range(action_count)])
    
    pss = f"""
    package executor_pkg {{
        struct executor_trait_s {{ }}
        struct empty_executor_trait_s : executor_trait_s {{ }}
        struct executor_claim_s {{
            rand empty_executor_trait_s trait;
        }}
    }}
    
    import executor_pkg::*;
    
    component my_chip {{
{actions}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None
