'''
Created on Mar 2, 2020

@author: ballance
'''

from unittest import TestCase
from antlr4.InputStream import InputStream
from pssparser.cu_parser import CUParser
from _io import StringIO

class TestTopDownInit(TestCase):
    
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
        component C {
            exec init_down {
            }
            exec init_up {
            }
        }
        component T {
            C  c1, c2;
            exec init_down {
            }  
            exec init_up {
            }
        }
        """
       
        self._runTest(text, "test_example_1")