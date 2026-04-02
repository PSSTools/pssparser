from io import StringIO
from unittest.case import TestCase

import pssparser.ast as pss_ast


class TestLoad(TestCase):

    def test_smoke(self):
        import pssparser.core as pssp_core

        factory = pssp_core.Factory.inst()
        marker_l = factory.mkMarkerCollector()
        parser = factory.mkAstBuilder(marker_l)
        linker = factory.mkAstLinker()
        ast_f = factory.getAstFactory()

        glbl = ast_f.mkGlobalScope(0)
        parser.build(glbl, StringIO(
            """
             component pss_top {
             }
            """
        ))

        self.assertFalse(marker_l.hasSeverity(pssp_core.MarkerSeverityE.Error))

        linked = linker.link(marker_l, [glbl])

        class ComponentCollector(pss_ast.VisitorBase):

            def __init__(self):
                super().__init__()
                self.components = []

            def visitComponent(self, c):
                self.components.append(c)
                super().visitComponent(c)

        v = ComponentCollector()
        linked.accept(v)

        self.assertFalse(marker_l.hasSeverity(pssp_core.MarkerSeverityE.Error))
        self.assertTrue(any(c.getName().getId() == "pss_top" for c in v.components))
