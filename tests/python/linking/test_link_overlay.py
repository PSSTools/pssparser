from io import StringIO

import pssparser.core as pss_core
from pssparser.utils import SymbolScopeUtil


def _parse_global(code: str, fileid: int = 0):
    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    ast_f = factory.getAstFactory()
    glbl = ast_f.mkGlobalScope(fileid)
    builder.build(glbl, StringIO(code))
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    return glbl


def test_overlay_add_type_in_same_file():
    factory = pss_core.Factory.inst()
    linker = factory.mkAstLinker()

    base = _parse_global(
        """
        struct A { }
        struct B : A { }
        """
    )
    marker_l = factory.mkMarkerCollector()
    root = linker.link(marker_l, [base])
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)

    overlay = _parse_global(
        """
        struct A { }
        struct B : A { }
        struct C : B { }
        """
    )
    overlay_markers = factory.mkMarkerCollector()
    root_p = linker.linkOverlay(overlay_markers, root, overlay)
    assert not overlay_markers.hasSeverity(pss_core.MarkerSeverityE.Error)
    assert root_p.symtabHas("A")
    assert root_p.symtabHas("B")
    assert root_p.symtabHas("C")


def test_overlay_remove_type_reports_error():
    factory = pss_core.Factory.inst()
    linker = factory.mkAstLinker()

    base = _parse_global(
        """
        struct A { }
        struct B : A { }
        struct C : B { }
        """
    )
    marker_l = factory.mkMarkerCollector()
    root = linker.link(marker_l, [base])
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)

    overlay = _parse_global(
        """
        struct A { }
        struct C : B { }
        """
    )
    overlay_markers = factory.mkMarkerCollector()
    root_p = linker.linkOverlay(overlay_markers, root, overlay)
    assert overlay_markers.hasSeverity(pss_core.MarkerSeverityE.Error)
    assert root_p is None or isinstance(root_p, object)
