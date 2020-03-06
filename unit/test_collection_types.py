'''
Created on Mar 6, 2020

@author: ballance
'''

from _io import StringIO
from unittest import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser


class TestCollectionTypes(TestCase):
   
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
        struct my_s {
            array<int,20>                 my_int_arr;
            int                           my_int_arr_1[20];
        }
        """
        
        self._runTest(text, "test_example_1")
        
    def test_example_2(self):
        text = """
        struct my_s {
            list<int>                  my_list;
        }
        """
        self._runTest(text, "test_example_2")
        
    def test_example_3(self):
        text = """
        struct my_s {
            map<int, string>         my_map;
        }
        """
        self._runTest(text, "test_example_3")
        
    def test_example_4(self):
        text = """
        struct my_s {
            set<int>                     my_int_set;
        }
        """
        self._runTest(text, "test_example_4")
        
    def test_example_5(self):
        # TODO: current parser requires a space: '> >'
        text = """
        struct my_s {
            list<map<string, int> >                 m_list_of_map;
            map<string, list<int> >                 m_map_of_list;
        }
        """
        self._runTest(text, "test_example_5")
        