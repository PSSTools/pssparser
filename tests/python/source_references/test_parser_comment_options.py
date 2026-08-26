"""The `Parser` surface for docstring and comment collection.

The builder itself has had `setCollectDocStrings` since the beginning, but
`Parser` offered no way to reach it, so the only way to parse with docstrings
was to build the builder by hand.
"""

import pytest

from pssparser import Parser

CODE = """component pss_top {
    /** How many channels. */
    int num_ch;

    function int probe(int chan) {
        // Read the status word.
        return chan;    // as-is
    }
}
"""

EXTEND_A = "component wb_dma_ch_c { }\n"

EXTEND_B = """extend component wb_dma_ch_c {
    /** Probe the status register. */
    function int probe(int chan) {
        // Read the status word.
        return chan;
    }
}
"""


def find(nodes, kind):
    """First *kind* in *nodes*, which are the user's own units.

    Searching the linked root instead would find the standard library's
    declarations first -- they sort ahead of the user's and carry no comments.
    """
    if not isinstance(nodes, (list, tuple)):
        nodes = [nodes]
    hits = []
    seen = set()

    def walk(n):
        if id(n) in seen:
            return
        seen.add(id(n))
        if type(n).__name__ == kind:
            hits.append(n)
        kids = list(n.getChildren()) if hasattr(n, "getChildren") else []
        for acc in ("getBody", "getElse_then", "getTarget", "getDefinition"):
            v = getattr(n, acc)() if hasattr(n, acc) else None
            if v is not None:
                kids.append(v)
        if hasattr(n, "getIf_thenList"):
            kids += list(n.getIf_thenList())
        for k in kids:
            walk(k)

    for n in nodes:
        walk(n)
    assert hits, "no %s in tree" % kind
    return hits[0]


def parse(sources, **kwargs):
    p = Parser(**kwargs)
    p.parses(sources)
    p.link()
    return p, p.user_units()


def test_default_construction_collects_nothing():
    """Other callers must see no change in behaviour or cost."""
    _, units = parse([("t.pss", CODE)])
    field = find(units, "Field")
    assert field.getDocstring() == ""
    assert list(field.getComments()) == []


def test_collect_docstrings_reaches_the_builder():
    _, units = parse([("t.pss", CODE)], collect_docstrings=True)
    assert find(units, "Field").getDocstring() == "How many channels."


def test_collect_docstrings_alone_leaves_comments_empty():
    """The two knobs are independent in the direction that matters."""
    _, units = parse([("t.pss", CODE)], collect_docstrings=True)
    assert list(find(units, "Field").getComments()) == []


def test_collect_comments_implies_docstrings():
    _, units = parse([("t.pss", CODE)], collect_comments=True)
    field = find(units, "Field")
    assert field.getDocstring() == "How many channels."
    assert [c.getText() for c in field.getComments()] == ["How many channels."]


def test_statement_comments_survive_parse_and_link():
    _, units = parse([("t.pss", CODE)], collect_comments=True)
    stmt = find(units, "ProceduralStmtReturn")
    assert sorted(c.getText() for c in stmt.getComments()) == [
        "Read the status word.",
        "as-is",
    ]


def test_comments_survive_extension_across_two_files():
    """Every operation in the fw-wb-dma model lives in an `extend` block.

    Parsed as two files so the merge happens at link time, which is how the
    real model is built.
    """
    _, units = parse(
        [("base.pss", EXTEND_A), ("ext.pss", EXTEND_B)],
        collect_comments=True,
    )
    func = find(units, "FunctionDefinition")
    assert func.getDocstring() == "Probe the status register."
    assert [c.getText() for c in find(units, "ProceduralStmtReturn").getComments()] == [
        "Read the status word."
    ]


def test_the_setting_survives_a_link_and_a_later_parse():
    """link() drops the builder, so the flags must be re-applied to the next."""
    p = Parser(collect_comments=True)
    p.parses([("a.pss", EXTEND_A)])
    p.link()
    p.parses([("b.pss", CODE)])
    p.link()
    assert find(p.user_units(), "Field").getDocstring() == "How many channels."
