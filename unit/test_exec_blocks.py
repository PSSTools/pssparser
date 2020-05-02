from _io import StringIO
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestExecBlocks(TestCase):
    
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
        
    def disabled_test_exec_file(self):
        text = '''
        component pss_top {
            action entry_a {
                exec file "foo" = """content""";
                
                ;
            }
        }
        '''
        
        self._runTest(text, "")