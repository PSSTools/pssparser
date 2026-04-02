"""
Tests for PSS pure functions.

Tests pure function declarations and restrictions:
- Pure function syntax
- Pure functions in components/structs
- Restrictions: no void, no output/inout params
- Pure function inheritance rules

Based on PSS LRM v3.0 function declaration syntax.

Limitations:
- Cannot test actual purity enforcement (requires execution)
- Cannot test optimization behavior
- Pure keyword behavior is primarily a semantic hint
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Basic Pure Function Tests
# ============================================================================

def test_pure_function_basic():
    """Test basic pure function declaration."""
    pss = """
component MyComponent {
    pure function int get_value() {
        return 42;
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_pure_function_with_params():
    """Test pure function with parameters."""
    pss = """
    component MyComponent {
        pure function int add(int a, int b) {
            return a + b;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_no_params():
    """Test pure function with no parameters."""
    pss = """
    component MyComponent {
        pure function int get_constant() {
            return 100;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_string_return():
    """Test pure function returning string."""
    pss = """
    component MyComponent {
        pure function string get_name() {
            return "test";
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_bool_return():
    """Test pure function returning bool."""
    pss = """
    component MyComponent {
        pure function bool is_valid(int x) {
            return x > 0;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_bit_return():
    """Test pure function returning bit."""
    pss = """
    component MyComponent {
        pure function bit[32] get_mask() {
            return 0xFFFFFFFF;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Pure Functions in Different Contexts
# ============================================================================


def test_multiple_pure_functions():
    """Test multiple pure functions in component."""
    pss = """
    component MyComponent {
        pure function int func1() {
            return 1;
        }
        
        pure function int func2() {
            return 2;
        }
        
        pure function int func3() {
            return 3;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_and_non_pure_mix():
    """Test mixing pure and non-pure functions."""
    pss = """
    component MyComponent {
        pure function int get_value() {
            return 42;
        }
        
        function void set_value(int x) {
        }
        
        pure function bool is_valid() {
            return true;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Pure Static Functions
# ============================================================================

def test_pure_static_function():
    """Test pure static function."""
    pss = """
    component MyComponent {
        pure static function int compute(int a, int b) {
            return a + b;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_struct_param():
    """Test pure function with struct parameter."""
    pss = """
    struct point_s {
        int x;
        int y;
    }
    
    component MyComponent {
        pure function int distance(point_s p1, point_s p2) {
            return 0;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_multiple_params():
    """Test pure function with multiple parameters of different types."""
    pss = """
    component MyComponent {
        pure function int calculate(int a, bit[8] b, bool flag, string name) {
            return 0;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Pure Function Return Types
# ============================================================================

def test_pure_function_struct_return():
    """Test pure function returning struct."""
    pss = """
    struct result_s {
        int value;
        bool valid;
    }
    
    component MyComponent {
        pure function result_s get_result() {
            result_s r;
            return r;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_enum_return():
    """Test pure function returning enum."""
    pss = """
    enum status_e {IDLE, BUSY, ERROR}
    
    component MyComponent {
        pure function status_e get_status() {
            return IDLE;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Pure Functions with Complex Logic
# ============================================================================

def test_pure_function_with_if_else():
    """Test pure function with if-else logic."""
    pss = """
    component MyComponent {
        pure function int abs(int x) {
            if (x < 0) {
                return -x;
            } else {
                return x;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_with_loop():
    """Test pure function with loop."""
    pss = """
    component MyComponent {
        pure function int factorial(int n) {
            int result = 1;
            int i = 1;
            while (i <= n) {
                result = result * i;
                i = i + 1;
            }
            return result;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_pure_function_with_local_vars():
    """Test pure function with local variables."""
    pss = """
    component MyComponent {
        pure function int compute(int a, int b) {
            int temp1 = a * 2;
            int temp2 = b * 3;
            int result = temp1 + temp2;
            return result;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Pure Functions in Inheritance
# ============================================================================


@pytest.mark.parametrize("func_count", [3, 6, 10])
def test_scalability_multiple_pure_functions(func_count):
    """Test component with multiple pure functions."""
    functions = "\n".join([f"""        pure function int func{i}() {{
            return {i};
        }}""" for i in range(func_count)])
    
    pss = f"""
    component MyComponent {{
{functions}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("param_count", [2, 5, 8])
def test_scalability_pure_function_params(param_count):
    """Test pure function with many parameters."""
    params = ", ".join([f"int p{i}" for i in range(param_count)])
    
    pss = f"""
    component MyComponent {{
        pure function int compute({params}) {{
            return 0;
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 3, 4])
def test_scalability_pure_function_nesting(nesting_depth):
    """Test pure function with nested control flow."""
    def generate_nested(depth):
        if depth == 0:
            return "                return 0;"
        indent = "    " * depth
        return f"{indent}if (x > 0) {{\n{generate_nested(depth - 1)}\n{indent}}}"
    
    nested = generate_nested(nesting_depth)
    
    pss = f"""
    component MyComponent {{
        pure function int nested(int x) {{
{nested}
            return -1;
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None
