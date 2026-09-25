"""A cast binds at the unary level (LRM 8.4.1, Table 11: precedence 2, right).

The cast used to take a whole ``expression`` as its operand, so
``(bit[4])b + c`` built ``Cast(Add(b, c))``. The value is different: with
``b = 200`` and ``c = 100`` it is 108 read correctly and 12 read that way
(pss-corpus ``proc.expr.cast.precedence.001``).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from test_ast_node_probes import _find_nodes_deep, _parse_only  # noqa: E402
from pssparser.ast import ExprBinOp  # noqa: E402


def _shape(e):
    """A compact s-expression of an expression tree, for asserting on."""
    n = type(e).__name__
    if n == "ExprCast":
        return ("cast", _shape(e.getExpr()))
    if n == "ExprBin":
        return (ExprBinOp(e.getOp()).name, _shape(e.getLhs()), _shape(e.getRhs()))
    if n == "ExprUnary":
        return ("unary", _shape(e.getRhs()))
    return "ref" if "Ref" in n or "Hierarchical" in n else n


def _init_of(parser, src):
    """The shape of the initializer of the only field named ``x``."""
    p = _parse_only("component pss_top { action A {"
                    " bit[8] a; bit[8] b; int c;"
                    f" int x = {src}; }} }}", parser)
    fields = [f for f in _find_nodes_deep(p, "Field")
              if f.getName().getId() == "x"]
    assert len(fields) == 1
    return _shape(fields[0].getInit())


@pytest.mark.parametrize("src, want", [
    # The corpus case: the cast takes `b`, not `b + c`.
    ("(bit[4])b + c", ("BinOp_Add", ("cast", "ref"), "ref")),
    # Tighter than every binary operator, `**` included (precedence 3).
    ("(bit[4])b * c", ("BinOp_Mul", ("cast", "ref"), "ref")),
    ("(bit[4])b ** c", ("BinOp_Exp", ("cast", "ref"), "ref")),
    ("(bit[4])b == c", ("BinOp_Eq", ("cast", "ref"), "ref")),
    # On the right of a binary operator it still takes only the next operand.
    ("c + (bit[4])b - a", ("BinOp_Sub", ("BinOp_Add", "ref", ("cast", "ref")), "ref")),
    # Parentheses still give a cast a whole expression.
    ("(bit[4])(b + c)", ("cast", ("BinOp_Add", "ref", "ref"))),
    # Right-associative with the unary operators.
    ("(bit[4])-b", ("cast", ("unary", "ref"))),
    ("-(bit[4])b", ("unary", ("cast", "ref"))),
    ("(int)(bit[4])b + c", ("BinOp_Add", ("cast", ("cast", "ref")), "ref")),
])
def test_cast_binds_at_the_unary_level(parser, src, want):
    assert _init_of(parser, src) == want


def test_parenthesized_name_is_still_a_parenthesized_expression(parser):
    """``(a) - b`` could read as a cast of ``-b`` to a type named ``a``.

    It was a subtraction before the cast moved into ``expression``; it must
    stay one.
    """
    assert _init_of(parser, "(a) - b") == ("BinOp_Sub", "ref", "ref")
