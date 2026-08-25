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


# ---------------------------------------------------------------------------
# Interaction with the PSS 3.1 `@doc` annotation (plan item P2-A6)
# ---------------------------------------------------------------------------
#
# PSS 3.1 §21.6.2 makes `std_pkg::doc` the normative mechanism for attaching
# model-level documentation to an element. The comment-derived docstring is a
# pssparser extension that predates it.
#
# Decision: the two are kept side by side and never merged. The annotation is
# reachable via `getAnnotations()`, the comment via `getDocstring()`; neither
# overwrites the other, so no information is lost when both are present and a
# consumer can apply whatever precedence it wants. The documented recommendation
# is to prefer `@doc` when it is present, since it is the standard mechanism.

def test_doc_annotation_and_comment_docstring_coexist():
    root = _build_and_link(
        """
        annotation doc { string text; }
        component C { }
        component pss_top {
            /** Comment doc */
            @doc {.text = "Annotation doc"}
            C c1;
        }
        """,
        True,
    )
    comp = root.getChild(root.symtabAt("pss_top"))
    field = comp.getChild(comp.symtabAt("c1"))

    assert field.getDocstring().strip() == "Comment doc"
    assert field.numAnnotations() == 1
    ann = field.getAnnotation(0)
    assert ann.numParameters() == 1
    assert ann.getParameter(0).getName().getId() == "text"


def test_doc_annotation_alone_leaves_docstring_empty():
    root = _build_and_link(
        """
        annotation doc { string text; }
        component C { }
        component pss_top {
            @doc {.text = "Annotation doc"}
            C c1;
        }
        """,
        True,
    )
    comp = root.getChild(root.symtabAt("pss_top"))
    field = comp.getChild(comp.symtabAt("c1"))

    assert not field.getDocstring().strip()
    assert field.numAnnotations() == 1
