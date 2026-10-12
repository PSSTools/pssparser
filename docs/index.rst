.. pssparser documentation master file, created by
   sphinx-quickstart on Mon Nov  4 14:21:57 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pssparser Documentation
===========================
pssparser provides a Portable Test and Stimulus Standard (PSS) language parser
with C++, Python and TypeScript APIs. It supports PSS 3.1 (the Public Review
Draft of 2026-08-28).

Supported Standard
------------------
pssparser accepts **PSS 3.1**. PSS 3.0 syntax that 3.1 removed is rejected; see
:doc:`pss31_migration`.

The pssparser version is pssparser's own and does not encode the LRM revision.
Major releases are for large changes, including support for a new LRM revision;
minor releases for medium changes; patch releases for small changes and fixes.
A program can read the supported revisions from ``pssparser.SUPPORTED_LRM``;
``pssparser --version`` prints them on its second line.

Overview
--------
pssparser is a comprehensive PSS language parser that converts PSS source code
into an Abstract Syntax Tree (AST) for further processing. It provides both C++ and
Python APIs and supports the PSS 3.1 language, including the 3.0 additions
(monitors, string enhancements, reference collections) and the 3.1 ones.

Key Features
------------
* **PSS 3.1 Support** - Grammar, linking and core library for PSS 3.1
* **Monitors** - Behavioral coverage with temporal operators
* **String Enhancements** - String methods and substring operator
* **Reference Collections** - Collections of reference types
* **C++, Python and TypeScript APIs** - Use from any of the three; the
  TypeScript API is the core compiled to WebAssembly, and runs in a browser
* **Complete AST** - Full abstract syntax tree representation
* **High Performance** - Fast parsing with minimal memory overhead

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   quickstart
   typescript_api
   cli
   lint
   waivers
   source_tools
   refs
   doc_comments
   comments
   annotations
   checker_plugin_guide
   example_single_checker
   example_rule_collection
   pss30_migration
   pss31_migration

.. toctree::
   :maxdepth: 2
   :caption: PSS 3.1 Features:

   pss31_features
   pss31_stdlib

.. toctree::
   :maxdepth: 2
   :caption: PSS 3.0 Features:

   pss30_features
   pss30_api

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation:

   pss30_architecture
   ast_structure
   ast_usage_guide
   ast_class_hierarchy
   sanitizers

.. toctree::
   :maxdepth: 2
   :caption: Reference:

   reference_api_docs
   ast/index
   markers
   lint-rules
   lint-rule-authoring
   lint-functions
   lint-nodes
   diagnostics-json

