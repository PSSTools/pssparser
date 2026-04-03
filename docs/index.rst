.. pssparser documentation master file, created by
   sphinx-quickstart on Mon Nov  4 14:21:57 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

pssparser Documentation
===========================
pssparser provides a Portable Test and Stimulus Standard (PSS) language parser
with C++ and Python APIs. The parser supports both PSS 2.x and PSS 3.0 specifications.

Overview
--------
pssparser is a comprehensive PSS language parser that converts PSS source code
into an Abstract Syntax Tree (AST) for further processing. It provides both C++ and
Python APIs and includes full support for PSS 3.0 features including monitors,
string enhancements, reference collections, and more.

Key Features
------------
* **PSS 3.0 Support** - Full grammar support for PSS 3.0 (August 2024)
* **Monitors** - Behavioral coverage with temporal operators
* **String Enhancements** - String methods and substring operator
* **Reference Collections** - Collections of reference types
* **C++ and Python APIs** - Use from either language
* **Complete AST** - Full abstract syntax tree representation
* **High Performance** - Fast parsing with minimal memory overhead

.. toctree::
   :maxdepth: 2
   :caption: Getting Started:

   quickstart
   cli
   pss30_migration

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

.. toctree::
   :maxdepth: 2
   :caption: Reference:

   reference_api_docs

