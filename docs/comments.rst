Comments
========

The parser can attach a source file's comments to the AST nodes they document,
so a downstream tool can carry the prose across -- a documentation generator, or
a code generator whose output is a transcription of its input.

Collection is **off by default**: it costs a token-stream walk per construct,
and most consumers only want the tree.

Two knobs
---------

.. code-block:: python

   from pssparser import Parser

   Parser(collect_docstrings=True)   # the doc comment on a declaration
   Parser(collect_comments=True)     # every comment, statements included

``collect_docstrings`` populates :py:meth:`getDocstring` on declarations. This
is the older and narrower of the two: one string per declaration, and nothing
at all on a statement. :doc:`doc_comments` covers it in full -- which comment
form is recognized, and how the text is unwrapped.

``collect_comments`` populates ``getComments()`` on **every** ``ScopeChild`` --
procedural statements as well as declarations -- with ``Comment`` nodes that
keep their own text, their own source location, and their relationship to what
they document. It implies ``collect_docstrings``: a consumer asking for every
comment always wants the documenting one identified as well.

The two are extracted independently. The docstring is whichever comment
*documents* the declaration, chosen by the rules in :doc:`doc_comments`;
``getComments()`` is everything that was *written* around it, classified by
position. A comment can appear in both, and the docstring's text may be
unwrapped differently from the same comment's ``getText()``.

On the C++ ``IAstBuilder`` the same knobs are ``setCollectDocStrings(bool)`` and
``setCollectComments(bool)``.

What a comment attaches to
--------------------------

Three placements, decided by source geometry rather than by markup. Nothing
distinguishes ``//`` from ``/* */`` or ``/** */`` here; position is what counts.

.. list-table::
   :header-rows: 1
   :widths: 12 40 48

   * - Placement
     - Rule
     - Example
   * - ``Leading``
     - A contiguous run of comment lines ending on the line immediately above
       the construct.
     - ``// Read the status word.`` above ``int s = read();``
   * - ``Trailing``
     - Begins on the same line as, and after, the construct.
     - ``rand bit[32] src;   // CHn_A0``
   * - ``Orphan``
     - Anything else: separated from the construct by a blank line.
     - a file note above the ``import`` statements

A blank line breaks the association
-----------------------------------

This is the rule the whole model turns on, and it is deliberate rather than
incidental::

    // This documents the declaration below it.
    int a;

    // This documents nothing.

    int b;

Writing a blank line is how an author says "this note is for whoever is editing
this file, not for whoever is reading the generated documentation." A consumer
that emits leading and trailing comments and ignores orphans gets that
distinction for free, and an author gets a way to suppress any one comment
without deleting it.

Comments that no construct can claim -- at the end of a block, after the last
statement -- land on the enclosing scope's ``getTrailing_comments()``.

Normalization
-------------

``getText()`` returns the comment with its markers removed:

* ``//`` and at most one following space are stripped, so the relative indent
  of a run of ``//`` lines survives.
* ``/* */`` loses its delimiters; a ``/**`` block also loses the ``*`` gutter on
  every line. Blank lines at either end go, trailing whitespace per line goes,
  and the common leading indent is removed -- so a block indented four levels
  deep in the source arrives flush left, with its *internal* indentation intact.

``getRaw()`` returns the untouched source text, delimiters included, for a
consumer that wants to do its own thing. ``getIs_block()`` distinguishes the two
forms.

Qualifiers
----------

A doc comment sits above the whole declaration, which means above ``rand``,
``static const``, ``mutable``, ``instance``, and any access modifier::

    /** How long the transfer is. */
    rand int len;

These qualifiers are parsed by a rule outside the declaration itself, and the
comment is found relative to the outermost token, not to the type. Releases
before 3.0.3 looked left of the type, found the qualifier beside it, and
collected nothing.

Enum items carry comments too::

    enum AddrMode {
        /** Address advances after each beat. */
        INCREMENT,
        /** Address stays put. */
        FIXED
    }
