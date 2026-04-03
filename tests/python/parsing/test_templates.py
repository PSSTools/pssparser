"""
Tests for PSS template and parameterization features.

Tests template parameters (value, type, category), instantiation,
inheritance, and default parameters.

Based on PSS LRM v3.0 Chapter 6 (Data Types) and template syntax.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok


# ============================================================================
# Value Parameter Tests
# ============================================================================

def test_template_value_param_simple():
    """Test simple value parameter."""
    pss = """
    component MyComponent {
        struct MyStruct<int SIZE> {
            bit[SIZE] data;
        }
    }
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    assert has_symbol(comp, "MyStruct")
    loc = get_location(comp.getTarget())
    assert loc is not None


def test_template_value_param_with_default():
    """Test value parameter with default."""
    pss = """
    component MyComponent {
        struct MyStruct<int SIZE = 8> {
            bit[SIZE] data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_multiple_value_params():
    """Test multiple value parameters."""
    pss = """
    component MyComponent {
        struct MyStruct<int WIDTH, int DEPTH> {
            bit[WIDTH] data[DEPTH];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_value_param_expression_default():
    """Test value parameter with expression default."""
    pss = """
    component MyComponent {
        struct MyStruct<int WIDTH, bool IS_WIDE = (WIDTH > 16)> {
            bit[WIDTH] data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Type Parameter Tests
# ============================================================================

def test_template_generic_type_param():
    """Test generic type parameter."""
    pss = """
    component MyComponent {
        struct MyContainer<type T> {
            T data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_generic_type_param_with_default():
    """Test generic type parameter with default."""
    pss = """
    component MyComponent {
        struct BaseStruct { }
        struct MyContainer<type T = BaseStruct> {
            T data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_struct_category_param():
    """Test struct category type parameter."""
    pss = """
    component MyComponent {
        struct BaseStruct { }
        struct MyContainer<struct T> {
            T data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_struct_category_param_with_restriction():
    """Test struct category with type restriction."""
    pss = """
    component MyComponent {
        struct BaseStruct { }
        struct DerivedStruct : BaseStruct { }
        struct MyContainer<struct T : BaseStruct> {
            T data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_template_struct_category_param_with_default():
    """Test struct category with default."""
    pss = """
    component MyComponent {
        struct BaseStruct { }
        struct DefaultStruct : BaseStruct { }
        struct MyContainer<struct T : BaseStruct = DefaultStruct> {
            T data;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Template Instantiation Tests
# ============================================================================


def test_template_mixed_params():
    """Test template with mixed parameter types."""
    pss = """
    component MyComponent {
        struct BaseStruct { }
        struct MyStruct<int SIZE, struct T : BaseStruct, bool FLAG = false> {
            bit[SIZE] data;
            T item;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None

from test_helpers import parse_pss, get_symbol, has_symbol, get_location
