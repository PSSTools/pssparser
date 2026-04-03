"""
Tests for PSS compile-time features.

Tests compile-time conditionals (compile if), compile-time queries (compile has),
and compile-time assertions.

Based on PSS LRM v3.0 Chapter 18 (Compile-time Elaboration).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Compile If Tests
# ============================================================================

def test_compile_if_true():
    """Test compile if with true condition."""
    pss = """
component MyComponent {
    compile if (true) {
        action A { }
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_compile_if_false():
    """Test compile if with false condition."""
    pss = """
    component MyComponent {
        compile if (false) {
            action A { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_else():
    """Test compile if-else."""
    pss = """
    component MyComponent {
        compile if (true) {
            action A { }
        } else {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_nested():
    """Test nested compile if."""
    pss = """
    component MyComponent {
        compile if (true) {
            compile if (true) {
                action A { }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_in_action():
    """Test compile if inside action."""
    pss = """
    component MyComponent {
        action A {
            compile if (true) {
                rand bit[8] field1;
            }
            compile if (false) {
                rand bit[16] field2;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_in_struct():
    """Test compile if inside struct."""
    pss = """
    component MyComponent {
        struct MyStruct {
            compile if (true) {
                bit[8] field1;
            }
            compile if (false) {
                bit[16] field2;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Compile Has Tests
# ============================================================================

def test_compile_has_type():
    """Test compile has for type existence."""
    pss = """
    component MyComponent {
        action A { }
        compile if (compile has (A)) {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_field():
    """Test compile has for field existence."""
    pss = """
    component MyComponent {
        struct MyStruct {
            bit[8] field1;
        }
        action A {
            MyStruct s;
            compile if (compile has (s.field1)) {
                rand bit[8] value;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_nested():
    """Test nested compile has checks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        compile if (compile has (A)) {
            compile if (compile has (B)) {
                action C { }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_has_negative():
    """Test compile has with negation."""
    pss = """
    component MyComponent {
        action A { }
        compile if (!compile has (NonExistent)) {
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Compile Assert Tests
# ============================================================================

def test_compile_assert_simple():
    """Test simple compile assert."""
    pss = """
    component MyComponent {
        compile assert (true, "This should pass");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_with_expression():
    """Test compile assert with expression."""
    pss = """
    component MyComponent {
        compile assert (1 + 1 == 2, "Math works");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_multiple():
    """Test multiple compile asserts."""
    pss = """
    component MyComponent {
        compile assert (true, "First assertion");
        compile assert (true, "Second assertion");
        compile assert (true, "Third assertion");
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_assert_in_action():
    """Test compile assert inside action."""
    pss = """
    component MyComponent {
        action A {
            compile assert (true, "Inside action");
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Combined Compile Features Tests
# ============================================================================

def test_compile_if_has_assert_combined():
    """Test combination of compile if, has, and assert."""
    pss = """
    component MyComponent {
        action A { }
        compile if (compile has (A)) {
            compile assert (true, "A exists");
            action B { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_compile_if_with_multiple_branches():
    """Test compile if with elsif and else."""
    pss = """
    component MyComponent {
        compile if (false) {
            action A { }
        } else compile if (false) {
            action B { }
        } else {
            action C { }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("branch_count", [2, 4, 6])
def test_scalability_multiple_compile_ifs(branch_count):
    """Test multiple compile if blocks."""
    branches = "\n".join([
        f"""        compile if (true) {{
            action A{i} {{ }}
        }}""" for i in range(branch_count)
    ])
    
    pss = f"""
    component MyComponent {{
{branches}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 3, 4])
def test_scalability_nested_compile_ifs(nesting_depth):
    """Test deeply nested compile if statements."""
    def generate_nested(depth):
        if depth == 0:
            return "                action A { }"
        indent = "    " * (depth + 2)
        return f"""{indent}compile if (true) {{
{generate_nested(depth-1)}
{indent}}}"""
    
    nested = generate_nested(nesting_depth)
    pss = f"""
    component MyComponent {{
{nested}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("assert_count", [3, 6, 10])
def test_scalability_multiple_asserts(assert_count):
    """Test multiple compile assertions."""
    asserts = "\n".join([
        f'        compile assert (true, "Assertion {i}");'
        for i in range(assert_count)
    ])
    
    pss = f"""
    component MyComponent {{
{asserts}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
