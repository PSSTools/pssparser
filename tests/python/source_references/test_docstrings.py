from io import StringIO

import pssparser.core as pss_core


def _build_and_link(code: str, collect_docstrings: bool):
    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    builder.setCollectDocStrings(collect_docstrings)
    linker = factory.mkAstLinker()
    ast_f = factory.getAstFactory()
    glbl = ast_f.mkGlobalScope(0)
    builder.build(glbl, StringIO(code))
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    root = linker.link(marker_l, [glbl])
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    return root


def test_collect_docstrings_field():
    root = _build_and_link(
        """
        component C { }
        component pss_top {
            /** Field doc */
            C c1;
        }
        """,
        True,
    )
    comp = root.getChild(root.symtabAt("pss_top"))
    field = comp.getChild(comp.symtabAt("c1"))
    assert field.getDocstring().strip() == "Field doc"


def test_collect_docstrings_disabled_by_default():
    root = _build_and_link(
        """
        component C { }
        component pss_top {
            /** Field doc */
            C c1;
        }
        """,
        False,
    )
    comp = root.getChild(root.symtabAt("pss_top"))
    field = comp.getChild(comp.symtabAt("c1"))
    assert field.getDocstring() == ""


def test_comment_not_attached_when_spacing_breaks_association():
    root = _build_and_link(
        """
        component C { }
        component pss_top {
            /** Field doc */

            
            C c1;
        }
        """,
        True,
    )
    comp = root.getChild(root.symtabAt("pss_top"))
    field = comp.getChild(comp.symtabAt("c1"))
    assert field.getDocstring() == ""
