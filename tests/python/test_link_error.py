

from _io import StringIO
from unittest import TestCase


class TestLinkError(TestCase):

    def test_unknown_field_type(self):
        text = """
        struct S {
            int                 f1;
            MyUnknownType       f2;
            bit                 f3;
        }
        """

        from pssparser import core as zspp_core

        factory = zspp_core.Factory.inst()
        
        marker_l = factory.mkMarkerCollector()
        
        parser = factory.mkAstBuilder(marker_l)
        linker = factory.mkAstLinker()
        ast_f = factory.getAstFactory()

        glbl = ast_f.mkGlobalScope(0)
        factory.loadStandardLibrary(parser, glbl)

        print("--> parse")
        parser.build(glbl, StringIO(text))
        print("<-- parse")
        self.assertFalse(marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error))        

        print("--> link")
        linked = linker.link(marker_l, [glbl])
        print("<-- link")

        self.assertTrue(marker_l.hasSeverity(zspp_core.MarkerSeverityE.Error))      