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


# A pyimport name colliding with another declaration printed "TODO: symbol
# collision with pyimport" to stdout and kept the first, uncounted (report A,
# TaskBuildSymbolTree). It is now an ordinary duplicate declaration -- except
# for the same module imported again, which names the same thing.

def _link_markers(sources):
    p = Parser()
    p.parses(sources)
    try:
        p.link()
    except Exception:
        pass
    return [m for m in p.markers if m["severity"] == "error"]


def test_pyimport_colliding_with_a_type_is_a_duplicate_declaration():
    errs = _link_markers([("test.pss", "pyimport os;\nstruct os { rand int x; }\n")])
    assert len(errs) == 1, errs
    assert "duplicate declaration of 'os'" in errs[0]["message"]


def test_the_same_pyimport_in_two_files_is_not_a_collision():
    errs = _link_markers([
        ("a.pss", "pyimport mymod;\n"),
        ("b.pss", "pyimport mymod;\n"),
    ])
    assert errs == []
