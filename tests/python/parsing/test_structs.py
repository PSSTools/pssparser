"""
Tests for PSS struct features
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_pss, get_symbol, has_symbol, assert_parse_ok


def test_empty_struct(parser):
    """Test empty struct definition"""
    code = """
        component pss_top {
            struct S {
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "S")


def test_struct_with_field(parser):
    """Test struct with single field"""
    code = """
        component pss_top {
            struct Point {
                int x;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Point")


def test_struct_with_multiple_fields(parser):
    """Test struct with multiple fields"""
    code = """
        component pss_top {
            struct Point {
                int x;
                int y;
                int z;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Point")


def test_struct_with_rand_fields(parser):
    """Test struct with random fields"""
    code = """
        component pss_top {
            struct Data {
                rand int value;
                rand bit[8] flags;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Data")


def test_struct_with_constraint(parser):
    """Test struct with constraint"""
    code = """
        component pss_top {
            struct Range {
                rand int min;
                rand int max;
                constraint {
                    min < max;
                    min >= 0;
                }
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Range")


def test_struct_nested_field(parser):
    """Test struct with nested struct field"""
    code = """
        component pss_top {
            struct Inner {
                int value;
            }
            struct Outer {
                Inner inner;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "Inner")
    assert has_symbol(pss_top, "Outer")


def test_struct_array_field(parser):
    """Test struct with array field"""
    code = """
        component pss_top {
            struct Buffer {
                int data[10];
                int size;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Buffer")


def test_struct_inheritance(parser):
    """Test struct inheritance"""
    code = """
        component pss_top {
            struct Base {
                int x;
            }
            struct Derived : Base {
                int y;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "Base")
    assert has_symbol(pss_top, "Derived")


def test_struct_in_action(parser):
    """Test struct used in action"""
    code = """
        component pss_top {
            struct Config {
                int mode;
                int timeout;
            }
            action A {
                Config cfg;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "Config")
    assert has_symbol(pss_top, "A")


def test_struct_with_bit_fields(parser):
    """Test struct with bit fields"""
    code = """
        component pss_top {
            struct Flags {
                bit enable;
                bit[4] mode;
                bit[8] status;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Flags")


def test_struct_with_bool_field(parser):
    """Test struct with boolean field"""
    code = """
        component pss_top {
            struct Control {
                bool enabled;
                int value;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Control")


def test_struct_with_string_field(parser):
    """Test struct with string field"""
    code = """
        component pss_top {
            struct Message {
                string text;
                int priority;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Message")


def test_toplevel_struct(parser):
    """Test struct at top level"""
    code = """
        struct Point {
            int x;
            int y;
        }
        component pss_top {
            action A {
                Point p;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(root, "Point")
    assert has_symbol(root, "pss_top")


def test_multiple_structs(parser):
    """Test multiple struct definitions"""
    code = """
        component pss_top {
            struct S1 { int x; }
            struct S2 { int y; }
            struct S3 { int z; }
        }
    """
    root = parse_pss(code, parser=parser)
    pss_top = get_symbol(root, "pss_top")
    assert has_symbol(pss_top, "S1")
    assert has_symbol(pss_top, "S2")
    assert has_symbol(pss_top, "S3")


@pytest.mark.parametrize("num_fields", [5, 10, 20])
def test_struct_many_fields(parser, num_fields):
    """Test struct with many fields"""
    fields = ' '.join(f'int field{i};' for i in range(num_fields))
    code = f"""
        component pss_top {{
            struct Data {{
                {fields}
            }}
        }}
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Data")


def test_struct_with_multiple_types(parser):
    """Test struct with various field types"""
    code = """
        component pss_top {
            struct Mixed {
                int i;
                bit[8] b;
                bool flag;
                string name;
            }
        }
    """
    root = parse_pss(code, parser=parser)
    assert has_symbol(get_symbol(root, "pss_top"), "Mixed")
