####################
Checker Plug-in Guide
####################

.. contents::
   :local:
   :depth: 2

Concept
=======

``pssparser`` ships with built-in syntax and semantic checks implemented in
C++.  The **checker plug-in system** lets you — or any third-party package —
add custom Python checks that run as a third phase, after a successful parse
and link.

Each checker is a Python class that inherits from
:class:`pssparser.checkers.CheckerBase`.  Checkers receive a
:class:`pssparser.checkers.CheckContext` object that provides read access to
the linked AST and an API to emit structured diagnostics.

The built-in ``CoreChecker`` (name ``"core"``) is always registered and
documents every marker the C++ parser and linker can produce.  It cannot be
disabled.

Writing a Checker
=================

Below is a complete, real-world example — a naming-convention checker that
warns when ``action`` or ``struct`` type names do not start with an uppercase
letter.  The full source lives in ``examples/pss_naming_checker/``.

.. code-block:: python

   # pss_naming/checker.py
   from __future__ import annotations
   from typing import TYPE_CHECKING

   import pssparser.ast as pss_ast
   from pssparser.checkers import CheckerBase, MarkerDef

   if TYPE_CHECKING:
       from pssparser.checkers import CheckContext


   class NamingConventionChecker(CheckerBase):
       name = "naming-convention"
       description = "Warn when action or struct type names do not start with uppercase"

       marker_defs = [
           MarkerDef(
               id="PSC001",
               severity="warning",
               summary="Action type name does not start with an uppercase letter",
               detail=(
                   "PSS convention uses PascalCase for action type names.  "
                   "Rename the action so that its first letter is uppercase, "
                   "e.g. rename ``write_data`` to ``WriteData``."
               ),
           ),
           MarkerDef(
               id="PSC002",
               severity="warning",
               summary="Struct type name does not start with an uppercase letter",
               detail=(
                   "PSS convention uses PascalCase for struct type names.  "
                   "Rename the struct so that its first letter is uppercase, "
                   "e.g. rename ``my_packet`` to ``MyPacket``."
               ),
           ),
       ]

       # Name-checking only needs the parse tree; no linked AST required.
       runs_without_link = True

       def check(self, context: "CheckContext") -> None:
           for global_scope in context.global_scopes:
               # context.file_map maps GlobalScope.getFileid() → source path.
               # GlobalScope.getFilename() is not reliably set by the parser.
               filename = context.file_map.get(global_scope.getFileid(), "")
               self._walk(context, global_scope, filename)

       def _walk(self, context, scope, filename: str) -> None:
           """Recursively walk *scope* and emit markers for naming violations."""
           for child in scope.children():
               if isinstance(child, pss_ast.Action):
                   self._check_name(context, child, filename, "PSC001", "Action")
               elif isinstance(child, pss_ast.Struct):
                   self._check_name(context, child, filename, "PSC002", "Struct")
               # Recurse into any child scope (components, packages, …)
               if isinstance(child, pss_ast.Scope):
                   self._walk(context, child, filename)

       @staticmethod
       def _check_name(context, node, filename, code, kind):
           name_expr = node.getName()
           name = name_expr.getId()
           if not name or name[0].isupper():
               return
           loc = name_expr.getLocation()
           context.add_marker(
               code=code,
               file=filename,
               line=loc.lineno,
               col=loc.linepos,
               message=f"{kind} '{name}' should start with an uppercase letter",
           )

Step-by-step walkthrough:

1. **Subclass** :class:`~pssparser.checkers.CheckerBase`.
2. **Set** ``name`` — a short unique slug used on the command line.
3. **Set** ``description`` — shown by ``--list-checkers``.
4. **Declare** ``marker_defs`` — one :class:`~pssparser.checkers.MarkerDef`
   per diagnostic code your checker can emit.
5. **Set** ``runs_without_link = True`` when your checker only needs the raw
   parse tree (faster; works even when ``--syntax-only`` is active).
6. **Implement** ``check(context)`` — walk the AST and call
   :meth:`~pssparser.checkers.CheckContext.add_marker` to emit diagnostics.

.. tip::

   ``context.file_map`` is a ``dict[int, str]`` mapping
   ``GlobalScope.getFileid()`` to the source file path.  Use it instead of
   ``GlobalScope.getFilename()``, which may be empty.

   ``context.global_scopes`` contains only the user-supplied source files;
   the built-in PSS library scopes are filtered out automatically.

Declaring Markers
=================

Every diagnostic your checker may emit must be declared as a
:class:`~pssparser.checkers.MarkerDef` in the class-level ``marker_defs``
list:

.. code-block:: python

   from pssparser.checkers import MarkerDef

   MarkerDef(
       id="PSC001",          # globally unique ID
       severity="warning",   # "error", "warning", "info", or "hint"
       summary="Short description for --list-markers",
       detail="Longer explanation shown by --describe PSC001",
   )

**ID naming convention**: use a three-letter prefix (e.g. ``PSC`` for your
checker package) followed by a zero-padded three-digit number (``PSC001``).
The ``PSS`` prefix is reserved for the built-in ``CoreChecker``.  Choose a
unique prefix and register it in your project's documentation to avoid future
collisions.

The :class:`~pssparser.checkers.CheckerManager` enforces globally unique IDs
across all registered checkers at discovery time.

Registering via entry_points
=============================

The standard way to make your checker available to all ``pssparser``
invocations is to declare it as an ``entry_points`` contribution in your
package's ``setup.cfg`` or ``pyproject.toml``:

``setup.cfg``:

.. code-block:: ini

   [options.entry_points]
   pssparser.checkers =
       naming-convention = mypkg.pss_rules:NamingConventionChecker
       unused-imports     = mypkg.pss_rules:UnusedImportChecker

``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."pssparser.checkers"]
   naming-convention = "mypkg.pss_rules:NamingConventionChecker"
   unused-imports    = "mypkg.pss_rules:UnusedImportChecker"

The left-hand side (e.g. ``naming-convention``) becomes the registered
*name* of the checker and is used on the command line with ``--checker`` and
``--no-checker``.

After installation (``pip install .``), your checker is auto-discovered every
time ``pssparser`` runs.

Ad-hoc Loading
==============

For development or one-off use you can load a checker without installing it:

.. code-block:: bash

   pssparser --load-checker mypkg.pss_rules:NamingConventionChecker model.pss

The ``--load-checker`` flag may be repeated to load multiple checkers.  The
loaded checker participates in all ``--checker`` / ``--no-checker`` filtering
using its ``name`` attribute.

Combine with ``--list-checkers`` to inspect what will run before doing an
actual parse:

.. code-block:: bash

   pssparser --load-checker mypkg.pss_rules:NamingConventionChecker \
             --list-checkers

Checker Selection
=================

By default, all registered (non-builtin) checkers run.  Use these flags to
change that:

``--checker NAME``
    Run **only** the named checker(s).  May be repeated.  ``NAME`` must match
    a registered checker name (from ``entry_points``) or a checker previously
    loaded with ``--load-checker``.  Specifying an unknown name is an error.

    .. code-block:: bash

       pssparser --checker naming-convention model.pss

``--no-checker NAME``
    **Exclude** the named checker.  May be repeated.  Ignored when
    ``--checker`` is also specified (explicit selection takes precedence).
    Unknown names are silently ignored.

    .. code-block:: bash

       pssparser --no-checker deprecated-syntax model.pss

Precedence rules:

1. Start with all registered + ``--load-checker`` checkers.
2. If ``--checker`` is present, keep *only* those names.
3. Otherwise, remove any names listed in ``--no-checker``.

Querying the Registry
=====================

``--list-checkers``
    Print a table of all registered checkers and their declared marker IDs,
    then exit with code 0.  No source files are required.

    .. code-block:: bash

       pssparser --list-checkers

``--list-markers``
    Print a table of every declared :class:`~pssparser.checkers.MarkerDef`
    across all checkers (including the built-in core), then exit with code 0.

    .. code-block:: bash

       pssparser --list-markers

``--describe ID``
    Print the full :class:`~pssparser.checkers.MarkerDef` record (summary,
    severity, detail text, and owning checker) for a single marker ID, then
    exit with code 0.  Exits with code 2 if the ID is not found.

    .. code-block:: bash

       pssparser --describe PSS002

Accessing the AST
=================

Inside ``check(context)``, the linked AST is available as
``context.root`` (a ``RootSymbolScope``) and the per-file ``GlobalScope``
nodes are in ``context.global_scopes``.  See :doc:`ast_usage_guide` for a
full guide to navigating the AST.

To resolve a ``GlobalScope`` to its source path, use ``context.file_map``::

    filename = context.file_map.get(gs.getFileid(), "")

``context.file_map`` is a ``dict[int, str]`` (fileid → path).
``GlobalScope.getFilename()`` is not reliably populated by the parser, so
always prefer ``file_map``.

``context.global_scopes`` contains only the user-supplied source files;
the built-in PSS library scopes are filtered out automatically.

If your checker only needs the *parse tree* (not the linked AST), set
``runs_without_link = True`` on the class.  The checker will then run even
when ``--syntax-only`` is passed.  When ``runs_without_link = False``
(the default), the checker is skipped in ``--syntax-only`` mode.
