###############
Developer Guide
###############

.. contents:: On this page
   :local:
   :depth: 3

This guide is for contributors and developers who want to understand, build,
or extend pssparser from source.

***********************
Repository layout
***********************

.. code-block:: text

   pssparser/
   ├── .github/workflows/    CI workflows (Linux, macOS, Windows, aarch64)
   ├── ast/                  pyastbuilder AST definition files
   ├── docs/                 Sphinx documentation source
   ├── python/               Python package sources
   │   ├── pssparser/        pssparser Python package
   │   │   ├── __init__.py   Re-exports Parser, ParseException
   │   │   ├── parser.py     Parser and ParseException classes
   │   │   ├── cli/          Command-line interface (app.py, commands.py, …)
   │   │   └── utils/        SymbolScopeUtil, SymbolTypeScopeUtil, …
   │   ├── core.pyx          Cython extension — IFactory, AstBuilder, Linker, …
   │   ├── core.pxd          Cython declaration for core.pyx
   │   ├── decl.pxd          C++ interface declarations (IFactory, etc.)
   │   ├── ast.pxd           C++ AST interface declarations
   │   └── ast_decl.pxd      C++ AST internal declarations
   ├── scripts/
   │   └── gen_ast.py        Drives pyastbuilder to generate ast.pyx + ast.cpp
   ├── src/                  C++ source — parser, linker, semantic tasks
   │   ├── include/pssp/     Public C++ headers
   │   └── *.cpp             Implementation files
   ├── tests/                Python pytest test suite
   ├── CMakeLists.txt        Root CMake; ExternalProject for antlr4, AST
   ├── setup.py              Python packaging
   ├── setup.cfg             Python package metadata
   └── ivpm.yaml             IVPM dependency manifest

Generated files (not committed)
================================

The following files are generated at build time and are excluded from version
control:

* ``python/ast.pyx`` — Cython wrapper for the AST model (from pyastbuilder)
* ``python/ast.cpp`` — Cython-generated C++ for ``ast.pyx``
* ``python/ast.h`` — Cython-generated C header
* ``python/ast_api.h`` — Cython public API header

***********************
Build system
***********************

pssparser uses a hybrid build:

1. **IVPM** manages C++ dependencies (antlr4 runtime, debug-mgr, ciostream,
   pyastbuilder).  Dependencies are downloaded to ``packages/`` and never
   committed.

2. **CMake** compiles the C++ core (``src/``) and the AST library (generated
   by pyastbuilder) as two separate ``ExternalProject`` sub-builds.

3. **Cython** wraps the C++ objects in ``core.pyx`` (hand-written) and the
   generated ``ast.pyx``.

4. **setup.py** / **setuptools** drives the Cython compilation and packages
   everything into a wheel.

***********************
Setting up for development
***********************

Requirements
============

* Python 3.9+
* CMake 3.22+
* C++17 compiler (GCC 9+, Clang 12+, MSVC 2019+)
* Java 11+ (ANTLR4 grammar tool is downloaded on first build)
* Git

Initial setup
=============

.. code-block:: bash

   git clone https://github.com/psstools/pssparser.git
   cd pssparser

   # Install IVPM and download C++ dependencies
   pip install ivpm
   python -m ivpm update --pip-install

   # Build the Cython extensions in-place
   ./packages/python/bin/python setup.py build_ext --inplace

Incremental rebuilds
====================

After changing C++ source files:

.. code-block:: bash

   ./packages/python/bin/python setup.py build_ext --inplace

After changing ``core.pyx`` only, the same command works but you can also
let CMake skip the full C++ rebuild by passing ``--no-cmake``:

.. code-block:: bash

   # Cython only (much faster when only .pyx changed)
   ./packages/python/bin/python setup.py build_ext --inplace --no-cmake

***********************
Running the tests
***********************

.. code-block:: bash

   cd python
   ../packages/python/bin/python -m pytest ../tests/ -v

Run a subset:

.. code-block:: bash

   ../packages/python/bin/python -m pytest ../tests/ -v -k "test_function"

Run with verbose output and stop on first failure:

.. code-block:: bash

   ../packages/python/bin/python -m pytest ../tests/ -v -x

Memory-check with valgrind (Linux only)
========================================

Use ``PYTHONMALLOC=malloc`` to bypass Python's custom allocator so that
valgrind can track all allocations:

.. code-block:: bash

   cd python
   PYTHONMALLOC=malloc valgrind \
       --leak-check=full \
       --error-exitcode=1 \
       ../packages/python/bin/python -m pytest ../tests/ -v

***********************
AST generation
***********************

The PSS AST is **generated** by
`pyastbuilder <https://github.com/fvutils/pyastbuilder>`_ from YAML
definition files in the ``ast/`` directory.  The generator is run by
``scripts/gen_ast.py`` as part of the CMake build.

.. code-block:: text

   ast/
   ├── pss_ast.yaml          Main AST class definitions
   └── …

The generator produces:

* ``build/pssparser_ast/ext/ast.pyx``  (Cython Python wrapper)
* ``build/pssparser_ast/ext/ast.cpp``  (C++ implementation)
* ``build/pssparser_ast/include/…``    (C++ headers for the AST model)

``scripts/gen_ast.py`` copies ``ast.pyx`` to ``python/`` and patches it to
add platform-specific ``ctypes`` loading (macOS/Windows DLL discovery).

Adding or modifying AST nodes
==============================

1. Edit the relevant ``ast/*.yaml`` file.
2. Rebuild: ``./packages/python/bin/python setup.py build_ext --inplace``
3. The generator re-runs automatically (CMake detects the YAML change).

Never edit ``python/ast.pyx`` directly — your changes will be overwritten on
the next build.

***********************
Grammar
***********************

The PSS grammar is split across two ANTLR4 grammar files:

* ``src/PSSParser.g4`` — main grammar for procedural code context (exec
  blocks, function bodies, import declarations)
* ``src/PSSExprParser.g4`` — constraint context (constraint expressions,
  data declarations)

This dual-grammar approach avoids ANTLR ambiguities that arise when the same
expression syntax is used in both contexts.

After editing a grammar file, rebuild with:

.. code-block:: bash

   ./packages/python/bin/python setup.py build_ext --inplace

CMake detects the grammar change and invokes the ANTLR4 tool to regenerate
the parser and lexer C++ files.

***********************
Semantic analysis tasks
***********************

Post-parse semantic processing is implemented as *task* classes in ``src/``:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - File
     - Purpose
   * - ``TaskBuildSymbolTree.cpp``
     - First-pass: populates symbol scopes for all declarations
   * - ``TaskLinkRefs.cpp``
     - Resolves all symbol-reference paths
   * - ``TaskCheckExprTypes.cpp``
     - Type-checks expressions
   * - ``TaskCollectUses.cpp``
     - Collects type usage information

These tasks implement the visitor pattern over the AST and are driven by
``Linker.cpp``.

***********************
Continuous integration
***********************

CI is defined in ``.github/workflows/ci.yml``.  Four jobs run in parallel:

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Job
     - Platform
     - Python versions
   * - ``ci-linux``
     - Linux x86_64 (manylinux 2.28)
     - 3.9, 3.10, 3.11, 3.12, 3.13
   * - ``ci-linux-aarch64``
     - Linux aarch64 (manylinux 2.28)
     - 3.10, 3.11, 3.12, 3.13
   * - ``ci-macos``
     - macOS (GitHub-hosted)
     - system Python
   * - ``ci-win32``
     - Windows x86_64
     - system Python

Each job:

1. Checks out the code
2. Installs IVPM and downloads dependencies
3. Builds the Cython extensions with ``setup.py build_ext --inplace``
4. Runs the full pytest suite
5. Builds a wheel and publishes it to PyPI (on any branch/tag, since
   versions are unique dev builds)

***********************
Code conventions
***********************

Python
======

* All public Python API follows ``snake_case`` for methods and attributes.
* The ``Parser`` class is the primary entry point; it should remain simple
  and delegate to the low-level ``core`` module.
* Cython (``.pyx``) files wrap C++ objects one-to-one.  Keep platform-specific
  code limited to the ``Factory.inst()`` method.

C++
===

* All public interfaces are pure virtual, prefixed with ``I``, in the
  ``pssp`` namespace.
* Concrete implementations live in ``src/`` and are never exposed in public
  headers.
* Use ``std::unique_ptr`` (aliased as ``IFooUP``) for owned objects.
* Tasks use the visitor pattern (``pssp::ast::VisitorBase``).

***********************
Adding a new PSS feature
***********************

A typical new-feature workflow:

1. **Grammar**: add the new syntax to ``PSSParser.g4`` or
   ``PSSExprParser.g4``.

2. **AST**: add new node types to ``ast/pss_ast.yaml`` (pyastbuilder
   regenerates the Cython/C++ wrappers on rebuild).

3. **Visitor**: implement the new ``visit*`` method(s) in the relevant
   ``Task*.cpp`` files.

4. **Tests**: add ``.pss`` examples and Python pytest cases in ``tests/``.

5. **Docs**: update ``docs/pss30_features.rst`` (or add a new ``.rst`` page)
   and note the new grammar in ``docs/pss30_migration.rst`` if it introduces
   reserved keywords.

***********************
Releasing
***********************

Wheels are published to PyPI automatically on every successful CI run.
Version strings are controlled by ``python/pssparser/__version__.py``.

To bump the version:

1. Edit ``BASE`` in ``__version__.py``.
2. Push a commit or tag — CI will build and publish the new version.
