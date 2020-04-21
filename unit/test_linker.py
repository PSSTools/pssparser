'''
Created on Mar 13, 2020

@author: ballance
'''
from _io import StringIO
import unittest
from unittest.case import TestCase

from antlr4 import InputStream

from pssparser.cu_parser import CUParser
from pssparser.model.type_identifier import TypeIdentifier
from pssparser.model.type_model_visitor import TypeModelVisitor
from pssparser.visitors.link_visitor import LinkVisitor
from pssparser.model.expr_var_ref_path import ExprVarRefPath


class TestLinker(TestCase):
    
    class LinkCheckVisitor(TypeModelVisitor):
        
        def __init__(self):
            super().__init__()
            
        def visit_type_identifier(self, tid:TypeIdentifier):
            if tid.target is None:
                raise Exception("Failed to find reference \"" + str(tid) + "\"")
            
        def visit_expr_var_ref_path(self, r:ExprVarRefPath):
            if r.target is None:
                raise Exception("Failed to find reference \"" + str(r) + "\"")
            
    
    def _runTest(self, text):
        input_stream = InputStream(text)
        parser = CUParser(input_stream, unittest.TestCase.id)
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
        
        self.assertEqual(len(cu.markers), 0, "Syntax Errors")
        
        # Now, run the linker...
        v = LinkVisitor([cu])
        v.link()
        
        # Run the link checker to ensure we didn't miss resolving any
        v = TestLinker.LinkCheckVisitor()
        cu.accept(v)
        
    
    def test_link_super_global(self):
        text = """
        component base {
        }
        component ext : base {
        }
        """
        self._runTest(text)
        
        
    def test_link_super_inner(self):
        text = """
        component pss_top {
            action base {
            }
            
            action ext : base {
            }
        }
        """
        self._runTest(text)
        

    def test_link_super_qname(self):
        text = """
        component pss_top {
            action base {
            }
            
            action ext : pss_top::base {
            }
        }
        """
        self._runTest(text)        
        
    def test_link_action_field(self):
        text = """
        component pss_top {
            action base {
              rand bit       f;
              
              constraint f == 0;
            }
        }
        """
        self._runTest(text)
        
