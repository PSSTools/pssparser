"""
Tests for PSS monitor features.

Tests monitor declarations, action handles, monitor activities,
and basic cover statements.

Based on PSS LRM v3.0 Chapter 11 (Monitors and Coverage).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from test_helpers import assert_parse_ok


# ============================================================================
# Basic Monitor Declaration Tests
# ============================================================================

def test_monitor_empty():
    """Test empty monitor declaration — verify linkage."""
    pss = """
component MyComponent {
    monitor EmptyMonitor {
    }
}
    """
    root = parse_pss(pss)
    comp = get_symbol(root, "MyComponent")
    assert comp is not None
    assert has_symbol(comp, "EmptyMonitor")
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_monitor_with_action_handle():
    """Test monitor with action handle."""
    pss = """
    component MyComponent {
        action A { }
        
        monitor MyMonitor {
            A a;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_with_activity():
    """Test monitor with activity block."""
    pss = """
    component MyComponent {
        action A { }
        
        monitor MyMonitor {
            A a;
            activity {
                a;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_multiple_action_handles():
    """Test monitor with multiple action handles."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        
        monitor MyMonitor {
            A a;
            B b;
            C c;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_action_handle_array():
    """Test monitor with action handle array."""
    pss = """
    component MyComponent {
        action A { }
        
        monitor MyMonitor {
            A actions[4];
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Monitor Activity Tests
# ============================================================================

def test_monitor_activity_sequence():
    """Test sequential activity in monitor."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        
        monitor MyMonitor {
            A a;
            B b;
            C c;
            activity {
                a;
                b;
                c;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_activity_schedule():
    """Test schedule block in monitor activity."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        action C { }
        
        monitor MyMonitor {
            A a;
            B b;
            C c;
            activity {
                schedule {
                    a;
                    b;
                    c;
                }
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Monitor with Constraints
# ============================================================================

def test_monitor_with_constraint():
    """Test monitor with constraint block."""
    pss = """
    component MyComponent {
        action A {
            rand bit[8] value;
        }
        
        monitor MyMonitor {
            A a;
            constraint c1 {
                a.value < 100;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_multiple_constraints():
    """Test monitor with multiple constraints."""
    pss = """
    component MyComponent {
        action A {
            rand bit[8] x;
            rand bit[8] y;
        }
        
        monitor MyMonitor {
            A a;
            constraint c1 {
                a.x < 50;
            }
            constraint c2 {
                a.y > 10;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Nested Monitor Tests
# ============================================================================

def test_monitor_with_monitor_handle():
    """Test monitor with handle to another monitor."""
    pss = """
    component MyComponent {
        action A { }
        
        monitor InnerMonitor {
            A a;
        }
        
        monitor OuterMonitor {
            InnerMonitor inner;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


def test_monitor_hierarchical_activity():
    """Test hierarchical monitor traversal."""
    pss = """
    component MyComponent {
        action A { }
        
        monitor InnerMonitor {
            A a;
            activity {
                a;
            }
        }
        
        monitor OuterMonitor {
            InnerMonitor inner;
            activity {
                inner;
            }
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Cover Statement Tests
# ============================================================================


def test_multiple_monitors_in_component():
    """Test multiple monitor declarations in one component."""
    pss = """
    component MyComponent {
        action A { }
        action B { }
        
        monitor Monitor1 {
            A a;
        }
        
        monitor Monitor2 {
            B b;
        }
        
        monitor Monitor3 {
            A a;
            B b;
        }
    }
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


# ============================================================================
# Monitor Scalability Tests
# ============================================================================

@pytest.mark.parametrize("handle_count", [2, 4, 8])
def test_scalability_action_handles(handle_count):
    """Test monitors with increasing action handles."""
    actions = "\n".join([f"        action A{i} {{ }}" for i in range(handle_count)])
    handles = "\n".join([f"            A{i} a{i};" for i in range(handle_count)])
    
    pss = f"""
    component MyComponent {{
{actions}
        
        monitor MyMonitor {{
{handles}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("activity_count", [3, 6, 10])
def test_scalability_sequential_activities(activity_count):
    """Test monitors with increasing sequential activities."""
    actions = "\n".join([f"        action A{i} {{ }}" for i in range(activity_count)])
    handles = "\n".join([f"            A{i} a{i};" for i in range(activity_count)])
    activities = "\n".join([f"                a{i};" for i in range(activity_count)])
    
    pss = f"""
    component MyComponent {{
{actions}
        
        monitor MyMonitor {{
{handles}
            activity {{
{activities}
            }}
        }}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("monitor_count", [2, 4, 6])
def test_scalability_multiple_monitors(monitor_count):
    """Test components with increasing number of monitors."""
    action_decl = "        action A { }"
    monitors = "\n".join([
        f"""        monitor Monitor{i} {{
            A a;
        }}""" for i in range(monitor_count)
    ])
    
    pss = f"""
    component MyComponent {{
{action_decl}
        
{monitors}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


@pytest.mark.parametrize("nesting_depth", [2, 3, 4])
def test_scalability_nested_monitors(nesting_depth):
    """Test deeply nested monitor hierarchies."""
    def generate_monitors(depth, current=0):
        if current >= depth:
            return f"""        monitor Monitor{current} {{
            A a;
        }}"""
        
        inner = generate_monitors(depth, current + 1)
        return f"""        monitor Monitor{current} {{
            Monitor{current + 1} m{current + 1};
        }}
        
{inner}"""
    
    monitors = generate_monitors(nesting_depth)
    pss = f"""
    component MyComponent {{
        action A {{ }}
        
{monitors}
    }}
    """
    ast = assert_parse_ok(pss)
    assert ast is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
from test_helpers import parse_pss, get_symbol, has_symbol, get_location
