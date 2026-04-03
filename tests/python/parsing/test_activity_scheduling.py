"""
Tests for PSS activity scheduling features.

Tests activity blocks (parallel, sequential, schedule, select, repeat, replicate),
join specifiers, action traversal, and inline constraints in activities.

Based on PSS LRM v3.0 Chapter 10 (Activities).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok, parse_pss, get_symbol, has_symbol, get_location


# ============================================================================
# Sequential Activity Tests
# ============================================================================

def test_sequential_implicit():
    """Test implicit sequential activity block."""
    pss = """
component MyComponent {
    action A { }
    action B { }
    action C { }
    action Top {
        A a;
        B b;
        C c;
        activity {
            do a;
            do b;
            do c;
        }
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    for name in ("A", "B", "C", "Top"):
        assert has_symbol(comp, name), f"action {name} not found"
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_sequential_explicit():
    """Test explicit sequence block."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action Top {
            A a;
            B b;
            activity {
                sequence {
                    do a;
                    do b;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_sequential_nested():
    """Test nested sequential blocks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                sequence {
                    do a;
                    sequence {
                        do b;
                        do c;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Parallel Activity Tests
# ============================================================================

def test_parallel_basic():
    """Test basic parallel block."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                parallel {
                    do a;
                    do b;
                    do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_parallel_nested():
    """Test nested parallel blocks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action D { }
        action Top {
            A a;
            B b;
            C c;
            D d;
            activity {
                parallel {
                    do a;
                    parallel {
                        do b;
                        do c;
                    }
                    do d;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_parallel_and_sequential_mixed():
    """Test mixing parallel and sequential blocks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action D { }
        action Top {
            A a;
            B b;
            C c;
            D d;
            activity {
                sequence {
                    do a;
                    parallel {
                        do b;
                        do c;
                    }
                    do d;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Schedule Activity Tests
# ============================================================================

def test_schedule_basic():
    """Test basic schedule block."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                schedule {
                    do a;
                    do b;
                    do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_schedule_nested():
    """Test nested schedule blocks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                schedule {
                    do a;
                    schedule {
                        do b;
                        do c;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_schedule_parallel_mixed():
    """Test schedule and parallel combination."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action D { }
        action Top {
            A a;
            B b;
            C c;
            D d;
            activity {
                schedule {
                    parallel {
                        do a;
                        do b;
                    }
                    do c;
                    do d;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Join Specifier Tests
# ============================================================================

def test_join_none():
    """Test join_none specifier."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                L1: parallel join_none {
                    do a;
                    do b;
                }
                do c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_join_first():
    """Test join_first specifier."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                L1: parallel join_first(1) {
                    do a;
                    do b;
                }
                do c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_join_branch():
    """Test join_branch specifier."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                L1: parallel join_branch(L2) {
                    L2: do a;
                    L3: do b;
                }
                do c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_join_select():
    """Test join_select specifier."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                L1: parallel join_select(1) {
                    do a;
                    do b;
                }
                do c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_join_branch_multiple():
    """Test join_branch with multiple labels."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action D { }
        action Top {
            A a;
            B b;
            C c;
            D d;
            activity {
                L1: parallel join_branch(L2, L3) {
                    L2: do a;
                    L3: do b;
                    L4: do c;
                }
                do d;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_join_schedule():
    """Test join specifier with schedule block."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                L1: schedule join_branch(L2) {
                    L2: do a;
                    L3: do b;
                }
                do c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Repeat Activity Tests
# ============================================================================

def test_repeat_count():
    """Test repeat with count."""
    pss = """
    component MyComponent {
        action A { }
        action Top {
            A a;
            activity {
                repeat (10) {
                    do a;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_repeat_with_index():
    """Test repeat with index variable."""
    pss = """
    component MyComponent {
        action A {
            rand bit[8] value;
        }
        action Top {
            A a;
            activity {
                repeat (i: 4) {
                    do a;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_repeat_while():
    """Test repeat-while loop."""
    pss = """
    component MyComponent {
        action A { }
        action Top {
            bit[8] counter;
            A a;
            activity {
                repeat {
                    do a;
                } while (counter < 10);
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_repeat_nested():
    """Test nested repeat blocks."""
    pss = """
    component MyComponent {
        action A { }
        action Top {
            A a;
            activity {
                repeat (5) {
                    repeat (3) {
                        do a;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Select Activity Tests
# ============================================================================

def test_select_basic():
    """Test basic select statement."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action Top {
            A a;
            B b;
            activity {
                select {
                    do a;
                    do b;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_select_with_guards():
    """Test select with guard conditions."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action Top {
            bit[8] mode;
            A a;
            B b;
            activity {
                select {
                    (mode == 1): do a;
                    (mode == 2): do b;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_select_with_weights():
    """Test select with weights."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                select {
                    [10]: do a;
                    [20]: do b;
                    [70]: do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_select_with_guards_and_weights():
    """Test select with both guards and weights."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            bit[8] mode;
            A a;
            B b;
            C c;
            activity {
                select {
                    (mode < 5) [10]: do a;
                    (mode >= 5) [20]: do b;
                    [70]: do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Replicate Activity Tests
# ============================================================================

def test_replicate_basic():
    """Test basic replicate statement."""
    pss = """
    component MyComponent {
        action A {
            rand bit[8] value;
        }
        action Top {
            A a;
            activity {
                replicate (i: 4) do a;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_replicate_with_expression():
    """Test replicate with count expression."""
    pss = """
    component MyComponent {
        action A { }
        action Top {
            bit[8] count;
            A a;
            activity {
                replicate (i: count) do a;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Foreach Activity Tests
# ============================================================================


def test_match_activity_basic():
    """Test basic activity match."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            bit[8] mode;
            A a;
            B b;
            C c;
            activity {
                match (mode) {
                    [1, 2]: do a;
                    [3]: do b;
                    default: do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_match_activity_with_ranges():
    """Test activity match with ranges."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            bit[8] value;
            A a;
            B b;
            C c;
            activity {
                match (value) {
                    [0..10]: do a;
                    [11..20]: do b;
                    default: do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Inline Constraint Tests
# ============================================================================


def test_traversal_labeled():
    """Test labeled action traversal."""
    pss = """
    component MyComponent {
        action A { }
        action Top {
            A a;
            activity {
                L1: do a;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_complex_parallel_schedule_repeat():
    """Test complex combination of parallel, schedule, and repeat."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            A a;
            B b;
            C c;
            activity {
                parallel {
                    schedule {
                        do a;
                        do b;
                    }
                    repeat (3) {
                        do c;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_complex_select_with_nested_parallel():
    """Test select with nested parallel blocks."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action Top {
            bit[8] mode;
            A a;
            B b;
            C c;
            activity {
                select {
                    (mode == 1): parallel {
                        do a;
                        do b;
                    }
                    (mode == 2): do c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_complex_nested_joins():
    """Test nested join specifiers."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        action D { }
        action Top {
            A a;
            B b;
            C c;
            D d;
            activity {
                L1: parallel join_branch(L2) {
                    L2: parallel join_first(1) {
                        L3: do a;
                        L4: do b;
                    }
                    L5: do c;
                }
                do d;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_complex_repeat_with_select():
    """Test repeat with nested select."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action Top {
            bit[8] mode;
            A a;
            B b;
            activity {
                repeat (5) {
                    select {
                        (mode == 1): do a;
                        (mode == 2): do b;
                    }
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Scalability Tests
# ============================================================================

@pytest.mark.parametrize("branch_count", [2, 4, 8, 16])
def test_scalability_parallel_branches(branch_count):
    """Test parallel with increasing number of branches."""
    actions = "\n".join([f"        action A{i} {{ }}" for i in range(branch_count)])
    instances = "\n".join([f"            A{i} a{i};" for i in range(branch_count)])
    traversals = "\n".join([f"                    do a{i};" for i in range(branch_count)])
    
    pss = f"""
    component MyComponent {{
{actions}
        action Top {{
{instances}
            activity {{
                parallel {{
{traversals}
                }}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("repeat_count", [10, 50, 100])
def test_scalability_repeat_count(repeat_count):
    """Test repeat with increasing counts."""
    pss = f"""
    component MyComponent {{
        action A {{ }}
        action Top {{
            A a;
            activity {{
                repeat ({repeat_count}) {{
                    do a;
                }}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 4, 6])
def test_scalability_nested_parallel(nesting_depth):
    """Test deeply nested parallel blocks."""
    def generate_nested(depth):
        if depth == 0:
            return "                    do a;"
        indent = "    " * (depth + 4)
        return f"{indent}parallel {{\n{generate_nested(depth-1)}\n{indent}}}"
    
    nested = generate_nested(nesting_depth)
    pss = f"""
    component MyComponent {{
        action A {{ }}
        action Top {{
            A a;
            activity {{
{nested}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("select_branches", [3, 6, 10])
def test_scalability_select_branches(select_branches):
    """Test select with increasing number of branches."""
    actions = "\n".join([f"        action A{i} {{ }}" for i in range(select_branches)])
    instances = "\n".join([f"            A{i} a{i};" for i in range(select_branches)])
    branches = "\n".join([f"                    do a{i};" for i in range(select_branches)])
    
    pss = f"""
    component MyComponent {{
{actions}
        action Top {{
{instances}
            activity {{
                select {{
{branches}
                }}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
