PSS 3.1 Features
================

This chapter documents PSS 3.1 language features as pssparser implements them.
For what *changed* between 3.0 and 3.1, and what that breaks, see
:doc:`pss31_migration`.

.. _template-strings:

Template Strings
================

PSS 3.1 §4.7.1 gives triple-quoted strings four kinds of **special element**.
A ``"""..."""`` string containing any of them is parsed into a structure rather
than kept as flat text, so a consumer can expand it without re-parsing.

A plain ``"..."`` string is never scanned for special elements.  Neither is a
triple-quoted string that contains none: it stays an ordinary ``ExprString``,
which makes "has special elements" a type test rather than a list-length test.

Element kinds
-------------

.. list-table::
   :header-rows: 1
   :widths: 22 78

   * - Notation
     - Meaning
   * - ``{{ expression }}``
     - Mustache expression (§4.7.1.1).  Substituted with the expression's
       value.  The type shall be scalar, and any function called shall be
       ``pure``.
   * - ``{% ... %}``
     - Control-flow directive (§4.7.1.2) -- see the table below.
   * - ``{# ... #}``
     - Block comment (§4.7.1.3), possibly spanning lines.
   * - ``{#}``
     - Line comment, ending at the end of the line.

Comment content is **not** processed for special elements: a ``{{`` inside a
comment is literal text.  Comments are retained in the AST rather than
discarded -- dropping them is the renderer's job, and a formatter that lost
them would be losing the user's writing.

Directives
----------

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Directive
     - Meaning
   * - ``{% if (expr) %}``
     - Opens a conditional block.
   * - ``{% else if (expr) %}``
     - Another arm of the same conditional.
   * - ``{% else %}``
     - The final arm.
   * - ``{% foreach ([it :] expr [[idx]]) %}``
     - Iterates a collection, introducing the iterator and index variables.
   * - ``{% repeat ([idx :] expr) %}``
     - Repeats a block a computed number of times.
   * - ``{% data_type name [= expr]; %}``
     - Declares a template-local variable.
   * - ``{% name = expr; %}``
     - Assigns to a template local.
   * - ``{%%}``
     - Closes the innermost open block.

An ``if``/``else if``/``else`` chain is held **flat**, as one node with several
clauses, because that is the shape of the source.  Nesting it into a tree would
be an invention a formatter then has to undo.

Scoping
-------

A ``foreach`` iterator, a ``repeat`` index, and a ``{% int x; %}`` declaration
are in scope "until the block closing directive" (§4.7.1.2).  They are real
symbols in a real scope, not a side table, which is what lets ``{% x = ...; %}``
be checked: nothing about the syntax distinguishes a legal assignment to a
template local from an illegal assignment to an action attribute, and the only
way to tell them apart is which symbol table the name resolved through
(``PSS112``).

Where special elements are permitted
------------------------------------

* Target-template exec blocks and target-template functions.
* The *filename* of an ``exec file`` block -- deliberately, so that different
  traversals of one action type can write to different files (§20.5.3).
* Any string expression.

Constant templates
------------------

§4.7: a triple-quoted string whose special elements reference only constant
expressions is itself a constant, and one that does not **cannot be used where
a constant string is required** (``PSS115``).

Constant, for this purpose, means ``const`` fields, enum items, type-template
value parameters, and template locals derived from those.  A function call is
never constant -- not even to a ``pure`` function.  ``pure`` says the call has
no side effects, not that a front end can evaluate the body, and pssparser does
not evaluate function bodies.

.. code-block:: pss

   static const int K = 2;

   component c {
       int sz;

       static const string ok  = """n={{K}}""";    // constant -- accepted
       static const string bad = """n={{sz}}""";   // PSS115

       action A {
           exec body C = """n={{sz}}""";           // fine: not a constant context
       }
   }

The last line is the point of ``PSS115`` being raised at the point of *use*:
the same template text is legal in an exec body and illegal in a ``const``
initializer, so the template alone cannot say whether anything is wrong.

What pssparser does not do
--------------------------

**It does not expand templates.**  A ``foreach`` over a solved collection has
no value until solve time, which is a tool's job rather than a front end's.
What a consumer is given instead is the structure, the resolved references, and
byte offsets into the original text -- enough to expand without re-parsing.

Every element records ``offset`` and ``extent`` into the owning template's
``raw`` text, and ``raw`` is byte-identical to the source between the quotes.
A renderer that cannot handle a construct can always fall back to copying the
original bytes.

Diagnostics
-----------

``PSS108``–``PSS115``; see :ref:`core-marker-catalogue`.

Known limits
------------

* A reference before its declaration inside a template is accepted.  The linker
  order-checks declarations in no context at all, which is a missing capability
  rather than a template defect (``known-issues.md`` P5-X1).
* ``PSS113`` reports only what its classifier can call *definitely* non-scalar.
  Member paths, subscripts, nested calls and user-defined types classify as
  unknown and are not reported (P3-X6c).
* A function that is pure only by virtue of an enclosing ``pure component`` is
  still reported by ``PSS114``: the qualifier on a component is not recorded
  (P5-X3).
