"""The core's parse-and-link session, through `Parser` and directly
(core-in-leaf-plan.md CF1). The lifecycle rules used to live in parser.py
and wasm/bindings.cpp each; these check that the core keeps them."""
import gc

import pytest

import pssparser
import pssparser.core as core
from pssparser.parser import ParseException

GOOD = "component pss_top {\n  action A { }\n}\n"
BAD_TYPE = "component pss_top {\n  action A { no_such_t f; }\n}\n"
COMPILE_IF = (
    "const int W = 8;\n"
    "component pss_top {\n"
    "  compile if (W > 16) { int wide_f; } else { int narrow_f; }\n"
    "}\n")


def test_root_outlives_the_parser():
    """The root wrapper owns the tree; dropping the Parser (and its
    session) must not free it."""
    p = pssparser.Parser()
    p.parses([("t.pss", GOOD)])
    root = p.link()
    del p
    gc.collect()
    names = [root.getUnit(i).getFileid() for i in range(root.numUnits())]
    assert 1 in names


def test_markers_are_resolved_and_sorted_across_files():
    p = pssparser.Parser()
    p.parses([("b.pss", BAD_TYPE), ("a.pss", BAD_TYPE)])
    with pytest.raises(ParseException):
        p.link()
    files = [m["file"] for m in p.markers]
    assert files == sorted(files)
    assert {"a.pss", "b.pss"} <= set(files)


def test_a_parse_starts_the_marker_list_afresh():
    p = pssparser.Parser()
    p.parses([("t.pss", BAD_TYPE)])
    with pytest.raises(ParseException):
        p.link()
    assert p.markers
    p.parses([("u.pss", GOOD)])
    assert p.markers == []


def test_the_message_names_only_the_failing_call():
    p = pssparser.Parser()
    p.parses([("t.pss", BAD_TYPE)])
    with pytest.raises(ParseException) as exc:
        p.link()
    assert "t.pss:2:" in str(exc.value)


def test_builtin_fileid_has_a_name():
    p = pssparser.Parser()
    assert p.resolve_location(-1, 3) == ("<builtin>", 3)
    assert p.resolve_location(7, 3) == ("<unknown>", 3)


def test_names_before_and_after_link():
    p = pssparser.Parser()
    p.parses([("t.pss", GOOD)])
    assert p._filenames == {1: "t.pss"}
    assert p.file_map == {}
    p.link()
    assert p._filenames == {}
    assert p.file_map == {1: "t.pss"}
    assert [u.getFileid() for u in p.user_units()] == [1]


def test_a_failed_source_does_not_consume_its_fileid():
    p = pssparser.Parser()
    with pytest.raises(ParseException):
        p.parses([("bad.pss", "component {")])
    p.parses([("good.pss", GOOD)])
    assert [u.getFileid() for u in p._files] == [0, 1]
    p.link()
    assert p.file_map == {1: "good.pss"}


def test_session_directly():
    s = core.Factory.inst().mkParserSession()
    s.beginParse()
    assert s.parseSource("t.pss", COMPILE_IF)
    assert s.nextFileid() == 2
    assert s.link()
    regions = s.inactiveRegions()
    assert len(regions) == 1 and regions[0][:2] == (1, 3)
    assert s.callMarkers() == []
    root = s.releaseRoot()
    assert root is not None


def test_units_can_be_linked_by_the_callers_own_linker():
    """pssc links `parser._files` itself. The wrappers own the units, so the
    linker's root takes them and nothing frees them twice."""
    p = pssparser.Parser()
    p.parses([("t.pss", GOOD)])
    linker = p.parser_f.mkAstLinker()
    mc = p.parser_f.mkMarkerCollector()
    root = linker.link(mc, p._files)
    del p
    gc.collect()
    assert root.numUnits() >= 2


def test_unlinked_units_are_freed_once():
    for _ in range(3):
        p = pssparser.Parser()
        p.parses([("t.pss", GOOD)])
        files = p._files
        del p
        gc.collect()
        assert files[1].getFileid() == 1
        del files
        gc.collect()
