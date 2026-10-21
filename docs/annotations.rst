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

The PSS 3.0 parenthesized form (``@desc_s("x")``, positional parameters
included) was removed from the language in 3.1, and ``pssparser`` rejects it.


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
       @desc_s {.desc = "Scope annotation"};   // standalone
       int f1;                                 // NOT annotated
   }

It is an error for an element annotation to have no subsequent element in its
scope:

.. code-block:: pss

   action config {
       int f1;
       @desc_s {.desc = "..."}   // Error: nothing follows in this scope
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

An annotation on any statement -- activity,
procedural, or a constraint item such as ``if`` or ``foreach`` -- attaches to
that statement, and an annotation with nothing after it at the end of a
statement body is an error, as at the end of any scope.

pssparser's own ``@lint_pkg::waive`` annotation waives a diagnostic within
the element it is applied to: see :doc:`waivers`.


Checks on an annotation's parameters
====================================

An annotation whose type is not declared is disregarded, as 7.13 requires,
with a warning (LINT403). For one whose type is known, the linker checks each
parameter against the field it names:

* **PSS150** (error). The value must suit its field. The check is stricter
  than for a function argument, because nothing converts an annotation value
  on its way to the generator that reads it: a string is not a number, a
  ``bool`` field takes a ``bool``, and an enum field takes an item of its own
  enum (an integer converts to an enum only by a cast, 7.5.1). An integer
  literal must fit the field's width, read as either signed or unsigned, so
  ``bit[8] m = -1`` is accepted and ``.m = 256`` is not. A field may be named
  only once in one parameter list.
* **LINT411** ``annotation-field-unset`` (warning). The annotation leaves a
  field that has no initializer unset. 7.13 is silent, and the field takes its
  type's default value, so this is a warning.
* **LINT409** ``duplicate-annotation`` (warning). The same annotation type is
  applied to one element twice. ``@block_s`` under an import and
  ``@pkg::block_s`` are the same type.

LINT409 and LINT411 entered the rule set in 2026.2. They are not in the
``minimal`` profile, and a ``rules-version`` pin of 2026.1 holds them back
(see :doc:`lint`).

The fields include those inherited from a base annotation and those added by
``extend annotation``.


Reading annotation values
=========================

``pssparser.annotations`` gives each field of an annotation the value the
annotation gives it, folded to a Python value:

.. code-block:: python

   from pssparser import Parser, annotations

   p = Parser()
   p.parses([("dev.pss", text)])
   root = p.link()

   for ann in annotations.find(root, comp, "gen_pkg::block_s"):
       vals = annotations.effective(root, ann)
       vals["name"].value          # "UART": written in the annotation
       vals["prefix"].is_default   # True: the field's initializer was used

``find(parser_or_root, node, type)`` returns the annotations of one type on
an element, in source order. ``node`` is the declaration or the symbol scope
that wraps it (a component's, an enum's or a function's). ``type`` is a
qualified name or the declaration itself, and is matched against the type the
linker resolved, never against how the annotation spelled it.

``effective(parser_or_root, annotation)`` maps each field name, in
declaration order (base fields first, then the type's own, then those added by
``extend annotation``), to a ``Value``:

``expr``
    The parameter's expression, or the field's initializer when the
    annotation leaves the field unset. ``None`` if there is neither.
``value``
    ``expr`` folded: a ``str``, an ``int`` (at the field's width, so ``~0``
    in a ``bit[8]`` is 255), a ``bool``, or an ``EnumValue(enum, name,
    value)``. ``None`` if it does not fold; a cast does not fold yet.
``field``
    The annotation type's ``Field``.
``is_default``
    True when the value comes from the field's initializer.
``location``
    The parameter's location, or the field declaration's for a default.
    ``None`` when ``expr`` is.

``on(parser_or_root, node)`` returns every annotation on an element whose
type resolved, whatever its type, and ``standalone(parser_or_root, scope)``
the standalone annotations written directly in a scope.
``qualified_name(type_of(parser_or_root, annotation))`` names an
annotation's type. ``fields(parser_or_root, type_scope)`` lists a type's
data fields in the order ``effective`` uses, and ``fold(parser_or_root,
expr)`` folds one expression, before any field width is applied.

All of these take the parser or the linked root first, because an AST node
does not lead back to the root it was linked under.


Doc comments and annotations
============================

A declaration's doc comment may be written above its annotations or between
them and the declaration. If both positions hold a doc comment, the nearer one
documents the declaration and LINT410 warns about the other. See
:doc:`doc_comments`.


Not supported: ``//@``
======================

There is no comment-form annotation. A ``//@doc(...)`` line is an ordinary
comment and is treated as one everywhere, including when doc-comment collection
is enabled — the text is not edited to remove it.

The lexer once carried a ``TOK_COMMENT_AT: '//@'`` token for this, but it was
unreachable: ``SL_COMMENT`` matches longer and always won. The token has been
removed. Nothing that worked before stops working, because nothing ever reached
it.
