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
