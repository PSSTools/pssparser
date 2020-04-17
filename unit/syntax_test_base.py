'''
Created on Mar 9, 2020

@author: ballance
'''
from _io import StringIO
import sys
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class SyntaxTestBase(TestCase):

    def _runTest(self, text):
        name = self._testMethodName
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
        
    def setUp(self):
        super().setUp()
        print("--> " + self._testMethodName + "********************************")
        sys.stdout.flush()
        
    def tearDown(self):
        print("<-- " + self._testMethodName + "********************************")
        sys.stdout.flush()
        super().tearDown()
        
    
