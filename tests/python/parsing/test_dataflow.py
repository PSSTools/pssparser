"""
Tests for PSS dataflow features (buffers, streams, states, flow objects)
Based on PSS v3.0 LRM Chapter 13
"""
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error


# =============================================================================
# Buffer Tests (LRM 13.1)
# =============================================================================

def test_buffer_simple(parser):
    """Test simple buffer declaration"""
    code = """
buffer data_buff_s {
    rand int data;
};
    """
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "data_buff_s")
    assert sym is not None
    assert has_symbol(sym, "data")
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_buffer_with_fields(parser):
    """Test buffer with multiple fields"""
    code = """
    struct mem_segment_s {
        int addr;
        int size;
    };
    
    buffer data_buff_s {
        rand mem_segment_s seg;
        rand bit[8] checksum;
    };
    """
    assert_parse_ok(code, parser)


def test_buffer_with_constraint(parser):
    """Test buffer with constraint"""
    code = """
    buffer data_buff_s {
        rand int size;
        rand int addr;
        
        constraint {
            size > 0;
            size <= 1024;
            addr % 4 == 0;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_buffer_inheritance(parser):
    """Test buffer inheritance"""
    code = """
    buffer base_buff_s {
        rand int data;
    };
    
    buffer extended_buff_s : base_buff_s {
        rand int extra_field;
    };
    """
    assert_parse_ok(code, parser)


def test_buffer_in_component(parser):
    """Test buffer used in component"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Stream Tests (LRM 13.2)
# =============================================================================

def test_stream_simple(parser):
    """Test simple stream declaration"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    """
    assert_parse_ok(code, parser)


def test_stream_with_fields(parser):
    """Test stream with multiple fields"""
    code = """
    struct packet_s {
        int id;
        int payload;
    };
    
    stream data_stream_s {
        rand packet_s pkt;
        rand bit[8] priority;
    };
    """
    assert_parse_ok(code, parser)


def test_stream_with_constraint(parser):
    """Test stream with constraint"""
    code = """
    stream data_stream_s {
        rand int size;
        rand int bandwidth;
        
        constraint {
            size > 0;
            bandwidth > 100;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_stream_inheritance(parser):
    """Test stream inheritance"""
    code = """
    stream base_stream_s {
        rand int data;
    };
    
    stream extended_stream_s : base_stream_s {
        rand int extra_field;
    };
    """
    assert_parse_ok(code, parser)


def test_stream_in_component(parser):
    """Test stream used in component"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# State Tests (LRM 13.3)
# =============================================================================

def test_state_simple(parser):
    """Test simple state declaration"""
    code = """
    state config_s {
        rand int mode;
    };
    """
    assert_parse_ok(code, parser)


def test_state_with_fields(parser):
    """Test state with multiple fields"""
    code = """
    enum mode_e {
        IDLE, ACTIVE, SLEEP
    };
    
    state config_s {
        rand mode_e mode;
        rand bit[8] power_level;
    };
    """
    assert_parse_ok(code, parser)


def test_state_with_constraint(parser):
    """Test state with constraint"""
    code = """
    state config_s {
        rand int frequency;
        rand int voltage;
        
        constraint {
            frequency > 0;
            voltage >= 1000;
            voltage <= 3300;
        }
    };
    """
    assert_parse_ok(code, parser)


def test_state_inheritance(parser):
    """Test state inheritance"""
    code = """
    state base_state_s {
        rand int value;
    };
    
    state extended_state_s : base_state_s {
        rand int extra_field;
    };
    """
    assert_parse_ok(code, parser)


def test_state_in_component(parser):
    """Test state used in component"""
    code = """
    state config_s {
        rand int mode;
    };
    
    component pss_top {
        pool config_s state_p;
        bind state_p *;
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Flow Object Usage Tests (LRM 13.4)
# =============================================================================

def test_buffer_output(parser):
    """Test buffer output in action"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action prod_buff_a {
            output data_buff_s out_buff;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_buffer_input(parser):
    """Test buffer input in action"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action cons_buff_a {
            input data_buff_s in_buff;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_buffer_producer_consumer(parser):
    """Test buffer producer-consumer pattern"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action producer_a {
            output data_buff_s out_buff;
        }
        
        action consumer_a {
            input data_buff_s in_buff;
        }
        
        action test_a {
            producer_a prod;
            consumer_a cons;
            
            activity {
                prod;
                cons;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_output(parser):
    """Test stream output in action"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action prod_stream_a {
            output data_stream_s out_stream;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_input(parser):
    """Test stream input in action"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action cons_stream_a {
            input data_stream_s in_stream;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_producer_consumer(parser):
    """Test stream producer-consumer pattern"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action producer_a {
            output data_stream_s out_stream;
        }
        
        action consumer_a {
            input data_stream_s in_stream;
        }
        
        action test_a {
            producer_a prod;
            consumer_a cons;
            
            activity {
                parallel {
                    prod;
                    cons;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_state_output(parser):
    """Test state output in action"""
    code = """
    state config_s {
        rand int mode;
    };
    
    component pss_top {
        pool config_s state_p;
        bind state_p *;
        
        action write_state_a {
            output config_s out_state;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_state_input(parser):
    """Test state input in action"""
    code = """
    state config_s {
        rand int mode;
    };
    
    component pss_top {
        pool config_s state_p;
        bind state_p *;
        
        action read_state_a {
            input config_s in_state;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_multiple_inputs(parser):
    """Test action with multiple inputs"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action multi_input_a {
            input data_buff_s in1;
            input data_buff_s in2;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_multiple_outputs(parser):
    """Test action with multiple outputs"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action multi_output_a {
            output data_buff_s out1;
            output data_buff_s out2;
        }
    }
    """
    assert_parse_ok(code, parser)


def test_mixed_flow_objects(parser):
    """Test action with mixed flow object types"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    stream data_stream_s {
        rand int data;
    };
    
    state config_s {
        rand int mode;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        pool data_stream_s stream_p;
        pool config_s state_p;
        
        bind buff_p *;
        bind stream_p *;
        bind state_p *;
        
        action mixed_a {
            input data_buff_s in_buff;
            output data_stream_s out_stream;
            input config_s in_state;
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Array Flow Object Tests
# =============================================================================

def test_buffer_array_output(parser):
    """Test buffer array output"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action prod_array_a {
            output data_buff_s out_buff[4];
        }
    }
    """
    assert_parse_ok(code, parser)


def test_buffer_array_input(parser):
    """Test buffer array input"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action cons_array_a {
            input data_buff_s in_buff[4];
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_array_output(parser):
    """Test stream array output"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action prod_array_a {
            output data_stream_s out_stream[2];
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_array_input(parser):
    """Test stream array input"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action cons_array_a {
            input data_stream_s in_stream[2];
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Complex Scenarios
# =============================================================================

def test_buffer_chain(parser):
    """Test chain of buffer operations"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action producer_a {
            output data_buff_s out_buff;
        }
        
        action processor_a {
            input data_buff_s in_buff;
            output data_buff_s out_buff;
        }
        
        action consumer_a {
            input data_buff_s in_buff;
        }
        
        action test_a {
            producer_a prod;
            processor_a proc;
            consumer_a cons;
            
            activity {
                prod;
                proc;
                cons;
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_stream_parallel(parser):
    """Test parallel streams"""
    code = """
    stream data_stream_s {
        rand int data;
    };
    
    component pss_top {
        pool data_stream_s stream_p;
        bind stream_p *;
        
        action producer_a {
            output data_stream_s out1;
            output data_stream_s out2;
        }
        
        action consumer_a {
            input data_stream_s in_stream;
        }
        
        action test_a {
            producer_a prod;
            consumer_a cons1;
            consumer_a cons2;
            
            activity {
                parallel {
                    prod;
                    cons1;
                    cons2;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


def test_all_flow_types(parser):
    """Test all flow object types together"""
    code = """
    buffer data_buff_s {
        rand int data;
    };
    
    stream data_stream_s {
        rand int data;
    };
    
    state config_s {
        rand int mode;
    };
    
    component pss_top {
        pool data_buff_s buff_p;
        pool data_stream_s stream_p;
        pool config_s state_p;
        
        bind buff_p *;
        bind stream_p *;
        bind state_p *;
        
        action setup_a {
            output config_s cfg;
        }
        
        action produce_a {
            input config_s cfg;
            output data_buff_s buff;
            output data_stream_s strm;
        }
        
        action consume_a {
            input data_buff_s buff;
            input data_stream_s strm;
        }
        
        action test_a {
            setup_a setup;
            produce_a prod;
            consume_a cons;
            
            activity {
                setup;
                parallel {
                    prod;
                    cons;
                }
            }
        }
    }
    """
    assert_parse_ok(code, parser)


# =============================================================================
# Scalability Tests
# =============================================================================

@pytest.mark.parametrize("count", [1, 5, 10])
def test_many_buffers(parser, count):
    """Test multiple buffer declarations"""
    buffers = "\n".join([
        f"buffer buff_{i}_s {{ rand int data_{i}; }};"
        for i in range(count)
    ])
    code = f"""
    {buffers}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [1, 5, 10])
def test_many_streams(parser, count):
    """Test multiple stream declarations"""
    streams = "\n".join([
        f"stream stream_{i}_s {{ rand int data_{i}; }};"
        for i in range(count)
    ])
    code = f"""
    {streams}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("count", [1, 5, 10])
def test_many_states(parser, count):
    """Test multiple state declarations"""
    states = "\n".join([
        f"state state_{i}_s {{ rand int data_{i}; }};"
        for i in range(count)
    ])
    code = f"""
    {states}
    """
    assert_parse_ok(code, parser)


@pytest.mark.parametrize("array_size", [2, 4, 8])
def test_buffer_array_sizes(parser, array_size):
    """Test various buffer array sizes"""
    code = f"""
    buffer data_buff_s {{
        rand int data;
    }};
    
    component pss_top {{
        pool data_buff_s buff_p;
        bind buff_p *;
        
        action test_a {{
            output data_buff_s out_buff[{array_size}];
        }}
    }}
    """
    assert_parse_ok(code, parser)
from test_helpers import parse_pss, get_symbol, has_symbol, get_location
