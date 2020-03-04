'''
Created on Mar 2, 2020

@author: ballance
'''

from unittest import TestCase
from antlr4.InputStream import InputStream
from pssparser.cu_parser import CUParser
from _io import StringIO

class TestTemplateTypesExamples(TestCase):
    
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
        struct my_template_s <type T> {
            T  t_attr;
        }

        buffer my_buff_s < type T> {
            T  t_attr;
        }

        //<example>
        component container {
        //</example>
        action my_consumer_action <int width, bool is_wide> {
            compile assert (width > 0);
        }
        //<example>
        }
        //</example>

        component eth_controller_c <struct ifg_config_s, bool full_duplex = true> {
        }
        """
        self._runTest(text, "test_example_1")

    # Note: will fail until arrayed flow objects are supported
    def test_example_2(self):
        # TODO: no resource type/identifier specified for the lock
        text = """
        //<example>
        component container {
        //</example>
        action my_consumer_action <int n_locks = 4> {
           compile assert (n_locks in [1..16]);
           lock my_resource_t  my_resource[n_locks];
        }
        //<example>
        }
        //</example>
        """
        self._runTest(text, "test_example_2")
        
        
    def test_example_3(self):
        text = """
        //<example>
        component container {
        //</example>
        action my_consumer_action <int width, bool is_wide = (width > 10)> {
            compile assert (width > 0);
        }
        //<example>
        }
        //</example>
        """
        self._runTest(text, "test_example_3")

    def test_example_4(self):
        text = """
        struct my_container_s <struct T> {
            T               t_attr;
        }

        struct my_template_s <type T> {
            T               t_attr;
        }
        """
        
        self._runTest(text, "test_example_4")
        

    def test_example_5(self):
        text = """
        struct base_t {
            rand bit[3:0]    core;
        }

        struct my_sub1_t : base_t {
            rand bit[3:0]    add1;
        }

        struct my_sub2_t : base_t {
            rand bit[3:0]    add2;
        }

        buffer b1 : base_t { }

        buffer b2 : base_t { }

        //<example>
        component container {
        //</example>
        action my_action_a <buffer B : base_t> {
        }
        //<example>
        }
        //</example>

        struct my_container_s  <struct T : base_t = my_sub1_t > {
            T                              t_attr;
            constraint t_attr.core >= 1;
        }
        """
        
        self._runTest(text, "test_example_5")
        
    def test_example_6(self):
        text = """
       struct my_base1_s {
           rand int attr1;
       }

        struct my_base2_s {
            rand int attr2;
        }

        struct my_container_s <struct T> : T {
        }

        struct top_s {
            rand my_container_s<my_base1_t>        cont1;
            rand my_container_s<my_base2_t>        cont2;
            constraint cont1.attr1  == cont2.attr2;
        }
        """
        self._runTest(text, "test_example_6")

    def test_example_7(self):
        text = """
        struct base_t {
            rand bit[3:0]    core;
        }

        struct my_sub1_t : base_t {
            rand bit[3:0]    add1;
        }

        struct my_sub2_t : base_t {
            rand bit[3:0]    add2;
        }

        struct my_container_s <struct T : base_t = my_sub_1> {
            T                              t_attr;
            constraint t_attr.core >= 1;
        }

        struct top_s {
            my_container_s<>                          my_sub_1_container_attr;
            my_container_s<my_sub2_t>        my_sub_2_container_attr;
        }
        """
        self._runTest(text, "test_example_7")
        

    def test_example_8(self):
        text = """
        component my_comp1_c <int bus_width = 32> {
            action my_action1_a { }
            action my_action2_a <int nof_iter = 4> { }
        }

        component pss_top {
            my_comp1_c<64> comp1;
            my_comp1_c<32> comp2;

            action test {
                activity {
                    do my_comp1_c<64>:: my_action1_a;
                    do my_comp1_c<64>:: my_action2_a<>;
                    do my_comp1_c::my_action1_a;  // Error -  my_comp1_c must be specialized
                    do my_comp1_c<>::my_action1_a; 
                }
            }
        }
        """
        self._runTest(text, "test_example_8")
        
    def test_example_9(self):
        text = """
        struct my_s_1 { }
        struct my_s_2 { }

        struct my_struct_t <int A = 4, int B = 7, int C = 3> {  }

        struct container_t {
            my_struct_t<2>                    a; // instantiated with <2, 7, 3>
            my_struct_t<2, 8>                b; // instantiated with <2, 8, 3>
        }
        """
        self._runTest(text, "test_example_9")
        

    def test_example_10(self):
        text = """
        struct domain_s <int LB = 4, int UB = 7> {
            rand int attr;
            constraint attr >= LB && attr <= UB; 
        }

        struct container_s {
            domain_s<2, 7>            domA;          // specialized with LB = 2, UB = 7
            domain_s<2, 8>            domB;          // specialized with LB = 2, UB = 8
        }

        extend struct domain_s {
            rand int attr_all;                                 // container_s::domA and container_s::domB will have attr_all
            constraint attr_all > LB && attr_all < UB; 
        }

        extend struct domain_s<2> {              // extend instance specialized with LB = 2, UB = 7 (default)
            rand int attr_2_7;                             // container_t::domA will have attr_2_7
            constraint attr_2_7 > LB && attr_2_7 < UB; // Error - LB and UB parameters not accessible in 
        }

        struct sub_somain_s<int MIN, int MAX> : domain_s<MIN, MAX> {
            rand int domain_size;
            constraint domain_size == MAX - MIN + 1;
    
            dynamic constraint half_max_domain {
                attr >= LB && attr <= UB/2;            // Error - LB and UB parameters not accessible in inherited struct
            }
        }
        """
        self._runTest(text, "test_example_10")
        
        