'''
Created on Mar 4, 2020

@author: ballance
'''

from _io import StringIO
from unittest import TestCase 

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestActionArrayElemTraversal(TestCase):

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
        component pss_top {
            action A { }
            action entry {
                A      a_arr[4]; // array<A, 4> is equivalent a_arr;

                A      a1, a2, a3, a4;
                activity {
                    a_arr[0];
                    a1;
                }
            }
        }
        """
        
        self._runTest(text, "test_example_1")
        

    def test_example_2(self):
        text = """
            component pss_top {
                action A { }
                action entry {
                    rand bit traverse_arr;
                    A      a_arr[2];
                    activity {
                        if (traverse_arr) {
                            a_arr;
                        } else {
                            a_arr[0];
                            a_arr[1];
                        }
                    }
                }
            }
        """
        
        self._runTest(text, "test_example_2")