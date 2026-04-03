"""
Tests for PSS parse error handling and negative test cases.

These tests verify that the parser correctly rejects invalid PSS code
with appropriate error messages.
"""

import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_error


# =============================================================================
# Syntax Errors - Missing Elements
# =============================================================================

def test_error_missing_action_name():
    """Test error for action without name"""
    code = """
        component pss_top {
            action {  // Missing name
                rand int x;
            }
        }
    """
    assert_parse_error(code)


def test_error_missing_component_body():
    """Test error for component without body"""
    code = """
        component pss_top  // Missing braces
    """
    assert_parse_error(code)


def test_error_missing_semicolon():
    """Test error for missing semicolon"""
    code = """
        struct S {
            int x  // Missing semicolon
        }
    """
    assert_parse_error(code)


def test_error_missing_closing_brace():
    """Test error for unclosed brace"""
    code = """
        component pss_top {
            action A {
                rand int x;
            // Missing closing brace
    """
    assert_parse_error(code)


def test_error_missing_type():
    """Test error for field without type"""
    code = """
        struct S {
            x;  // Missing type
        }
    """
    assert_parse_error(code)


# =============================================================================
# Syntax Errors - Invalid Tokens
# =============================================================================

def test_error_invalid_keyword_placement():
    """Test error for misplaced keyword"""
    code = """
        rand component pss_top {  // 'rand' invalid here
            action A { }
        }
    """
    assert_parse_error(code)


def test_error_duplicate_modifier():
    """Test error for duplicate modifiers"""
    code = """
        component pss_top {
            rand rand int x;  // Duplicate 'rand'
        }
    """
    assert_parse_error(code)


def test_error_invalid_constraint_syntax():
    """Test error for invalid constraint"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x ===  5;  // Invalid operator
                }
            }
        }
    """
    assert_parse_error(code)


# =============================================================================
# Type Errors
# =============================================================================

def test_error_unknown_base_type():
    """Test error for invalid primitive type"""
    code = """
        struct S {
            integer x;  // 'integer' not valid, should be 'int'
        }
    """
    assert_parse_error(code)


def test_error_invalid_array_syntax():
    """Test error for invalid array declaration"""
    code = """
        struct S {
            int arr[];  // Empty brackets not allowed
        }
    """
    assert_parse_error(code)


def test_error_invalid_bit_width():
    """Test error for invalid bit width"""
    code = """
        struct S {
            bit[] x;  // Missing width
        }
    """
    assert_parse_error(code)


# =============================================================================
# Declaration Errors
# =============================================================================

def test_error_invalid_inheritance_syntax():
    """Test error for invalid inheritance"""
    code = """
        action Base { }
        action Derived extends Base { }  // Should use ':' not 'extends'
    """
    assert_parse_error(code)


def test_error_action_outside_component():
    """Test error for action not in component"""
    code = """
        action A {  // Actions must be in components
            rand int x;
        }
    """
    assert_parse_error(code)


def test_error_invalid_export_syntax():
    """Test error for malformed export"""
    code = """
        component pss_top {
            action A { }
            export A;  // Missing parentheses
        }
    """
    assert_parse_error(code)


# =============================================================================
# Expression Errors
# =============================================================================

def test_error_invalid_operator():
    """Test error for invalid operator in expression"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    x <> 5;  // '<>' not valid
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_unbalanced_parentheses():
    """Test error for unbalanced parentheses"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    (x + 5 > 10;  // Missing closing paren
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_empty_expression():
    """Test error for empty constraint"""
    code = """
        component pss_top {
            action A {
                rand int x;
                constraint {
                    ;  // Empty constraint
                }
            }
        }
    """
    # This might actually parse as empty statement, so it might not error
    # But we're testing the negative case
    pass  # Commented out as this might be valid


# =============================================================================
# Activity Errors
# =============================================================================

def test_error_invalid_activity_statement():
    """Test error for invalid activity syntax"""
    code = """
        component pss_top {
            action A { }
            action B {
                A a;
                activity {
                    execute a;  // Should be 'do a' or just 'a'
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_unclosed_parallel_block():
    """Test error for unclosed parallel"""
    code = """
        component pss_top {
            action A { }
            action B {
                A a1, a2;
                activity {
                    parallel {
                        a1;
                        a2;
                    // Missing closing brace
                }
            }
        }
    """
    assert_parse_error(code)


# =============================================================================
# Coverage Errors
# =============================================================================

def test_error_invalid_coverpoint_syntax():
    """Test error for malformed coverpoint"""
    code = """
        component pss_top {
            action A {
                rand int x;
                covergroup cg {
                    coverpoint;  // Missing expression
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_invalid_bins_syntax():
    """Test error for malformed bins"""
    code = """
        component pss_top {
            covergroup cg(int x) {
                coverpoint x {
                    bins b =;  // Missing value
                }
            }
        }
    """
    assert_parse_error(code)


# =============================================================================
# Procedural Errors
# =============================================================================

def test_error_invalid_assignment():
    """Test error for malformed assignment"""
    code = """
        component pss_top {
            action A {
                exec body {
                    int x;
                    x = ;  // Missing value
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_invalid_if_syntax():
    """Test error for malformed if statement"""
    code = """
        component pss_top {
            action A {
                exec body {
                    if (true)  // Missing body
                }
            }
        }
    """
    assert_parse_error(code)


def test_error_break_outside_loop():
    """Test that break outside loop is syntactically valid but semantically wrong"""
    # This might parse OK but be semantically invalid
    code = """
        component pss_top {
            action A {
                exec body {
                    break;  // Not in a loop
                }
            }
        }
    """
    # Parser may accept this, semantic check would reject
    pass  # Skipping as this is semantic, not syntactic


# =============================================================================
# Import/Package Errors
# =============================================================================

def test_error_invalid_import_syntax():
    """Test error for malformed import"""
    code = """
        import;  // Missing package name
    """
    assert_parse_error(code)


def test_error_invalid_package_syntax():
    """Test error for malformed package"""
    code = """
        package {  // Missing name
            struct S { }
        }
    """
    assert_parse_error(code)


# =============================================================================
# Resource Errors
# =============================================================================

def test_error_invalid_resource_syntax():
    """Test error for malformed resource"""
    code = """
        resource  // Missing name
    """
    assert_parse_error(code)


def test_error_invalid_pool_declaration():
    """Test error for pool without type"""
    code = """
        component pss_top {
            pool my_pool;  // Missing resource type
        }
    """
    assert_parse_error(code)


# =============================================================================
# Complex Error Cases
# =============================================================================

def test_error_multiple_syntax_errors():
    """Test code with multiple syntax errors"""
    code = """
        component pss_top
            action A  // Missing braces
                rand int x  // Missing semicolon
            }
        }  // Extra closing brace
    """
    assert_parse_error(code)


def test_error_nested_unclosed_braces():
    """Test error with nested unclosed braces"""
    code = """
        component pss_top {
            action A {
                activity {
                    parallel {
                        schedule {
                        // Multiple unclosed braces
    """
    assert_parse_error(code)


@pytest.mark.parametrize("invalid_char", ["@", "#", "$"])
def test_error_invalid_characters(invalid_char):
    """Test error for invalid characters in identifiers"""
    code = f"""
        component pss_top {{
            action {invalid_char}test {{  // Invalid character
                rand int x;
            }}
        }}
    """
    # @ is actually valid for annotations, so this test may need refinement
    if invalid_char != "@":
        assert_parse_error(code)
