"""Lossless tokenization of PSS source.

This is the entry point for tools that work on source *text* rather than on
meaning -- formatters, syntax highlighters, comment extractors, linters that
report on layout.  It lexes without parsing, and it keeps everything::

    >>> from pssparser import tokens
    >>> ts = tokens.tokenize("component c { } // done\\n")
    >>> ts.text == "component c { } // done\\n"
    True

That identity is the contract, and it holds for *any* input, including input
that does not lex and input the parser would reject.  Whitespace, comments and
unrecognized characters are all tokens here; nothing is skipped and nothing is
normalized.

Why not read the AST?
    Because the AST is a different thing.  Building it evaluates ``compile
    if`` and discards the branch that lost, drops the parentheses the author
    wrote, and does not record where most expressions were.  Every one of those
    is fatal to a formatter, which must reproduce what is on the page.

Offsets
    ``start`` and ``stop`` are **inclusive** and count code points, so they
    index a Python ``str`` directly::

        assert src[t.start:t.stop + 1] == t.text

Encoding
    PSS source is UTF-8.  Passing :class:`bytes` that are not valid UTF-8
    raises :exc:`UnicodeDecodeError` -- the same thing ``bytes.decode`` would
    do, and the right signal for a caller to leave the file alone.
"""

import io

from .core import (
    CHANNEL_BOM,
    CHANNEL_DEFAULT,
    CHANNEL_ERROR,
    CHANNEL_ML_COMMENT,
    CHANNEL_SL_COMMENT,
    CHANNEL_WS,
    Factory,
    Token,
    TokenStream,
    TYPE_BOM,
    TYPE_ERROR_CHAR,
)

__all__ = [
    "tokenize",
    "Token",
    "TokenStream",
    "CHANNEL_DEFAULT",
    "CHANNEL_WS",
    "CHANNEL_SL_COMMENT",
    "CHANNEL_ML_COMMENT",
    "CHANNEL_ERROR",
    "CHANNEL_BOM",
    "TYPE_ERROR_CHAR",
    "TYPE_BOM",
]


def tokenize(src):
    """Tokenizes *src*, returning a :class:`TokenStream`.

    :param src: PSS source as :class:`str` or UTF-8 :class:`bytes`, or any
        object with a ``read`` method returning either.
    :raises UnicodeDecodeError: if the input is not valid UTF-8.

    Reading a file is the common case, and reading it in binary mode is the
    right way to do it: text mode would translate newlines, and this function's
    whole promise is that it does not change the bytes.

    .. code-block:: python

        with open(path, "rb") as fp:
            ts = tokenize(fp.read())
    """
    if isinstance(src, str):
        src = io.BytesIO(src.encode("utf-8"))
    elif isinstance(src, (bytes, bytearray)):
        src = io.BytesIO(bytes(src))
    elif not hasattr(src, "read"):
        raise TypeError(
            "expecting str, bytes or a readable object, not %s"
            % type(src).__name__)

    return Factory.inst().mkTokenizer(src)
