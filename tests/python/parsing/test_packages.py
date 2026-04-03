"""
Tests for PSS package declarations and imports.

Tests cover:
- Package declarations
- Import statements
- Package hierarchy
- Qualified names
- Package-scoped declarations
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_package_empty(parser):
    """Test empty package declaration"""
    code = """
    package empty_pkg {
    }
    """
    assert_parse_ok(code, parser)


def test_package_with_struct(parser):
    """Test package with struct"""
    code = """
package my_pkg {
    struct my_s {
        rand int value;
    };
}
    """
    root = parse_pss(code, parser=parser)
    pkg = get_symbol(root, "my_pkg")
    assert pkg is not None
    assert has_symbol(pkg, "my_s")


def test_package_with_enum(parser):
    """Test package with enum"""
    code = """
    package my_pkg {
        enum status_e { IDLE, BUSY, DONE };
    }
    """
    assert_parse_ok(code, parser)


def test_package_with_function(parser):
    """Test package with function"""
    code = """
    package my_pkg {
        function int compute(int a, int b);
    }
    """
    assert_parse_ok(code, parser)


def test_package_with_component(parser):
    """Test package with component"""
    code = """
    package my_pkg {
        component my_c {
            action test_a {
                rand int value;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_package_multiple_items(parser):
    """Test package with multiple declarations"""
    code = """
    package my_pkg {
        struct data_s {
            rand int value;
        };
        
        enum mode_e { AUTO, MANUAL };
        
        function void process(int val);
    }
    """
    assert_parse_ok(code, parser)


def test_import_wildcard(parser):
    """Test wildcard import"""
    code = """
    package my_pkg {
        struct my_s {
            rand int value;
        };
    }
    
    import my_pkg::*;
    """
    assert_parse_ok(code, parser)


def test_import_specific(parser):
    """Test specific item import"""
    code = """
    package my_pkg {
        struct my_s {
            rand int value;
        };
    }
    
    import my_pkg::my_s;
    """
    assert_parse_ok(code, parser)


def test_import_multiple(parser):
    """Test multiple imports"""
    code = """
    package pkg1 {
        struct s1 {
            rand int v1;
        };
    }
    
    package pkg2 {
        struct s2 {
            rand int v2;
        };
    }
    
    import pkg1::*;
    import pkg2::*;
    """
    assert_parse_ok(code, parser)


def test_qualified_name_usage(parser):
    """Test qualified name usage"""
    code = """
    package my_pkg {
        struct my_s {
            rand int value;
        };
    }
    
    component test_c {
        action test_a {
            my_pkg::my_s data;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_package_with_component_action(parser):
    """Test package with component containing action"""
    code = """
    package my_pkg {
        component my_c {
            action my_a {
                rand int value;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_nested_package_reference(parser):
    """Test nested package structure"""
    code = """
    package outer_pkg {
        package inner_pkg {
            struct data_s {
                rand int value;
            };
        }
    }
    """
    assert_parse_ok(code, parser)


def test_package_import_in_component(parser):
    """Test import inside component"""
    code = """
    package util_pkg {
        function int helper(int val);
    }
    
    component my_c {
        import util_pkg::*;
        
        action test_a {
            rand int value;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_multiple_packages(parser):
    """Test multiple package declarations"""
    code = """
    package pkg1 {
        struct s1 {
            rand int v1;
        };
    }
    
    package pkg2 {
        struct s2 {
            rand int v2;
        };
    }
    
    package pkg3 {
        struct s3 {
            rand int v3;
        };
    }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [2, 5, 10])
def test_package_scalability(parser, count):
    """Test multiple packages for scalability"""
    packages = "\n".join([
        f"""
    package pkg_{i} {{
        struct data_{i} {{
            rand int value;
        }};
    }}
        """ for i in range(count)
    ])
    assert_parse_ok(packages, parser)


def test_import_function(parser):
    """Test importing specific function"""
    code = """
    package math_pkg {
        function int add(int a, int b);
        function int sub(int a, int b);
    }
    
    import math_pkg::add;
    """
    assert_parse_ok(code, parser)


def test_package_import_chain(parser):
    """Test chain of imports"""
    code = """
    package base_pkg {
        struct base_s {
            rand int value;
        };
    }
    
    package mid_pkg {
        import base_pkg::*;
        
        struct mid_s {
            base_s base;
        };
    }
    
    import mid_pkg::*;
    """
    assert_parse_ok(code, parser)
from test_helpers import get_symbol, has_symbol, get_location
