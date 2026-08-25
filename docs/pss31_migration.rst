############################
PSS 3.1 Migration Guide
############################

This guide covers migrating from PSS 3.0 to PSS 3.1 with pssparser.

PSS 3.1 is largely backward compatible with PSS 3.0. The exceptions are listed
first, because they require source changes.

.. note::

   This guide is written incrementally as PSS 3.1 support lands. Sections are
   added as each area of the parser is migrated.

Breaking Changes
================

.. _annotation-syntax-cutover:

Annotation application syntax
-----------------------------

**This is a hard cut-over. The PSS 3.0 syntax is removed, not deprecated.**

PSS 3.1 §7.13 replaces the parenthesized annotation-application form with a
braced, name-mapped one:

.. code-block:: text

   annotation             ::= @ annotation_type_identifier [ annotation_params_list ]
   annotation_params_list ::= { annotation_param_item { , annotation_param_item } }
   annotation_param_item  ::= . identifier = constant_expression

Three things change together:

* parentheses become braces,
* every parameter name is written with a leading ``.``,
* positional parameters are gone — every parameter is name-mapped.

.. code-block:: pss

    annotation desc_s {
        string desc;
        string owner;
    }

    // PSS 3.0 -- no longer accepted
    @desc_s("block", owner="dv")
    component C { }

    // PSS 3.1
    @desc_s {.desc = "block", .owner = "dv"}
    component C { }

**Action required**: rewrite every annotation application. The old form is now
an ordinary syntax error, so nothing is silently mis-parsed — but there is no
deprecation warning to migrate against, and no parser option to accept it.

Positional parameters have no mechanical translation: the name each argument
mapped to has to come from the annotation declaration's field order.

Element and standalone annotations
----------------------------------

PSS 3.1 distinguishes two application forms by the presence of a terminating
semicolon:

.. code-block:: pss

    // Element annotation -- attaches to the declaration that follows it.
    @desc_s {.desc = "the component"}
    component C { }

    // Standalone annotation -- anchored to the enclosing scope.
    @file_note_s {.text = "generated; do not edit"};

An element annotation must be followed by an element in the same scope. This is
an error (``PSS100``), where PSS 3.0 discarded the annotation silently:

.. code-block:: pss

    component C {
        int a;
        @desc_s {.desc = "nothing follows this"}   // PSS100
    }

If the annotation is meant to describe the scope rather than a following
element, terminate it with ``;`` to make it standalone.

Annotations in more places
--------------------------

PSS 3.1 admits ``annotation`` as an alternative of most body-item productions,
so annotations may now appear in scopes that previously rejected them —
including struct, action, component, activity, procedural, constraint,
covergroup, override, and monitor bodies. This is purely additive.

Unknown annotation types are a warning
--------------------------------------

§7.13 requires that *PSS processing tools shall disregard unrecognized
annotations*. An annotation naming an undeclared type therefore produces a
warning (``PSS101``) and the source still compiles. Nothing inside an
unrecognized annotation is checked — no parameter-name or constant-expression
diagnostics are reported for it.

Recognized annotations are checked: parameter names must exist on the
annotation type (including inherited fields), and initializers must be constant
expressions (``PSS102``).

Standard annotations
--------------------

``std_pkg`` now declares the two standard documentation annotations of §21.6:

.. code-block:: pss

    package std_pkg {
        annotation code_doc { string text; }
        annotation doc      { string text; }
    }

``@doc`` is the standard mechanism for attaching model-level documentation to an
element; ``@code_doc`` attaches implementation-level text that a tool may emit
as a comment in generated target code.

pssparser's comment-derived docstrings (``--collect-docstrings``) continue to
work and are **not** merged with these annotations. When both are present, the
comment is available through ``getDocstring()`` and the annotation through
``getAnnotations()``; neither overwrites the other. Consumers that want a single
answer should prefer ``@doc``, since it is the standard mechanism.

A doc comment written above an annotated declaration still attaches to the
declaration:

.. code-block:: pss

    /** Comment doc */
    @doc {.text = "Annotation doc"}
    C c1;

.. _soft-reserved-word:

``soft`` is now a reserved word
-------------------------------

PSS 3.1 adds soft constraints (§13.1.12), so ``soft`` becomes a keyword and can
no longer be used as an identifier:

.. code-block:: pss

    // 3.0 -- was legal, now a syntax error
    struct S { int soft; }

    // 3.1
    struct S { int soft_limit; }

This is worth calling out because it is not obvious from the LRM. Table 3, the
keyword table, does **not** list ``soft`` — but Annex B B.14 spells it
literally in ``soft_constraint_item``, and the two cannot both be right. We
follow Annex B, which is the normative grammar, and treat the omission from
Table 3 as an error in the table.

.. _mustache-brace-collision:

``{{`` in target-template code
------------------------------

.. warning::

   This breaks existing target-template code that happens to contain two
   adjacent open braces. It is not specific to any one construct.

PSS 3.1 §4.7.1 makes ``{{`` open a *mustache expression* inside a triple-quoted
string. Triple-quoted strings have **no escape character**, so target code that
legitimately contains ``{{`` is now read as the start of an expression:

.. code-block:: pss

    // Was verbatim text in PSS 3.0. Now an error: the parser reads
    // `{{1,2},{3,4}}` as a mustache expression, and `1,2},{3,4` is not one.
    exec declaration C = """
        int m[2][2] = {{1,2},{3,4}};
    """;

**Write a literal** ``{{`` **by separating the braces:**

.. code-block:: pss

    exec declaration C = """
        int m[2][2] = { {1,2},{3,4} };
    """;

A single ``{`` is ordinary text, so ``{ {`` needs nothing special — it is simply
not the two-character delimiter. This is the *only* portable spelling: PSS 3.1
defines no escape sequence, no raw block, and no way to change the delimiters, so
a tool-specific escape such as ``\{{`` would not be accepted by other PSS tools.

Only the **opening** delimiter is special. A stray ``}}`` in text is not an
error, so the closing braces that C and C++ produce constantly are unaffected.

The failure is loud, never silent — a malformed ``{{`` is reported, not quietly
treated as text — and the diagnostic names this workaround inline:

.. code-block:: text

    PSS109: malformed mustache expression: unexpected ','; if '{{' was
    intended as literal text, separate the braces ('{ {')

An unterminated ``{{`` reports ``PSS108`` and carries the same hint. Treating an
unparseable mustache as literal text would let a genuinely malformed
``{{ x + }}`` pass unnoticed, which is worse than failing on valid-looking C.

.. note::

   Where the target language is whitespace-sensitive (Python, Makefiles, YAML),
   the extra space is not always acceptable, and PSS 3.1 then offers no way to
   emit a literal ``{{`` at all. This is a gap in the standard rather than in
   pssparser. Other template languages avoid it: Jinja provides both
   ``{% raw %}`` and configurable delimiters, and the original Mustache
   specification's set-delimiter tag exists precisely because "double-braces may
   occur in the text."

.. _triple-quote-escape-removed:

``\\"""`` is no longer an escape
---------------------------------

.. warning::

   This breaks any source relying on a backslash to embed ``"""`` inside a
   triple-quoted string.

PSS 3.1 §4.7 is explicit that a triple-quoted string "may contain any ASCII
character... **There is no escape character**", the sole exclusion being three
consecutive double quotes.

pssparser previously accepted a backslash before the closing delimiter as an
escape, so the string continued past where the standard ends it:

.. code-block:: pss

    // Read as content `a\"""...` and scanning continued -- non-conformant.
    // Now the string ends at the `"""`, with content `a\`.
    exec declaration C = """a\""";

There is no replacement: the standard provides no way to write three
consecutive double quotes inside a triple-quoted string. Restructure the target
code so the sequence does not occur.

This lands together with the ``{{`` change above; both are the same class of
correction, from a local extension to what the standard actually specifies.

New Features
============

Soft constraints
----------------

A soft constraint states a preference rather than a requirement. It is
discarded when it conflicts with a hard constraint, an active default
constraint, or a higher-priority soft constraint, instead of failing the solve:

.. code-block:: pss

    action A {
        rand int x;

        constraint c {
            x < 100;             // hard -- always holds
            soft x > 10;         // preference
            soft x in [50..60];  // higher-priority preference
        }
    }

Relative priority comes from **position in the model**, not from anything
written in the source: a later declaration outranks an earlier one in the same
scope, a derived type outranks its base, and a type extension outranks the
initial declaration. The parser records position in
``ConstraintStmt.getIndex()``; a consumer that reorders constraint-scope
children silently changes what the model means.

.. note::

   Example160 in the LRM writes ``soft y inside [5..9];``. There is no
   ``inside`` operator in Annex B — PSS spells set membership ``in`` — so that
   example does not parse. Write ``soft y in [5..9];``.

``unique`` over a single collection
-----------------------------------

PSS 3.0 supported only the braced form of ``unique``. PSS 3.1 (§13.1.10) adds a
single-argument form, which means something different:

.. code-block:: pss

    unique { a, b, c };   // these three attributes must differ
    unique arr;           // the *elements* of arr must differ
    unique arr[2..5];     // elements 2..5 of arr must differ

Both forms populate ``getList()``, so a consumer must read
``getIs_braced()`` to tell them apart — with a single operand, ``unique { a }``
and ``unique a`` are otherwise identical in the AST while constraining
different things.

Range slices
------------

A bracketed range selects a sub-collection or a substring. All three spellings
are accepted; an omitted endpoint means "to the end" in that direction:

.. code-block:: pss

    arr[2..5]    // elements 2 through 5
    arr[2..]     // element 2 onward
    arr[..5]     // up to element 5

Annex B calls this ``array_slice`` in an ``in`` expression and ``string_slice``
on a reference path, but the two productions are identical and the operand's
type is what tells them apart. The AST therefore carries one node,
``ExprSliceRange``, with optional ``getLower()`` and ``getUpper()``. Bit slices
are spelled differently (``v[7:0]``) and remain ``ExprBitSlice``.

Two consequences worth knowing:

* **A slice is not an index.** ``arr[1]`` yields an element and ``arr[1..3]``
  yields a sub-collection, so ``arr[1..3].f`` is an error (``PSS107``) while
  ``arr[1].f`` is fine.
* **Previously, the range end was silently discarded.** ``s[1..3]`` parsed
  before 3.1 support but built the same AST as ``s[1]``. Code that relied on
  that reading will now see a slice node.

Enum base types
---------------

An enum declaration may now fix the representation of its enumerators:

.. code-block:: pss

    enum small_e : bit[4] { A, B, C }

``EnumDecl.getBase_type()`` returns null when none was written, so "not
declared" stays distinguishable from "declared as ``int``".

Multi-dimensional arrays
------------------------

Several declaration forms accepted only one dimension in 3.0 and now accept
any number: ``input``/``output``/``lock``/``share`` reference fields,
procedural declarations, and monitor instantiations.

.. code-block:: pss

    input B b[2][3];
    monitor_t m[2][3];
    exec init_up { int a[2][3]; }

The leftmost dimension is the outermost, so given ``A a_arr[3][2]``,
``a_arr[1]`` is a sub-array of two handles (§11.3.2). Dimensions are
represented by nesting ``array<elem, size>``, unchanged from how a single
dimension has always been stored.

.. warning::

   ``int a[3][2]`` written as a plain data declaration previously built the
   *transposed* type. Only equal dimensions were unaffected. Code that walked
   nested ``array<>`` types will now see the dimensions in the declared order.

``mutable`` component attributes
--------------------------------

A component is immutable once its ``init_up`` exec has run. ``mutable`` marks
component data that is not part of that structure and may still be updated
during solve-time execution:

.. code-block:: pss

    component pss_top {
        mutable int total_sum;
        mutable list<ref my_comp_c> used_comps;
    }

Like ``soft``, ``mutable`` is now a reserved word and cannot be used as an
identifier. It is not permitted on a component *instance* field (``PSS105``):
whether the fields inside a component may change is decided by their own
qualifiers, not by one on the instance.

Type categories
---------------

3.1 splits the type categories into two groups, and only the first may follow
``ref``:

.. code-block:: text

    ref_type_category   ::= action | monitor | component | object_kind
    plain_type_category ::= struct | numeric

Two consequences:

* ``monitor`` and ``numeric`` are accepted where they previously were not --
  ``function void f(numeric n);`` and ``struct S<monitor M> { }``.
* **``ref struct`` is no longer legal.** ``struct`` is a plain category in 3.1,
  so it may not follow ``ref``. ``ref buffer``, ``ref action`` and the other ref
  categories are unaffected.

Function platform qualifiers
----------------------------

``function_decl`` accepts a platform qualifier, which the 3.1 standard library
relies on:

.. code-block:: pss

    target function void write(int addr, int data);
    solve function int compute_size();
    target solve function void both();

``FunctionPrototype.getIs_target()`` and ``getIs_solve()`` now report it. They
previously returned ``false`` unconditionally regardless of what was written,
and ``target solve`` recorded only ``target``.

Exec block tags
---------------

A target-template exec block may carry a tag, used solely to decide whether two
emitted blocks are equivalent and may be coalesced during code generation. It
affects neither traversal, solving, nor runtime execution.

.. code-block:: pss

    struct tag_s { string name; }

    action A {
        exec header C = tag_s {.name = "hdr"}: """
            #include <stdio.h>
        """;
    }

Tags are permitted only on ``header``, ``declaration``, ``run_start``,
``run_end`` and ``exec file`` blocks. Writing one on ``body`` or on a solve exec
(``init_down``, ``init_up``, ``pre_solve``, ``post_solve``, ``pre_body``) is an
error (``PSS106``) -- those emit nothing a generator could deduplicate.

An untagged block matches nothing, *including another untagged block*, so
``getTag()`` returns null rather than an empty tag.

.. note::

   Target-template exec blocks previously produced no AST at all -- the builder
   discarded them. They now build an ``ExecTargetTemplateBlock`` carrying the
   template text, the language identifier or filename, and the tag. The
   ``{{expr}}`` substitutions and ``{% %}`` directives inside the template
   body are now scanned into a ``TemplateString`` on ``getTemplate()``, with
   the raw text still preserved verbatim in ``getData()``. A triple-quoted
   string containing no special elements gets no ``TemplateString`` at all.

The ``pre_body`` exec kind
--------------------------

``exec pre_body`` runs before the body exec and is now recognized. It was
previously reported as an unknown exec-block kind.

Deprecations
============

Brace-less ``compile if`` branches
----------------------------------

A ``compile if`` branch consisting of a single unbraced item remains legal but
is deprecated, and now produces a warning (``PSS104``). This form will continue
to be accepted; there is no plan to remove it.

.. code-block:: pss

    // Deprecated -- warns
    compile if (CFG) struct S { }

    // Preferred
    compile if (CFG) { struct S { } }

The warning is reported for both branches of a ``compile if``, whichever way the
condition evaluates: the spelling is deprecated regardless of which branch is
selected.

See Also
========

* :doc:`checker_plugin_guide` — the full marker catalogue, including the
  ``PSS100``–``PSS107`` band used by the PSS 3.1 diagnostics.
* :doc:`pss30_migration` — migrating from PSS 2.x to PSS 3.0.
