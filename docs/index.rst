pssparser Documentation
=======================

**pssparser** is an `ANTLR4 <https://www.antlr.org/>`_-based parser for the
`Accellera Portable Test and Stimulus Standard (PSS) <https://www.accellera.org/downloads/standards/portable-test-stimulus>`_
language. It builds an Abstract Syntax Tree (AST) with full PSS 2.x and PSS 3.0
support, and exposes both a Python and a C++ API.

.. code-block:: python

   from pssparser import Parser

   parser = Parser()
   parser.parses([("hello.pss", """
       component pss_top {
           action Hello { }
       }
   """)])
   root = parser.link()

.. rubric:: Feature highlights

* **Full PSS 3.0 grammar** — monitors, string methods, reference collections,
  atomic blocks, yield, randomize, platform qualifiers
* **Python and C++ APIs** — use from either language
* **Complete linked AST** — symbol resolution and type linking included
* **CLI tool** — ``pssparser`` command for syntax/semantic checking
* **Structured diagnostics** — file/line/column markers with severity levels
* **Parse profiling** — decision-level ANTLR profiling for performance analysis

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   installation
   quickstart
   user_guide
   cli
   pss30_features
   pss30_migration

.. toctree::
   :maxdepth: 2
   :caption: Integrator Guide

   integrator_guide

.. toctree::
   :maxdepth: 2
   :caption: Developer Guide

   developer_guide
   pss30_architecture
   ast_structure
   ast_usage_guide
   ast_class_hierarchy

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   reference_api_docs
   pss30_api

Indices and tables
==================

* :ref:`genindex`
* :ref:`search`
