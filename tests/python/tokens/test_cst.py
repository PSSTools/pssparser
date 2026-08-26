"""The parse-only CST, from Python.

Two properties carry the rest and are tested first: the tree's token indices
index the accompanying stream, and nothing the parser matched was folded away.
The first is what lets structure and text be used together; the second is why
this exists instead of the AST.
"""

import pytest

from pssparser import cst, tokens


SIMPLE = ("component pss_top {\n"
          "    action A { rand int x; }\n"
          "}\n")


def nodes(tree):
    return list(tree.root.walk())


def terminals(tree):
    return [n for n in nodes(tree) if not n.is_rule and n.token_index >= 0]


# ---------------------------------------------------------------------------
# Structure and text agree
# ---------------------------------------------------------------------------

def test_root_is_the_compilation_unit():
    tree = cst.parse(SIMPLE)
    assert tree.root.is_rule
    assert tree.root.rule_name == "compilation_unit"
    assert tree.num_syntax_errors == 0


def test_parsing_does_not_cost_losslessness():
    assert cst.parse(SIMPLE).text == SIMPLE


def test_terminals_are_the_default_channel_tokens_in_order():
    # The join everything above this depends on: walking the tree and walking
    # the stream must produce the same code, in the same order.
    tree = cst.parse(SIMPLE)
    from_tree = [n.token.text for n in terminals(tree)]
    from_stream = [t.text for t in tree.tokens.code()]
    assert from_tree == from_stream


def test_token_indices_index_the_accompanying_stream():
    tree = cst.parse(SIMPLE)
    for n in nodes(tree):
        if n.is_rule:
            assert n.token_index == -1
            assert n.token is None
        elif n.token_index >= 0:
            assert tree.tokens[n.token_index] is n.token


def test_rule_spans_cover_their_terminals():
    tree = cst.parse(SIMPLE)
    for n in nodes(tree):
        if not n.is_rule or n.start_token < 0:
            continue
        assert n.start_token <= n.stop_token, n.rule_name
        for sub in n.walk():
            if not sub.is_rule and sub.token_index >= 0:
                assert n.start_token <= sub.token_index <= n.stop_token, \
                    n.rule_name


def test_node_text_is_the_source_it_spans():
    tree = cst.parse(SIMPLE)
    for n in nodes(tree):
        if n.is_rule and n.start_token >= 0:
            assert n.text in SIMPLE, n.rule_name
    # The root spans the file, minus only the trailing newline after the last
    # code token -- nothing follows `}` that the grammar matched.
    assert tree.root.text == SIMPLE.rstrip("\n")


def test_node_text_includes_the_comments_inside_it():
    src = "component c { /* keep me */ int x; }"
    tree = cst.parse(src)
    comp = [n for n in nodes(tree)
            if n.rule_name == "component_declaration"][0]
    assert "/* keep me */" in comp.text


# ---------------------------------------------------------------------------
# Nothing was folded away
# ---------------------------------------------------------------------------

def test_both_compile_if_branches_are_present():
    tree = cst.parse("package p {\n"
                     "  compile if (false) {\n"
                     "    component taken { }\n"
                     "  } else {\n"
                     "    component not_taken { }\n"
                     "  }\n"
                     "}\n")
    assert tree.num_syntax_errors == 0
    texts = [n.token.text for n in terminals(tree)]
    assert "taken" in texts
    assert "not_taken" in texts


def test_redundant_parentheses_survive():
    # An AST folds `((x))` to `x`.  Reformatting source that way is a change
    # nobody asked for.
    tree = cst.parse("component c { int x; constraint { ((x)) > 0; } }")
    assert [n.token.text for n in terminals(tree)].count("(") == 2


# ---------------------------------------------------------------------------
# Degraded input
# ---------------------------------------------------------------------------

def test_syntax_errors_are_counted_not_raised():
    tree = cst.parse("component c { this is not pss }")
    assert tree.num_syntax_errors > 0
    # A tree is still produced and the tokens are still complete, which is what
    # lets a caller hand back the input unchanged.
    assert tree.root is not None
    assert tree.text == "component c { this is not pss }"


def test_invalid_utf8_raises_rather_than_producing_a_tree():
    with pytest.raises(UnicodeDecodeError):
        cst.parse(b"// caf\xe9\ncomponent c { }\n")


def test_byte_order_mark_does_not_shift_the_tree():
    # The BOM is a token in the stream but not in the grammar.  If the index
    # mapping were off by it, every terminal in a BOM'd file would name the
    # wrong token -- silently, and only for files with a BOM.
    with_bom = cst.parse("﻿component c { }\n")
    without = cst.parse("component c { }\n")
    assert with_bom.num_syntax_errors == 0
    assert [n.token.text for n in terminals(with_bom)] == \
        [n.token.text for n in terminals(without)]


def test_unlexable_text_does_not_shift_the_tree():
    tree = cst.parse("component c { } $ component d { }\n")
    assert tree.tokens.num_errors == 1
    # The `$` is in the stream but never in the tree, and the terminals after
    # it still name their own tokens.
    assert not any(n.token.is_error for n in terminals(tree))
    assert "d" in [n.token.text for n in terminals(tree)]


def test_empty_input():
    tree = cst.parse("")
    assert tree.root is not None
    assert len(tree.tokens) == 0
    assert tree.text == ""


def test_rejects_input_that_is_not_source():
    with pytest.raises(TypeError):
        cst.parse(42)


# ---------------------------------------------------------------------------
# Node protocol
# ---------------------------------------------------------------------------

def test_nodes_are_indexable_and_iterable():
    root = cst.parse(SIMPLE).root
    assert len(root) == root.num_children
    assert list(root) == list(root.children)
    assert root[0] == root.children[0]
    assert root[-1] == root.children[-1]
    with pytest.raises(IndexError):
        root[len(root)]


def test_nodes_compare_by_position_not_identity():
    root = cst.parse(SIMPLE).root
    a = root.children[0]
    b = root.children[0]
    assert a is not b
    assert a == b
    assert hash(a) == hash(b)
    assert a != root


def test_tree_survives_dropping_the_reference_to_the_cst():
    # Nodes borrow from a C++ tree the Cst owns.  Holding only a node must keep
    # that tree alive, or this is a use-after-free rather than a test.
    node = cst.parse(SIMPLE).root
    assert node.rule_name == "compilation_unit"
    assert len(list(node.walk())) > 1


@pytest.mark.parametrize("path", __import__("pssparser").get_stdlib_files(),
                         ids=lambda p: p.rsplit("/", 1)[-1])
def test_stdlib_parses_and_round_trips(path):
    with open(path, "rb") as fp:
        data = fp.read()
    tree = cst.parse(data)
    assert tree.num_syntax_errors == 0
    assert tree.text.encode("utf-8") == data
