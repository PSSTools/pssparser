"""Doc-comment extraction tests.

Covers the public ``Parser(collect_docstrings=...)`` entry point (E1) and the
``DocCommentExtractor`` association/normalization rules (E2) described in
``docs/doc_comments.rst``.
"""

import pytest

from pssparser import Parser


def link(code: str, collect_docstrings: bool = True):
    """Parse *code* and return the linked root."""
    p = Parser(collect_docstrings=collect_docstrings)
    p.parses([("test.pss", code)])
    return p.link()


def _unwrap(node):
    """Linking wraps a type declaration in a SymbolTypeScope.

    The docstring stays on the declaration, so a consumer reading
    ``getDocstring()`` off the scope sees an empty string.  Reach the
    declaration through ``getTarget()``.
    """
    target = getattr(node, "getTarget", None)
    if target is not None:
        inner = target()
        if inner is not None:
            return inner
    return node


def _name_of(child):
    getter = getattr(child, "getName", None)
    if getter is None:
        return None
    name = getter()
    return name.getId() if hasattr(name, "getId") else name


def find(scope, *path):
    """Walk *path* of names down from *scope*.

    Children are scanned by name rather than looked up with ``symtabAt``:
    that API does ``map.find(key)`` and dereferences the iterator without
    checking it against ``end()``, so a name that is not present segfaults
    instead of reporting a miss.
    """
    node = scope
    for name in path:
        node = _unwrap(node)
        children = node.getChildren()
        match = None
        for i in range(len(children)):
            if _name_of(children[i]) == name:
                match = children[i]
                break
        assert match is not None, "no member %r (looking up %s)" % (name, path)
        node = match
    return _unwrap(node)


def doc(scope, *path) -> str:
    return find(scope, *path).getDocstring()


# ---------------------------------------------------------------------------
# T-D1 -- public API gate
# ---------------------------------------------------------------------------

SIMPLE = """
component pss_top {
    /** Field doc */
    int f1;
}
"""


def test_parser_collects_docstrings_when_asked():
    root = link(SIMPLE, collect_docstrings=True)
    assert doc(root, "pss_top", "f1") == "Field doc"


def test_parser_does_not_collect_docstrings_by_default():
    p = Parser()
    assert p.collect_docstrings is False
    p.parses([("test.pss", SIMPLE)])
    root = p.link()
    assert doc(root, "pss_top", "f1") == ""


def test_collect_docstrings_survives_a_link_boundary():
    """link() drops the builder; the next parse must still collect."""
    p = Parser(collect_docstrings=True)
    p.parses([("a.pss", SIMPLE)])
    p.link()
    p.parses([("b.pss", SIMPLE)])
    root = p.link()
    assert doc(root, "pss_top", "f1") == "Field doc"


# ---------------------------------------------------------------------------
# T-D2 / T-D2b -- anchor selection (D2 and the E2.4 wrapper audit)
# ---------------------------------------------------------------------------


def test_qualified_and_unqualified_fields_in_an_action():
    """D2: `rand` sat between the comment and the anchor, so `x` lost its doc."""
    root = link("""
        component C {
            /// doc f1
            int f1;
            action A {
                /// doc x
                rand int x;
                /// doc y
                int y;
                /// doc z
                static const int z = 1;
            }
        }
        """)
    assert doc(root, "C", "f1") == "doc f1"
    assert doc(root, "C", "A", "x") == "doc x"
    assert doc(root, "C", "A", "y") == "doc y"
    assert doc(root, "C", "A", "z") == "doc z"


def test_access_modifier_wrapper():
    root = link("""
        component C {
            action A {
                /// doc p
                private rand int p;
            }
        }
        """)
    assert doc(root, "C", "A", "p") == "doc p"


def test_struct_attr_field_wrapper():
    root = link("""
        struct S {
            /// doc s1
            rand int s1;
        }
        """)
    assert doc(root, "S", "s1") == "doc s1"


def test_component_data_declaration_wrappers():
    root = link("""
        component C { }
        component pss_top {
            /// doc inst
            instance C inst;
            /// doc k
            static const int k = 1;
        }
        """)
    assert doc(root, "pss_top", "inst") == "doc inst"
    assert doc(root, "pss_top", "k") == "doc k"


def test_abstract_action_wrapper():
    root = link("""
        component C {
            /// doc A
            abstract action A { }
        }
        """)
    assert doc(root, "C", "A") == "doc A"


def test_unwrapped_declarations_still_document():
    """Rules that already start with their own keyword must not regress."""
    root = link("""
        buffer B { }
        component C {
            /// doc pool
            pool B p;
            action A {
                /// doc in_b
                input B in_b;
                /// doc lock_p
                lock B lk;
            }
        }
        """)
    assert doc(root, "C", "p") == "doc pool"
    assert doc(root, "C", "A", "in_b") == "doc in_b"
    assert doc(root, "C", "A", "lk") == "doc lock_p"


def test_annotation_between_comment_and_declaration():
    """An annotation sits between the comment and the declaration it wraps."""
    root = link("""
        annotation desc_s {
            string desc;
        }
        component C {
            /// doc A
            @desc_s("block", owner="dv")
            action A { }
        }
        """)
    assert doc(root, "C", "A") == "doc A"


def test_type_declaration_docstring_is_on_the_target():
    """Linking wraps a type in a SymbolTypeScope; the docstring stays on the
    declaration, which is what consumers must read."""
    p = Parser(collect_docstrings=True)
    p.parses([("t.pss", "/// doc C\ncomponent C { }\n")])
    root = p.link()
    scope = root.getChild(root.symtabAt("C"))
    assert scope.getDocstring() == ""
    assert scope.getTarget().getDocstring() == "doc C"


# ---------------------------------------------------------------------------
# T-D3 / T-D4 -- association, for line comments (§3.6 behavior change)
# ---------------------------------------------------------------------------


def test_blank_line_breaks_a_line_comment_association():
    root = link("""
        component C {
            // far away

            int f1;
        }
        """)
    assert doc(root, "C", "f1") == ""


def test_blank_line_breaks_a_block_comment_association():
    root = link("""
        component C {
            /** far away */

            int f1;
        }
        """)
    assert doc(root, "C", "f1") == ""


def test_separated_line_comment_blocks_do_not_merge():
    root = link("""
        component C {
            // block one

            // block two
            int f1;
        }
        """)
    assert doc(root, "C", "f1") == "block two"


def test_consecutive_line_comments_accumulate():
    root = link("""
        component C {
            // one
            // two
            int f1;
        }
        """)
    assert doc(root, "C", "f1") == "one\ntwo"


# ---------------------------------------------------------------------------
# T-D5 -- normalization: usable as reStructuredText
# ---------------------------------------------------------------------------


def test_indented_block_comment_dedents_with_no_star_residue():
    root = link("""
        component C {
                /**
                 * Line one.
                 *
                 *     indented code
                 */
                int f1;
        }
        """)
    assert doc(root, "C", "f1") == "Line one.\n\n    indented code"


def test_no_docstring_retains_a_marker():
    """The corpus check in miniature: no residue for any supported form."""
    root = link("""
        component C {
            /// a
            int f1;
            //! b
            int f2;
            /* c */
            int f3;
            /** d */
            int f4;
            /*! e */
            int f5;
            // f
            int f6;
        }
        """)
    for i, expected in enumerate("abcdef", start=1):
        text = doc(root, "C", "f%d" % i)
        assert text == expected
        for marker in ("/*", "*/", "//"):
            assert marker not in text


# ---------------------------------------------------------------------------
# T-D9 -- nodes built into typed lists rather than through addChild
# ---------------------------------------------------------------------------


def _docs_by_name(nodes):
    return {(_name_of(n) or ""): n.getDocstring() for n in nodes}


def test_enum_items_document():
    root = link("""
        enum E {
            /// the first one
            A,
            /// the second one
            B = 5,
            C
        }
        """)
    assert _docs_by_name(find(root, "E").getChildren()) == {
        "A": "the first one",
        "B": "the second one",
        "C": "",
    }


def test_enum_items_in_an_extension_document():
    root = link("""
        enum E { A }
        extend enum E {
            /// added later
            B
        }
        """)
    assert _docs_by_name(find(root, "E").getChildren()) == {
        "A": "",
        "B": "added later",
    }


def _proto_params(fn):
    return _docs_by_name(fn.getPrototype(0).getParameters())


def test_function_parameters_document():
    root = link("""
        package p {
            function void f(
                /// how many bytes
                int len,
                /// where to put them
                int addr);
        }
        """)
    assert _proto_params(find(root, "p", "f")) == {
        "len": "how many bytes",
        "addr": "where to put them",
    }


def test_inline_block_comment_documents_a_parameter():
    """A block comment ahead of a parameter on the same line still leads it.

    The trailing-comment rule would otherwise reject it -- it begins on the
    same line as the preceding `(` or `,` -- which would silently undocument
    every parameter written in the usual one-line form.
    """
    root = link("""
        package p {
            function void f(/** how many */ int len, /** where */ int addr);
        }
        """)
    assert _proto_params(find(root, "p", "f")) == {
        "len": "how many",
        "addr": "where",
    }


def test_template_parameters_document():
    root = link("""
        struct S <
            /// element width
            int W = 8,
            /// element type
            type T
        > { }
        """)
    assert _docs_by_name(find(root, "S").getParams().getParams()) == {
        "W": "element width",
        "T": "element type",
    }


# ---------------------------------------------------------------------------
# Corpus check -- normalization escapes that targeted tests miss
# ---------------------------------------------------------------------------

_RESIDUE = ("/*", "*/", "//")


def _all_docstrings(root):
    out = []
    seen = set()

    def walk(node, depth=0):
        if depth > 40 or id(node) in seen:
            return
        seen.add(id(node))
        getter = getattr(node, "getDocstring", None)
        if getter is not None:
            text = getter()
            if text:
                out.append(text)
        children = getattr(node, "getChildren", None)
        if children is not None:
            for child in children():
                walk(child, depth + 1)

    for i in range(root.numUnits()):
        walk(root.getUnit(i))
    return out


def test_standard_library_docstrings_carry_no_marker_residue():
    """Every parse loads the standard library, so this covers real sources
    written without any awareness of the extractor."""
    p = Parser(collect_docstrings=True)
    p.parses([("t.pss", "component pss_top { }")])
    root = p.link()

    texts = _all_docstrings(root)
    assert texts, "the standard library should yield some docstrings"

    for text in texts:
        for marker in _RESIDUE:
            assert marker not in text, "residual %r in %r" % (marker, text)
        assert not text.lstrip().startswith("*"), "residual continuation star: %r" % text
        assert text == text.strip(), "untrimmed docstring: %r" % text


# ---------------------------------------------------------------------------
# T-D10 -- trailing comments (E5, §3.5)
# ---------------------------------------------------------------------------


def test_trailing_comment_documents_its_own_declaration():
    root = link("""
        component C {
            action A {
                rand int len;   // how many bytes
                int other;
            }
        }
        """)
    assert doc(root, "C", "A", "len") == "how many bytes"
    assert doc(root, "C", "A", "other") == ""


def test_doxygen_trailing_markers_are_accepted():
    root = link("""
        component C {
            int a;   ///< marked with slashes
            int b;   //!< marked with a bang
            int c;   /**< marked as a block */
        }
        """)
    assert doc(root, "C", "a") == "marked with slashes"
    assert doc(root, "C", "b") == "marked with a bang"
    assert doc(root, "C", "c") == "marked as a block"


def test_leading_comment_wins_over_trailing():
    root = link("""
        component C {
            /// the leading one
            int f1;   // the trailing one
        }
        """)
    assert doc(root, "C", "f1") == "the leading one"


def test_trailing_comment_on_a_scope():
    root = link("""
        component C {
            action A { }   // an action
        }
        """)
    assert doc(root, "C", "A") == "an action"


# ---------------------------------------------------------------------------
# T-D4b -- the full DocComment on the AST (E4)
# ---------------------------------------------------------------------------


def test_raw_form_and_location_are_exposed():
    import pssparser.ast as ast

    root = link("""
        component C {
            /** Summary.
             *  More.
             */
            int f1;
        }
        """)
    f1 = find(root, "C", "f1")
    assert f1.getDocstring() == "Summary.\nMore."
    assert f1.getDocRaw() == "/** Summary.\n             *  More.\n             */"
    assert f1.getDocForm() == ast.DocCommentForm.DocForm_DocBlock
    # The comment's own location, not the declaration's: an error in the doc
    # text can then be reported where the author wrote it.
    assert f1.getDocLocation().lineno == 3
    assert f1.getDocLocation().lineno < f1.getLocation().lineno


def test_doc_form_distinguishes_the_comment_styles():
    import pssparser.ast as ast

    root = link("""
        component C {
            // a
            int f1;
            /// b
            int f2;
            /* c */
            int f3;
            /** d */
            int f4;
            int f5;
        }
        """)
    F = ast.DocCommentForm
    assert find(root, "C", "f1").getDocForm() == F.DocForm_Line
    assert find(root, "C", "f2").getDocForm() == F.DocForm_DocLine
    assert find(root, "C", "f3").getDocForm() == F.DocForm_Block
    assert find(root, "C", "f4").getDocForm() == F.DocForm_DocBlock
    assert find(root, "C", "f5").getDocForm() == F.DocForm_None


# ---------------------------------------------------------------------------
# T-D11 -- source extents (E6)
# ---------------------------------------------------------------------------


def test_scope_reports_a_usable_range():
    root = link("""
        component C {
            action A {
            }
        }
        """)
    a = find(root, "C", "A")
    start, end = a.getLocation(), a.getEndLocation()
    assert start.lineno == 3
    assert end.lineno == 4          # the closing brace
    assert end.lineno > start.lineno
    assert start.extent > 0


def test_field_reports_a_usable_range():
    root = link("""
        component C {
            action A {
                rand int f1 = 5;
            }
        }
        """)
    f1 = find(root, "C", "A", "f1")
    assert f1.getLocation().lineno == 4
    assert f1.getEndLocation().lineno == 4
    # From the declarator through its initializer: `f1 = 5`.
    assert f1.getLocation().extent == len("f1 = 5")


def test_synthesized_members_are_still_identifiable():
    """A negative line number marks a member the parser invented."""
    root = link("component C { }")
    c = find(root, "C")
    synthesized = [ch for ch in c.getChildren() if ch.getLocation().lineno < 0]
    for ch in synthesized:
        assert ch.getDocstring() == ""


# ---------------------------------------------------------------------------
# T-D12 -- the standard-library sources ship with the package (E7)
# ---------------------------------------------------------------------------


def test_standard_library_sources_are_locatable():
    import os
    import pssparser

    files = pssparser.get_stdlib_files()
    names = sorted(os.path.basename(f) for f in files)
    assert names == [
        "addr_reg_pkg.pss",
        "executor_pkg.pss",
        "std_pkg.pss",
        "sync_pkg.pss",
    ]
    for f in files:
        assert os.path.isfile(f)
        with open(f) as fp:
            assert fp.read().strip(), "%s is empty" % f
    assert os.path.isdir(pssparser.get_stdlib_dir())


def test_standard_library_sources_parse_and_document():
    """The shipped text is valid PSS and carries doc comments.

    Built through the low-level API rather than ``Parser``: every ``Parser``
    loads the compiled-in copy of the standard library first, so handing it
    these files as well reports a duplicate declaration for every type in them.
    A consumer that wants to *document* the core library has to build the units
    itself, exactly as this does.
    """
    import pssparser
    import pssparser.core as pss_core

    factory = pss_core.Factory.inst()
    marker_l = factory.mkMarkerCollector()
    builder = factory.mkAstBuilder(marker_l)
    builder.setCollectDocStrings(True)
    ast_f = factory.getAstFactory()

    docstrings = []
    for i, path in enumerate(pssparser.get_stdlib_files()):
        glbl = ast_f.mkGlobalScope(i)
        with open(path) as fp:
            builder.build(glbl, fp)
        assert not marker_l.hasSeverity(pss_core.MarkerSeverityE.Error), path
        docstrings += _all_docstrings_of(glbl)

    assert docstrings, "the standard-library sources should carry doc comments"
    for text in docstrings:
        for marker in _RESIDUE:
            assert marker not in text, "residual %r in %r" % (marker, text)


def _all_docstrings_of(node, depth=0):
    out = []
    if depth > 40:
        return out
    getter = getattr(node, "getDocstring", None)
    if getter is not None and getter():
        out.append(getter())
    children = getattr(node, "getChildren", None)
    if children is not None:
        for child in children():
            out += _all_docstrings_of(child, depth + 1)
    return out
