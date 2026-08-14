Doc Comments
############

``pssparser`` can associate the comments in a PSS source file with the
declarations they document, and hand back normalized text that a documentation
generator can use directly. This page is the contract: what counts as a doc
comment, which declaration it attaches to, and what the parser does to the text
before you see it.

Collection is off by default. Turn it on through the ``Parser`` constructor:

.. code-block:: python

   from pssparser import Parser

   parser = Parser(collect_docstrings=True)
   parser.parse(["design.pss"])
   root = parser.link()

Every ``ScopeChild`` then carries the text on ``getDocstring()``. Nodes with no
doc comment return the empty string.

This holds on the **linked tree** as well as on the AST. Linking wraps each
declaration in a symbol scope, and the linker copies the doc comment — along
with ``getDocRaw()``, ``getDocForm()`` and ``getDocLocation()`` — onto that
scope:

.. code-block:: python

   scope = root.getChild(root.symtabAt("my_component"))
   text  = scope.getDocstring()

The same call works for a package, a function, an enum and a type, which are
four different scope classes. Earlier releases required a ``getTarget()`` hop
for a ``SymbolTypeScope``, and offered no route at all for the other three,
because they set no target. Reading ``getDocstring()`` directly is now the
supported way; ``getTarget()`` still returns the declaration where there is
one, and the declaration still carries its own copy.

.. note::

   ``getTarget()`` is not a general back-pointer. It is declared as a
   traversal edge, so a scope that sets one is visited through it; that is why
   an enum scope deliberately leaves it unset. Use it to reach declaration-only
   APIs such as ``getParams()``, not to read documentation.

.. _multi-declaration-docstrings:

When more than one declaration contributes
==========================================

One symbol scope can come from several declarations. A package is declared once
per file that opens it, and a function may be declared and then defined
elsewhere. When more than one of them carries a doc comment:

   **The first non-empty doc comment in link order wins.**

Nothing is merged and nothing is overwritten. Concatenating would assemble one
description out of prose written in unrelated files, and last-wins would depend
on link order in a way a reader cannot see. An empty docstring is not a
contribution, so a file that happens to link first does not silence a later one
that actually documented the package.

.. code-block:: pss

   // a.pss
   /** Transfer descriptors. */
   package dma { }

   // b.pss -- links second; this comment is not used
   /** Also transfer descriptors. */
   package dma { }

``package a::b { }`` documents ``b``. It also creates an intermediate scope
``a``, which has no declaration of its own and so is never documented by it.


Which comments are doc comments
===============================

By default **every** comment form is a doc comment:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Form
     - Spelling
     - Notes
   * - Line
     - ``//``
     - An ordinary comment. Counts by default.
   * - Doc line
     - ``///``, ``//!``
     - The marked line forms.
   * - Block
     - ``/* ... */``
     - An ordinary block comment. Counts by default.
   * - Doc block
     - ``/** ... */``, ``/*! ... */``
     - The marked block forms.

Requiring a marker would leave the common case undocumented: in PSS sources a
plain ``//`` above a declaration is overwhelmingly meant to describe it. A
project that prefers the stricter Doxygen reading can set strict mode, in which
only ``///``, ``//!``, ``/**`` and ``/*!`` count:

.. code-block:: c++

   builder->setDocCommentStrictMarkers(true);


Association
===========

A doc comment attaches to the declaration that follows it. The rule is
adjacency, and there is exactly one of them:

**A blank line breaks the association.**

.. code-block:: pss

   // documents f1
   int f1;

   // does NOT document f2 -- a blank line intervenes

   int f2;

This is what Doxygen, Javadoc and Python docstrings all do, and it now applies
uniformly to line comments and block comments alike.

Consecutive line comments accumulate into one block:

.. code-block:: pss

   // First line.
   // Second line.
   int f1;          // -> "First line.\nSecond line."

A block comment is a complete doc block by itself, so two adjacent blocks do
not merge -- the nearest one wins:

.. code-block:: pss

   /** ignored */
   /** documents f1 */
   int f1;

No whitespace at all is still an association:

.. code-block:: pss

   /** documents f1 */int f1;

The comment attaches to the declaration **as written in source**, including any
qualifier or annotation that precedes the type:

.. code-block:: pss

   /// documents x
   rand int x;

   /// documents A
   abstract action A { }

   /// documents B
   @my_annotation
   action B { }


Trailing comments
-----------------

A comment beginning on the same line that a declaration ends attaches to that
declaration:

.. code-block:: pss

   rand int len;   // how many bytes

Doxygen's explicit markers (``///<``, ``//!<``, ``/**< ... */``, ``/*!< ... */``)
are also accepted, and the ``<`` is stripped. They are accepted, not required:
since a plain ``//`` documents a declaration when written above it, requiring a
marker below it would be inconsistent.

**A leading doc comment always wins.** A trailing comment is used only when the
declaration has no leading one.

**A trailing comment is never also a leading comment.** A comment on the same
line as the preceding construct belongs to that construct and is excluded from
the next declaration's lookup:

.. code-block:: pss

   int a;  // documents a, and not b
   int b;

The one exception is a comment that also ends on the following declaration's own
line, which is positionally leading it. This is what keeps inline parameter
documentation working:

.. code-block:: pss

   function void f(/** how many */ int len, /** where */ int addr);

The full comment on the AST
===========================

Beyond ``getDocstring()``, every ``ScopeChild`` carries the comment as it was
written:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Accessor
     - Meaning
   * - ``getDocstring()``
     - Normalized body text.
   * - ``getDocRaw()``
     - Verbatim source of the comment block, markers included. Lets a consumer
       apply another dialect without re-lexing.
   * - ``getDocForm()``
     - ``DocCommentForm``: ``DocForm_None``, ``DocForm_Line``,
       ``DocForm_DocLine``, ``DocForm_Block``, ``DocForm_DocBlock``.
   * - ``getDocLocation()``
     - Where the comment itself starts, so an error in the doc text can be
       reported where the author wrote it rather than at the declaration.


Source extents
==============

``getLocation()`` and ``getEndLocation()`` bound a declaration, and
``getLocation().extent`` gives its length in characters. Together they are
enough for a ``[source]`` link that highlights a range:

.. code-block:: python

   start, end = node.getLocation(), node.getEndLocation()
   # lines start..end, columns start.linepos..end.linepos

``extent`` is measured from where ``location`` points. For a field that is the
identifier, not the type, because ``location`` deliberately marks the name.

A node the parser synthesized rather than read from source reports a negative
``lineno``.


The standard library
====================

The parser compiles the standard library in, so parsing never needs the
sources. A tool that *documents* the core library does, and can locate them:

.. code-block:: python

   import pssparser

   pssparser.get_stdlib_dir()     # directory, installed or in-tree
   pssparser.get_stdlib_files()   # the .pss sources, sorted

.. warning::

   Do not hand these files to ``Parser.parse()``. Every ``Parser`` loads the
   compiled-in copy first, so the files arrive as a second declaration of every
   type in them and linking fails with a duplicate-declaration error for each.
   To document them, build the units through ``core.Factory`` directly.


Normalization
=============

``getDocstring()`` returns a normalized body. The verbatim source is retained
separately so a consumer can implement another dialect without re-lexing.

1. **Markers are stripped**, longest match first, so ``///`` is recognized
   before ``//`` and ``/**`` before ``/*``. A Doxygen ``<`` immediately
   following a marked form is stripped with it.

2. **Continuation stars are removed** from block-comment lines: any amount of
   leading whitespace, a ``*``, and one following space.

3. **The body is dedented.** The longest common leading-whitespace prefix across
   non-blank lines is removed. **Relative indentation is preserved** -- the
   consumer reads the body as reStructuredText, where indentation is syntax, so
   a nested code block must survive.

   For a block comment the first line sits after the opening marker and its
   indentation says nothing about the body, so it is stripped separately and
   left out of the common-prefix computation (the semantics of Python's
   ``inspect.cleandoc``). In a run of line comments every line counts.

4. **Tabs are expanded** to spaces in leading whitespace before the prefix is
   computed, so mixed indentation dedents predictably. The width defaults to 4
   and is configurable with ``setDocCommentTabWidth()``.

5. **Leading and trailing blank lines are trimmed**, along with trailing
   whitespace at the very end of the body. Whitespace *inside* the body is left
   alone.

So this source:

.. code-block:: pss

           /**
            * Sends one word.
            *
            *     write(addr, data);
            */
           function void send(int addr, int data);

yields exactly::

   Sends one word.

       write(addr, data);


What is documented
==================

Doc comments attach to packages, components, actions, structs and buffers,
enums and their items, functions and their parameters, template parameters,
constraint blocks, exec blocks, pools, bind statements, and fields -- qualified
(``rand``, ``static const``, ``private``, ``instance``) or not.


Changes in Release A
====================

Two behaviors changed. Both make line comments behave the way block comments
already did, so they are fixes rather than breaks -- but they change output:

* **A blank line now breaks a line-comment association.** Previously the rule
  was enforced for block comments only, so a line comment attached across any
  amount of blank space.

* **Separated line-comment blocks are no longer concatenated.** Previously every
  line comment preceding a declaration was joined into one string, regardless of
  the blank lines between them.

In addition, output that was previously unusable is now correct: markers are
stripped for every form, continuation stars are removed at any indentation
depth, and the body is dedented. Text that used to arrive with ``*`` markers and
full source indentation now arrives as clean reStructuredText.

Finally, a comment on the same line as the preceding construct no longer leaks
into the next declaration's documentation.
