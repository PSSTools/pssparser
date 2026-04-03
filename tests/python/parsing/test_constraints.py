"""
Tests for PSS constraint features
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    parse_pss, get_symbol, has_symbol, assert_parse_ok,
    assert_parse_error, generate_constraints
)


def test_empty_constraint(parser):
    """Test action with empty constraint block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_simple_constraint(parser):
    """Test simple constraint expression"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > 0;
                }
            }
        }
    """
    root = assert_parse_ok(code)
    assert has_symbol(get_symbol(root, "pss_top"), "A")


def test_multiple_constraints(parser):
    """Test multiple constraint expressions in block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > 0;
                    x < 100;
                    x != 50;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_named_constraint(parser):
    """Test named constraint block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint valid_range {
                    x >= 10;
                    x <= 90;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_implication_constraint(parser):
    """Test implication constraint (->)"""
    code = """
        component pss_top {
            action A {
                rand bit enable;
                rand int value;
                constraint {
                    enable -> value > 0;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_if_else_constraint(parser):
    """Test if-else in constraint"""
    code = """
        component pss_top {
            action A {
                rand int mode;
                rand int x;
                constraint {
                    if (mode == 0) {
                        x < 10;
                    } else {
                        x > 100;
                    }
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_foreach_constraint_basic(parser):
    """Test basic foreach constraint"""
    code = """
        component pss_top {
            action A {
                rand int arr[10];
                constraint {
                    foreach (arr[i]) {
                        arr[i] > 0;
                    }
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_foreach_constraint_with_index(parser):
    """Test foreach constraint using index variable"""
    code = """
        component pss_top {
            action A {
                rand int arr[10];
                constraint {
                    foreach (arr[i]) {
                        arr[i] == i + 1;
                    }
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_foreach_constraint_nested(parser):
    """Test nested foreach constraints (simplified)"""
    code = """
        component pss_top {
            action A {
                rand int matrix[5];
                constraint {
                    foreach (matrix[i]) {
                        matrix[i] >= 0;
                        matrix[i] <= 100;
                    }
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_unique_constraint(parser):
    """Test unique constraint"""
    code = """
        component pss_top {
            action A {
                rand int arr[10];
                constraint {
                    unique { arr };
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_multiple_fields(parser):
    """Test constraint referencing multiple fields"""
    code = """
        component pss_top {
            action A {
                rand int x;
                rand int y;
                rand int z;
                constraint {
                    x + y == z;
                    x > 0;
                    y > 0;
                    z > 0;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_in_struct(parser):
    """Test constraint in struct"""
    code = """
        component pss_top {
            struct Point {
                rand int x;
                rand int y;
                constraint valid {
                    x >= 0;
                    y >= 0;
                    x < 100;
                    y < 100;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "Point")


def test_constraint_override(parser):
    """Test multiple constraints in inheritance"""
    code = """
        component pss_top {
            action Base {
                rand int x;
                constraint c1 {
                    x > 0;
                }
            }
            
            action Derived : Base {
                rand int y;
                constraint c2 {
                    y < 100;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "Base")
    assert has_symbol(pss_top, "Derived")


def test_constraint_modes(parser):
    """Test constraint with modes"""
    code = """
        component pss_top {
            action A {
                rand int x;
                rand int mode;
                constraint mode_c {
                    if (mode == 0) {
                        x < 10;
                    } else {
                        x > 100;
                    }
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_array_size(parser):
    """Test constraint referencing array size"""
    code = """
        component pss_top {
            action A {
                rand int size;
                rand int arr[10];
                constraint {
                    size <= 10;
                    size > 0;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


@pytest.mark.parametrize("operator", [">", "<", ">=", "<=", "==", "!="])
def test_constraint_comparison_operators(parser, operator):
    """Test various comparison operators in constraints"""
    code = f"""
        component pss_top {{
            action A {{
                rand int x;
                constraint {{
                    x {operator} 10;
                }}
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


@pytest.mark.parametrize("operator", ["&&", "||"])
def test_constraint_logical_operators(parser, operator):
    """Test logical operators in constraints"""
    code = f"""
        component pss_top {{
            action A {{
                rand int x;
                rand int y;
                constraint {{
                    (x > 0) {operator} (y > 0);
                }}
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_inside(parser):
    """Test constraint with 'in' operator"""
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
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_range(parser):
    """Test constraint with range"""
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
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_set_expression(parser):
    """Test constraint with set operations"""
    code = """
        component pss_top {
            action A {
                rand int x;
                rand int y;
                constraint {
                    x in [1..10];
                    y in [5..15];
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_parentheses(parser):
    """Test constraint with complex parenthesized expressions"""
    code = """
        component pss_top {
            action A {
                rand int x;
                rand int y;
                rand int z;
                constraint {
                    ((x > 0) && (y > 0)) -> (z > 0);
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_ternary(parser):
    """Test constraint with ternary operator"""
    code = """
        component pss_top {
            action A {
                rand int sel;
                rand int x;
                rand int y;
                constraint {
                    (sel == 0 ? x : y) > 10;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_named_block(parser):
    """Test constraint with named block"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint range_c {
                    x >= 10;
                    x <= 90;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


@pytest.mark.parametrize("num_constraints", [10, 50, 100])
def test_many_constraints(parser, num_constraints):
    """Test action with many constraint expressions"""
    constraints = []
    for i in range(num_constraints):
        constraints.append(f"x{i} > 0;")
        constraints.append(f"x{i} < 1000;")
    
    code = f"""
        component pss_top {{
            action A {{
                {' '.join(f'rand int x{i};' for i in range(num_constraints))}
                constraint {{
                    {' '.join(constraints)}
                }}
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_weight(parser):
    """Test constraint with weighted values"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint weight_c {
                    x in [1..10];
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_with_bitwise_ops(parser):
    """Test constraint with bitwise operations"""
    code = """
        component pss_top {
            action A {
                rand bit[8] x;
                constraint {
                    (x & 8'h0F) == 8'h05;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")


def test_constraint_invalid_syntax():
    """Test that invalid constraint syntax is rejected"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x > ;  // Missing operand
                }
            }
        }
    """
    assert_parse_error(code)


def test_constraint_on_non_rand_field(parser):
    """Test constraint on non-rand field (should parse)"""
    code = """
        component pss_top {
            action A {
                int x;
                rand int y;
                constraint {
                    y > x;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "A")
