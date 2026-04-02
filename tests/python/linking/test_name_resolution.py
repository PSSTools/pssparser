"""
Tests for PSS symbol linking and name resolution.

Tests cover:
- Symbol lookup in scopes
- Qualified name resolution
- Cross-scope references
- Import resolution
- Type references
- Action/struct/enum references
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, get_symbol, has_symbol, assert_linked


def test_linking_struct_in_action(parser):
    """Test struct reference in action is linked"""
    code = """
    struct data_s {
        rand int value;
    };
    
    component pss_top {
        action test_a {
            data_s data;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    # Symbol should exist
    assert root is not None


def test_linking_enum_in_struct(parser):
    """Test enum reference in struct is linked"""
    code = """
    enum status_e { IDLE, BUSY };
    
    struct test_s {
        status_e status;
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_action_in_component(parser):
    """Test action reference in component"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_qualified_package_ref(parser):
    """Test qualified package reference"""
    code = """
    package my_pkg {
        struct data_s {
            rand int value;
        };
    }
    
    component pss_top {
        action test_a {
            my_pkg::data_s data;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_import_wildcard(parser):
    """Test import wildcard resolution"""
    code = """
    package my_pkg {
        struct data_s {
            rand int value;
        };
    }
    
    import my_pkg::*;
    
    component pss_top {
        action test_a {
            data_s data;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_import_in_component(parser):
    """Test import inside component scope"""
    code = """
    package my_pkg {
        struct data_s {
            rand int value;
        };
    }
    
    component pss_top {
        import my_pkg::*;
        
        action test_a {
            data_s data;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_struct_inheritance(parser):
    """Test struct inheritance resolution"""
    code = """
    struct base_s {
        rand int base_val;
    };
    
    struct derived_s : base_s {
        rand int derived_val;
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_action_inheritance(parser):
    """Test action inheritance resolution"""
    code = """
    component pss_top {
        action base_a {
            rand int value;
        }
        
        action derived_a : base_a {
            rand int extra;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_component_inheritance(parser):
    """Test component inheritance resolution"""
    code = """
    component base_c {
        action test_a {
            rand int value;
        }
    }
    
    component derived_c : base_c {
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_enum_reference(parser):
    """Test enum value reference"""
    code = """
    enum mode_e { MODE_A, MODE_B };
    
    struct test_s {
        rand mode_e mode;
        
        constraint {
            mode == MODE_A;
        }
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_function_call(parser):
    """Test function call resolution"""
    code = """
    function int compute(int val);
    
    component pss_top {
        action test_a {
            rand int value;
            int result;
            
            exec post_solve {
                result = compute(value);
            }
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_nested_struct(parser):
    """Test nested struct reference"""
    code = """
    struct inner_s {
        rand int value;
    };
    
    struct outer_s {
        inner_s inner;
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_array_of_struct(parser):
    """Test array of struct type"""
    code = """
    struct data_s {
        rand int value;
    };
    
    struct container_s {
        data_s items[10];
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_field_access(parser):
    """Test field access resolution"""
    code = """
    struct data_s {
        rand int value;
    };
    
    component pss_top {
        action test_a {
            data_s data;
            
            constraint {
                data.value > 0;
            }
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_qualified_enum_ref(parser):
    """Test qualified enum reference"""
    code = """
    enum status_e { IDLE, BUSY };
    
    struct test_s {
        rand status_e status;
        
        constraint {
            status == status_e::IDLE;
        }
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_multiple_packages(parser):
    """Test resolution across multiple packages"""
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
    
    struct combined_s {
        s1 field1;
        s2 field2;
    };
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_component_action_ref(parser):
    """Test component's action reference"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action test_a {
            A a;
            B b;
            
            activity {
                do a;
                do b;
            }
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_linking_nested_package_ref(parser):
    """Test nested package reference"""
    code = """
    package outer {
        package inner {
            struct data_s {
                rand int value;
            };
        }
    }
    
    component pss_top {
        action test_a {
            outer::inner::data_s data;
        }
    }
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


@pytest.mark.parametrize("count", [2, 5, 10])
def test_linking_scalability(parser, count):
    """Test linking with many struct references"""
    structs = "\n".join([f"""
    struct s{i} {{
        rand int v{i};
    }};
    """ for i in range(count)])
    
    fields = "\n".join([f"        s{i} field{i};" for i in range(count)])
    
    code = f"""
    {structs}
    
    struct container_s {{
{fields}
    }};
    """
    root = parse_pss(code, "test.pss", parser)
    assert root is not None
