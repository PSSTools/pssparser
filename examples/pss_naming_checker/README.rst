pss_naming_checker — example ``pssparser`` checker plug-in
==========================================================

This directory contains a fully-working example of a third-party checker
plug-in for ``pssparser-linter``.  Read it together with
``docs/checker_plugin_guide.rst`` to understand how to build your own.


What it does
------------

``NamingConventionChecker`` (id: ``naming-convention``) warns when ``action``
or ``struct`` type names do not start with an uppercase letter — a common PSS
coding convention (PascalCase for named types).

Markers emitted:

+--------+----------+---------------------------------------------------+
| Code   | Severity | Meaning                                           |
+========+==========+===================================================+
| PSC001 | warning  | An ``action`` name does not start with uppercase  |
+--------+----------+---------------------------------------------------+
| PSC002 | warning  | A ``struct`` name does not start with uppercase   |
+--------+----------+---------------------------------------------------+


Quick demo
----------

Install into your environment (editable install works well for development)::

    pip install -e examples/pss_naming_checker/

Parse a file and enable the checker::

    pssparser-linter --checker naming-convention my_design.pss

Show all markers the checker can emit::

    pssparser-linter --list-markers naming-convention


Project layout
--------------

::

    examples/pss_naming_checker/
    ├── README.rst              ← this file
    ├── setup.cfg               ← package metadata + entry_point declaration
    ├── setup.py                ← minimal shim for editable installs
    ├── src/
    │   └── pss_naming/
    │       ├── __init__.py
    │       └── checker.py      ← NamingConventionChecker implementation
    └── tests/
        └── test_naming_checker.py


Key implementation notes
------------------------

Entry-point declaration (``setup.cfg``)::

    [options.entry_points]
    pssparser.checkers =
        naming-convention = pss_naming.checker:NamingConventionChecker

The group **must** be ``pssparser.checkers``; the key is the checker's
``name`` attribute.

Checker class (``checker.py``)::

    class NamingConventionChecker(CheckerBase):
        name = "naming-convention"
        runs_without_link = True   # raw parse tree is enough

        def check(self, context: CheckContext) -> None:
            for gs in context.global_scopes:
                filename = context.file_map.get(gs.getFileid(), "")
                self._walk(context, gs, filename)

``context.file_map`` maps ``GlobalScope.getFileid()`` → source path because
``GlobalScope.getFilename()`` is not reliably set by the current parser
implementation.

AST traversal::

    for child in scope.children():
        if isinstance(child, pss_ast.Action):
            name = child.getName().getId()
            loc  = child.getName().getLocation()
            context.add_marker(code="PSC001", file=filename,
                               line=loc.lineno, col=loc.linepos,
                               message=f"Action '{name}' should start uppercase")
        if isinstance(child, pss_ast.Scope):
            self._walk(context, child, filename)  # recurse

``GlobalScope`` → direct children are top-level declarations
(``Component``, ``PackageScope``, ``Action``, ``Struct``, …).  Recurse into
any ``Scope`` to reach nested declarations inside ``component`` bodies.
