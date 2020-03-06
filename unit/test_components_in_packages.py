'''
Created on Mar 6, 2020

@author: ballance
'''

from _io import StringIO
from unittest import TestCase 

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestComponentsInPackages(TestCase):
    
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
        package P {
            component C1 {
                action A {}
            }
            component C2 {
                action A {}
            }
        }

        component pss_top {
            import P::*;
            C1 c1;                          // Instantiating component C1 from package P.
            C2 c2;                          // Instantiating component C2 from package P. 
            action entry {
                activity { 
                    do C1::A;                   // Using components name as a qualifier to 
                                                // access action A
                    do C2::A;
                }
            }
        }
        """
        
        self._runTest(text, "test_example_1")