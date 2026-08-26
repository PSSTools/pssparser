Source-Preserving APIs
======================

.. currentmodule:: pssparser

Most of ``pssparser`` exists to answer questions about what PSS source
*means*: it builds an abstract syntax tree, resolves names, checks types.  Two
APIs exist for the opposite purpose -- tools that care about what the source
*says*, byte for byte.

* :mod:`pssparser.tokens` -- a lossless token stream
* :mod:`pssparser.cst` -- a parse-only concrete syntax tree

They are what a formatter, a syntax highlighter, a comment extractor or a
layout linter should use.  Everything below is public API with the same
stability commitment as the rest of the package.

Why not the AST?
----------------

The AST is built to reason about meaning, and it earns its usefulness by
discarding what does not affect meaning.  Three of those omissions are fatal
to a tool that reproduces source:

``compile if`` is evaluated
    Building the AST resolves the condition and keeps only the branch that
    won.  A formatter must reproduce both branches, because both are in the
    file the user is editing.

Parentheses are folded
    ``((x))`` becomes ``x``.  Removing parentheses the author wrote is a
    change nobody asked for, and in a long expression it is a change that
    makes the result harder to read.

Extents are approximate
    Most expressions carry a start location and nothing else.  You cannot
    reconstruct a line from a position.

None of this is a defect in the AST.  It is a different tree for a different
job, and reaching for it here would mean losing information before the tool
has a chance to use it.

Tokens
------

.. automodule:: pssparser.tokens
   :members: tokenize
   :noindex:

The contract is one line::

    "".join(t.text for t in tokenize(src)) == src

and it holds for **any** input, including input that does not lex.  That
unconditional form is deliberate: a formatter's safety argument rests on being
able to reproduce its input exactly, and a guarantee with an "unless the file
has a syntax error" clause is not one it can rest on.  Malformed files are
exactly when a user most wants the tool to leave their source alone.

So nothing is skipped:

.. list-table::
   :header-rows: 1
   :widths: 22 12 66

   * - Constant
     - Value
     - Carries
   * - ``CHANNEL_DEFAULT``
     - 0
     - Everything the parser sees.
   * - ``CHANNEL_WS``
     - 10
     - Runs of space, tab, CR and LF.
   * - ``CHANNEL_SL_COMMENT``
     - 11
     - ``//`` comments -- **including the trailing newline**.
   * - ``CHANNEL_ML_COMMENT``
     - 12
     - ``/*`` ... ``*/`` comments.  These do not nest.
   * - ``CHANNEL_ERROR``
     - 13
     - Text no lexer rule matched.  Synthetic.
   * - ``CHANNEL_BOM``
     - 14
     - A leading byte-order mark.  Synthetic.

The two synthetic channels are what make the guarantee unconditional.  ANTLR's
input stream drops a leading BOM and its lexer silently consumes characters it
cannot match; both would be silent modifications of the user's file, so both
are recovered and handed back as tokens.

Offsets index a Python string
    ``start`` and ``stop`` are inclusive and count code points, so
    ``src[t.start:t.stop + 1] == t.text`` always holds.

Example: strip trailing whitespace from comments
    .. code-block:: python

        from pssparser import tokens

        def strip_comment_tails(src):
            out = []
            for t in tokens.tokenize(src):
                if t.channel == tokens.CHANNEL_SL_COMMENT:
                    out.append(t.text.rstrip() + "\\n")
                else:
                    out.append(t.text)
            return "".join(out)

Concrete syntax trees
---------------------

.. automodule:: pssparser.cst
   :members: parse
   :noindex:

:func:`pssparser.cst.parse` runs the parser and stops there -- no AST is
constructed, so ``compile if`` is never evaluated and nothing is folded.

Every terminal node carries an index into :attr:`Cst.tokens`, and every rule
node carries the range of token indices it spans, so a consumer moves between
structure and text freely::

    tree = cst.parse(src)
    for node in tree.root.walk():
        if node.rule_name == "component_declaration":
            print(node.text)          # the source, comments included

Those indices are into the *token stream*, which counts trivia, error and BOM
tokens, not into ANTLR's numbering, which does not.  The two are reconciled
inside the parser so a caller never has to think about it -- a BOM'd file and
the same file without one produce identical trees.

Syntax errors are counted, not raised
    :attr:`Cst.num_syntax_errors` reports whether the input matched the
    grammar.  A tree and a complete token stream are produced either way,
    which is what lets a tool hand back a file it could not parse instead of
    failing on it.

Encoding
--------

PSS source is UTF-8.  Passing bytes that are not raises
:exc:`UnicodeDecodeError` from both entry points -- the same exception
``bytes.decode`` would raise, and the right signal to leave the file alone.

Read files in **binary** mode.  Text mode translates newlines, which defeats
the entire purpose::

    with open(path, "rb") as fp:
        tree = cst.parse(fp.read())

Known lexer behavior
--------------------

Recorded here because a source-preserving tool has to reason about each one.
These are pinned by characterization tests in
``tests/python/tokens/test_lexer_probes.py``.

``//`` comments own their newline
    The newline is inside the ``SL_COMMENT`` token, not in the whitespace run
    after it.  Counting blank lines after a trailing comment is off by one
    unless you know this.

Block comments do not nest
    ``/* a /* b */ c */`` ends at the **first** ``*/``, leaving ``c */`` as
    code.  A "comment out this region" feature built on the opposite
    assumption produces broken source.

An unterminated block comment is not an error
    ``/* a`` with no close lexes as ``TOK_DIV``, ``TOK_ASTERISK``, ``ID`` --
    three ordinary tokens, with ``num_errors`` still zero.  Do not use
    ``num_errors`` as an "is this file sane" check; detecting this needs the
    parser.

``//@`` is an ordinary comment
    A ``TOK_COMMENT_AT`` rule for a comment-form annotation once existed in
    the grammar.  It was unreachable -- ``SL_COMMENT`` matches longer and wins
    -- and the LRM defines no such annotation, so it has been removed.

Escaped identifiers are terminated by whitespace
    In ``\\abc def``, the space is not part of the ``ESCAPED_ID`` token, and
    it is not optional: deleting it would run the identifier into what
    follows.

Triple-quoted strings are one token, verbatim
    An ``exec`` target-template payload arrives as a single
    ``TRIPLE_DOUBLE_QUOTED_STRING`` whose text is byte-identical to the
    source.  Nothing inside is tokenized, so nothing inside can be reformatted
    by accident.  There is no escape character (PSS 4.7): ``"""x\\"""`` ends at
    the ``"""``, with content ``x\\``.

Line numbers count LF
    Under lone-CR line endings every token reports line 1.  Offsets are
    unaffected, so a tool that works in offsets does not care; one that
    reports diagnostics by line does.
