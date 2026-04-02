"""
Tests for PSS components
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for test_helpers
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok,
    generate_components
)


def test_empty_component(parser):
    """Test parsing of empty component"""
    code = """
        component C {
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(root, "C")


def test_component_with_action(parser):
    """Test component containing an action"""
    code = """
        component pss_top {
            action A {
                rand int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert pss_top is not None
    assert has_symbol(pss_top, "A")


def test_multiple_components(parser):
    """Test multiple components at top level"""
    code = """
        component A { }
        component B { }
        component pss_top { }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "A")
    assert has_symbol(root, "B")
    assert has_symbol(root, "pss_top")


def test_component_inheritance(parser):
    """Test component inheritance"""
    code = """
        component Base {
            action A { }
        }
        
        component Derived : Base {
            action B { }
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Base")
    assert has_symbol(root, "Derived")


def test_component_with_component_field(parser):
    """Test component containing another component as a field"""
    code = """
        component Inner {
            action A { }
        }
        
        component Outer {
            Inner inner_inst;
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Inner")
    assert has_symbol(root, "Outer")


def test_component_with_struct(parser):
    """Test component with struct definition"""
    code = """
        component pss_top {
            struct Point {
                int x;
                int y;
            }
            
            action Move {
                Point dest;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert has_symbol(pss_top, "Point")
    assert has_symbol(pss_top, "Move")


def test_pure_component(parser):
    """Test pure component modifier"""
    code = """
        pure component Utility {
            action Helper { }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(root, "Utility")


@pytest.mark.parametrize("num_components", [5, 10, 20])
def test_many_components(parser, num_components):
    """Test parsing many components"""
    code = generate_components(num_components)
    root = parse_pss(code, parser=parser)
    
    for i in range(num_components):
        assert has_symbol(root, f"C{i}"), f"Component C{i} not found"


def test_component_with_field(parser):
    """Test component with field"""
    code = """
        component Inner { }
        
        component Outer {
            Inner inst;
        }
    """
    root = parse_pss(code, parser=parser)
    
    assert has_symbol(root, "Inner")
    assert has_symbol(root, "Outer")


def test_component_extension(parser):
    """Test component extension"""
    code = """
        component Base {
            action A { }
        }
        
        extend component Base {
            action B { }
        }
    """
    root = parse_pss(code, parser=parser)
    base = get_symbol(root, "Base")
    
    assert base is not None
    # After extension, both actions should be accessible
    assert has_symbol(base, "A")
    assert has_symbol(base, "B")


def test_pss_top_component(parser):
    """Test pss_top component (standard entry point)"""
    code = """
        component pss_top {
            action entry {
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    
    assert pss_top is not None
    assert has_symbol(pss_top, "entry")


# =============================================================================
# Pure Components
# =============================================================================

def test_pure_component_with_functions(parser):
    """Test pure component with pure functions"""
    code = """
        pure component MathUtils {
            pure function int add(int a, int b) {
                return a + b;
            }
            
            pure function int multiply(int a, int b) {
                return a * b;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_pure_component_no_actions(parser):
    """Test that pure component can have only functions"""
    code = """
        pure component Utilities {
            pure function int square(int x) {
                return x * x;
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component Pools and Resources
# =============================================================================

def test_component_with_resource_pool(parser):
    """Test component with resource pool"""
    code = """
        resource CPU { }
        
        component pss_top {
            pool CPU cpus;
            
            action Task {
                lock CPU cpu;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_multiple_pools(parser):
    """Test component with multiple resource pools"""
    code = """
        resource CPU { }
        resource Memory { }
        resource Bus { }
        
        component System {
            pool CPU cpus;
            pool Memory mem_banks;
            pool Bus buses;
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component Nesting and Composition
# =============================================================================

def test_deeply_nested_components(parser):
    """Test deeply nested component hierarchy"""
    code = """
        component Level1 {
            action A1 { }
        }
        
        component Level2 {
            Level1 l1;
            action A2 { }
        }
        
        component Level3 {
            Level2 l2;
            action A3 { }
        }
        
        component Level4 {
            Level3 l3;
            action A4 { }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_multiple_instances(parser):
    """Test component with multiple instances of same type"""
    code = """
        component Worker {
            action DoWork { }
        }
        
        component Parallel {
            Worker w1;
            Worker w2;
            Worker w3;
            Worker w4;
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_array_instances(parser):
    """Test component with array of component instances"""
    code = """
        component Worker {
            action DoWork { }
        }
        
        component Pool {
            Worker workers[8];
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component Functions
# =============================================================================

def test_component_with_functions(parser):
    """Test component with function declarations"""
    code = """
        component pss_top {
            function void setup() {
                // Setup code
            }
            
            function int calculate(int x) {
                return x * 2;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_import_functions(parser):
    """Test component with import functions"""
    code = """
        component pss_top {
            import function void external_init();
            import function int external_compute(int val);
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_export_functions(parser):
    """Test component with export actions (LRM §22.9)"""
    code = """
        component pss_top {
            action DoWork { rand int size; }
            export DoWork(int size);
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component with Multiple Features
# =============================================================================

def test_component_with_enums(parser):
    """Test component with enum declarations"""
    code = """
        component pss_top {
            enum State {
                IDLE, ACTIVE, DONE
            }
            
            action Task {
                State current_state;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_typedef(parser):
    """Test component with typedef"""
    code = """
        component pss_top {
            typedef bit[32] word_t;
            
            action Process {
                word_t data;
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_covergroups(parser):
    """Test component with covergroup"""
    code = """
        component pss_top {
            covergroup CG(int val) {
                coverpoint val;
            }
            
            action Task {
                rand int x;
                CG cg(x);
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_exec_blocks(parser):
    """Test component with exec blocks"""
    code = """
        component pss_top {
            exec init_down {
                // Initialization
            }
            
            exec init_up {
                // Post-initialization
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component Compile-time Features
# =============================================================================

def test_component_with_compile_if(parser):
    """Test component with compile if"""
    code = """
        component pss_top {
            compile if (1) {
                action Feature1 { }
            } else {
                action Feature2 { }
            }
        }
    """
    assert_parse_ok(code, parser)


def test_component_with_compile_assert(parser):
    """Test component with compile assert"""
    code = """
        component pss_top {
            compile assert(1, "Configuration valid");
            
            action Task { }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Component Override
# =============================================================================

def test_component_with_override_block(parser):
    """Test component with override block"""
    code = """
        component Base {
            action A { }
            action B { }
        }
        
        component Derived : Base { }
        
        component Top {
            Derived d;
            
            override {
                type Base with Derived;
            }
        }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Complex Scenarios
# =============================================================================

def test_component_comprehensive(parser):
    """Test component with many features combined"""
    code = """
        resource CPU { }
        buffer DataBuf { int size; }
        
        component SubSystem {
            enum Mode { FAST, SLOW }
            
            struct Config {
                Mode mode;
                int threshold;
            }
            
            pool CPU processors;
            
            action Process {
                lock CPU cpu;
                input DataBuf in_buf;
                output DataBuf out_buf;
                Config cfg;
                
                constraint {
                    cfg.threshold > 0;
                }
            }
            
            function void init() {
                // Initialization
            }
            
            covergroup CG(Mode m) {
                coverpoint m;
            }
        }
        
        component pss_top {
            SubSystem sys1;
            SubSystem sys2;
            
            action Entry {
                SubSystem::Process p;
                
                activity {
                    p;
                }
            }
        }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("depth", [2, 3, 4])
def test_component_hierarchy_scalability(parser, depth):
    """Test nested component hierarchy at various depths"""
    # Build nested structure
    code_parts = []
    for i in range(depth):
        if i == 0:
            code_parts.append(f"component Level{i} {{ action A{i} {{ }} }}")
        else:
            code_parts.append(f"component Level{i} {{ Level{i-1} l{i-1}; action A{i} {{ }} }}")
    
    code = "\n".join(code_parts)
    assert_parse_ok(code, parser)
