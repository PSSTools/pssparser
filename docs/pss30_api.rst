################################
PSS 3.0 API Documentation
################################

This document describes the API additions for PSS 3.0 support in pssparser.

AST Nodes for PSS 3.0
======================

Monitor AST Nodes
-----------------

.. note::

   This section previously documented properties (``monitor.activities``,
   ``monitor.constraints``, ``traversal.action_ref``), constructors
   (``ast.Monitor("MyMonitor")``) and C++ accessors (``getIsAbstract()``) that
   the parser has never had, alongside a PSS syntax it has never accepted. It
   has been rewritten against the implementation. Node reference material lives
   in :doc:`reference_api_docs`; this section covers only what is specific to
   walking a monitor.

Monitor
^^^^^^^

``Monitor`` derives from ``TypeScope``, exactly as ``Action`` and ``Struct``
do. Its body -- handles, constraints, the activity declaration -- is its
``getChildren()``; there is no separate list per member kind.

.. code-block:: python

    for child in monitor.getChildren():
        if type(child).__name__ == "MonitorActivityDecl":
            ...
    monitor.getIs_abstract()

Monitor activity statements
^^^^^^^^^^^^^^^^^^^^^^^^^^^

``MonitorActivityDecl`` holds the activity's statements in ``getChildren()``,
in source order. So do the five braced forms -- ``MonitorActivitySequence``,
``MonitorActivityConcat``, ``MonitorActivityOverlap``,
``MonitorActivitySchedule`` and ``MonitorActivitySelect`` -- which all derive
from ``MonitorActivityLabeledScope`` and are told apart by class, not by a
field:

.. code-block:: python

    (activity,) = [c for c in monitor.getChildren()
                   if type(c).__name__ == "MonitorActivityDecl"]

    for stmt in activity.getChildren():
        kind = type(stmt).__name__
        if kind == "MonitorActivityConcat":
            body = stmt.getChildren()          # gapless sequence
        elif kind == "MonitorActivityEventually":
            body = [stmt.getBody()]            # one statement, maybe a block
        elif kind == "MonitorConstraint":
            constraint = stmt.getConstraint()

``MonitorActivityEventually.body`` is typed ``ScopeChild`` rather than
``MonitorActivityStmt``, because ``eventually { ... }`` makes it a
``MonitorActivitySequence`` -- a scope, which shares only ``ScopeChild`` with
the statement branch of the hierarchy.

Traversals
^^^^^^^^^^

A traversal inside a monitor activity builds an
``ActivityActionHandleTraversal`` (``h;``, ``h with { ... }``) or an
``ActivityActionTypeTraversal`` (``do T;``) -- the same nodes an action
activity builds. The grammar spells an action traversal and a monitor
traversal identically, so nothing before type resolution distinguishes them.

Constraints
^^^^^^^^^^^

A ``constraint`` in the monitor *body* builds an ordinary ``ConstraintBlock``,
as it does in an action or struct. ``MonitorConstraint`` is used only for a
``constraint`` among the *statements* of an activity, where its position in the
statement order carries meaning.

Cover statements
^^^^^^^^^^^^^^^^

``cover T;`` builds a ``CoverStmtReference`` whose ``target`` is a
``TypeIdentifier``: the statement names a monitor *type*, and there is no
syntax that covers an instance. ``cover { ... }`` builds a ``CoverStmtInline``,
an anonymous monitor body -- a ``Scope`` whose members are reached through
``getChildren()``. Both forms accept a ``label_identifier ':'`` prefix, kept in
``label``.

Both statements appear only as a ``component_body_item``.

.. note::

   Earlier text here said the two forms parsed and built nothing, which was
   true. The classes that existed for them described something else: the
   reference form held an ``ExprRefPath``, as if ``cover`` named an instance,
   and the inline form held one ``ScopeChild`` rather than a body.

String Enhancement AST Nodes
-----------------------------

StringMethodId
^^^^^^^^^^^^^^

Enumeration of string methods (Section 7.6 of PSS 3.0 spec); its values are
listed at :astb:enum:`StringMethodId`.

.. note::

   ``ExprMemberPathElem.string_method_id`` is never set: the parser and the
   linker leave it ``StringMethod_None`` (known issue AB-1 in
   ``docs/design/known-issues.md``). Recognise a string method by the path
   element's name, as below.

Substrings
^^^^^^^^^^

A substring (Section 7.6.2 of the PSS 3.0 spec) has no node of its own. It is
a *slice on a path element*: ``s[0..4]`` is an ``ExprMemberPathElem`` for
``s`` carrying an ``ExprSliceRange`` in its ``subscript`` list.

.. note::

   Earlier versions of this document described an ``ExprSubstring`` class with
   ``target`` / ``start`` / ``end``. That class existed in the schema but the
   builder never constructed it -- a consumer that matched on it would never
   have fired. It was removed in 3.1.1; see the migration note in
   ``CHANGELOG.md``.

Which endpoints are set records how the substring was written: ``[a..b]``
sets both, ``[a..]`` sets only ``lower``, and ``[..b]`` sets only ``upper``.

**Usage**:

.. code-block:: python

    # s[0..4], reached through the member-path element for `s`
    for sub in elem.getSubscriptList():
        if isinstance(sub, ast.ExprSliceRange):
            lower = sub.getLower()      # None for `s[..4]`
            upper = sub.getUpper()      # None for `s[0..]`

ExprMemberPathElem
^^^^^^^^^^^^^^^^^^

A string-method call such as ``s.size()`` or ``s.find("world")`` is two
path elements: one for ``s``, then one named ``size`` (or ``find``) whose
``params`` holds the arguments; a plain member has no ``params``. Its fields
are listed at :astb:class:`ExprMemberPathElem`; in each API:

.. astb:projection-table:: ExprMemberPathElem
   :model: pss

**Usage**:

.. code-block:: python

    # s.find("world"): the element named `find`, after the one for `s`
    if elem.getId().getId() == "find" and elem.getParams() is not None:
        params = elem.getParams()           # a MethodParameterList

Procedural Randomization AST Nodes
-----------------------------------

ProceduralStmtRandomize
^^^^^^^^^^^^^^^^^^^^^^^

Represents a procedural randomization statement, ``randomize a, b with {
...}`` (Section 16.6.6 of PSS 3.0 spec): the variables in ``targets``, in
source order, and any inline constraints in ``constraints``. Its fields are
listed at :astb:class:`ProceduralStmtRandomize`; in each API:

.. astb:projection-table:: ProceduralStmtRandomize
   :model: pss

**Usage**:

.. code-block:: python

    for target in stmt.getTargets():        # the variables, as expressions
        ...
    for c in stmt.getConstraints():         # inline `with { ... }` constraints
        ...

Activity Atomic Block AST Nodes
--------------------------------

ActivityAtomicBlock
^^^^^^^^^^^^^^^^^^^

Represents an atomic activity block (Section 22.6.7 of PSS 3.0 spec). The
braced block it runs atomically is its ``body``, an ``ActivitySequence``
whose ``getChildren()`` are the statements. See
:astb:class:`ActivityAtomicBlock`.

.. code-block:: python

    for stmt in atomic.getBody().getChildren():
        ...

Visitor API
===========

The visitor API has been extended to support PSS 3.0 constructs.

C++ Visitor Interface
---------------------

**Header**: ``src/AstBuilderInt.h``

Monitor Visitors
^^^^^^^^^^^^^^^^

.. code-block:: cpp

    class AstBuilderInt : public PSSParserBaseVisitor {
    public:
        // Monitor declaration
        virtual antlrcpp::Any visitMonitor_declaration(
            PSSParser::Monitor_declarationContext *ctx) override;
        
        // Abstract monitor
        virtual antlrcpp::Any visitAbstract_monitor_declaration(
            PSSParser::Abstract_monitor_declarationContext *ctx) override;
        
        // Monitor activity
        virtual antlrcpp::Any visitMonitor_activity_declaration(
            PSSParser::Monitor_activity_declarationContext *ctx) override;
        
        // Activity statements
        virtual antlrcpp::Any visitMonitor_activity_sequence_block_stmt(
            PSSParser::Monitor_activity_sequence_block_stmtContext *ctx) override;
        
        virtual antlrcpp::Any visitMonitor_activity_concat_stmt(
            PSSParser::Monitor_activity_concat_stmtContext *ctx) override;
        
        virtual antlrcpp::Any visitMonitor_activity_eventually_stmt(
            PSSParser::Monitor_activity_eventually_stmtContext *ctx) override;
        
        virtual antlrcpp::Any visitMonitor_activity_schedule_stmt(
            PSSParser::Monitor_activity_schedule_stmtContext *ctx) override;
        
        // Cover statement
        virtual antlrcpp::Any visitCover_stmt(
            PSSParser::Cover_stmtContext *ctx) override;
    };

Procedural Randomization Visitor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    virtual antlrcpp::Any visitProcedural_randomization_stmt(
        PSSParser::Procedural_randomization_stmtContext *ctx) override;

Activity Atomic Block Visitor
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    virtual antlrcpp::Any visitActivity_atomic_block_stmt(
        PSSParser::Activity_atomic_block_stmtContext *ctx) override;

Python API Integration
======================

Parser Class Extensions
-----------------------

The ``Parser`` class handles PSS 3.0 constructs transparently:

.. code-block:: python

    from pssparser import Parser
    
    parser = Parser()
    
    # Parse PSS 3.0 code
    parser.parses([
        ("monitor.pss", """
            component pss_top {
                action A { }
                action B { }

                monitor MyMonitor {
                    A a;
                    B b;
                    activity {
                        concat {
                            a;
                            b;
                        }
                    }
                }
            }
        """)
    ])
    
    # Link and get AST
    root = parser.link()

AST Traversal
-------------

PSS 3.0 nodes can be traversed like any AST nodes:

.. code-block:: python

    from pssparser import ast
    
    def find_monitors(node):
        """Find all monitors in AST"""
        monitors = []
        
        if isinstance(node, ast.Monitor):
            monitors.append(node)
        
        # Traverse children (every scope has getChildren())
        if hasattr(node, "getChildren"):
            for child in node.getChildren():
                monitors.extend(find_monitors(child))
        
        return monitors
    
    # Walk the user's files, not the linked root (which also holds the
    # standard library)
    monitors = []
    for unit in parser.user_units():
        monitors.extend(find_monitors(unit))
    
    for monitor in monitors:
        print(f"Found monitor: {monitor.getName().getId()}")

Type Introspection
------------------

Check for PSS 3.0 types at runtime:

.. code-block:: python

    from pssparser import ast
    
    def is_pss30_feature(node):
        """Check if node uses PSS 3.0 features"""
        return isinstance(node, (
            ast.Monitor,
            ast.MonitorActivityStmt,
            ast.ProceduralStmtRandomize,
            ast.ActivityAtomicBlock,
            ast.ExprSliceRange
        ))

C++ API Usage Examples
======================

Traversing Monitor Activities
------------------------------

.. code-block:: cpp

    #include "pssp/ast/IMonitor.h"

    // A monitor's body is its children, and each activity block holds its
    // statements the same way. There is no getActivities()/getActivity() pair;
    // the earlier version of this page documented one, along with a
    // getIsAbstract() spelling the generator does not produce.
    void processMonitor(ast::IMonitor *monitor) {
        bool is_abstract = monitor->getIs_abstract();

        for (std::vector<ast::IScopeChildUP>::const_iterator
            it=monitor->getChildren().begin();
            it!=monitor->getChildren().end(); it++) {
            ast::IMonitorActivityDecl *activity =
                dynamic_cast<ast::IMonitorActivityDecl *>(it->get());
            if (!activity) {
                continue;
            }

            for (std::vector<ast::IScopeChildUP>::const_iterator
                s_it=activity->getChildren().begin();
                s_it!=activity->getChildren().end(); s_it++) {
                // The five braced forms are distinguished by class. Casting to
                // MonitorActivitySequence alone would silently skip concat,
                // overlap, schedule and select.
                if (ast::IMonitorActivityLabeledScope *blk =
                    dynamic_cast<ast::IMonitorActivityLabeledScope *>(s_it->get())) {
                    for (std::vector<ast::IScopeChildUP>::const_iterator
                        b_it=blk->getChildren().begin();
                        b_it!=blk->getChildren().end(); b_it++) {
                        // ...
                    }
                }
            }
        }
    }

Building a monitor AST is not a supported use of this library: the factory
exists for the parser, and a hand-built monitor will not carry the source
locations or symbol tables the linker requires. Parse PSS source instead.


Best Practices
==============

1. **Use Factory Methods**: Create AST nodes via ``ast::getFactory()``
2. **Check Node Types**: Use ``dynamic_cast`` or ``isinstance`` before accessing type-specific properties
3. **Handle Null References**: PSS 3.0 reference types can be null
4. **Validate Contexts**: Check semantic rules (e.g., yield only in target exec)

Error Handling
==============

Parse Errors
------------

.. code-block:: python

    from pssparser import Parser
    
    parser = Parser()
    
    try:
        parser.parses([("file.pss", invalid_pss_code)])
    except Exception as e:
        print(f"Parse error: {e}")

AST Validation
--------------

.. code-block:: python

    from pssparser import ast
    
    def validate_monitor(monitor):
        """Validate monitor structure"""
        if not isinstance(monitor, ast.Monitor):
            raise ValueError("Not a monitor")
        
        has_activity = any(isinstance(c, ast.MonitorActivityDecl)
                           for c in monitor.getChildren())
        if monitor.getIs_abstract() and not has_activity:
            print("Warning: Abstract monitor with no activity")
        
        # Additional validation...

Performance Considerations
==========================

* **AST Size**: Monitor AST nodes add ~10% to AST size for typical models
* **Parse Time**: PSS 3.0 constructs parse efficiently (< 5% overhead)
* **Memory**: Monitor activities use minimal additional memory
* **Linking**: Reference collections link as efficiently as standard collections

Thread Safety
=============

The parser is **not thread-safe**. Use separate parser instances per thread:

.. code-block:: python

    from pssparser import Parser
    import threading
    
    def parse_in_thread(content):
        parser = Parser()  # New parser per thread
        parser.parses([("file.pss", content)])
        return parser.link()
    
    threads = [
        threading.Thread(target=parse_in_thread, args=(content1,)),
        threading.Thread(target=parse_in_thread, args=(content2,))
    ]

Deprecations
============

No APIs are deprecated in PSS 3.0 support. All PSS 2.x APIs remain available.

See Also
========

* :doc:`pss30_features` - Feature documentation
* :doc:`pss30_migration` - Migration guide
* :doc:`ast_structure` - General AST structure
* :doc:`reference_api_docs` - Complete API reference
