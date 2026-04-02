"""
Tests for PSS forall constraints
Based on PSS v3.0 LRM Section 10.2.2 (Forall Constraints)
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error, parse_pss, get_symbol, has_symbol, get_location


def test_forall_basic(parser):
    """Test basic forall constraint"""
    code = """
    component pss_top {
        action A {
            rand int val;
        };
        
        action test_a {
            A a1;
            A a2;
            A a3;
            
            constraint {
                forall (a : A) {
                    a.val > 5;
                }
            }
        }
    }
    """
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "test_a")
    assert has_symbol(comp, "A")


def test_forall_multiple_constraints(parser):
    """Test forall with multiple constraints"""
    code = """
    component pss_top {
        action A {
            rand int val;
            rand int id;
        };
        
        action test_a {
            A a1;
            A a2;
            
            constraint {
                forall (a : A) {
                    a.val > 0;
                    a.val < 100;
                    a.id >= 1;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_nested_actions(parser):
    """Test nested forall on different action types"""
    code = """
    component pss_top {
        action B {
            rand int x;
        };
        
        action A {
            rand int val;
            B b1;
            B b2;
        };
        
        action test_a {
            A a1;
            A a2;
            
            constraint {
                forall (a : A) {
                    a.val > 0;
                    forall (b : B) {
                        b.x < 50;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_with_implication(parser):
    """Test forall combined with implication"""
    code = """
    component pss_top {
        action A {
            rand int val;
            rand int mode;
        };
        
        action test_a {
            A a1;
            A a2;
            rand int enable;
            
            constraint {
                (enable == 1) -> {
                    forall (a : A) {
                        a.val > 10;
                        (a.mode == 2) -> (a.val < 50);
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_multiple_types(parser):
    """Test forall on multiple action types"""
    code = """
    component pss_top {
        action A {
            rand int val;
        };
        
        action B {
            rand int data;
        };
        
        action test_a {
            A a1, a2;
            B b1, b2;
            
            constraint {
                forall (a : A) {
                    a.val > 0;
                }
                
                forall (b : B) {
                    b.data < 100;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_with_foreach(parser):
    """Test forall combined with foreach"""
    code = """
    component pss_top {
        action A {
            rand int vals[3];
        };
        
        action test_a {
            A a1;
            A a2;
            
            constraint {
                forall (a : A) {
                    foreach (a.vals[i]) {
                        a.vals[i] > 0;
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_with_unique(parser):
    """Test forall combined with unique"""
    code = """
    component pss_top {
        action A {
            rand int id;
            rand int val;
        };
        
        action test_a {
            A a1, a2, a3;
            
            constraint {
                unique {a1.id, a2.id, a3.id};
                
                forall (a : A) {
                    a.val > 0;
                    a.val < 100;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_inheritance(parser):
    """Test forall with action inheritance"""
    code = """
    component pss_top {
        action base_a {
            rand int val;
        };
        
        action derived_a : base_a {
            rand int extra;
        };
        
        action test_a {
            derived_a d1;
            derived_a d2;
            
            constraint {
                forall (d : derived_a) {
                    d.extra > 5;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_complex_expressions(parser):
    """Test forall with complex constraint expressions"""
    code = """
    component pss_top {
        action A {
            rand int val;
            rand int priority;
        };
        
        action test_a {
            A a1, a2, a3;
            rand int threshold;
            
            constraint {
                threshold > 10;
                
                forall (a : A) {
                    a.val >= threshold;
                    a.val <= threshold * 10;
                    a.priority > 0;
                    a.priority < 6;
                    (a.priority > 3) -> (a.val > 50);
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_three_levels(parser):
    """Test forall nested three levels deep"""
    code = """
    component pss_top {
        action C {
            rand int z;
        };
        
        action B {
            rand int y;
            C c1;
        };
        
        action A {
            rand int x;
            B b1;
        };
        
        action test_a {
            A a1, a2;
            
            constraint {
                forall (a : A) {
                    a.x > 0;
                    forall (b : B) {
                        b.y < 100;
                        forall (c : C) {
                            c.z >= 10;
                        }
                    }
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Scalability Tests
# =============================================================================

@pytest.mark.parametrize("count", [2, 5, 10])
def test_forall_many_instances(parser, count):
    """Test forall with many action instances"""
    instances = "\n".join([f"            A a{i};" for i in range(count)])
    
    code = f"""
    component pss_top {{
        action A {{
            rand int val;
        }};
        
        action test_a {{
{instances}
            
            constraint {{
                forall (a : A) {{
                    a.val > 0;
                    a.val < 100;
                }}
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("constraint_count", [1, 3, 5])
def test_forall_many_constraints(parser, constraint_count):
    """Test forall with many constraints"""
    constraints = "\n".join([
        f"                    a.val != {i * 10};"
        for i in range(constraint_count)
    ])
    
    code = f"""
    component pss_top {{
        action A {{
            rand int val;
        }};
        
        action test_a {{
            A a1, a2;
            
            constraint {{
                forall (a : A) {{
{constraints}
                }}
            }}
        }}
    }}
    """
    assert_parse_ok(code, parser)


def test_forall_struct_types(parser):
    """Test forall with struct field access"""
    code = """
    struct data_s {
        rand int value;
        rand int id;
    };
    
    component pss_top {
        action A {
            rand data_s data;
        };
        
        action test_a {
            A a1, a2, a3;
            
            constraint {
                forall (a : A) {
                    a.data.value > 0;
                    a.data.id >= 1;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_forall_mixed_with_regular_constraints(parser):
    """Test forall mixed with regular constraints"""
    code = """
    component pss_top {
        action A {
            rand int val;
        };
        
        action test_a {
            A a1, a2;
            rand int global_limit;
            
            constraint {
                global_limit > 50;
                global_limit < 200;
                
                forall (a : A) {
                    a.val < global_limit;
                    a.val > 0;
                }
                
                a1.val != a2.val;
            }
        }
    }
    """
    assert_parse_ok(code, parser)
