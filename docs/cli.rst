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
- ``--max-errors N`` stops reporting further errors for a file after ``N``
  (default 20; ``0`` disables the cap). Only error-severity diagnostics count
  against it — warnings never trigger it, and a clean file never sees it.
  A capped file gets one extra marker, ``PSS029``, announcing the cutoff;
  everything past it is dropped, not merely hidden, so re-run with a higher
  (or ``0``) ``--max-errors`` to see what comes after. The Python API
  (:class:`pssparser.Parser`) defaults to unlimited — the cap is a
  terminal-output affordance the CLI opts into via
  ``Parser.set_max_errors()``, not something a library caller should have to
  ask to disable.

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

Diagnostic rendering
=====================

By default (no ``--json``), a diagnostic is rendered Rust/Clang-style: a
``file:line:col: severity: message`` header, the offending source line, and a
caret underlining the exact span. For example, an unterminated ``component``:

.. code-block:: pss

   component C {
       action A {
       }

.. code-block:: text

   model.pss:1:13: error: unclosed '{' for component 'C'
    1 | component C {
      |             ^

Some diagnostics carry one or more **related locations** — a second place in
the source that explains the error, such as the opening brace an unclosed
construct never closed, or (in the example above, run to completion) where
the input actually ran out. Each related location renders as an indented
``note:`` line under the primary diagnostic, with its own source line and
caret when one is available:

.. code-block:: text

   model.pss:1:13: error: unclosed '{' for component 'C'
    1 | component C {
      |             ^
     note: input ends here
      --> model.pss:4:1

   1 error in 1 file

Here the related location points *past* the last line of the file (there is
nothing left to show a source line for), so only the ``note:`` label and the
``file:line:col`` pointer are printed — the source line and caret are omitted
whenever the related location has no line to render, rather than printing an
empty or misleading one.

``--json`` output carries the same information structurally: each diagnostic
object may include a ``"related"`` array of ``{file, line, col, label}``
entries, so an editor or script can render (or otherwise use) related
locations without re-parsing prose.

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

       pssparser --describe PSS020

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

