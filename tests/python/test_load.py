'''
Created on Mar 24, 2021

@author: mballance
'''
from unittest.case import TestCase
from _io import StringIO

class TestLoad(TestCase):
    
    def test_smoke(self):
        import pssparser
        
        marker_l = pssparser.core.BaseMarkerListener()
        
        parser = pssparser.core.AstBuilder(marker_l)
        glbl = pssparser.core.mkGlobalScope(0)
        
        print("glbl=" + str(glbl))

        input = StringIO(
            """
            /**
             * Just a comment
             */
             component pss_top {
             }
            """)
        print("--> parse")
        parser.parse(glbl, input)
        print("<-- parse")
        
        class MyVisitor(pssparser.core.BaseVisitor):
            
            def __init__(self):
                super().__init__()
                
            def visitComponent(self, c):
                print("visitComponent")
                
        v = MyVisitor()
        print("glbl=" + str(glbl))
        glbl.accept(v)

#        pssparser.core.doit(2)