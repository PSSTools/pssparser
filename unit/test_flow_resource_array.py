'''
Created on Mar 4, 2020

@author: ballance
'''

from unittest import TestCase
from antlr4.InputStream import InputStream
from pssparser.cu_parser import CUParser
from _io import StringIO


class TestFlowResourceArray(TestCase):
    
    def _runTest(self, text, name):
        input_stream = InputStream(text)
        parser = CUParser(input_stream, name)
        cu = parser.parse()
        
        if len(cu.markers) > 0:
            print("Test Failed:")
            in_reader = StringIO(text)
            i=1
            while True:
                line = in_reader.readline()
                if line == "":
                    break
                line = line[:-1]
                print("%3d: %s" % (i, line))
                i+=1
        
        self.assertEqual(len(cu.markers), 0, "Errors")    
    
    def test_example_1(self):
        text = """
        buffer data_buff {
            rand int int_attr;
        };

        component flow_object_array_c {
            pool data_buff buff_p;
            bind buff_p *;
    
            action prod_buff_a {
                output data_buff out_1_buff;
            };

            action prod_3_buff_a {
                output data_buff out_3_buff [3];
            };
    
            action cons_buff_a {
                input data_buff in_1_buff;
            };

            action cons_2_buff_a {
                input data_buff in_2_buff [2];
            };
 
            action activity_a {
                prod_buff_a   prod_1b;
                prod_3_buff_a prod_3b;

                cons_buff_a   cons_1b;
                cons_2_buff_a cons_2b_0;
                cons_2_buff_a cons_2b_1;

                activity {
                    prod_1b with {out_1_buff.int_attr == 1;};
                    prod_3b with {
                        foreach (b:out_3_buff) { b.int_attr == 3;};
                    };
            
                     cons_1b with { in_1_buff.int_attr == 3;};

                    cons_2b_0;
                    constraint { foreach (b: cons_2b_0.in_2_buff) {
                        b.int_attr == 3;
                    };};

                    cons_2b_1 with {in_2_buff[0].int_attr >= 2 && in_2_buff[1].int_attr <= 3;};
                    bind cons_2b_1.in_2_buff[1] prod_3b.out_3_buff[0]; // conflict
                };
            };
        };
        """
        
        self._runTest(text, "test_example_1")
        
    def test_example_2(self):
        text = """
        state power_state {
            rand int in [0..4] level;
        }
 
        // graphics component with power state
        component graphics_c {
            pool power_state power_state_var;
            bind power_state_var *; // accessible to all actions under this

            // component power_transition action with input/output
            action power_transition {
                input power_state curr; //current state
                output power_state next; //next state
            }
        }

        // system component with setting power state action
        component my_multimedia_ss_c {
            graphics_c gfx0;
            graphics_c gfx1;
            // consider using object array 

            // actions to request system power state
            action observe_same_power_state {
                rand int in [0..4] observed_level;

                // input multiple power state levels from sub components 
                input power_state gfx_state [2];

                // applying the required observed state to all input states
                constraint { foreach (s : gfx_state) {
                    s.level == observed_level;
                }}
            }

            // explicit binding of the two power state pools variables to the
            // respective inputs of action observe_same_power_state
            bind gfx0.power_state_var observe_same_power_state.gfx_state[0];
            bind gfx1.power_state_var observe_same_power_state.gfx_state[1]; 

        }
        """
        
        self._runTest(text, "test_example_2")
        
        