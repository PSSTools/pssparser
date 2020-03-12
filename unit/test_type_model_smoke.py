'''
Created on Mar 9, 2020

@author: ballance
'''
from _io import StringIO
from typing import Dict, Tuple, List
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser
from pssparser.visitors.find_types_visitor import FindTypesVisitor, TypeCategory


class TestTypeModelSmoke(TestCase):
    
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
        
        return cu
        
    def _runTestExpect(self, text, name, expects : Dict[TypeCategory,List[str]]):
        cu = self._runTest(text, name)
        
        for t,exp in expects.items():
            v = FindTypesVisitor({t})
            cu.accept(v)

            i = 0
            while i < len(v.type_l):
                qname = "::".join(v.type_l[i].name)
                self.assertTrue(qname in exp, "Failed to find type \"" + qname + "\"")
                exp.remove(qname)
                v.type_l.pop(i)
                
            self.assertEqual(len(v.type_l), 0)
            self.assertEqual(len(exp), 0)
                
    
    def test_component_action(self):
        text = """
        component C {
            action A {
            }
            action B {
            }
        }
        """
        
        self._runTestExpect(text, "test_component_action", {
            TypeCategory.Component : [ "C" ],
            TypeCategory.Action : [ "C::A", "C::B"]
            })
        
    def test_component_in_pkg(self):
        text = """
        package my_pkg {
            component C {
                action A {
                }
                action B {
                }
            }
        }
        """
        
        self._runTestExpect(text, "test_component_action", {
            TypeCategory.Component : [ "my_pkg::C" ],
            TypeCategory.Action : [ "my_pkg::C::A", "my_pkg::C::B"]
            })        