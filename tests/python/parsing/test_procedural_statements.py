"""
Tests for PSS procedural statements.

Tests procedural statements that can appear in exec blocks and functions:
- Yield statement (v3.0 - cooperative multitasking)
- Randomize statement with inline constraints
- Break/continue statements
- Return statements in different contexts
- Assignment statements (various forms)

Based on PSS LRM v3.0 Chapter 22 (Procedural Interface).

Limitations:
- Randomize with inline constraints may cause issues (similar to activity inline constraints)
- Yield only allowed in target exec blocks and functions
- Some procedural features require execution context to validate
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Yield Statement Tests (v3.0 - Section 22.7.14)
# ============================================================================

def test_yield_in_exec_body():
    """Test yield statement in exec body block."""
    pss = """
component MyComponent {
    action compute {
        exec body {
            yield;
        }
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    assert has_symbol(comp, "compute")
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_yield_in_while_loop():
    """Test yield in while loop (polling pattern)."""
    pss = """
    component MyComponent {
        action compute {
            exec body {
                while (true) {
                    yield;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_yield_in_function():
    """Test yield statement in function."""
    pss = """
    component MyComponent {
        function void polling_wait() {
            while (true) {
                yield;
            }
        }
        
        action compute {
            exec body {
                polling_wait();
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_yields():
    """Test multiple yield statements in exec block."""
    pss = """
    component MyComponent {
        action compute {
            exec body {
                yield;
                yield;
                yield;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_yield_with_control_flow():
    """Test yield with if/else control flow."""
    pss = """
    component MyComponent {
        action compute {
            exec body {
                if (true) {
                    yield;
                } else {
                    yield;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_yield_in_exec_pre_post():
    """Test yield in pre/post exec blocks."""
    pss = """
    component MyComponent {
        action compute {
            exec pre_solve {
                yield;
            }
            
            exec post_solve {
                yield;
            }
            
            exec body {
                yield;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Return Statement Tests
# ============================================================================

def test_return_void_function():
    """Test return in void function."""
    pss = """
    component MyComponent {
        function void do_work() {
            return;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_return_with_value():
    """Test return with value in function."""
    pss = """
    component MyComponent {
        function int get_value() {
            return 42;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_return_with_expression():
    """Test return with complex expression."""
    pss = """
    component MyComponent {
        function int calculate(int a, int b) {
            return a + b * 2;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_conditional_return():
    """Test conditional return statements."""
    pss = """
    component MyComponent {
        function int abs(int x) {
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


def test_multiple_returns():
    """Test multiple return paths."""
    pss = """
    component MyComponent {
        function int classify(int x) {
            if (x < 0) return 0;
            if (x == 0) return 1;
            return 2;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Break/Continue Statement Tests
# ============================================================================

def test_break_in_while():
    """Test break statement in while loop."""
    pss = """
    component MyComponent {
        function void process() {
            while (true) {
                break;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_continue_in_while():
    """Test continue statement in while loop."""
    pss = """
    component MyComponent {
        function void process() {
            while (true) {
                continue;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_break_continue_in_foreach():
    """Test break/continue in foreach loop."""
    pss = """
    component MyComponent {
        function void process() {
            int arr[10];
            foreach (arr[i]) {
                if (i == 5) break;
                if (i == 3) continue;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_nested_loops_with_break():
    """Test break in nested loops."""
    pss = """
    component MyComponent {
        function void process() {
            int arr[5];
            foreach (arr[i]) {
                while (true) {
                    break;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Assignment Statement Tests
# ============================================================================

def test_simple_assignment():
    """Test simple variable assignment."""
    pss = """
    component MyComponent {
        function void process() {
            int x;
            x = 10;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compound_assignments():
    """Test compound assignment operators."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 10;
            x += 5;
            x -= 3;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_bitwise_compound_assignments():
    """Test bitwise compound assignments."""
    pss = """
    component MyComponent {
        function void process() {
            bit[8] x = 0xFF;
            x &= 0x0F;
            x |= 0x80;
            x <<= 2;
            x >>= 1;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_array_element_assignment():
    """Test array element assignment."""
    pss = """
    component MyComponent {
        function void process() {
            int arr[10];
            arr[0] = 42;
            arr[5] = arr[0] + 10;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_struct_field_assignment():
    """Test struct field assignment."""
    pss = """
    struct MyStruct {
        int field1;
        bit[8] field2;
    }
    
    component MyComponent {
        function void process() {
            MyStruct s;
            s.field1 = 100;
            s.field2 = 0xAB;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Variable Declaration with Initialization
# ============================================================================

def test_var_decl_with_init():
    """Test variable declaration with initialization."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 42;
            bit[8] y = 0xFF;
            bool flag = true;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_multiple_var_decls():
    """Test multiple variable declarations."""
    pss = """
    component MyComponent {
        function void process() {
            int a = 1, b = 2, c = 3;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_var_decl_with_expression():
    """Test variable declaration with expression."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 10;
            int y = x + 5;
            int z = x * y / 2;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Procedural If/While/Foreach Statements
# ============================================================================

def test_if_statement_basic():
    """Test basic if statement."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 10;
            if (x > 5) {
                x = 0;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_if_else_statement():
    """Test if-else statement."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 10;
            if (x > 5) {
                x = 0;
            } else {
                x = 100;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_if_else_if_chain():
    """Test if-else-if chain."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 10;
            if (x < 5) {
                x = 0;
            } else if (x < 10) {
                x = 5;
            } else if (x < 20) {
                x = 15;
            } else {
                x = 100;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_while_loop_basic():
    """Test basic while loop."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 0;
            while (x < 10) {
                x += 1;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_foreach_array():
    """Test foreach on array."""
    pss = """
    component MyComponent {
        function void process() {
            int arr[10];
            foreach (arr[i]) {
                arr[i] = i * 2;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_nested_control_flow():
    """Test nested control flow."""
    pss = """
    component MyComponent {
        function void process() {
            int arr[10];
            foreach (arr[i]) {
                if (i % 2 == 0) {
                    while (arr[i] < 100) {
                        arr[i] += 10;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Procedural Match Statement
# ============================================================================

def test_procedural_match():
    """Test procedural match statement."""
    pss = """
    component MyComponent {
        function void process() {
            int x = 5;
            match (x) {
                [0..3]: { x = 0; }
                [4..7]: { x = 1; }
                default: { x = 2; }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_procedural_match_multiple_cases():
    """Test procedural match with multiple cases."""
    pss = """
    component MyComponent {
        function void process() {
            bit[8] val = 0x42;
            match (val) {
                [0]: { val = 1; }
                [1]: { val = 2; }
                [2..10]: { val = 100; }
                [20,30,40]: { val = 200; }
                default: { val = 0; }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.parametrize("yield_count", [5, 10, 20])
def test_scalability_multiple_yields(yield_count):
    """Test multiple yield statements."""
    yields = "\n".join(["                yield;" for _ in range(yield_count)])
    
    pss = f"""
    component MyComponent {{
        action compute {{
            exec body {{
{yields}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("return_count", [3, 6, 10])
def test_scalability_multiple_returns(return_count):
    """Test function with multiple return paths."""
    returns = "\n".join([f"            if (x == {i}) return {i};" for i in range(return_count)])
    
    pss = f"""
    component MyComponent {{
        function int classify(int x) {{
{returns}
            return -1;
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 3, 4])
def test_scalability_nested_control_flow(nesting_depth):
    """Test deeply nested control flow."""
    def generate_nested(depth):
        if depth == 0:
            return "                x += 1;"
        indent = "    " * depth
        return f"{indent}if (x < 100) {{\n{generate_nested(depth - 1)}\n{indent}}}"
    
    nested = generate_nested(nesting_depth)
    
    pss = f"""
    component MyComponent {{
        function void process() {{
            int x = 0;
{nested}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None
