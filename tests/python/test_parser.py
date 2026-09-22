import unittest
from pssparser import Parser
from pssparser.core import Factory
from pssparser.utils import *

class TestParser(unittest.TestCase):
    
    def test_smoke(self):
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }
             """),
            ("def.pss", """
component X {
//    D d1;
}
             """),
        ])

        sym_tree_root = parser.link()
        self.assertTrue(sym_tree_root.symtabHas("pss_top"))

        pss_top_i = sym_tree_root.symtabAt("pss_top")
        pss_top = sym_tree_root.getChild(pss_top_i)
        self.assertTrue(pss_top.symtabHas("A"))

        sym_tree_root_u = SymbolScopeUtil(sym_tree_root)
        A = sym_tree_root_u.getQname("pss_top::A")
        self.assertIsNotNone(A)

    def test_inheritance(self):
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }

                action B : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())
        
        A = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::A"))
        A_super = A.getSuper()
        assert A_super is None

        B = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::B"))
        B_super = B.getSuper()
        assert B_super is not None
        assert B_super.getName() == "A"

    def test_extension(self):
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }

             extend component pss_top {
                action B : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())
        
        A = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::A"))
        A_super = A.getSuper()
        assert A_super is None

        B = SymbolTypeScopeUtil(sym_tree_root_u.getQname("pss_top::B"))
        B_super = B.getSuper()
        assert B_super is not None
        assert B_super.getName() == "A"

    def test_extension_s(self):
        parser = Parser()

        parser.parses([
            ("abc.pss", """
             component C {}
             component pss_top {
                action A { }
             }

             extend component pss_top {
                action B : A { }
             }

             extend component pss_top {
                action C : A { }
             }
             """),
        ])

        sym_tree_root_u = SymbolScopeUtil(parser.link())

        pss_top_u = SymbolScopeUtil(sym_tree_root_u.getQname("pss_top"))
        extensions = pss_top_u.getExtensions()
        # Two `extend component pss_top` blocks, so two extensions.
        #
        # This asserted 3 until 2026-09-22. getExtensions() counts the distinct
        # parents of a scope's children other than the initial declaration, and
        # the third was the compiler-injected `set_executor` prototype, which
        # was pushed straight into the component's child list and so carried a
        # parent belonging to neither the declaration nor an extension. The
        # injection is gone (known-issues CL-S3) and with it the phantom
        # extension.
        self.assertEqual(len(extensions), 2)
