############
Installation
############

.. contents:: On this page
   :local:
   :depth: 2

**********************
Installing from PyPI
**********************

The easiest way to install pssparser is from `PyPI <https://pypi.org/project/pssparser/>`_:

.. code-block:: bash

   pip install pssparser

Pre-built binary wheels are provided for:

* Linux x86_64 — Python 3.9 – 3.13
* Linux aarch64 — Python 3.10 – 3.13
* macOS (Apple Silicon + Intel) — Python 3.9 – 3.13
* Windows x86_64 — Python 3.9 – 3.13

If a wheel is not available for your platform, ``pip`` will attempt to build
from source (see :ref:`building-from-source` below).

Verifying the installation
==========================

.. code-block:: python

   import pssparser
   from pssparser import Parser

   p = Parser()
   p.parses([("test.pss", "component pss_top { action A {} }")])
   root = p.link()
   print("OK – linked symbol root:", root)

Or via the CLI:

.. code-block:: bash

   pssparser --version


.. _building-from-source:

**********************
Building from Source
**********************

Prerequisites
=============

* **Python 3.9+**
* **CMake 3.22+**
* **C++17-capable compiler** (GCC 9+, Clang 12+, MSVC 2019+)
* **Git**
* **Java 11+** (required by ANTLR4 to regenerate the grammar; the grammar
  tool is downloaded automatically on first build)

The build system uses `IVPM <https://github.com/fvutils/ivpm>`_ to manage
C++ dependencies (ANTLR4 runtime, debug-mgr, ciostream, etc.).  IVPM is
installed automatically when you use the project's bundled Python environment.

Clone the repository
====================

.. code-block:: bash

   git clone https://github.com/psstools/pssparser.git
   cd pssparser

Set up the Python environment
==============================

.. code-block:: bash

   # Create a local Python environment managed by IVPM
   python -m pip install ivpm
   python -m ivpm update --pip-install

This installs IVPM and downloads all C++ package dependencies into
``packages/``.  The local Python interpreter is at
``packages/python/bin/python`` (Linux/macOS) or
``packages/python/Scripts/python`` (Windows).

Build the extension in-place
==============================

.. code-block:: bash

   # Linux / macOS
   ./packages/python/bin/python setup.py build_ext --inplace

   # Windows
   packages\python\Scripts\python setup.py build_ext --inplace

CMake downloads and compiles the ANTLR4 runtime and the
`pyastbuilder <https://github.com/fvutils/pyastbuilder>`_-generated AST
library on the first run.  Subsequent builds are incremental.

Run the tests
=============

.. code-block:: bash

   cd python
   ../packages/python/bin/python -m pytest ../tests/ -v

Build a wheel
=============

.. code-block:: bash

   ./packages/python/bin/python setup.py bdist_wheel

The wheel is written to ``dist/``.

***********************
Development install
***********************

For iterative development, build in-place and install in editable mode so
that changes to Python source files take effect immediately:

.. code-block:: bash

   ./packages/python/bin/python setup.py build_ext --inplace
   ./packages/python/bin/python -m pip install -e .

.. note::
   Changes to ``.pyx`` or C++ source files always require a re-run of
   ``setup.py build_ext --inplace`` to recompile.

**********************
Building the Docs
**********************

Install the documentation dependencies:

.. code-block:: bash

   pip install -r requirements_docs.txt

Build the HTML docs from the ``docs/`` directory:

.. code-block:: bash

   make -C docs html

The output is written to ``docs/_build/html/``.  Open
``docs/_build/html/index.html`` in a browser to view the result.
