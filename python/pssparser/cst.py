"""Parse-only concrete syntax trees for PSS source.

The structural companion to :mod:`pssparser.tokens`.  Where that module gives
you the text, this gives you the shape of it -- which tokens form a
declaration, an expression, a constraint block -- without building an abstract
syntax tree::

    >>> from pssparser import cst
    >>> tree = cst.parse("component c { }")
    >>> tree.root.rule_name
    'compilation_unit'
    >>> tree.text == "component c { }"
    True

Concrete, not abstract
    The distinction is the whole point.  An AST is built to answer questions
    about *meaning*, and it earns that by discarding things that do not affect
    meaning: the parentheses in ``((x))``, the branch of a ``compile if`` whose
    condition was false, the exact extent of most expressions.  Each of those
    is something a tool that reproduces source must have, so this tree keeps
    them all -- and, because no AST is built, ``compile if`` is never evaluated
    in the first place.

Structure and text
    Every terminal node carries an index into :attr:`Cst.tokens`, and every
    rule node carries the range of token indices it spans.  So a consumer moves
    between the two views freely::

        node.token_index          # -> index into tree.tokens
        node.start_token          # -> first token index the rule spans
        node.text                 # -> the source it spans, comments included

What this does not do
    No name resolution, no type checking, no linking.
    :attr:`Cst.num_syntax_errors` reports only whether the input matched the
    grammar.  For semantic analysis, use :class:`pssparser.Parser`.
"""

import io

from .core import Cst, CstNode, Factory

__all__ = ["parse", "Cst", "CstNode"]


def parse(src):
    """Parses *src*, returning a :class:`Cst`.

    :param src: PSS source as :class:`str` or UTF-8 :class:`bytes`, or any
        object with a ``read`` method returning either.
    :raises UnicodeDecodeError: if the input is not valid UTF-8.

    Syntax errors are counted, not raised: the tree and the token stream are
    both still produced, because a tool that reformats source needs to be able
    to hand back a file it could not parse rather than fail on it.
    """
    if isinstance(src, str):
        src = io.BytesIO(src.encode("utf-8"))
    elif isinstance(src, (bytes, bytearray)):
        src = io.BytesIO(bytes(src))
    elif not hasattr(src, "read"):
        raise TypeError(
            "expecting str, bytes or a readable object, not %s"
            % type(src).__name__)

    return Factory.inst().mkCstParser(src)
