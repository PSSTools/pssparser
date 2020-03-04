'''
Created on Mar 4, 2020

@author: ballance
'''

from unittest import TestCase
from antlr4.InputStream import InputStream
from pssparser.cu_parser import CUParser
from _io import StringIO

class TestFineGrainedScheduling(TestCase):

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
        //<example>
        component container {
            action A {
        //</example>
                activity {
                    PARALLEL_1 : parallel join_branch(A) {
                        A: do MyActionA;
                        B: do MyActionB;
                    }
                    do MyActionC;
                }
        //<example>
            }
        }
        //</example>
        """
        
        self._runTest(text, "test_example_1")

    def test_example_2(self):
        text = """
        //<example>
        component container {
            action A {
        //</example>
                activity {
                    PARALLEL_1 : parallel join_select(1) {
                        A: do MyActionA;
                        B: do MyActionB;
                    }
                    do MyActionC;
                }
        //<example>
            }
        }
        //</example>
        """
        
        self._runTest(text, "test_example_2")

    def test_example_3(self):
        text = """
        //<example>
        component container {
            action A {
        //</example>
                activity {
                    PARALLEL_1 : parallel join_none {
                        A: do MyActionA;
                        B: do MyActionB;
                    }
                    do MyActionC;
                }
        //<example>
            }
        }
        //</example>
        """
        
        self._runTest(text, "test_example_3")

    def test_example_4(self):
        text = """
        //<example>
        component container {
            action A {
        //</example>
                activity {
                    PARALLEL_1 : parallel join_first(1) {
                        A: do MyActionA;
                        B: do MyActionB;
                    }
                    do MyActionC;
                }
        //<example>
            }
        }
        //</example>
        """
        
        self._runTest(text, "test_example_4")
