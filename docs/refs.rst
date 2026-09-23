Identifier occurrences
======================

``pssparser.refs.occurrences()`` lists every identifier in the user's files,
with the declaration each one names. It is what a rename, find-references or
go-to-definition tool needs, and it does not ask the tool to re-implement any
of the linker's rules: the linker records what each name binds to, and this
reports it.

.. code-block:: python

    import pssparser
    from pssparser import refs
    from pssparser.refs import Resolution

    p = pssparser.Parser()
    p.parse(["m1.pss", "m2.pss"])
    try:
        p.link()
    except pssparser.ParseException:
        pass                        # occurrences are still available

    for o in refs.occurrences(p):
        print(o.fileid, o.line, o.col, o.text, o.resolution.value,
              o.is_declaration, o.decl_location)

What is reported
----------------

One ``Occurrence`` per identifier with a source location in a user file
(fileid 1 and up), sorted by ``(fileid, line, col)``:

- declaration names -- types, fields, functions, parameters, enum items,
  constraint blocks, packages, loop variables, labels;
- every element of a qualified name (``my_pkg::cfg_s``) and of a member path
  (``cfg.depth``, ``comp.count``, ``items.push_back``);
- names in ``with { ... }`` blocks, ``extend`` targets, ``{{name}}``
  references in triple-quoted templates, and the conditions of
  ``compile if`` / ``compile assert`` (including ``compile has(...)``).

Names with no location -- the implicit ``pss_top``, the synthetic ``comp``
field -- are not reported: there is nothing in the source to point at.

Contextual keywords that the lexer returns as identifiers but that name
nothing are not occurrences: the kind in ``exec body``, and the language tag in
``exec body C = ...`` or ``import target C function ...``.

``Occurrence`` fields
---------------------

``fileid``, ``line``, ``col``, ``extent``
    Where the identifier is; ``line`` and ``col`` are 1-based, as in
    ``Location``.
``text``
    The identifier as written.
``is_declaration``
    True where this occurrence is the name being declared.
``decl``
    The declaring AST node, as its most-derived wrapper class (``Field``,
    ``Action``, ``FunctionPrototype``, ...), or ``None``. **Every occurrence of
    one declaration has the same** ``decl``: group by ``==`` or ``hash()``, not
    by ``id()`` -- each access creates a new wrapper object.
``decl_location``
    ``refs.Location(fileid, line, col, extent)`` of the declaration's name, or
    ``None``.
``resolution``
    How the name was bound; see below.
``base_decl``
    For a declaration that overrides or shadows one in a base type -- a
    constraint of the same name, an override function, a field hiding a base
    field -- the declaration it overrides. It is the *immediate* one; follow
    ``base_decl`` of that ``decl`` to walk the chain.

``Resolution``
--------------

A **closed set**: a client that meets a value it does not know should fail,
not guess. The members compare equal to their string values.

=============  ==============================================================
``user``       Bound to a declaration in a user file.
``library``    Bound to a standard-library declaration (fileid 0).
``builtin``    A built-in with no source declaration: ``comp``, ``this``,
               collection methods (``push_back``), built-in types
               (``list``), covergroup ``option.<name>``. ``decl`` is
               ``None`` or a synthetic node with no location.
``unresolved`` Not bound. ``decl`` is ``None``.
``dependent``  Not bound, inside a generic template body, where what the name
               means depends on a template parameter (``t.x`` with
               ``type T``). ``decl`` is ``None``.
=============  ==============================================================

Templates
---------

A member reached through a specialization (``tmpl_s<8> a; ... a.depth``)
binds to the member of the generic template, the one in the source, so every
use of it across every specialization groups with its single declaration.

Inside a generic body the linker resolves names in the specializations only.
A name that every specialization binds to the same declaration is reported as
bound to it; one they disagree on is ``dependent``.

When linking failed
-------------------

``occurrences()`` works after ``link()`` raised ``ParseException``: every
identifier is still reported, and the ones the error left unbound are
``unresolved``.

Known gaps
----------

The linker does not yet bind every kind of name. On legal input those are
reported as ``unresolved`` rather than dropped, and
``tests/python/baselines/occurrences.json`` records them for the test corpus:
activity labels (``L.a``), ``bind`` operands, names inside covergroup bodies,
and ``this`` (``docs/design/known-issues.md`` R-THIS). A ``symbol``
declaration's own name has no location yet (R-SYMNAME).

``compile if``
--------------

``Parser.inactive_regions()`` returns the branches a ``compile if`` left
out, as ``pssparser.InactiveRegion(fileid, start_line, start_col, end_line,
end_col)``, both ends inclusive. Names inside a region are not in the AST and
are not reported by ``occurrences()``; a tool that must treat them can find
them by position.
