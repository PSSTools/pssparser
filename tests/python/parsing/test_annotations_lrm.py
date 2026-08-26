"""LRM conformance for annotation application (PSS 3.1 7.13, Syntax 20).

The standard form is the only form: literal braces, dot-prefixed named
parameters.

    annotation_params_list ::= { annotation_param_item {, annotation_param_item} }
    annotation_param_item  ::= . identifier = constant_expression

PSS 3.1 removed the 3.0 parenthesized form, positional parameters with it, and
`ast/annotation.yaml` follows: an `AnnotationParam` always carries a name.  That
the paren form is *rejected* is pinned next door, by
`test_annotations_31.py::test_annotation_old_paren_form_rejected`.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from pssparser import Parser, ParseException  # noqa: E402


def link(code: str):
    p = Parser()
    p.parses([("test.pss", code)])
    return p.link()


def annotations_of(node):
    return list(node.getAnnotations())


def _name_of(child):
    getter = getattr(child, "getName", None)
    if getter is None:
        return None
    name = getter()
    return name.getId() if hasattr(name, "getId") else name


def find(root, *path):
    node = root
    for name in path:
        target = getattr(node, "getTarget", None)
        if target is not None and target() is not None:
            node = target()
        match = None
        for child in node.getChildren():
            if _name_of(child) == name:
                match = child
                break
        assert match is not None, "no member %r (looking up %s)" % (name, path)
        node = match
    target = getattr(node, "getTarget", None)
    if target is not None and target() is not None:
        node = target()
    return node


DECL = """
annotation desc_s {
    string desc;
    int    weight;
}
"""


# ---------------------------------------------------------------------------
# T-D14 -- the LRM brace form
# ---------------------------------------------------------------------------


def test_brace_form_parses_and_names_its_parameter():
    root = link(DECL + """
        @desc_s {.desc = "Configures the IP"}
        component C { }
        """)
    params = annotations_of(find(root, "C"))[0].getParameters()
    assert len(params) == 1
    assert params[0].getName().getId() == "desc"


def test_brace_form_takes_multiple_parameters():
    root = link(DECL + """
        @desc_s {.desc = "a", .weight = 3}
        component C { }
        """)
    params = annotations_of(find(root, "C"))[0].getParameters()
    assert [p.getName().getId() for p in params] == ["desc", "weight"]


def test_the_brace_form_carries_the_parameter_name():
    """Every parameter is name-mapped -- there is no positional form to fall
    back to, so the name is always present."""
    root = link(DECL + '@desc_s {.desc = "x"}\ncomponent C { }\n')
    params = annotations_of(find(root, "C"))[0].getParameters()
    assert len(params) == 1
    assert params[0].getName().getId() == "desc"


def test_empty_brace_list_parses():
    root = link(DECL + "@desc_s {}\ncomponent C { }\n")
    assert annotations_of(find(root, "C"))[0].getParameters() == []


def test_lrm_example_323_parses_verbatim():
    """PSS 3.1 21.6.1 Example323 -- `code_doc` applied to a statement."""
    link("""
        package p {
            import addr_reg_pkg::*;
            import std_pkg::*;

            function void zero_mem32(addr_handle_t base, int count) {
                repeat (i : count) {
                    @code_doc {.text="Zero the target memory word" }
                    write32(make_handle_from_handle(base, 4*i), 0);
                }
            }
        }
        """)


def test_code_doc_is_declared_in_std_pkg():
    """PSS 3.1 Syntax124 declares code_doc in std_pkg."""
    link("""
        package p {
            import std_pkg::*;
            @code_doc {.text = "documented"}
            component C { }
        }
        """)


# ---------------------------------------------------------------------------
# T-D14b -- standalone annotations and the "no subsequent element" rule
# ---------------------------------------------------------------------------


def test_standalone_annotation_is_terminated_by_a_semicolon():
    """LRM 7.13 Example32: a standalone annotation attaches to a lexical
    location, so it must not attach to whatever is declared next."""
    root = link(DECL + """
        component C {
            @desc_s {.desc = "Scope annotation"};
            int f1;
        }
        """)
    assert annotations_of(find(root, "C", "f1")) == []


def test_element_annotation_attaches_to_the_next_declaration():
    root = link(DECL + """
        component C {
            @desc_s {.desc = "documents f1"}
            int f1;
            int f2;
        }
        """)
    assert len(annotations_of(find(root, "C", "f1"))) == 1
    assert annotations_of(find(root, "C", "f2")) == []


def test_unattached_annotation_in_a_package_is_reported():
    """LRM 7.13: "It is an error if no subsequent element is present in the
    scope."  Example32's third case.

    Reported semantically here: `package_body_item` admits a bare `annotation`,
    so the annotation parses and is found unattached when the scope closes.
    """
    with pytest.raises(ParseException) as exc:
        link(DECL + """
            package p {
                component C { }
                @desc_s {.desc = "nothing follows"}
            }
            """)
    assert "no subsequent element" in str(exc.value)


def test_unattached_annotation_in_a_component_is_reported():
    """The same case one scope down.

    Rejected by the grammar rather than by the check above: a
    `component_body_item_ann` is `annotation* component_body_item`, so the
    annotation has nothing to prefix and the `}` is a syntax error.  Either way
    the LRM's requirement -- that this is an error -- holds.
    """
    with pytest.raises(ParseException):
        link(DECL + """
            component C {
                int f1;
                @desc_s {.desc = "nothing follows"}
            }
            """)


# ---------------------------------------------------------------------------
# T-D13 -- the dead comment-form token is gone (E8)
# ---------------------------------------------------------------------------


def test_comment_at_is_an_ordinary_comment():
    """`//@` was an unreachable lexer token; it has always been a comment."""
    root = link("""
        component C {
            //@desc_s(text = "not an annotation")
            int f1;
        }
        """)
    assert annotations_of(find(root, "C", "f1")) == []


def test_comment_at_is_collected_as_a_docstring_verbatim():
    """Nothing strips the `@` line: silently editing a user's comment text is
    exactly the special case this avoids."""
    p = Parser(collect_docstrings=True)
    p.parses([("test.pss", """
        component C {
            //@doc(text = "hello")
            int f1;
        }
        """)])
    root = p.link()
    assert find(root, "C", "f1").getDocstring() == '@doc(text = "hello")'


def _strip_grammar_comments(text: str) -> str:
    import re
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    return re.sub(r"//[^\n]*", " ", text)


def test_no_comment_at_rule_remains_in_the_grammar():
    src = Path(__file__).parents[3] / "src"
    if not src.is_dir():
        pytest.skip("grammar sources are not present in an installed package")
    for name in ("PSSLexer.g4", "PSSParser.g4"):
        text = _strip_grammar_comments((src / name).read_text())
        assert "TOK_COMMENT_AT" not in text, "%s still references the token" % name
