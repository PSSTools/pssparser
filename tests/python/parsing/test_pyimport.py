from io import StringIO

import pssparser.core as pss_core
from pssparser import Parser


def _parse_global(code: str):
    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    ast_f = factory.getAstFactory()
    glbl = ast_f.mkGlobalScope(0)
    builder.build(glbl, StringIO(code))
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    return glbl


def _id_list(node_list):
    return [i.getId() for i in node_list]


def _parse_and_link(code: str):
    p = Parser()
    p.parses([("test.pss", code)])
    return p.link()


def test_pyimport_single_module():
    root = _parse_and_link("pyimport mymod;")
    assert root is not None


def test_pyimport_with_alias():
    root = _parse_and_link("pyimport mymod::foo::submod as sm;")
    assert root is not None


def test_pyimport_from_module():
    root = _parse_and_link("from mymod::foo::submod pyimport a, b, c;")
    assert root is not None


def test_pyimport_multiple_statements():
    root = _parse_and_link(
        """
        pyimport mymod;
        pyimport mymod::foo::submod as sm;
        from mymod::foo::submod pyimport a, b;
        """
    )
    assert root is not None
