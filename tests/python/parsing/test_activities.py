"""
Tests for PSS activity blocks and control flow.

Tests cover:
- Activity block declarations
- Sequential execution (default and explicit)
- Parallel execution
- Repeat and replicate
- Conditional execution (if/else)
- Match statements
- Select (branch points)
- Action traversals
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_activity_empty(parser):
    """Test empty activity block"""
    code = """
    component pss_top {
        action test_a {
            activity {
            }
        }
    }
    """
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "test_a")


def test_activity_simple_traversal(parser):
    """Test simple action traversal"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
            
            activity {
                do a;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_multiple_traversals(parser):
    """Test multiple sequential traversals"""
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
    assert_parse_ok(code, parser)


def test_activity_sequence_explicit(parser):
    """Test explicit sequence block"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a1;
            A a2;
            
            activity {
                sequence {
                    do a1;
                    do a2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_parallel(parser):
    """Test parallel execution"""
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
                parallel {
                    do a;
                    do b;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_repeat(parser):
    """Test repeat construct"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
            
            activity {
                repeat (3) {
                    do a;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_repeat_variable(parser):
    """Test repeat with variable count"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            rand int count;
            A a;
            
            constraint {
                count in [1..10];
            }
            
            activity {
                repeat (count) {
                    do a;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_replicate(parser):
    """Test replicate construct"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
            
            activity {
                replicate (i : 4) {
                    do a;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_if(parser):
    """Test if statement in activity"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action test_a {
            rand int mode;
            A a;
            B b;
            
            activity {
                if (mode == 1) {
                    do a;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_if_else(parser):
    """Test if-else statement in activity"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action test_a {
            rand int mode;
            A a;
            B b;
            
            activity {
                if (mode == 1) {
                    do a;
                } else {
                    do b;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_if_else_if(parser):
    """Test if-else-if chain in activity"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action C {
            rand int value;
        }
        
        action test_a {
            rand int mode;
            A a;
            B b;
            C c;
            
            activity {
                if (mode == 1) {
                    do a;
                } else if (mode == 2) {
                    do b;
                } else {
                    do c;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_select(parser):
    """Test select statement"""
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
                select {
                    do a;
                    do b;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_nested_sequence_parallel(parser):
    """Test nested sequence and parallel"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action test_a {
            A a1;
            A a2;
            B b1;
            B b2;
            
            activity {
                sequence {
                    parallel {
                        do a1;
                        do b1;
                    }
                    parallel {
                        do a2;
                        do b2;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_repeat_nested(parser):
    """Test nested repeat"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
            
            activity {
                repeat (2) {
                    repeat (3) {
                        do a;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_labeled_traversal(parser):
    """Test labeled action traversal"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a;
            
            activity {
                label1: do a;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_traversal_simple(parser):
    """Test simple action traversal without inline constraint"""
    code = """
    component pss_top {
        action A {
            rand int value;
            
            constraint {
                value == 10;
            }
        }
        
        action test_a {
            A a;
            
            activity {
                do a;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_complex_control_flow(parser):
    """Test complex control flow combination"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action B {
            rand int value;
        }
        
        action test_a {
            rand int mode;
            rand int count;
            A a;
            B b;
            
            activity {
                if (mode == 1) {
                    repeat (count) {
                        do a;
                    }
                } else {
                    parallel {
                        do a;
                        do b;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [1, 5, 10])
def test_activity_scalability_repeat(parser, count):
    """Test activity with various repeat counts"""
    code = f"""
    component pss_top {{
        action A {{
            rand int value;
        }}
        
        action test_a {{
            A a;
            
            activity {{
                repeat ({count}) {{
                    do a;
                }}
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("branches", [2, 4, 8])
def test_activity_scalability_parallel(parser, branches):
    """Test activity with various parallel branch counts"""
    actions = "\n".join([f"A a{i};" for i in range(branches)])
    traversals = "\n                ".join([f"do a{i};" for i in range(branches)])
    
    code = f"""
    component pss_top {{
        action A {{
            rand int value;
        }}
        
        action test_a {{
            {actions}
            
            activity {{
                parallel {{
                    {traversals}
                }}
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


def test_activity_sequence_with_braces(parser):
    """Test sequence using braces without keyword"""
    code = """
    component pss_top {
        action A {
            rand int value;
        }
        
        action test_a {
            A a1;
            A a2;
            
            activity {
                {
                    do a1;
                    do a2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_parallel_with_labels(parser):
    """Test parallel with labeled branches"""
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
                parallel {
                    branch1: do a;
                    branch2: do b;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_multiple_selects(parser):
    """Test multiple select statements"""
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
                select {
                    do a;
                    do b;
                }
                
                select {
                    do a;
                    do b;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_activity_repeat_with_parallel(parser):
    """Test repeat containing parallel"""
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
                repeat (3) {
                    parallel {
                        do a;
                        do b;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)
from test_helpers import get_symbol, has_symbol, get_location
