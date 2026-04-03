"""
Tests for PSS default constraints
Based on PSS v3.0 LRM Section 16.1.10 (Default value constraints)
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error, parse_pss, get_symbol, has_symbol, get_location


def test_default_basic(parser):
    """Test basic default constraint"""
    code = """
    component pss_top {
        action test_a {
            rand int val;
            
            constraint default val == 42;
        }
    }
    """
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "test_a")
    assert action is not None
    assert has_symbol(action, "val")


def test_default_multiple_fields(parser):
    """Test default constraints on multiple fields"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            
            constraint default a == 10;
            constraint default b == 20;
            constraint default c == 30;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_with_regular_constraints(parser):
    """Test default constraint with regular constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int val;
            rand int limit;
            
            constraint default val == 100;
            
            constraint {
                limit > val;
                limit < 500;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_in_struct(parser):
    """Test default constraint in struct"""
    code = """
    struct my_s {
        rand int attr1;
        rand int attr2;
        
        constraint default attr1 == 0;
        constraint default attr2 == 5;
    };
    
    component pss_top {
        action test_a {
            rand my_s s;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_override_struct_default(parser):
    """Test overriding struct default in action"""
    code = """
    struct my_s {
        rand int attr1;
        constraint default attr1 == 0;
    };
    
    component pss_top {
        action test_a {
            rand my_s s1;
            rand my_s s2;
            
            constraint default s1.attr1 == 10;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_disable(parser):
    """Test disabling default constraint"""
    code = """
    struct my_s {
        rand int attr1;
        constraint default attr1 == 0;
    };
    
    component pss_top {
        action test_a {
            rand my_s s1;
            rand my_s s2;
            
            constraint default s1.attr1 == 10;
            constraint default disable s2.attr1;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_array_element(parser):
    """Test default constraint on array element"""
    code = """
    component pss_top {
        action test_a {
            rand int arr[4];
            
            constraint default arr[0] == 1;
            constraint default arr[1] == 2;
            constraint default arr[2] == 3;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_hierarchical(parser):
    """Test default on hierarchical field"""
    code = """
    struct inner_s {
        rand int value;
    };
    
    struct outer_s {
        rand inner_s inner;
    };
    
    component pss_top {
        action test_a {
            rand outer_s data;
            
            constraint default data.inner.value == 100;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_multiple_instances(parser):
    """Test default on multiple struct instances"""
    code = """
    struct my_s {
        rand int val;
    };
    
    component pss_top {
        action test_a {
            rand my_s s1;
            rand my_s s2;
            rand my_s s3;
            
            constraint default s1.val == 10;
            constraint default s2.val == 20;
            constraint default s3.val == 30;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_in_action_inheritance(parser):
    """Test default constraints with action inheritance"""
    code = """
    component pss_top {
        action base_a {
            rand int val;
            constraint default val == 50;
        };
        
        action derived_a : base_a {
            rand int extra;
            constraint default extra == 100;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_different_types(parser):
    """Test default constraints on different field types"""
    code = """
    component pss_top {
        action test_a {
            rand int int_val;
            rand bit[8] bit_val;
            rand bool flag;
            
            constraint default int_val == 42;
            constraint default bit_val == 0xFF;
            constraint default flag == true;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_with_named_constraints(parser):
    """Test default with named constraint blocks"""
    code = """
    component pss_top {
        action test_a {
            rand int val;
            rand int limit;
            
            constraint default val == 100;
            
            constraint range_c {
                val > 0;
                val < 1000;
            }
            
            constraint limit_c {
                limit > val;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_expressions(parser):
    """Test default with various constant expressions"""
    code = """
    component pss_top {
        action test_a {
            rand int a;
            rand int b;
            rand int c;
            rand int d;
            
            constraint default a == 10;
            constraint default b == 10 * 5;
            constraint default c == 0x20;
            constraint default d == (100 + 50);
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_multiple_disable(parser):
    """Test disabling multiple defaults"""
    code = """
    struct my_s {
        rand int a;
        rand int b;
        rand int c;
        
        constraint default a == 1;
        constraint default b == 2;
        constraint default c == 3;
    };
    
    component pss_top {
        action test_a {
            rand my_s s1;
            rand my_s s2;
            
            constraint default disable s1.a;
            constraint default disable s1.b;
            constraint default s1.c == 10;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_in_buffer(parser):
    """Test default constraint in buffer"""
    code = """
    buffer my_buf {
        rand int size;
        rand int priority;
        
        constraint default size == 64;
        constraint default priority == 1;
    };
    
    component pss_top {
        pool my_buf buf_p;
        bind buf_p *;
    }
    """
    assert_parse_ok(code, parser)


def test_default_in_stream(parser):
    """Test default constraint in stream"""
    code = """
    stream my_stream {
        rand int bandwidth;
        rand int priority;
        
        constraint default bandwidth == 1000;
        constraint default priority == 5;
    };
    
    component pss_top {
        pool my_stream stream_p;
        bind stream_p *;
    }
    """
    assert_parse_ok(code, parser)


def test_default_in_state(parser):
    """Test default constraint in state"""
    code = """
    state config_s {
        rand int mode;
        rand int frequency;
        
        constraint default mode == 1;
        constraint default frequency == 1000;
    };
    
    component pss_top {
        pool config_s state_p;
        bind state_p *;
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Scalability Tests
# =============================================================================

@pytest.mark.parametrize("count", [2, 5, 10])
def test_default_many_fields(parser, count):
    """Test default constraints on many fields"""
    fields = "\n".join([f"            rand int v{i};" for i in range(count)])
    defaults = "\n".join([f"            constraint default v{i} == {i * 10};" for i in range(count)])
    
    code = f"""
    component pss_top {{
        action test_a {{
{fields}
            
{defaults}
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [2, 4, 6])
def test_default_many_structs(parser, count):
    """Test defaults on many struct instances"""
    instances = "\n".join([f"            rand my_s s{i};" for i in range(count)])
    defaults = "\n".join([f"            constraint default s{i}.val == {i * 10};" for i in range(count)])
    
    code = f"""
    struct my_s {{
        rand int val;
    }};
    
    component pss_top {{
        action test_a {{
{instances}
            
{defaults}
        }}
    }}
    """
    assert_parse_ok(code, parser)


def test_default_combined_with_dynamic(parser):
    """Test default combined with dynamic constraints"""
    code = """
    component pss_top {
        action test_a {
            rand int val;
            rand int mode;
            
            constraint default val == 50;
            
            dynamic constraint small_c {
                val < 20;
            }
            
            dynamic constraint large_c {
                val > 100;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_default_complex_scenario(parser):
    """Test complex scenario with multiple defaults"""
    code = """
    struct config_s {
        rand int mode;
        rand int priority;
        constraint default mode == 1;
    };
    
    struct data_s {
        rand int value;
        rand config_s cfg;
        constraint default value == 100;
    };
    
    component pss_top {
        action test_a {
            rand data_s d1;
            rand data_s d2;
            rand int threshold;
            
            constraint default d1.value == 200;
            constraint default disable d2.value;
            constraint default d1.cfg.priority == 5;
            constraint default threshold == 1000;
            
            constraint {
                d1.value < threshold;
                d2.value > 0;
            }
        }
    }
    """
    assert_parse_ok(code, parser)
