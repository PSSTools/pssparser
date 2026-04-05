###
CLI
###

The `pssparser` package provides a parser-focused command-line interface.

Basic usage
===========

Parse and link one or more PSS source files:

.. code-block:: bash

   pssparser file1.pss file2.pss

Common options
==============

- ``--syntax-only`` parses without performing linking / symbol resolution
- ``--json`` emits diagnostics as JSON
- ``--dump-ast OUT`` writes a JSON dump of the linked AST
- ``--quiet`` suppresses normal diagnostic output

Examples
========

Syntax-only parse:

.. code-block:: bash

   pssparser --syntax-only model.pss

Emit diagnostics as JSON:

.. code-block:: bash

   pssparser --json model.pss

Dump the linked AST:

.. code-block:: bash

   pssparser --dump-ast ast.json model.pss

Checker flags
=============

The following flags control the checker plug-in system.  See
:doc:`checker_plugin_guide` for a full explanation of the plug-in
architecture.

Query-and-exit flags
---------------------

These flags do **not** require source files.

``--list-checkers``
    Print a table of all registered checkers — name, description, and
    declared marker IDs — then exit with code 0.

    .. code-block:: bash

       pssparser --list-checkers

``--list-markers``
    Print a table of every declared marker ID across all registered checkers
    (including the built-in ``core``), then exit with code 0.  Columns are
    ``ID``, ``SEV``, ``CHECKER``, and ``SUMMARY``.

    .. code-block:: bash

       pssparser --list-markers

``--describe ID``
    Print the full definition (summary, severity, detail, owning checker) for
    the marker with the given ID, then exit with code 0.  Exits with code 2
    and an error message if the ID is not found.

    .. code-block:: bash

       pssparser --describe PSS001

Checker selection flags
------------------------

``--checker NAME``
    Run *only* the named checker.  May be repeated to select multiple
    checkers.  ``NAME`` must match a registered entry-point name or a checker
    previously loaded with ``--load-checker``.  Specifying an unknown name
    produces an error and exits with code 2.

    .. code-block:: bash

       pssparser --checker naming-convention model.pss

``--no-checker NAME``
    Exclude the named checker from the active set.  May be repeated.
    Silently ignored when the name is not in the registry, or when
    ``--checker`` is also specified (explicit selection takes precedence).

    .. code-block:: bash

       pssparser --no-checker deprecated-syntax model.pss

``--load-checker MODULE:CLASS``
    Dynamically import ``CLASS`` from ``MODULE`` and add it to the active
    checker set.  No package installation required.  May be repeated.  The
    loaded checker participates in ``--checker`` / ``--no-checker`` filtering
    using its ``name`` attribute.

    .. code-block:: bash

       pssparser --load-checker myproject.rules:StyleChecker model.pss

