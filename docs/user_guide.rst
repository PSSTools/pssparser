##########
User Guide
##########

.. contents:: On this page
   :local:
   :depth: 3

This guide covers the Python API in depth.  For a quick overview see
:doc:`quickstart`, and for the CLI see :doc:`cli`.

*********************************
The Parser class
*********************************

``Parser`` is the top-level convenience class exported from the
``pssparser`` package:

.. code-block:: python

   from pssparser import Parser, ParseException

All parse and link operations go through a single ``Parser`` instance.  The
parser accumulates ``GlobalScope`` objects internally — one per parsed file —
and passes them all to the linker when you call :meth:`~pssparser.Parser.link`.

Lifecycle
=========

.. code-block:: text

   Parser()
      │
      ├── .parse(files)     ─┐  any number of times, in order
      ├── .parses(tuples)    ─┘
      │
      └── .link()  ───►  RootSymbolScope

A ``Parser`` instance is **single-use**: after :meth:`~pssparser.Parser.link`
is called the internal file list is cleared.  Create a new ``Parser`` for each
independent compile.

Parsing from disk
=================

.. code-block:: python

   from pssparser import Parser

   p = Parser()
   p.parse(["lib/stdlib.pss", "src/design.pss"])
   root = p.link()

:meth:`~pssparser.Parser.parse` accepts a list of file paths.  It can be
called multiple times before :meth:`~pssparser.Parser.link`:

.. code-block:: python

   p = Parser()
   p.parse(["lib.pss"])
   p.parse(["app.pss"])
   root = p.link()

Parsing from strings
====================

:meth:`~pssparser.Parser.parses` takes a list of ``(filename, content)``
tuples.  The *filename* is used only for diagnostic messages:

.. code-block:: python

   p = Parser()
   p.parses([
       ("types.pss", "struct Point { int x; int y; }"),
       ("top.pss",   "component pss_top { action Move {} }"),
   ])
   root = p.link()

Syntax-only mode
================

Skip the linking step to perform a fast syntax check only:

.. code-block:: python

   p = Parser()
   try:
       p.parses([("f.pss", pss_source)])
       # No p.link() call — only syntax is validated
   except ParseException as e:
       print(e)

*********************************
Diagnostics and markers
*********************************

Both :meth:`~pssparser.Parser.parse` / :meth:`~pssparser.Parser.parses` and
:meth:`~pssparser.Parser.link` raise :class:`~pssparser.ParseException` on
error.  Warnings, info, and hints are collected but do **not** raise an
exception.

Reading markers from an exception
==================================

.. code-block:: python

   from pssparser import Parser, ParseException

   p = Parser()
   try:
       p.parses([("bad.pss", "component { action A {} }")])
   except ParseException as exc:
       for m in exc.markers:
           print(f"{m['severity']:7s} {m['file']}:{m['line']}:{m['col']}: {m['message']}")

Reading warnings after a successful parse
==========================================

Non-fatal markers (warnings, info, hints) are available through
:attr:`~pssparser.Parser.markers` even on a successful run:

.. code-block:: python

   p = Parser()
   p.parses([("ok.pss", pss_source)])
   root = p.link()

   for m in p.markers:
       if m['severity'] == 'warning':
           print(f"Warning: {m['message']}")

Marker dict keys
================

Each marker is a plain Python ``dict``:

.. list-table::
   :header-rows: 1
   :widths: 15 15 70

   * - Key
     - Type
     - Description
   * - ``severity``
     - ``str``
     - ``"error"``, ``"warning"``, ``"info"``, or ``"hint"``
   * - ``message``
     - ``str``
     - Human-readable diagnostic message
   * - ``file``
     - ``str``
     - Source filename as passed to ``parse``/``parses``
   * - ``line``
     - ``int``
     - 1-based line number
   * - ``col``
     - ``int``
     - 1-based column number

*********************************
Working with the linked AST
*********************************

After :meth:`~pssparser.Parser.link`, you receive a
:class:`pssparser.ast.RootSymbolScope`.  This is the root of the fully
resolved symbol tree.

Navigating by name
==================

The symbol scope provides dictionary-like lookup by name:

.. code-block:: python

   from pssparser import Parser
   import pssparser.core as core

   p = Parser()
   p.parses([("top.pss", """
       component pss_top {
           action Write { rand int<8> addr; }
           action Read  { rand int<8> addr; }
       }
   """)])
   root = p.link()

   # root is a RootSymbolScope
   # Find 'pss_top' in the root's children
   if root.symtabHas("pss_top"):
       top_idx = root.symtabAt("pss_top")
       top_sym = root.getChild(top_idx)
       print("Found pss_top:", top_sym)

Using SymbolScopeUtil
======================

:class:`pssparser.utils.SymbolScopeUtil` wraps a symbol scope and provides
higher-level helpers:

.. code-block:: python

   from pssparser.utils import SymbolScopeUtil

   util = SymbolScopeUtil(root)

   # Look up a qualified name  (e.g. "mypkg::pss_top::Write")
   write_sym = util.getQname("pss_top::Write")
   print("Write symbol:", write_sym)

   # Walk to the root from any nested scope
   outer = util.getRoot()

Iterating children
==================

.. code-block:: python

   for i in range(root.numChildren()):
       child = root.getChild(i)
       print(i, type(child).__name__)

Resolving a symbol reference
==============================

Many AST nodes contain :class:`pssparser.ast.SymbolRefPath` objects that
point to a declaration elsewhere in the tree.  Use
:func:`pssparser.core.resolveSymbolPathRef` to resolve them:

.. code-block:: python

   import pssparser.core as core

   resolved = core.resolveSymbolPathRef(root, some_symbol_ref.getTarget())
   if resolved is not None:
       print("Resolved to:", type(resolved).__name__)

*********************************
Parse profiling
*********************************

pssparser exposes ANTLR4 decision-level profiling to help identify slow
grammar rules.

Enable profiling before the first parse call:

.. code-block:: python

   from pssparser import Parser

   p = Parser()
   p.enable_profiling(True)
   p.parses([("large.pss", large_pss_source)])
   root = p.link()

   info = p.get_profile_info()
   if info:
       print("Total time in prediction:", info.total_time_in_prediction, "µs")
       print("Total SLL lookahead ops:", info.total_sll_lookahead_ops)
       print("Total LL lookahead ops: ", info.total_ll_lookahead_ops)
       print("DFA size:               ", info.dfa_size)

       # Per-decision breakdown
       decisions = info.get_decision_info()
       decisions.sort(key=lambda d: d.time_in_prediction, reverse=True)
       for d in decisions[:10]:
           print(f"  Decision {d.decision:4d}: {d.time_in_prediction:8.0f}µs "
                 f"  invocations={d.invocations}  LL-fallbacks={d.ll_fallback}")

:class:`~pssparser.core.ParseProfileInfo` attributes:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Description
   * - ``total_time_in_prediction``
     - Total microseconds spent in prediction across all decisions
   * - ``total_sll_lookahead_ops``
     - Total number of SLL lookahead operations
   * - ``total_ll_lookahead_ops``
     - Total number of LL lookahead operations (more expensive)
   * - ``total_sll_atn_lookahead_ops``
     - SLL ATN (Augmented Transition Network) operations
   * - ``total_ll_atn_lookahead_ops``
     - LL ATN operations
   * - ``total_atn_lookahead_ops``
     - Combined ATN lookahead operations
   * - ``dfa_size``
     - Total number of DFA states cached (larger = more memory, faster re-parses)

Per-decision attributes (:class:`~pssparser.core.DecisionProfileInfo`):

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Attribute
     - Description
   * - ``decision``
     - Decision number (maps to a grammar rule alternative)
   * - ``invocations``
     - Times this decision was evaluated
   * - ``time_in_prediction``
     - Microseconds in prediction for this decision
   * - ``ll_fallback``
     - Times the parser had to fall back from SLL to LL (expensive)
   * - ``ambiguity_count``
     - Number of ambiguities detected
   * - ``error_count``
     - Number of errors at this decision point
   * - ``max_lookahead``
     - Maximum lookahead depth required

*********************************
Low-level factory API
*********************************

The :class:`pssparser.core.Factory` singleton gives access to all low-level
builder and linker objects that :class:`~pssparser.Parser` uses internally.
This is useful when you need fine-grained control or want to reuse components.

Getting the factory
===================

.. code-block:: python

   import pssparser.core as core

   factory = core.Factory.inst()

Building and linking manually
==============================

.. code-block:: python

   import pssparser.core as core
   import pssparser.ast  as ast
   from io import StringIO

   factory  = core.Factory.inst()
   ast_f    = ast.Factory.inst()

   # Marker listener collects diagnostics
   markers  = factory.mkMarkerCollector()
   builder  = factory.mkAstBuilder(markers)

   # Build each file into a GlobalScope
   stdlib = ast_f.mkGlobalScope(0)
   factory.loadStandardLibrary(builder, stdlib)

   gs1 = ast_f.mkGlobalScope(1)
   builder.build(gs1, StringIO("component pss_top { action A {} }"))

   if markers.hasSeverity(core.MarkerSeverityE.Error):
       for i in range(markers.numMarkers()):
           m = markers.getMarker(i)
           print("Error:", m.msg())
   else:
       # Link
       linker    = factory.mkAstLinker()
       link_mc   = factory.mkMarkerCollector()
       root      = linker.link(link_mc, [stdlib, gs1])
       print("Root:", root)

Marker severity values
=======================

:class:`pssparser.core.MarkerSeverityE` is an :class:`~enum.IntEnum`:

.. code-block:: python

   from pssparser.core import MarkerSeverityE

   MarkerSeverityE.Error    # 0
   MarkerSeverityE.Warn     # 1
   MarkerSeverityE.Info     # 2
   MarkerSeverityE.Hint     # 3

*********************************
Python API summary
*********************************

.. rubric:: Top-level (``pssparser`` package)

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Name
     - Description
   * - :class:`Parser`
     - High-level parse/link driver
   * - :class:`ParseException`
     - Raised on parse or link errors; carries ``markers`` list

.. rubric:: ``pssparser.core`` module

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Name
     - Description
   * - :class:`~pssparser.core.Factory`
     - Singleton; creates builder, linker, marker objects
   * - :class:`~pssparser.core.AstBuilder`
     - Builds a ``GlobalScope`` from an input stream
   * - :class:`~pssparser.core.Linker`
     - Links a list of ``GlobalScope`` objects into a ``RootSymbolScope``
   * - :class:`~pssparser.core.MarkerCollector`
     - Collects diagnostics during parse/link
   * - :class:`~pssparser.core.Marker`
     - A single diagnostic (message, severity, location)
   * - :class:`~pssparser.core.Location`
     - File / line / column triple
   * - :class:`~pssparser.core.MarkerSeverityE`
     - ``Error``, ``Warn``, ``Info``, ``Hint``
   * - :class:`~pssparser.core.ParseProfileInfo`
     - Aggregate ANTLR profiling data for a parse
   * - :class:`~pssparser.core.DecisionProfileInfo`
     - Per-decision profiling data
   * - :func:`~pssparser.core.resolveSymbolPathRef`
     - Resolve a ``SymbolRefPath`` to its declaration node

.. rubric:: ``pssparser.utils`` module

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Name
     - Description
   * - :class:`~pssparser.utils.SymbolScopeUtil`
     - Qualified-name lookup, root traversal, extension listing
   * - :class:`~pssparser.utils.SymbolTypeScopeUtil`
     - Extends ``SymbolScopeUtil`` with supertype resolution
