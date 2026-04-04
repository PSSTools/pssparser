################
Integrator Guide
################

.. contents:: On this page
   :local:
   :depth: 3

This guide covers using pssparser from C++ — embedding the parser in your own
tool, traversing the AST in C++, and using pssparser as a CMake dependency.

***********************
C++ API Overview
***********************

All public C++ interfaces live in the ``pssp`` namespace and follow an
*interface-only* pattern: every class is a pure virtual interface (prefixed
with ``I``), and objects are created through ``IFactory``.  Headers are
in ``include/pssp/``.

The core workflow is the same as the Python API:

1. Get the factory singleton via ``pssparser_getFactory()``
2. Create an ``IAstBuilder``
3. Build one ``IGlobalScope`` per source file
4. Create an ``ILinker`` and call ``link()``
5. Traverse the resulting ``IRootSymbolScope``

***********************
CMake integration
***********************

After installing pssparser, the CMake package can be consumed with
``find_package``:

.. code-block:: cmake

   find_package(pssparser REQUIRED)

   add_executable(mytool main.cpp)
   target_link_libraries(mytool PRIVATE pssparser::pssparser)

Header include path is set automatically.  Alternatively, import the
pssparser Python package and use its ``get_incdirs()`` / ``get_libdirs()``
helpers (the same mechanism used by dependent Python packages via IVPM):

.. code-block:: cmake

   execute_process(
       COMMAND python -c "import pssparser; print(pssparser.get_incdirs()[0])"
       OUTPUT_VARIABLE PSSP_INCLUDE_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)
   execute_process(
       COMMAND python -c "import pssparser; print(pssparser.get_libdirs()[0])"
       OUTPUT_VARIABLE PSSP_LIB_DIR OUTPUT_STRIP_TRAILING_WHITESPACE)

   include_directories(${PSSP_INCLUDE_DIR})
   link_directories(${PSSP_LIB_DIR})
   target_link_libraries(mytool PRIVATE pssparser)

***********************
Obtaining the factory
***********************

The library exports a single C entry point:

.. code-block:: cpp

   #include "pssp/IFactory.h"

   // Declared in the shared library:
   extern "C" pssp::IFactory *pssparser_getFactory();

Typical initialisation pattern:

.. code-block:: cpp

   #include <dlfcn.h>   // POSIX
   #include "pssp/IFactory.h"
   #include "pssp/ast/IFactory.h"
   #include "dmgr/IDebugMgr.h"

   // Load the library (or link directly)
   pssp::IFactory *factory = pssparser_getFactory();

   // Initialise with a debug manager and the AST factory
   dmgr::IDebugMgr  *dmgr    = dmgr_getFactory()->mkDebugMgr();
   pssp::ast::IFactory *ast_f = pssp_ast_getFactory();
   factory->init(dmgr, ast_f);

In practice, if you link the shared library directly you only need to call
``pssparser_getFactory()`` — the linker handles symbol resolution.

***********************
Parsing PSS source
***********************

.. code-block:: cpp

   #include <fstream>
   #include <sstream>
   #include "pssp/IFactory.h"
   #include "pssp/ast/IFactory.h"

   pssp::IFactory         *factory = /* ... see above ... */;
   pssp::ast::IFactory    *ast_f   = factory->getAstFactory();

   // --- Create a marker listener to collect diagnostics
   pssp::IMarkerCollector *markers = factory->mkMarkerCollector();

   // --- Create a builder
   pssp::IAstBuilder *builder = factory->mkAstBuilder(markers);

   // --- Load the built-in standard library (always first)
   pssp::ast::IGlobalScope *stdlib = ast_f->mkGlobalScope(0);
   factory->loadStandardLibrary(builder, stdlib);

   // --- Parse a file
   std::ifstream in("design.pss");
   pssp::ast::IGlobalScope *gs = ast_f->mkGlobalScope(1);
   builder->build(gs, &in);

   // --- Check for errors
   if (markers->hasSeverity(pssp::MarkerSeverityE::Error)) {
       for (auto &m : markers->getMarkers()) {
           fprintf(stderr, "[error] %s %d:%d  %s\n",
               "<file>", m->loc().lineno, m->loc().linepos,
               m->msg().c_str());
       }
       return 1;
   }

   // --- Parse more files, then link
   pssp::IMarkerCollector *link_mc = factory->mkMarkerCollector();
   pssp::ILinker          *linker  = factory->mkAstLinker();

   std::vector<pssp::ast::IGlobalScope *> scopes = { stdlib, gs };
   pssp::ast::IRootSymbolScope *root = linker->link(link_mc, scopes);

***********************
Traversing the AST
***********************

The linked ``IRootSymbolScope`` is a ``ISymbolChildrenScope`` — a scope that
maps names to child symbol scopes.

Symbol table lookup
===================

.. code-block:: cpp

   #include "pssp/ast/ISymbolScope.h"

   pssp::ast::IRootSymbolScope *root = /* ... */;

   // Check if a name exists and retrieve its index
   if (root->symtabHas("pss_top")) {
       int idx = root->symtabAt("pss_top");
       pssp::ast::IScopeChild *node = root->getChild(idx);
       // Cast to the concrete type you expect, e.g. ISymbolTypeScope
   }

Iterating children
==================

.. code-block:: cpp

   for (int i = 0; i < root->numChildren(); ++i) {
       pssp::ast::IScopeChild *child = root->getChild(i);
       // Inspect via dynamic_cast or the visitor pattern
   }

Visitor pattern
================

All AST nodes accept a visitor through the ``accept()`` method.  Implement
``pssp::ast::VisitorBase`` (generated by pyastbuilder) to receive callbacks
for each node type:

.. code-block:: cpp

   #include "pssp/ast/VisitorBase.h"

   class MyVisitor : public pssp::ast::VisitorBase {
   public:
       void visitAction(pssp::ast::IAction *node) override {
           printf("Action: %s\n", node->getName()->getId().c_str());
           VisitorBase::visitAction(node);  // recurse into children
       }
   };

   MyVisitor v;
   root->accept(&v);

***********************
IFactory reference
***********************

``pssp::IFactory`` (``include/pssp/IFactory.h``):

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Method
     - Description
   * - ``init(dmgr, ast_factory)``
     - Initialise with a debug manager and the AST factory (call once)
   * - ``getAstFactory()``
     - Returns the ``pssp::ast::IFactory`` instance
   * - ``getDebugMgr()``
     - Returns the ``dmgr::IDebugMgr`` instance
   * - ``loadStandardLibrary(builder, global)``
     - Populate ``global`` with built-in PSS declarations
   * - ``mkAstBuilder(marker_l)``
     - Create a new ``IAstBuilder`` (one per compile unit is typical)
   * - ``mkAstLinker()``
     - Create a new ``ILinker``
   * - ``mkMarkerCollector()``
     - Create a fresh ``IMarkerCollector``
   * - ``mkAstSymbolTableIterator(root)``
     - Create an iterator over the symbol table
   * - ``mkTaskFindElementByLocation(...)``
     - Find the AST node at a given source location
   * - ``lookupLocation(root, scope, line, col)``
     - Map a source position to the deepest enclosing scope

***********************
IAstBuilder reference
***********************

``pssp::IAstBuilder`` (``include/pssp/IAstBuilder.h``):

.. list-table::
   :header-rows: 1
   :widths: 45 55

   * - Method
     - Description
   * - ``build(global, in)``
     - Parse the stream ``in`` into ``global``
   * - ``setCollectDocStrings(bool)``
     - Enable doc-string collection during parsing
   * - ``getCollectDocStrings()``
     - Query doc-string collection state
   * - ``setEnableProfile(bool)``
     - Enable ANTLR decision-level profiling
   * - ``getEnableProfile()``
     - Query profiling state
   * - ``getProfileInfo()``
     - Retrieve ``IParseProfileInfo`` after a profiled parse

***********************
ILinker reference
***********************

``pssp::ILinker`` (``include/pssp/ILinker.h``):

Linking resolves all symbol references and builds the unified
``IRootSymbolScope``.

.. code-block:: cpp

   pssp::ILinker *linker = factory->mkAstLinker();
   pssp::IMarkerCollector *mc = factory->mkMarkerCollector();

   std::vector<pssp::ast::IGlobalScope *> scopes = { stdlib, gs1, gs2 };
   pssp::ast::IRootSymbolScope *root = linker->link(mc, scopes);

***********************
Diagnostic types
***********************

``pssp::IMarker`` (``include/pssp/IMarker.h``):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``msg()``
     - Diagnostic message string
   * - ``severity()``
     - ``pssp::MarkerSeverityE::{Error, Warn, Info, Hint}``
   * - ``loc()``
     - ``pssp::ast::Location {fileid, lineno, linepos}``

``pssp::IMarkerCollector`` (``include/pssp/IMarkerCollector.h``):

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Method
     - Description
   * - ``hasSeverity(s)``
     - Returns ``true`` if any marker has severity ``>= s``
   * - ``markers()``
     - ``std::vector<IMarkerUP>`` — all collected markers

***********************
Thread safety
***********************

* ``pssparser_getFactory()`` returns a **process-global** singleton; call it
  once at startup and share the pointer across threads (read-only after
  ``init()``).
* ``IAstBuilder`` and ``ILinker`` are **not thread-safe**.  Create one builder
  per thread if you need to parse concurrently.
* The resulting ``IRootSymbolScope`` is **read-only** after linking; it is
  safe to traverse from multiple threads simultaneously.
