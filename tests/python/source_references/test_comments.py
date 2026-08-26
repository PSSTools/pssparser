"""Comment capture: `setCollectComments`, placements, and normalization.

The companion `test_docstrings.py` is the compatibility gate -- the docstring
is derived from the same leading run collected here, so both files exercise
one code path and neither may be changed to accommodate the other.
"""

from io import StringIO

import pytest

import pssparser.ast as pss_ast
import pssparser.core as pss_core

LEADING = pss_ast.CommentPlacement.CommentPlacement_Leading
TRAILING = pss_ast.CommentPlacement.CommentPlacement_Trailing
ORPHAN = pss_ast.CommentPlacement.CommentPlacement_Orphan


def build(code: str, collect_comments: bool = True):
    """Parse *code* and return the unlinked global scope.

    Deliberately not linked: linking wraps declarations in symbol scopes, and
    these tests are about where a comment attaches in the AST the builder
    produces.
    """
    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    builder.setCollectComments(collect_comments)
    glbl = factory.getAstFactory().mkGlobalScope(0)
    builder.build(glbl, StringIO(code))
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    return glbl


def find(node, kind, nth=0):
    """The *nth* descendant of *node* whose class name is *kind*.

    Follows `getTarget`/`getDefinition` so the same helper works on a linked
    tree, where declarations sit behind symbol-scope wrappers.
    """
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

    walk(node)
    assert len(hits) > nth, "no %s[%d] in tree" % (kind, nth)
    return hits[nth]


def texts(node, placement=None):
    return [
        c.getText()
        for c in node.getComments()
        if placement is None or c.getPlacement() == placement
    ]


def fn(body: str, decls: str = "") -> str:
    return "component pss_top {\n%s    function int probe(int chan) {\n%s\n    }\n}\n" % (
        decls,
        body,
    )


# ---------------------------------------------------------------- leading


def test_leading_line_comment_run_attaches_to_the_statement():
    g = build(fn("""        // Read the status word.
        // It is the low half.
        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == [
        "Read the status word.",
        "It is the low half.",
    ]


def test_leading_block_comment_loses_its_gutter_and_keeps_relative_indent():
    g = build(fn("""        /**
         * Read the status word.
         *
         *     an indented line
         */
        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == [
        "Read the status word.\n\n    an indented line"
    ]


def test_a_blank_line_detaches_the_comment():
    """The documented way to write a note that does *not* propagate.

    `sphinx-pss`'s native-style.md defines the rule and
    docs/pss-doc-comment-plan.md's two-slot convention relies on it; a file
    note above the imports stays out of generated code by exactly this
    mechanism.
    """
    g = build(fn("""        // Not about the statement below.

        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == []
    assert texts(stmt, ORPHAN) == ["Not about the statement below."]
    assert stmt.getDocstring() == ""


def test_two_blocks_separated_by_a_blank_line_do_not_merge():
    g = build(fn("""        // Detached preamble.

        // Actually about the statement.
        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == ["Actually about the statement."]
    assert texts(stmt, ORPHAN) == ["Detached preamble."]


# --------------------------------------------------------------- trailing


def test_trailing_comment_stays_on_its_own_statement():
    """The misattribution case: it must not become the *next* statement's.

    Before comments were partitioned this way the docstring collector
    concatenated every preceding `//` token with no adjacency test, so
    `return 0; // done` documented whatever followed it.
    """
    g = build(fn("""        int s = 0;      // start clean
        s = chan + 1;"""))
    decl = find(g, "ProceduralStmtDataDeclaration")
    assign = find(g, "ProceduralStmtAssignment")
    assert texts(decl, TRAILING) == ["start clean"]
    assert texts(assign) == []


def test_trailing_comment_on_a_field_declaration():
    g = build("""component pss_top {
    int src;        // CHn_A0
}
""")
    field = find(g, "Field")
    assert texts(field, TRAILING) == ["CHn_A0"]


def test_trailing_comment_on_the_last_statement_of_a_block():
    g = build(fn("""        return chan;    // done"""))
    stmt = find(g, "ProceduralStmtReturn")
    assert texts(stmt, TRAILING) == ["done"]


def test_a_comment_after_the_next_construct_starts_is_not_claimed():
    """Two statements on one line: the comment belongs to the second."""
    g = build(fn("""        int s = 0; int t = 1;   // about t"""))
    first = find(g, "ProceduralStmtDataDeclaration", 0)
    second = find(g, "ProceduralStmtDataDeclaration", 1)
    assert texts(first, TRAILING) == []
    assert texts(second, TRAILING) == ["about t"]


# ------------------------------------------------------------------ depth


def test_comment_inside_a_nested_body_attaches_to_the_nested_statement():
    g = build(fn("""        int s = 0;
        if (chan > 0) {
            // Nested two levels deep.
            s = 1;
        }"""))
    inner = find(g, "ProceduralStmtAssignment")
    assert texts(inner, LEADING) == ["Nested two levels deep."]


def test_an_attributed_field_carries_its_doc_comment():
    """`rand int len;` -- the case sphinx-pss's 3.0.3 version floor names.

    The comment sits above the whole declaration, so above `rand`. The field
    is built by the inner data_declaration rule, which looks left of the
    *type* and found only the `rand` sitting beside it.
    """
    g = build("""struct cfg_s {
    /** How long the transfer is. */
    rand int len;
    /** Where it reads from. */
    rand bit[32] src;   // CHn_A0
}
""")
    assert texts(find(g, "Field", 0), LEADING) == ["How long the transfer is."]
    src = find(g, "Field", 1)
    assert texts(src, LEADING) == ["Where it reads from."]
    assert texts(src, TRAILING) == ["CHn_A0"]


@pytest.mark.parametrize(
    "container,decl",
    [
        ("struct cfg_s", "rand int len;"),
        ("component pss_top", "static const int len = 4;"),
        ("component pss_top", "int len;"),
    ],
    ids=["rand", "static-const", "plain"],
)
def test_a_qualifier_does_not_hide_the_doc_comment(container, decl):
    """The qualifier is parsed by an outer rule than the declaration.

    `rand`, `static const`, `mutable` and the access modifiers all sit ahead
    of the data_declaration that builds the field, so a rule that looks left
    of the *type* finds the qualifier beside it and stops. Three separate
    wrapper rules -- attr_field, const_field_declaration and
    component_data_declaration -- each have to hand the outer token down.
    """
    g = build("""%s {
    /** How long the transfer is. */
    %s
}
""" % (container, decl))
    assert texts(find(g, "Field"), LEADING) == ["How long the transfer is."]


def test_a_trailing_comment_documents_its_own_declaration():
    """sphinx-pss's convention; a leading comment still wins over it."""
    g = build("""struct cfg_s {
    rand int a;     // bytes
    /** The real doc. */
    rand int b;     // ignored in favour of the doc comment
}
""")
    assert find(g, "Field", 0).getDocstring() == "bytes"
    assert find(g, "Field", 1).getDocstring() == "The real doc."


def test_enum_items_carry_their_doc_comments():
    """Items are pushed onto the enum's list, never through addChild."""
    g = build("""enum AddrMode {
    /** Address advances after each beat. */
    INCREMENT,
    /** Address stays put. */
    FIXED
}
""")
    decl = find(g, "EnumDecl")
    items = list(decl.getItems())
    assert [i.getDocstring() for i in items] == [
        "Address advances after each beat.",
        "Address stays put.",
    ]
    assert items[0].getLocation().lineno == 3


def test_declarations_carry_comments_too():
    g = build("""/** The device under test. */
component pss_top {
    /** How many channels. */
    int num_ch;
}
""")
    comp = find(g, "Component")
    assert texts(comp, LEADING) == ["The device under test."]
    assert texts(find(g, "Field"), LEADING) == ["How many channels."]


# ---------------------------------------------------------------- orphans


@pytest.mark.parametrize(
    "kind,code",
    [
        (
            "ExecScope",
            fn("""        return chan;
        // dangling at the end of the body"""),
        ),
        (
            "Component",
            """component pss_top {
    int x;
    // dangling at the end of the component
}
""",
        ),
    ],
)
def test_a_comment_with_nothing_after_it_lands_on_the_enclosing_scope(kind, code):
    g = build(code)
    scope = find(g, kind)
    assert [c.getText() for c in scope.getTrailing_comments()] == [
        "dangling at the end of the %s"
        % ("body" if kind == "ExecScope" else "component")
    ]


# ------------------------------------------------------------- mechanics


def test_interleaved_line_and_block_comments_keep_source_order():
    """`//` and `/* */` arrive on separate hidden channels."""
    g = build(fn("""        // first
        /* second */
        // third
        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == ["first", "second", "third"]


def test_raw_and_is_block_are_preserved():
    g = build(fn("""        /* keep me */
        int s = 0;"""))
    c = find(g, "ProceduralStmtDataDeclaration").getComments()[0]
    assert c.getRaw() == "/* keep me */"
    assert c.getIs_block()
    assert c.getText() == "keep me"

    g = build(fn("""        // keep me
        int s = 0;"""))
    c = find(g, "ProceduralStmtDataDeclaration").getComments()[0]
    assert not c.getIs_block()
    assert c.getRaw().rstrip("\r\n") == "// keep me"


def test_a_comment_records_its_own_location():
    g = build("""component pss_top {

    // on line three
    int x;
}
""")
    c = find(g, "Field").getComments()[0]
    assert c.getLocation().lineno == 3


def test_comment_text_survives_awkward_content():
    g = build(fn("""        // a close marker */ and a µ sign
        int s = 0;"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert texts(stmt, LEADING) == ["a close marker */ and a µ sign"]


def test_statements_carry_a_source_location():
    """Recorded for the first time alongside the comments; the IR needs it."""
    g = build(fn("""        int s = 0;
        s = chan;"""))
    assert find(g, "ProceduralStmtDataDeclaration").getLocation().lineno == 3
    assert find(g, "ProceduralStmtAssignment").getLocation().lineno == 4


def test_one_declaration_statement_with_several_names_does_not_duplicate():
    """`int a, b;` is one source statement and several AST declarations."""
    g = build(fn("""        // about the pair
        int a, b;"""))
    assert texts(find(g, "ProceduralStmtDataDeclaration", 0), LEADING) == [
        "about the pair"
    ]
    assert texts(find(g, "ProceduralStmtDataDeclaration", 1)) == []


# -------------------------------------------------------------- disabled


def test_nothing_is_collected_when_the_flag_is_off():
    code = fn("""        // Read the status word.
        int s = 0;      // trailing""")
    g = build(code, collect_comments=False)
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert list(stmt.getComments()) == []
    assert stmt.getDocstring() == ""


def test_collect_comments_implies_docstring_collection():
    factory = pss_core.Factory.inst()
    builder = factory.mkAstBuilder(factory.mkMarkerCollector())
    assert not builder.getCollectComments()
    assert not builder.getCollectDocStrings()
    builder.setCollectComments(True)
    assert builder.getCollectComments()
    assert builder.getCollectDocStrings()


def test_the_docstring_is_the_leading_run():
    g = build(fn("""        // first
        // second
        int s = 0;      // trailing, not part of it"""))
    stmt = find(g, "ProceduralStmtDataDeclaration")
    assert stmt.getDocstring() == "first\nsecond"


# ----------------------------------------------------------------- extend


def test_comments_survive_type_extension():
    """Every operation in the fw-wb-dma model is written in an `extend`."""
    code = """component wb_dma_ch_c { }

extend component wb_dma_ch_c {
    /** Probe the status register. */
    function int probe(int chan) {
        // Read the status word.
        return chan;
    }
}
"""
    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    builder.setCollectComments(True)
    glbl = factory.getAstFactory().mkGlobalScope(0)
    builder.build(glbl, StringIO(code))
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)
    root = factory.mkAstLinker().link(marker_l, [glbl])
    assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error)

    func = find(root, "FunctionDefinition")
    assert texts(func, LEADING) == ["Probe the status register."]
    assert texts(find(root, "ProceduralStmtReturn"), LEADING) == [
        "Read the status word."
    ]
