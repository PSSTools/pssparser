####################
API Reference
####################

.. contents:: Table of Contents
   :local:
   :depth: 2

.. note::
   pssparser's core Cython extension cannot be introspected by Sphinx
   ``autodoc``.  This page documents the public API manually.  See also
   :doc:`user_guide` for usage examples.

*****************************************
``pssparser`` — top-level package
*****************************************

.. py:class:: pssparser.Parser

   High-level driver for parse and link operations.

   .. py:method:: parse(files: List[str]) -> bool

      Parse one or more PSS files from disk.  Can be called multiple times
      before :meth:`link`.

      :param files: List of file-system paths to ``.pss`` files.
      :raises ParseException: If any file contains syntax or semantic errors.
      :returns: ``True`` on success.

   .. py:method:: parses(files: List[Tuple[str, str]]) -> bool

      Parse PSS source from in-memory strings.

      :param files: List of ``(filename, content)`` tuples.  The filename is
                    used only in diagnostic messages.
      :raises ParseException: On syntax or semantic errors.
      :returns: ``True`` on success.

   .. py:method:: link() -> pssparser.ast.RootSymbolScope

      Link all previously parsed files into a single symbol tree.

      Clears the internal file list so the parser can be reused for a new
      compile.

      :raises ParseException: If linking fails (unresolved references, type
                               errors, etc.).
      :returns: The fully linked :class:`pssparser.ast.RootSymbolScope`.

   .. py:method:: enable_profiling(enable: bool = True)

      Enable or disable ANTLR decision-level profiling.  Must be called
      before the first :meth:`parse` / :meth:`parses` call.

   .. py:method:: get_profile_info() -> Optional[pssparser.core.ParseProfileInfo]

      Return parse profiling data from the last parse operation, or ``None``
      if profiling was not enabled.

   .. py:attribute:: markers
      :type: List[dict]

      Structured list of diagnostics from the last parse/link operation
      (including non-fatal warnings, info, hints).

      Each entry is a ``dict`` with keys ``severity``, ``message``, ``file``,
      ``line``, and ``col``.

.. py:exception:: pssparser.ParseException

   Raised by :meth:`~pssparser.Parser.parse`,
   :meth:`~pssparser.Parser.parses`, and :meth:`~pssparser.Parser.link` on
   error.

   .. py:attribute:: markers
      :type: List[dict]

      List of error markers (same format as :attr:`~pssparser.Parser.markers`).


*****************************************
``pssparser.core`` — Cython extension
*****************************************

.. py:class:: pssparser.core.Factory

   Process-global singleton.  Use :meth:`inst` to obtain the instance.

   .. py:staticmethod:: inst() -> Factory

      Return the shared ``Factory`` instance, loading ``libpssparser`` on
      first call.

   .. py:method:: getAstFactory() -> pssparser.ast.Factory

      Return the AST factory used to allocate AST nodes.

   .. py:method:: getDebugMgr() -> debug_mgr.core.DebugMgr

      Return the debug manager.

   .. py:method:: loadStandardLibrary(builder: AstBuilder, scope: pssparser.ast.GlobalScope)

      Populate *scope* with the built-in PSS standard library declarations.
      Always call this before parsing user files.

   .. py:method:: mkAstBuilder(marker_l: MarkerListener) -> AstBuilder

      Create a new parser/builder.

   .. py:method:: mkAstLinker() -> Linker

      Create a new linker.

   .. py:method:: mkMarkerCollector() -> MarkerCollector

      Create a fresh collector for diagnostics.

   .. py:method:: mkTaskFindElementByLocation() -> TaskFindElementByLocation

      Create a task that finds the AST node at a given source location.

   .. py:method:: lookupLocation(root, scope, lineno: int, linepos: int) -> Optional[LookupLocationResult]

      Map a source location to the deepest enclosing scope.

.. py:class:: pssparser.core.AstBuilder

   Parses PSS source into a ``GlobalScope``.

   .. py:method:: build(root: pssparser.ast.GlobalScope, in_s)

      Parse the stream *in_s* (a file-like object) into *root*.

   .. py:method:: setCollectDocStrings(collect: bool)
   .. py:method:: getCollectDocStrings() -> bool

      Control whether doc-strings embedded in PSS source are collected.

   .. py:method:: setEnableProfile(enable: bool)
   .. py:method:: getEnableProfile() -> bool

      Control ANTLR decision-level profiling.

   .. py:method:: getProfileInfo() -> Optional[ParseProfileInfo]

      Return profiling data after a profiled parse.

.. py:class:: pssparser.core.Linker

   Links a list of ``GlobalScope`` objects into a ``RootSymbolScope``.

   .. py:method:: link(marker_l: MarkerListener, scopes) -> pssparser.ast.RootSymbolScope

      Perform linking.  *scopes* is a list of ``GlobalScope`` objects
      (stdlib first).

.. py:class:: pssparser.core.MarkerCollector

   Collects diagnostics emitted during parsing and linking.

   .. py:method:: markers() -> List[Marker]

      Return all collected markers.

   .. py:method:: numMarkers() -> int

      Return the number of markers.

   .. py:method:: getMarker(idx: int) -> Marker

      Return the marker at index *idx*.

   .. py:method:: hasSeverity(s: MarkerSeverityE) -> bool

      Return ``True`` if any marker has severity *s* or worse.

.. py:class:: pssparser.core.Marker

   A single diagnostic.

   .. py:method:: msg() -> str

      Return the human-readable message string.

   .. py:method:: severity() -> MarkerSeverityE

      Return the severity level.

   .. py:method:: loc() -> Location

      Return the source location.

.. py:class:: pssparser.core.Location

   A source file location.

   .. py:attribute:: file
      :type: int

      File ID (index into the file list passed to ``parse``/``parses``).

   .. py:attribute:: line
      :type: int

      1-based line number.

   .. py:attribute:: pos
      :type: int

      0-based column position.

.. py:class:: pssparser.core.MarkerSeverityE

   Severity enumeration (``IntEnum``).

   .. py:attribute:: Error = 0
   .. py:attribute:: Warn  = 1
   .. py:attribute:: Info  = 2
   .. py:attribute:: Hint  = 3

.. py:class:: pssparser.core.ParseProfileInfo

   Aggregate ANTLR profiling statistics for a parse run.

   .. py:attribute:: total_time_in_prediction
      :type: float

      Total microseconds spent in prediction.

   .. py:attribute:: total_sll_lookahead_ops
      :type: int
   .. py:attribute:: total_ll_lookahead_ops
      :type: int
   .. py:attribute:: total_sll_atn_lookahead_ops
      :type: int
   .. py:attribute:: total_ll_atn_lookahead_ops
      :type: int
   .. py:attribute:: total_atn_lookahead_ops
      :type: int
   .. py:attribute:: dfa_size
      :type: int

      Total number of DFA states cached.

   .. py:method:: get_decision_info() -> List[DecisionProfileInfo]

      Per-decision profiling breakdown.

   .. py:method:: get_ll_decisions() -> int

      Number of decisions that required LL fallback.

.. py:class:: pssparser.core.DecisionProfileInfo

   Per-decision profiling data.

   .. py:attribute:: decision       :type: int
   .. py:attribute:: invocations    :type: int
   .. py:attribute:: time_in_prediction :type: float
   .. py:attribute:: sll_lookahead_ops  :type: int
   .. py:attribute:: ll_lookahead_ops   :type: int
   .. py:attribute:: sll_atn_transitions :type: int
   .. py:attribute:: ll_atn_transitions  :type: int
   .. py:attribute:: ll_fallback         :type: int
   .. py:attribute:: ambiguity_count     :type: int
   .. py:attribute:: context_sensitivity_count :type: int
   .. py:attribute:: error_count         :type: int
   .. py:attribute:: max_lookahead       :type: int

.. py:function:: pssparser.core.resolveSymbolPathRef(root: pssparser.ast.SymbolChildrenScope, ref: pssparser.ast.SymbolRefPath) -> Optional[pssparser.ast.ScopeChild]

   Resolve a ``SymbolRefPath`` to the declaration node it refers to.

   :param root: The root symbol scope to search from.
   :param ref: The reference path to resolve.
   :returns: The target ``ScopeChild``, or ``None`` if resolution fails.


*****************************************
``pssparser.utils`` — helpers
*****************************************

.. py:class:: pssparser.utils.SymbolScopeUtil(obj: pssparser.ast.SymbolChildrenScope)

   Wrapper providing higher-level helpers for symbol scope navigation.

   .. py:method:: getQname(name: str) -> pssparser.ast.ScopeChild

      Look up a ``::``-separated qualified name starting from *obj*.

      :raises Exception: If any segment of the path is not found.

   .. py:method:: getRoot() -> pssparser.ast.SymbolChildrenScope

      Walk ``getUpper()`` links to find the root scope.

   .. py:method:: getExtensions() -> list

      Return a list of extension scopes that contribute children to *obj*.

.. py:class:: pssparser.utils.SymbolTypeScopeUtil(obj: pssparser.ast.SymbolChildrenScope)

   Extends :class:`SymbolScopeUtil` with type-hierarchy helpers.

   .. py:method:: getSuper() -> Optional[pssparser.ast.ScopeChild]

      Resolve and return the super-type symbol scope, or ``None``.


*****************************************
``pssparser.ast`` — AST nodes
*****************************************

The ``pssparser.ast`` module is generated at build time by
`pyastbuilder <https://github.com/fvutils/pyastbuilder>`_.  The classes
below represent the most commonly used nodes.

Core structure
==============

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``ScopeChild``
     - Base of all AST nodes; has ``parent``, location, ``assocData``
   * - ``Scope``
     - Container; adds ``numChildren()`` / ``getChild(i)``
   * - ``GlobalScope``
     - Root of one parsed file
   * - ``NamedScope``
     - Scope with an ``ExprId`` name
   * - ``NamedScopeChild``
     - Non-scope child with a name
   * - ``PackageScope``
     - Package declaration
   * - ``TypeScope``
     - Base for component, action, struct, etc.

Declarations
============

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``Component``
     - Component type declaration
   * - ``Action``
     - Action type declaration
   * - ``Struct``
     - Struct type declaration
   * - ``Enum``
     - Enum type declaration
   * - ``Field``
     - Data field (rand or non-rand)
   * - ``Function``
     - Function declaration

Symbol scopes (linked tree)
===========================

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``RootSymbolScope``
     - Root of the linked symbol tree
   * - ``SymbolScope``
     - Linked scope with a symbol table
   * - ``SymbolTypeScope``
     - Linked type scope (component, action, etc.)
   * - ``SymbolChildrenScope``
     - Base for scopes with child lookup
   * - ``SymbolRefPath``
     - Reference path to a declaration (resolved by ``resolveSymbolPathRef``)

Expressions
===========

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``ExprId``
     - Identifier expression; ``.getId()`` returns the name string
   * - ``ExprNumber``
     - Numeric literal; ``.getVal()`` returns the integer value
   * - ``ExprBool``
     - Boolean literal
   * - ``ExprString``
     - String literal
   * - ``ExprBin``
     - Binary operation; ``.getLhs()``, ``.getRhs()``, ``.getOp()``
   * - ``ExprUnary``
     - Unary operation
   * - ``ExprRefPath``
     - Reference path expression

Activities
==========

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``ActivityDecl``
     - Top-level ``activity { }`` block
   * - ``ActivitySequence``
     - Sequential list of statements
   * - ``ActivityParallel``
     - Parallel execution block
   * - ``ActivitySchedule``
     - Unordered/flexible scheduling
   * - ``ActivitySelect``
     - Random branch selection
   * - ``ActivityRepeatCount``
     - Count-based loop
   * - ``ActivityRepeatWhile``
     - Condition-based loop
   * - ``ActivityIfElse``
     - Conditional activity
   * - ``ActivityActionHandleTraversal``
     - Action invocation within an activity

Constraints
===========

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Class
     - Description
   * - ``ConstraintBlock``
     - Named or anonymous ``constraint { }`` block
   * - ``ConstraintScope``
     - Scoped group of constraint statements
   * - ``ConstraintStmtExpr``
     - Expression constraint (most common form)
   * - ``ConstraintStmtForeach``
     - Array element constraint
   * - ``ConstraintStmtIf``
     - Conditional constraint
   * - ``ConstraintStmtImplication``
     - Implication constraint (``a -> b``)
   * - ``ConstraintStmtUnique``
     - Uniqueness constraint

For the complete generated class list see :doc:`ast_class_hierarchy`.
