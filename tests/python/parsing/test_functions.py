"""
Tests for PSS function declarations and usage.

Tests cover:
- Basic function declarations
- Function parameters and return types
- Pure functions
- Import functions
- Platform qualifiers (solve, target)
- Functions in different contexts
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_function_void_no_params(parser):
    """Test void function with no parameters"""
    code = """
    function void my_func();
    """
    root = parse_pss(code, parser=parser)
    assert root is not None


def test_function_int_return(parser):
    """Test function returning int"""
    code = """
    function int get_value();
    """
    assert_parse_ok(code, parser)


def test_function_with_single_param(parser):
    """Test function with single parameter"""
    code = """
    function int compute(int value);
    """
    assert_parse_ok(code, parser)


def test_function_with_multiple_params(parser):
    """Test function with multiple parameters"""
    code = """
    function int add(int a, int b, int c);
    """
    assert_parse_ok(code, parser)


def test_function_bit_return_type(parser):
    """Test function with bit return type"""
    code = """
    function bit[32] alloc_addr(bit[32] size);
    """
    assert_parse_ok(code, parser)


def test_pure_function(parser):
    """Test pure function declaration"""
    code = """
    pure function int factorial(int n);
    """
    assert_parse_ok(code, parser)


def test_pure_function_with_multiple_params(parser):
    """Test pure function with multiple parameters"""
    code = """
    pure function int compute(int a, int b, int c);
    """
    assert_parse_ok(code, parser)


def test_function_method(parser):
    """Test function with body in component"""
    code = """
    component my_c {
        function int compute(int a, int b) {
            return a + b;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_function_target_with_body(parser):
    """Test target-qualified function with body"""
    code = """
    component my_c {
        target function void func4(int a) {
        }
    }
    """
    assert_parse_ok(code, parser)


def test_import_function(parser):
    """Test import function declaration"""
    code = """
    import function int compute(int a, int b);
    """
    assert_parse_ok(code, parser)


def test_import_function_with_language(parser):
    """Test import function with language specifier"""
    code = """
    import C function int add(int a, int b);
    """
    assert_parse_ok(code, parser)


def test_import_function_void(parser):
    """Test imported void function"""
    code = """
    import C function void transfer_mem(bit[32] src, bit[32] dst);
    """
    assert_parse_ok(code, parser)


def test_function_in_component(parser):
    """Test function declaration in component"""
    code = """
    component my_c {
        function int helper(int val);
        
        action test_a {
            rand int value;
        }
    }
    """
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "my_c")
    assert comp is not None
    assert has_symbol(comp, "test_a")
    loc = get_location(comp.getTarget())
    assert loc is not None


def test_function_call_in_exec_block(parser):
    """Test function call in exec block"""
    code = """
    function int compute(int val);
    
    component my_c {
        action test_a {
            rand int value;
            int result;
            
            exec post_solve {
                result = compute(value);
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_function_string_param(parser):
    """Test function with string parameter"""
    code = """
    function void log_message(string msg);
    """
    assert_parse_ok(code, parser)


def test_multiple_function_declarations(parser):
    """Test multiple function declarations"""
    code = """
    function int add(int a, int b);
    function int sub(int a, int b);
    function int mul(int a, int b);
    """
    assert_parse_ok(code, parser)


def test_function_in_package(parser):
    """Test function declaration in package"""
    code = """
    package math_pkg {
        function int add(int a, int b);
        function int multiply(int a, int b);
    }
    """
    assert_parse_ok(code, parser)


def test_import_solve_function(parser):
    """Test imported function with solve keyword in component"""
    code = """
    component my_c {
        import function int alloc_resource(int size);
    }
    """
    assert_parse_ok(code, parser)


def test_import_target_function(parser):
    """Test imported target function with body"""
    code = """
    component my_c {
        import target function void write_register(bit[32] addr, bit[32] data);
    }
    """
    assert_parse_ok(code, parser)


def test_function_string_param(parser):
    """Test function with string parameter"""
    code = """
    function void log_message(string msg);
    """
    assert_parse_ok(code, parser)


def test_function_enum_return(parser):
    """Test function returning enum"""
    code = """
    enum status_e { IDLE, BUSY, DONE };
    function status_e get_status();
    """
    assert_parse_ok(code, parser)


def test_function_enum_param(parser):
    """Test function with enum parameter"""
    code = """
    enum mode_e { AUTO, MANUAL };
    function void configure(mode_e mode);
    """
    assert_parse_ok(code, parser)


def test_function_call_in_constraint(parser):
    """Test function call in constraint - should work for pure functions"""
    code = """
    pure function int compute(int val);
    
    struct test_s {
        rand int input_val;
        rand int output_val;
        
        constraint {
            output_val == compute(input_val);
        }
    };
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [3, 5, 10])
def test_function_scalability_params(parser, count):
    """Test function with many parameters for scalability"""
    params = ", ".join([f"int p{i}" for i in range(count)])
    code = f"""
    function int compute({params});
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [5, 10, 15])
def test_function_scalability_declarations(parser, count):
    """Test many function declarations for scalability"""
    funcs = "\n".join([f"function int func_{i}(int val);" for i in range(count)])
    code = funcs
    assert_parse_ok(code, parser)


def test_import_cpp_function(parser):
    """Test import C++ function"""
    code = """
    import CPP function int compute_value(int a, int b);
    """
    assert_parse_ok(code, parser)


def test_function_with_bit_sliced_return(parser):
    """Test function returning bit type"""
    code = """
    function bit[16] get_word();
    """
    assert_parse_ok(code, parser)


def test_function_complex_example(parser):
    """Test complex function usage in component"""
    code = """
    function bit[32] alloc_addr(bit[32] size);
    function void transfer_mem(bit[32] src, bit[32] dst, bit[32] size);
    
    component mem_xfer_c {
        action xfer_a {
            rand bit[32] size;
            bit[32] src_addr;
            bit[32] dst_addr;
            
            constraint size in [8..4096];
            
            exec post_solve {
                src_addr = alloc_addr(size);
                dst_addr = alloc_addr(size);
            }
            
            exec body {
                transfer_mem(src_addr, dst_addr, size);
            }
        }
    }
    """
    assert_parse_ok(code, parser)
from test_helpers import get_symbol, has_symbol, get_location
