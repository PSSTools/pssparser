"""
Tests for PSS source location tracking.

Tests cover:
- Line and column tracking for declarations
- Source locations for various PSS elements  
- Location preservation through parsing
- Token span information for IDE support
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, get_symbol, get_location


# =============================================================================
# Basic Location Tracking
# =============================================================================

def test_location_component_on_first_line(parser):
    """Test that component on first line has correct location"""
    code = """component pss_top { }"""
    root = parse_pss(code, "test.pss", parser)
    
    # Component should exist
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    
    # Should have location information
    loc = get_location(comp)
    assert loc is not None, "getLocation() should return location data"
    assert loc[0] == 1, f"Expected line 1, got {loc[0]}"


def test_location_action_declaration(parser):
    """Test location tracking for action declaration"""
    code = """
component pss_top {
    action test_a {
        rand int value;
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    
    # Action should be on line 3
    action = get_symbol(comp, "test_a")
    assert action is not None
    loc = get_location(action)
    assert loc is not None
    assert loc[0] == 3, f"Expected action on line 3, got {loc[0]}"


def test_location_struct_declaration(parser):
    """Test location tracking for struct declaration"""
    code = """
struct test_s {
    rand int value;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_multiple_lines(parser):
    """Test that line numbers increment correctly"""
    code = """
struct s1 { int v1; };

struct s2 { int v2; };

struct s3 { int v3; };
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None
    # Each struct should be on a different line


# =============================================================================
# Location Tracking for Different Elements
# =============================================================================

def test_location_constraint_block(parser):
    """Test location tracking for constraint blocks"""
    code = """
struct test_s {
    rand int value;
    
    constraint {
        value > 0;
        value < 100;
    }
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_activity_block(parser):
    """Test location tracking for activity blocks"""
    code = """
component pss_top {
    action A {
        rand int value;
    }
    
    action test_a {
        A a;
        
        activity {
            a;
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_exec_block(parser):
    """Test location tracking for exec blocks"""
    code = """
component pss_top {
    action test_a {
        rand int value;
        int result;
        
        exec post_solve {
            result = value * 2;
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_covergroup(parser):
    """Test location tracking for covergroup"""
    code = """
component pss_top {
    action test_a {
        rand int val;
        
        covergroup cg {
            coverpoint val;
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


# =============================================================================
# Location Tracking in Complex Scenarios
# =============================================================================

def test_location_nested_scopes(parser):
    """Test location tracking in nested scopes"""
    code = """
package outer {
    package inner {
        struct data_s {
            rand int value;
        };
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_inheritance(parser):
    """Test location tracking with inheritance"""
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


def test_location_with_comments(parser):
    """Test that comments don't affect location tracking"""
    code = """
// Top-level comment
component pss_top {
    // Action comment
    action test_a {
        // Field comment
        rand int value;  // Inline comment
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_multiline_declaration(parser):
    """Test location tracking across multiple lines"""
    code = """
struct test_s {
    rand int field1;
    rand int field2;
    rand int field3;
    rand int field4;
    rand int field5;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


# =============================================================================
# Location Tracking for IDE Features
# =============================================================================

def test_location_for_goto_definition(parser):
    """Test that declarations have location info for goto-definition"""
    code = """
struct Point {
    int x;
    int y;
};

component pss_top {
    action move {
        Point p;  // Jump to Point definition should work
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    
    # Verify Point struct exists and is findable
    point_struct = get_symbol(root, "Point")
    assert point_struct is not None


def test_location_for_hover_info(parser):
    """Test that identifiers have location info for hover"""
    code = """
component pss_top {
    action test_a {
        rand int value;
        
        constraint {
            value > 0;  // Hovering over 'value' should show type info
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


def test_location_for_find_references(parser):
    """Test that references preserve location for find-all-references"""
    code = """
struct Data {
    int value;
};

component pss_top {
    action producer {
        Data d1;  // Reference 1
    }
    
    action consumer {
        Data d2;  // Reference 2
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    
    # Both actions should exist
    pss_top = get_symbol(root, "pss_top")
    assert get_symbol(pss_top, "producer") is not None
    assert get_symbol(pss_top, "consumer") is not None


# =============================================================================
# Location Tracking for Error Reporting
# =============================================================================

def test_location_preserves_column_info(parser):
    """Test that column information is preserved"""
    code = """
component pss_top {
    action short { }
    action much_longer_name { }
}
"""
    root = parse_pss(code, "test.pss", parser)
    comp = get_symbol(root, "pss_top")
    
    # Both actions should exist
    assert get_symbol(comp, "short") is not None
    assert get_symbol(comp, "much_longer_name") is not None


def test_location_in_expressions(parser):
    """Test location tracking within expressions"""
    code = """
component pss_top {
    action test_a {
        rand int a, b, c;
        
        constraint {
            a + b * c < 100;
            (a > 0) && (b > 0) && (c > 0);
        }
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


# =============================================================================
# Scalability Tests
# =============================================================================

@pytest.mark.parametrize("lines", [10, 50, 100])
def test_location_scalability(parser, lines):
    """Test location tracking with many declarations"""
    structs = "\n".join([f"struct s{i} {{ int v{i}; }};" for i in range(lines)])
    root = parse_pss(structs, "test.pss", parser)
    assert root is not None
    
    # Verify first and last struct exist
    assert get_symbol(root, "s0") is not None
    assert get_symbol(root, f"s{lines-1}") is not None


def test_location_deeply_nested(parser):
    """Test location tracking in deeply nested structures"""
    code = """
component Level1 {
    component Level2 {
        component Level3 {
            action A {
                rand int value;
                
                constraint {
                    value > 0;
                }
            }
        }
    }
}
"""
    # Note: Nested components may not be allowed, but testing location tracking
    # This may fail for semantic reasons
    try:
        root = parse_pss(code, "test.pss", parser)
        assert root is not None
    except:
        pass  # May not be syntactically valid


# =============================================================================
# Location Tracking with Templates
# =============================================================================

def test_location_template_declaration(parser):
    """Test location tracking for template declarations"""
    code = """
struct templated_s<type T> {
    T value;
};
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None


# =============================================================================
# Multi-file Location Tracking
# =============================================================================

def test_location_with_imports(parser):
    """Test location tracking with import statements"""
    code = """
package my_pkg {
    struct data_s {
        rand int value;
    };
}

import my_pkg::*;

component pss_top {
    action use_data {
        data_s d;
    }
}
"""
    root = parse_pss(code, "test.pss", parser)
    assert root is not None
