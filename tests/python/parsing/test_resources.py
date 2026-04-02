"""
Tests for PSS resource features (resources, pools, lock/share).

Tests cover:
- Resource type declarations
- Resource pools and binding
- Lock (exclusive) resource claims
- Share (non-exclusive) resource claims
- Resource constraints
- Pool size specifications
- Resource arrays
- Binding directives
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_resource_simple_declaration(parser):
    """Test simple resource declaration"""
    code = """
resource channel_s {
};
    """
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "channel_s")
    assert sym is not None
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_resource_with_fields(parser):
    """Test resource with fields"""
    code = """
    resource dma_channel_s {
        rand bit[4] priority;
        rand bit[8] id;
    };
    """
    assert_parse_ok(code, parser)


def test_resource_with_constraint(parser):
    """Test resource with constraint"""
    code = """
    resource cpu_core_s {
        rand bit[8] frequency;
        
        constraint {
            frequency >= 100;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_resource_pool_single(parser):
    """Test single resource pool"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool channel_s chan_p;
    }
    """
    assert_parse_ok(code, parser)


def test_resource_pool_sized(parser):
    """Test resource pool with size"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool[4] channel_s chan_p;
    }
    """
    assert_parse_ok(code, parser)


def test_resource_lock_in_action(parser):
    """Test lock resource claim in action"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool[2] channel_s chan_p;
        
        action test_a {
            lock channel_s chan;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_share_in_action(parser):
    """Test share resource claim in action"""
    code = """
    resource cpu_s {
    };
    
    component pss_top {
        pool[2] cpu_s cpu_p;
        
        action test_a {
            share cpu_s cpu;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_multiple_locks(parser):
    """Test multiple lock claims"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool[4] channel_s chan_p;
        
        action test_a {
            lock channel_s chan_a;
            lock channel_s chan_b;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_lock_and_share(parser):
    """Test both lock and share claims"""
    code = """
    resource channel_s {
    };
    
    resource cpu_s {
    };
    
    component pss_top {
        pool[4] channel_s chan_p;
        pool[2] cpu_s cpu_p;
        
        action test_a {
            lock channel_s chan;
            share cpu_s cpu;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_inheritance(parser):
    """Test resource type inheritance"""
    code = """
    resource base_channel_s {
        rand bit[4] priority;
    };
    
    resource ext_channel_s : base_channel_s {
        rand bit[2] mode;
    };
    """
    assert_parse_ok(code, parser)


def test_resource_array_claim(parser):
    """Test resource array claim"""
    code = """
    resource config_s {
    };
    
    component pss_top {
        pool[16] config_s config_p;
        
        action test_a {
            lock config_s configs[4];
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_bind_wildcard(parser):
    """Test resource binding with wildcard"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool[4] channel_s chan_p;
        bind chan_p {*};
        
        action test_a {
            lock channel_s chan;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_multiple_pools(parser):
    """Test multiple resource pools"""
    code = """
    resource channel_s {
    };
    
    resource cpu_s {
    };
    
    component pss_top {
        pool[4] channel_s chan_p;
        pool[2] cpu_s cpu_p;
        
        action test_a {
            lock channel_s chan;
            share cpu_s cpu;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_in_parallel_activity(parser):
    """Test resource claims in parallel activities"""
    code = """
    resource channel_s {
    };
    
    component pss_top {
        pool[2] channel_s chan_p;
        
        action use_channel {
            lock channel_s chan;
        }
        
        action test_a {
            use_channel uc1;
            use_channel uc2;
            
            activity {
                parallel {
                    do uc1;
                    do uc2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_pool_in_subcomponent(parser):
    """Test resource pool in subcomponent"""
    code = """
    resource channel_s {
    };
    
    component sub_c {
        pool[2] channel_s chan_p;
        
        action test_a {
            lock channel_s chan;
        }
    }
    
    component pss_top {
        sub_c sub;
    }
    """
    assert_parse_ok(code, parser)


def test_resource_with_multiple_fields(parser):
    """Test resource with multiple fields"""
    code = """
    resource dma_channel_s {
        rand bit[4] priority;
        rand bit[8] bandwidth;
        rand bit[16] id;
        rand bool enabled;
    };
    """
    assert_parse_ok(code, parser)


def test_resource_share_array(parser):
    """Test share with resource array"""
    code = """
    resource config_s {
    };
    
    component pss_top {
        pool[16] config_s config_p;
        
        action test_a {
            share config_s configs[8];
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_enum_field(parser):
    """Test resource with enum field"""
    code = """
    enum priority_e { LOW, MEDIUM, HIGH };
    
    resource task_s {
        rand priority_e priority;
    };
    """
    assert_parse_ok(code, parser)


def test_resource_nested_in_component(parser):
    """Test resource declared in component"""
    code = """
    component pss_top {
        resource channel_s {
            rand bit[4] id;
        };
        
        pool[4] channel_s chan_p;
        
        action test_a {
            lock channel_s chan;
        }
    }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("pool_size", [1, 4, 8, 16])
def test_resource_scalability_pool_size(parser, pool_size):
    """Test various pool sizes"""
    code = f"""
    resource channel_s {{
    }};
    
    component pss_top {{
        pool[{pool_size}] channel_s chan_p;
        
        action test_a {{
            lock channel_s chan;
        }}
    }}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("num_resources", [2, 4, 8])
def test_resource_scalability_multiple_types(parser, num_resources):
    """Test multiple resource types"""
    resources = "\n".join([f"""
    resource res_{i}_s {{
        rand bit[4] id;
    }};
    """ for i in range(num_resources)])
    
    pools = "\n        ".join([f"pool[2] res_{i}_s pool_{i};" for i in range(num_resources)])
    
    code = f"""
    {resources}
    
    component pss_top {{
        {pools}
    }}
    """
    assert_parse_ok(code, parser)


def test_resource_in_struct(parser):
    """Test resource reference in struct"""
    code = """
    resource channel_s {
        rand bit[4] id;
    };
    
    component pss_top {
        pool[2] channel_s chan_p;
        
        action test_a {
            lock channel_s chan;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_resource_string_field(parser):
    """Test resource with string field"""
    code = """
    resource task_s {
        string name;
        rand bit[4] priority;
    };
    """
    assert_parse_ok(code, parser)

from test_helpers import get_symbol, has_symbol, get_location
