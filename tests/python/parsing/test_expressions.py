"""
Tests for PSS expressions
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok, assert_parse_error
)


def test_integer_literal(parser):
    """Test integer literal expressions"""
    code = """
        component pss_top {
            action A {
                int x = 42;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_binary_literal(parser):
    """Test binary literal"""
    code = """
        component pss_top {
            action A {
                bit[8] x = 8'b10101010;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_hex_literal(parser):
    """Test hexadecimal literal"""
    code = """
        component pss_top {
            action A {
                bit[16] x = 16'hABCD;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_bool_literal(parser):
    """Test boolean literals"""
    code = """
        component pss_top {
            action A {
                bool a = true;
                bool b = false;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_string_literal(parser):
    """Test string literal"""
    code = """
        component pss_top {
            action A {
                string s = "hello world";
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


@pytest.mark.parametrize("op", ["+", "-", "*", "/", "%"])
def test_arithmetic_operators(parser, op):
    """Test arithmetic operators"""
    code = f"""
        component pss_top {{
            action A {{
                int result = 10 {op} 5;
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


@pytest.mark.parametrize("op", ["<", ">", "<=", ">=", "==", "!="])
def test_comparison_operators(parser, op):
    """Test comparison operators"""
    code = f"""
        component pss_top {{
            action A {{
                rand int x;
                constraint {{
                    x {op} 10;
                }}
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


@pytest.mark.parametrize("op", ["&&", "||"])
def test_logical_operators(parser, op):
    """Test logical operators"""
    code = f"""
        component pss_top {{
            action A {{
                bool a = true;
                bool b = false;
                bool result = a {op} b;
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_logical_not(parser):
    """Test logical NOT operator"""
    code = """
        component pss_top {
            action A {
                bool a = true;
                bool result = !a;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


@pytest.mark.parametrize("op", ["&", "|", "^"])
def test_bitwise_operators(parser, op):
    """Test bitwise operators"""
    code = f"""
        component pss_top {{
            action A {{
                bit[8] result = 8'hFF {op} 8'h0F;
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_bitwise_not(parser):
    """Test bitwise NOT operator"""
    code = """
        component pss_top {
            action A {
                bit[8] x = 8'hFF;
                bit[8] result = ~x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


@pytest.mark.parametrize("op", ["<<", ">>"])
def test_shift_operators(parser, op):
    """Test shift operators"""
    code = f"""
        component pss_top {{
            action A {{
                bit[8] result = 8'h01 {op} 4;
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_ternary_operator(parser):
    """Test ternary conditional operator"""
    code = """
        component pss_top {
            action A {
                int sel = 1;
                int result = (sel == 0) ? 10 : 20;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_parenthesized_expression(parser):
    """Test parenthesized expressions"""
    code = """
        component pss_top {
            action A {
                int result = (10 + 5) * 2;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_array_indexing(parser):
    """Test array index expression"""
    code = """
        component pss_top {
            action A {
                int arr[10];
                int x = arr[5];
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_bit_slice(parser):
    """Test bit slice expression"""
    code = """
        component pss_top {
            action A {
                bit[16] x = 16'hABCD;
                bit[8] low = x[7:0];
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_field_access(parser):
    """Test struct field access"""
    code = """
        component pss_top {
            struct Point {
                int x;
                int y;
            }
            action A {
                Point p;
                int val = p.x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_in_expression(parser):
    """Test 'in' expression"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x in [1, 2, 3, 4, 5];
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_range_expression(parser):
    """Test range expression"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x in [10..20];
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_range_list_expression(parser):
    """Test range list expression"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x in [1..10, 20..30, 40..50];
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_cast_expression(parser):
    """Test type cast expression"""
    code = """
        component pss_top {
            action A {
                int x = 10;
                bit[8] b = (bit[8])x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_unary_plus_minus(parser):
    """Test unary plus and minus"""
    code = """
        component pss_top {
            action A {
                int x = 10;
                int y = -x;
                int z = +x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_complex_expression(parser):
    """Test complex nested expression"""
    code = """
        component pss_top {
            action A {
                int result = ((10 + 5) * 2) - (8 / 4);
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_expression_with_function_call(parser):
    """Test expression with function call"""
    code = """
        component pss_top {
            function int add(int a, int b) {
                return a + b;
            }
            action A {
                int result = add(10, 20);
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_aggregate_literal_empty(parser):
    """Test empty aggregate literal"""
    code = """
        component pss_top {
            action A {
                int arr[5] = {};
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_aggregate_literal_values(parser):
    """Test aggregate literal with values"""
    code = """
        component pss_top {
            action A {
                int arr[5] = {1, 2, 3, 4, 5};
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_struct_literal(parser):
    """Test struct initialization"""
    code = """
        component pss_top {
            struct Point {
                int x;
                int y;
            }
            action A {
                Point p;
                exec body {
                    p.x = 10;
                    p.y = 20;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_type_reference(parser):
    """Test type reference in expression"""
    code = """
        component pss_top {
            struct Data {
                int x;
                int y;
            }
            action A {
                Data d;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_precedence_arithmetic(parser):
    """Test operator precedence for arithmetic"""
    code = """
        component pss_top {
            action A {
                int result = 2 + 3 * 4;  // Should be 14, not 20
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_precedence_logical(parser):
    """Test operator precedence for logical ops"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > 0 && x < 100 || x == 255;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_associativity_left(parser):
    """Test left associativity"""
    code = """
        component pss_top {
            action A {
                int result = 10 - 5 - 2;  // Should be 3, not 7
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_nested_array_access(parser):
    """Test nested array access"""
    code = """
        component pss_top {
            action A {
                int arr[5];
                int idx = 2;
                int val = arr[arr[idx]];
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_chained_field_access(parser):
    """Test chained field access"""
    code = """
        component pss_top {
            struct Inner {
                int value;
            }
            struct Outer {
                Inner inner;
            }
            action A {
                Outer o;
                int x = o.inner.value;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_expression_in_constraint(parser):
    """Test complex expression in constraint"""
    code = """
        component pss_top {
            action A {
                rand int a;
                rand int b;
                rand int c;
                constraint {
                    a + b * 2 == c;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_expression_with_literal_const(parser):
    """Test expression with literal constant"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x < 100;
                    x > 0;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_null_literal(parser):
    """Test null literal"""
    code = """
        component pss_top {
            struct Data { int x; }
            action A {
                Data d = null;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_invalid_expression():
    """Test that invalid expressions are rejected"""
    code = """
        component pss_top {
            action A {
                int x = 10 +;  // Missing operand
            }
        }
    """
    assert_parse_error(code)
