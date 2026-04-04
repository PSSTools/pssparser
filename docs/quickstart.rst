##########
Quickstart
##########

.. contents:: On this page
   :local:
   :depth: 2

************
Installation
************

.. code-block:: bash

   pip install pssparser

See :doc:`installation` for platform details and building from source.

*****************************
Parsing and linking PSS files
*****************************

The :class:`~pssparser.Parser` class is the primary entry point for all
parse/link operations.

Parsing from strings
====================

Use :meth:`~pssparser.Parser.parses` to parse in-memory PSS content:

.. code-block:: python

   from pssparser import Parser

   parser = Parser()
   parser.parses([
       ("file1.pss", """
           component pss_top {
               action Write {
                   rand int<8> addr;
                   rand int<8> data;
               }
               action Read {
                   rand int<8> addr;
               }
           }
       """)
   ])
   root = parser.link()

The ``root`` object is a fully linked :class:`pssparser.ast.RootSymbolScope`
that you can traverse and query.

Parsing from files
==================

Use :meth:`~pssparser.Parser.parse` to parse files from disk:

.. code-block:: python

   from pssparser import Parser

   parser = Parser()
   parser.parse(["design.pss", "tests.pss"])
   root = parser.link()

Multiple files can be split across several :meth:`~pssparser.Parser.parse`
calls before a single :meth:`~pssparser.Parser.link`:

.. code-block:: python

   parser = Parser()
   parser.parse(["lib.pss"])
   parser.parse(["app.pss"])
   root = parser.link()

Handling errors
===============

Both methods raise :class:`~pssparser.ParseException` on syntax or semantic
errors, with structured diagnostic information:

.. code-block:: python

   from pssparser import Parser, ParseException

   parser = Parser()
   try:
       parser.parses([("bad.pss", "component { }")])  # missing name
       root = parser.link()
   except ParseException as e:
       print("Parse failed:", e)
       for m in e.markers:
           print(f"  [{m['severity']}] {m['file']}:{m['line']}:{m['col']}: {m['message']}")

Each marker dict contains:

* ``severity`` — ``"error"``, ``"warning"``, ``"info"``, or ``"hint"``
* ``message`` — human-readable description
* ``file`` — source filename
* ``line`` — 1-based line number
* ``col`` — 1-based column number

*****************************
CLI syntax checker
*****************************

The ``pssparser`` command checks one or more PSS files and reports diagnostics:

.. code-block:: bash

   # Syntax + semantic check
   pssparser design.pss tests.pss

   # Syntax check only (no linking)
   pssparser --syntax-only design.pss

   # Machine-readable JSON diagnostics
   pssparser --json design.pss

   # Dump the linked AST to a JSON file
   pssparser --dump-ast ast.json design.pss

Exit codes: ``0`` = success, ``1`` = diagnostics reported, ``2`` = usage error.

See :doc:`cli` for the full option reference.

*****************************
Next steps
*****************************

* :doc:`user_guide` — detailed API usage, AST traversal, markers, profiling
* :doc:`cli` — full CLI reference
* :doc:`integrator_guide` — embedding pssparser from C++
* :doc:`developer_guide` — building from source, running tests, contributing




