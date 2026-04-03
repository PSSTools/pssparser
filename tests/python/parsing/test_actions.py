"""
Tests for basic PSS actions - demonstrating pytest patterns
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok,
    assert_parse_error, assert_linked, generate_actions
)


def test_empty_action(parser):
    """Test parsing of empty action"""
    code = """
        component pss_top {
            action A {
            }
        }
    """
    root = parse_pss(code, parser=parser)
    
    # Verify component exists
    pss_top = assert_linked(root, "pss_top")
    
    # Verify action exists
    action_a = assert_linked(pss_top, "A")
    assert action_a is not None


def test_action_with_field(parser):
    """Test action with a field"""
    code = """
        component pss_top {
            action A {
                int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "A")


def test_action_with_rand_field(parser):
    """Test action with random field"""
    code = """
        component pss_top {
            action A {
                rand int x;
            }
        }
    """
    root = assert_parse_ok(code)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_action_with_constraint(parser):
    """Test action with constraint block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > 0;
                    x < 100;
                }
            }
        }
    """
    root = assert_parse_ok(code)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


@pytest.mark.parametrize("action_type,keyword", [
    ("action", "action"),
    ("abstract action", "abstract action"),
])
def test_action_types(parser, action_type, keyword):
    """Test different action type modifiers"""
    code = f"""
        component pss_top {{
            {keyword} A {{
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_inheritance(parser):
    """Test action inheritance"""
    code = """
        component pss_top {
            action Base {
                rand int x;
            }
            
            action Derived : Base {
                rand int y;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    # Both actions should exist
    assert has_symbol(pss_top, "Base")
    assert has_symbol(pss_top, "Derived")


def test_multiple_actions(parser):
    """Test multiple actions in component"""
    code = """
        component pss_top {
            action A { }
            action B { }
            action C { }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "A")
    assert has_symbol(pss_top, "B")
    assert has_symbol(pss_top, "C")


@pytest.mark.parametrize("num_actions", [10, 50, 100])
def test_many_actions(parser, num_actions):
    """Test parsing many actions"""
    code = generate_actions(num_actions)
    root = parse_pss(code, parser=parser)
    
    pss_top = get_symbol(root, "pss_top")
    assert pss_top is not None
    
    # Verify all actions exist
    for i in range(num_actions):
        assert has_symbol(pss_top, f"A{i}"), f"Action A{i} not found"


def test_action_with_exec_block(parser):
    """Test action with exec block"""
    code = """
        component pss_top {
            action A {
                exec body {
                    int x = 5;
                }
            }
        }
    """
    root = assert_parse_ok(code)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_invalid_syntax():
    """Test that invalid action syntax is rejected"""
    code = """
        component pss_top {
            action {  // Missing name
            }
        }
    """
    assert_parse_error(code)


def test_action_duplicate_name():
    """Test duplicate action names"""
    code = """
        component pss_top {
            action A { }
            action A { }  // Duplicate
        }
    """
    # This should parse but may fail at link time
    # TODO: Add proper duplicate checking when API available
    root = parse_pss(code)
    assert root is not None


def test_abstract_action(parser):
    """Test abstract action"""
    code = """
        component pss_top {
            abstract action A {
                rand int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_action_with_flow_objects(parser):
    """Test action with flow object fields (input/output)"""
    code = """
        buffer Data_t { };
        
        component pss_top {
            action A {
                input Data_t in_data;
                output Data_t out_data;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


# =============================================================================
# Export Actions
# =============================================================================

def test_export_action_basic(parser):
    """Test basic export action"""
    code = """
        component pss_top {
            action MyAction { }
            
            export MyAction();
        }
    """
    assert_parse_ok(code, parser)


def test_export_action_with_params(parser):
    """Test export action with parameters"""
    code = """
        component pss_top {
            action MyAction {
                rand int x;
            }
            
            export MyAction(int size, bool enable);
        }
    """
    assert_parse_ok(code, parser)


def test_export_action_multiple(parser):
    """Test multiple export actions"""
    code = """
        component pss_top {
            action ActionA { }
            action ActionB { }
            
            export ActionA();
            export ActionB();
            export ActionA(int val);
        }
    """
    assert_parse_ok(code, parser)


def test_export_action_with_platform_qualifier(parser):
    """Test export action with platform qualifier"""
    code = """
        component pss_top {
            action MyAction { }
            
            export target MyAction();
            export solve MyAction(int x);
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Activities
# =============================================================================

def test_action_with_activity_block(parser):
    """Test action with activity block"""
    code = """
        component pss_top {
            action Inner { }
            
            action Outer {
                Inner a1;
                Inner a2;
                
                activity {
                    a1;
                    a2;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_parallel_activity(parser):
    """Test action with parallel activity"""
    code = """
        component pss_top {
            action Task { }
            
            action Parallel_Test {
                Task t1, t2, t3;
                
                activity {
                    parallel {
                        t1;
                        t2;
                        t3;
                    }
                }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_schedule_activity(parser):
    """Test action with schedule activity"""
    code = """
        component pss_top {
            action Task { }
            
            action Scheduled {
                Task t1, t2;
                
                activity {
                    schedule {
                        t1;
                        t2;
                    }
                }
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Field Types
# =============================================================================

def test_action_with_various_field_types(parser):
    """Test action with different field types"""
    code = """
        component pss_top {
            struct S { int val; }
            enum E { A, B, C }
            
            action TestAction {
                int int_field;
                rand bit[8] bit_field;
                bool bool_field;
                string str_field;
                S struct_field;
                E enum_field;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_array_fields(parser):
    """Test action with array fields"""
    code = """
        component pss_top {
            action TestAction {
                int arr1[10];
                rand int arr2[5];
                bit[8] bytes[256];
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_lock_share_fields(parser):
    """Test action with lock/share resource fields"""
    code = """
        resource MyResource { }
        
        component pss_top {
            pool MyResource resources;
            
            action TestAction {
                lock MyResource res1;
                share MyResource res2;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_action_handle_fields(parser):
    """Test action with action handle fields"""
    code = """
        component pss_top {
            action Inner { }
            
            action Outer {
                Inner a1;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_action_handle_array(parser):
    """Test action with action handle array"""
    code = """
        component pss_top {
            action Inner { }
            
            action Outer {
                Inner a2[5];
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Override Declarations
# =============================================================================

def test_action_with_type_override(parser):
    """Test action with type override"""
    code = """
        component pss_top {
            action Base { }
            action Derived : Base { }
            
            action Container {
                Base b;
                
                override {
                    type Base with Derived;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_instance_override(parser):
    """Test action with instance override"""
    code = """
        component pss_top {
            action Base { }
            action Derived : Base { }
            
            action Container {
                Base b1;
                Base b2;
                
                override {
                    instance b1 with Derived;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Inheritance Advanced
# =============================================================================

def test_action_multi_level_inheritance(parser):
    """Test multi-level action inheritance"""
    code = """
        component pss_top {
            action Level1 {
                rand int a;
            }
            
            action Level2 : Level1 {
                rand int b;
            }
            
            action Level3 : Level2 {
                rand int c;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_abstract_inheritance(parser):
    """Test abstract action with inheritance"""
    code = """
        component pss_top {
            abstract action Base {
                rand int x;
            }
            
            action Concrete1 : Base {
                rand int y;
            }
            
            action Concrete2 : Base {
                rand int z;
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Covergroups
# =============================================================================

def test_action_with_covergroup_declaration(parser):
    """Test action with covergroup declaration"""
    code = """
        component pss_top {
            action TestAction {
                rand int val;
                
                covergroup cg {
                    coverpoint val;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_covergroup_instantiation(parser):
    """Test action with covergroup instantiation"""
    code = """
        component pss_top {
            covergroup MyCG(int x) {
                coverpoint x;
            }
            
            action TestAction {
                rand int val;
                
                MyCG cg1(val);
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Action Compile-time Features
# =============================================================================

def test_action_with_compile_if(parser):
    """Test action with compile if"""
    code = """
        component pss_top {
            action TestAction {
                compile if (1) {
                    rand int field1;
                } else {
                    rand int field2;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_action_with_compile_assert(parser):
    """Test action with compile assert"""
    code = """
        component pss_top {
            action TestAction {
                rand int val;
                
                compile assert(1, "This should always pass");
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Complex Action Scenarios
# =============================================================================


def test_action_comprehensive(parser):
    """Test action with multiple features combined"""
    code = """
        buffer DataBuf { int size; }
        resource CPU { }
        
        component pss_top {
            pool CPU cpus;
            
            action ProcessData {
                // Fields
                rand int size;
                input DataBuf in_data;
                output DataBuf out_data;
                lock CPU cpu;
                
                // Constraint
                constraint {
                    size > 0;
                    size < 1024;
                }
                
                // Activity
                activity {
                    // Processing happens here
                }
                
                // Exec blocks
                exec body {
                    int result = size * 2;
                }
                
                // Covergroup
                covergroup cg {
                    coverpoint size;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("num_fields", [5, 10, 20])
def test_action_scalability_fields(parser, num_fields):
    """Test action with many fields"""
    fields = "\n".join([f"                rand int field{i};" for i in range(num_fields)])
    code = f"""
        component pss_top {{
            action TestAction {{
{fields}
            }}
        }}
    """
    assert_parse_ok(code, parser)
