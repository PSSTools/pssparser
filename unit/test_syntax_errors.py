from _io import StringIO
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestSyntaxErrors(TestCase):

    def _runTest(self, text, name="foo"):
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
        
    def test_extra_comma(self):
        text = '''
        component pss_top {
            action A { }
            action entry {
                A a1, a2;
                activity {
                    a1,;
                    a2;
                }
            }
        }
        '''
        self._runTest(text)
        
        