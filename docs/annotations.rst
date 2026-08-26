Annotations
###########

Annotations attach metadata to elements of a PSS model. They have no effect on
the model itself; tools may read them to influence what they generate. See
PSS 3.1 §7.13 for the language definition.


Declaring an annotation type
============================

Annotation types are declared in a package scope:

.. code-block:: pss

   annotation desc_s {
       string desc;
       int    weight;
   }


Applying an annotation
======================

The canonical form
------------------

PSS 3.1 Syntax 20 specifies literal braces with dot-prefixed named parameters::

   annotation        ::= @ annotation_type_identifier [ annotation_params_list ]
   annotation_params_list ::= { annotation_param_item {, annotation_param_item} }
   annotation_param_item  ::= . identifier = constant_expression

The outer braces are literal; the inner braces are BNF repetition. So:

.. code-block:: pss

   @desc_s {.desc = "Configures the IP", .weight = 3}
   component my_ip { }

The standard defines no positional form: every parameter is named.

The paren form (a ``pssparser`` extension)
------------------------------------------

``pssparser`` also accepts a parenthesized form with positional, named, or
mixed parameters:

.. code-block:: pss

   @desc_s("Configures the IP")             // positional
   @desc_s(desc = "Configures the IP")      // named
   @desc_s("Configures the IP", weight = 3) // mixed

This is an extension, not standard PSS. It predates the LRM syntax and covers
ground the standard does not — the LRM has no positional form at all — so it is
retained without a deprecation warning. **Prefer the brace form** in code that
must be portable between tools.

Both forms produce the same ``AnnotationParam`` structure; a named parameter
carries its name, a positional one does not.


Element and standalone annotations
==================================

An **element annotation** attaches to the next model element declared in the
scope, and is not itself terminated by a semicolon:

.. code-block:: pss

   @desc_s {.desc = "Configures the IP"}
   action config { }

A **standalone annotation** is terminated by a single semicolon. It attaches to
a lexical location rather than to an element, so it does *not* document
whatever is declared after it:

.. code-block:: pss

   action config {
       @desc_c {.desc = "Scope annotation"};   // standalone
       int f1;                                 // NOT annotated
   }

It is an error for an element annotation to have no subsequent element in its
scope:

.. code-block:: pss

   action config {
       int f1;
       @desc_c {.desc = "..."}   // Error: nothing follows in this scope
   }

Depending on where it appears this is reported either as a syntax error (in a
scope whose grammar requires a body item after the annotations) or as
``annotation '...' has no subsequent element in this scope to attach to``.


Annotating statements
=====================

An annotation may be applied to a procedural statement, which is what the
standard ``code_doc`` annotation is for (PSS 3.1 §21.6.1):

.. code-block:: pss

   function void zero_mem32(addr_handle_t base, int count) {
       repeat (i : count) {
           @code_doc {.text="Zero the target memory word" }
           write32(make_handle_from_handle(base, 4*i), 0);
       }
   }

``code_doc`` is declared in ``std_pkg``:

.. code-block:: pss

   package std_pkg {
       annotation code_doc {
           string text;
       }
   }


Not supported: ``//@``
======================

There is no comment-form annotation. A ``//@doc(...)`` line is an ordinary
comment and is treated as one everywhere, including when doc-comment collection
is enabled — the text is not edited to remove it.

The lexer once carried a ``TOK_COMMENT_AT: '//@'`` token for this, but it was
unreachable: ``SL_COMMENT`` matches longer and always won. The token has been
removed. Nothing that worked before stops working, because nothing ever reached
it.
