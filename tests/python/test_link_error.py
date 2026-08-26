

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

# ---------------------------------------------------------------------------
# A caught link failure must leave a walkable model.
#
# `link()` used to snapshot its state *after* the raise, so a caller that
# caught ParseException found user_units() == [] and file_map == {}. The units
# still existed -- ownership had already moved into the linked root inside
# link() -- but the Parser had not recorded where they went, so the only way
# to get a degraded view of a model with one bad reference was to parse the
# whole thing a second time into a Parser that is never linked.
#
# What survives a caught failure is the per-file view: declarations and their
# doc comments. What does not is the cross-file view -- unresolved references
# and unmerged extensions are what the error was about.
# ---------------------------------------------------------------------------

import pytest

from pssparser import Parser
from pssparser.parser import ParseException


_BAD = """package p {
    /** Documented despite the error. */
    component C {
        NoSuchType f;
    }
}
"""

_GOOD = """package q {
    /** A second file. */
    component D { }
}
"""


def _link_failing(collect_docstrings=True):
    p = Parser(collect_docstrings=collect_docstrings)
    p.parses([("bad.pss", _BAD), ("good.pss", _GOOD)])
    with pytest.raises(ParseException):
        p.link()
    return p


def test_failed_link_still_reports_its_files():
    p = _link_failing()
    assert sorted(p.file_map.values()) == ["bad.pss", "good.pss"]
    assert len(p.user_units()) == 2


def test_failed_link_leaves_the_units_walkable():
    """Not merely present -- readable, and without faulting.

    The units are owned by the linked root at this point, so a mistake here
    is a use-after-free rather than an assertion failure.
    """
    p = _link_failing()

    found = {}

    def visit(node):
        for child in node.getChildren():
            name = getattr(child, "getName", lambda: None)()
            if name is not None:
                key = name.getId() if hasattr(name, "getId") else name
                found[key] = child.getDocstring()
            if hasattr(child, "getChildren"):
                visit(child)

    for unit in p.user_units():
        visit(unit)

    assert found.get("C") == "Documented despite the error."
    assert found.get("D") == "A second file."


def test_failed_link_still_reports_its_markers():
    p = _link_failing()
    assert p.markers, "the error that was raised should still be readable"


def test_successful_link_is_unchanged():
    """The reorder touches the success path too, which every consumer uses.

    A mistake here breaks everything rather than only the degraded case, so
    this asserts the success path explicitly rather than relying on the rest
    of the suite to notice.
    """
    p = Parser(collect_docstrings=True)
    p.parses([("a.pss", "package p { component C { } }\n"), ("b.pss", _GOOD)])
    root = p.link()

    assert root is not None
    assert sorted(p.file_map.values()) == ["a.pss", "b.pss"]
    assert len(p.user_units()) == 2
    assert p.root is root
