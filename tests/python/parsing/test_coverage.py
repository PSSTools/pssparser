"""
Tests for PSS coverage features (covergroups, coverpoints, bins, cross).

Tests cover:
- Covergroup declarations (explicit and inline)
- Coverpoints (basic, with conditions)
- Bins (explicit, auto, ranges, arrays)
- Cross coverage
- Ignore and illegal bins
- Coverage options
- Sampling mechanisms
"""

import pytest
from pssparser import Parser
from test_helpers import parse_pss, assert_parse_ok, assert_parse_error


def test_coverage_inline_covergroup(parser):
    """Test inline covergroup in struct"""
    code = """
struct test_s {
    rand bit[4] value;
    covergroup {
        coverpoint value;
    } cg_inst;
};
    """
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "test_s")
    assert sym is not None
    assert has_symbol(sym, "value")
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_coverage_explicit_covergroup(parser):
    """Test explicit covergroup with parameter"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        coverpoint data_param;
    }
    
    struct test_s {
        rand bit[8] data;
        cg_type cg_inst(data);
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_coverpoint_simple(parser):
    """Test simple coverpoint"""
    code = """
    struct test_s {
        rand bit[8] addr;
        
        covergroup {
            coverpoint addr;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_coverpoint_labeled(parser):
    """Test labeled coverpoint"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            val_cp: coverpoint value;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_explicit(parser):
    """Test explicit bins"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            coverpoint value {
                bins low = [0..63];
                bins mid = [64..127];
                bins high = [128..255];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_array(parser):
    """Test bin arrays"""
    code = """
    struct test_s {
        rand bit[4] value;
        
        covergroup {
            coverpoint value {
                bins vals[] = [0..15];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_explicit_values(parser):
    """Test bins with explicit value list"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            coverpoint value {
                bins special = [10, 20, 30, 40];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_open_range(parser):
    """Test bins with open-ended range"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            coverpoint value {
                bins high = [200..];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_default(parser):
    """Test default bin"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            coverpoint value {
                bins defined = [0..100];
                bins others[] = default;
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_ignore_bins(parser):
    """Test ignore bins"""
    code = """
    struct test_s {
        rand bit[4] value;
        
        covergroup {
            coverpoint value {
                bins valid[] = [0..15];
                ignore_bins ignore = [7, 8];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_illegal_bins(parser):
    """Test illegal bins"""
    code = """
    struct test_s {
        rand bit[4] value;
        
        covergroup {
            coverpoint value {
                bins valid[] = [0..6, 9..15];
                illegal_bins illegal = [7, 8];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_cross_labeled(parser):
    """Test labeled cross coverage"""
    code = """
    struct test_s {
        rand bit[4] a;
        rand bit[4] b;
        
        covergroup {
            a_cp: coverpoint a;
            b_cp: coverpoint b;
            aXb: cross a_cp, b_cp;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_in_action(parser):
    """Test covergroup in action"""
    code = """
    component pss_top {
        action test_a {
            rand bit[8] value;
            
            covergroup {
                coverpoint value;
            } cg;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_option_per_instance(parser):
    """Test per_instance coverage option"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.per_instance = true;
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_option_at_least(parser):
    """Test at_least coverage option"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.at_least = 2;
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_option_auto_bin_max(parser):
    """Test auto_bin_max coverage option"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.auto_bin_max = 128;
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_option_weight(parser):
    """Test weight coverage option"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.weight = 5;
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_option_goal(parser):
    """Test goal coverage option"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.goal = 95;
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_multiple_coverpoints(parser):
    """Test multiple coverpoints"""
    code = """
    struct test_s {
        rand bit[8] addr;
        rand bit[8] data;
        rand bit[2] cmd;
        
        covergroup {
            coverpoint addr;
            coverpoint data;
            coverpoint cmd;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_enum_coverpoint(parser):
    """Test enum as coverpoint"""
    code = """
    enum op_e { READ, WRITE, EXEC };
    
    struct test_s {
        rand op_e op;
        
        covergroup {
            coverpoint op;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_multiple_crosses_labeled(parser):
    """Test multiple labeled cross coverages"""
    code = """
    struct test_s {
        rand bit[4] a;
        rand bit[4] b;
        rand bit[4] c;
        
        covergroup {
            a_cp: coverpoint a;
            b_cp: coverpoint b;
            c_cp: coverpoint c;
            aXb: cross a_cp, b_cp;
            bXc: cross b_cp, c_cp;
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_bins_mixed(parser):
    """Test mixed bin definitions"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        covergroup {
            coverpoint value {
                bins low = [0..63];
                bins special[] = [64, 128, 192];
                bins high = [200..];
                bins others[] = default;
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)


def test_coverage_multiple_options(parser):
    """Test multiple coverage options"""
    code = """
    covergroup cg_type(bit[8] data_param) {
        option.per_instance = true;
        option.at_least = 2;
        option.auto_bin_max = 64;
        option.weight = 10;
        option.goal = 100;
        
        coverpoint data_param;
    }
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("bin_count", [4, 8, 16])
def test_coverage_scalability_bins(parser, bin_count):
    """Test covergroup with many bins"""
    bins = "\n                ".join([f"bins bin_{i} = [{i*10}..{(i+1)*10-1}];" for i in range(bin_count)])
    
    code = f"""
    struct test_s {{
        rand bit[8] value;
        
        covergroup {{
            coverpoint value {{
                {bins}
            }}
        }} cg;
    }};
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("cp_count", [3, 6, 10])
def test_coverage_scalability_coverpoints(parser, cp_count):
    """Test covergroup with many coverpoints"""
    params = ", ".join([f"bit[8] cp_{i}_param" for i in range(cp_count)])
    cps = "\n        ".join([f"coverpoint cp_{i}_param;" for i in range(cp_count)])
    
    code = f"""
    covergroup cg_type({params}) {{
        {cps}
    }}
    """
    assert_parse_ok(code, parser)


def test_coverage_nested_in_component(parser):
    """Test coverage in nested component structure"""
    code = """
    component pss_top {
        action send_a {
            rand bit[16] size;
            
            covergroup {
                sz: coverpoint size {
                    bins small = [0..255];
                    bins medium = [256..1023];
                    bins large = [1024..];
                }
            } sz_cov;
        }
        
        action test_a {
            send_a s;
            
            activity {
                repeat (10) {
                    do s;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_coverage_with_constraint(parser):
    """Test covergroup with constrained field"""
    code = """
    struct test_s {
        rand bit[8] value;
        
        constraint {
            value < 200;
        }
        
        covergroup {
            coverpoint value {
                bins valid[] = [0..199];
                illegal_bins invalid = [200..];
            }
        } cg;
    };
    """
    assert_parse_ok(code, parser)
from test_helpers import get_symbol, has_symbol, get_location
