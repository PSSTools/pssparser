from io import StringIO

import pssparser.core as pss_core


def _build_and_link(code: str, collect_docstrings: bool = False):
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
    return factory, glbl, root


def _linepos(doc: str, idx: int):
    lineno = 1
    linepos = 1
    i = 0
    while i < idx:
        if doc[i] == "\n":
            lineno += 1
            linepos = 1
        else:
            linepos += 1
        i += 1
    return lineno, linepos


def _name(obj):
    n = obj.getName()
    return n.getId() if hasattr(n, "getId") else n


def test_lookup_type_declaration_returns_type_target():
    doc = """
component pss_top {
}
"""
    factory, glbl, root = _build_and_link(doc)
    idx = doc.find("pss_top")
    line, pos = _linepos(doc, idx)
    res = factory.mkTaskFindElementByLocation().find(root, glbl, line, pos)
    assert res.is_valid
    assert res.target_kind == pss_core.FindElementKindE.Type
    assert _name(res.target) == "pss_top"


def test_lookup_field_declaration_returns_field_target():
    doc = """
component C { }
component pss_top {
    /** Field doc */
    C      c1;
}
"""
    factory, glbl, root = _build_and_link(doc, collect_docstrings=True)
    idx = doc.find("c1;")
    line, pos = _linepos(doc, idx)
    res = factory.mkTaskFindElementByLocation().find(root, glbl, line, pos)
    assert res.is_valid
    assert res.target_kind == pss_core.FindElementKindE.Field
    assert _name(res.target) == "c1"
    assert res.target.getDocstring().strip() == "Field doc"


def test_lookup_type_token_in_field_decl_returns_type_target():
    doc = """
component C { }
component pss_top {
    C      c1;
}
"""
    factory, glbl, root = _build_and_link(doc)
    idx = doc.rfind("C")
    line, pos = _linepos(doc, idx)
    res = factory.mkTaskFindElementByLocation().find(root, glbl, line, pos)
    assert res.is_valid
    assert res.target_kind == pss_core.FindElementKindE.Type
    assert _name(res.target) == "C"


def test_lookup_nested_action_returns_type_target():
    doc = """
component pss_top {
    action A {
    }
}
"""
    factory, glbl, root = _build_and_link(doc)
    idx = doc.find("A")
    line, pos = _linepos(doc, idx)
    res = factory.mkTaskFindElementByLocation().find(root, glbl, line, pos)
    assert res.is_valid
    assert res.target_kind == pss_core.FindElementKindE.Type
    assert _name(res.target) == "A"
