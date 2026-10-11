######################
AST Class Hierarchy
######################

This document explains the class hierarchy and inheritance relationships
in the PSS AST.

.. contents:: Table of Contents
   :local:
   :depth: 2

********************
Inheritance Overview
********************

The PSS AST follows a clear inheritance hierarchy with **ScopeChild** as the
root base class for most nodes.

Key Base Classes
================

**ScopeChild**
    Base class for most AST nodes. Provides:
    
    - ``parent`` pointer to containing scope
    - ``location`` and ``endLocation`` for error reporting
    - ``index`` within parent's children list
    - ``assocData`` for user-defined metadata
    - ``annotations``, ``comments`` and the doc-comment fields

**Scope** (extends ScopeChild)
    Container for child nodes. Provides:
    
    - ``children`` list of contained ScopeChild nodes
    - ``compile_conds``, the ``compile if`` conditions that guard them
    
**NamedScope** (extends Scope)
    Scope with an identifier name:
    
    - ``name`` (ExprId) for the scope identifier
    - Used for packages, types, etc.

**NamedScopeChild** (extends ScopeChild)
    Child node with a name but not a scope:
    
    - ``name`` (ExprId) for the identifier
    - Used for fields, parameters, enum items, etc.

Each one's complete fields, in every API, are in the :doc:`ast/index`:
:astb:class:`ScopeChild`, :astb:class:`Scope`, :astb:class:`NamedScope`,
:astb:class:`NamedScopeChild`.

************************
Complete Class Hierarchy
************************

The trees below are generated from ``ast/*.yaml`` when the documentation is
built, so they are always the current schema. Each name links to its entry
in the :doc:`ast/index`.

Core Structure
==============

.. astb:inheritance-tree:: Scope
   :model: pss

.. astb:inheritance-tree:: NamedScopeChild
   :model: pss

.. astb:inheritance-tree:: ScopeChildRef
   :model: pss

.. astb:inheritance-tree:: PackageImportStmt
   :model: pss

.. astb:inheritance-tree:: PyImportStmt
   :model: pss

.. astb:inheritance-tree:: PyImportFromStmt
   :model: pss

Type System Hierarchy
=====================

.. astb:inheritance-tree:: DataType
   :model: pss

Expression Hierarchy
====================

.. astb:inheritance-tree:: Expr
   :model: pss

Activity Hierarchy
==================

.. astb:inheritance-tree:: ActivityStmt
   :model: pss

.. astb:inheritance-tree:: ActivitySelectBranch
   :model: pss

.. astb:inheritance-tree:: ActivityMatchChoice
   :model: pss

.. astb:inheritance-tree:: ActivityBindStmt
   :model: pss

.. astb:inheritance-tree:: ActivitySymbolCall
   :model: pss

.. astb:inheritance-tree:: ActivityConstraint
   :model: pss

.. astb:inheritance-tree:: ActivitySchedulingConstraint
   :model: pss

.. astb:inheritance-tree:: ActivityJoinSpec
   :model: pss

.. astb:inheritance-tree:: ActivityDecl
   :model: pss

.. astb:inheritance-tree:: SymbolDeclaration
   :model: pss

``SymbolDeclaration`` is a scope and is named in the symbol table, because a
``symbol_call`` names it. Its body statements are the ordinary activity
statement classes -- a symbol body *is* an activity body -- rather than a
parallel set.

Constraint Hierarchy
====================

.. astb:inheritance-tree:: ConstraintScope
   :model: pss

.. astb:inheritance-tree:: ConstraintStmt
   :model: pss

.. astb:inheritance-tree:: ConstraintSymbolScope
   :model: pss

Procedural Code Hierarchy
==========================

.. astb:inheritance-tree:: ExecBlock
   :model: pss

.. astb:inheritance-tree:: ExecScope
   :model: pss

.. astb:inheritance-tree:: ExecStmt
   :model: pss

.. astb:inheritance-tree:: ExecTargetTemplateBlock
   :model: pss

Function Hierarchy
==================

.. astb:inheritance-tree:: FunctionDefinition
   :model: pss

.. astb:inheritance-tree:: FunctionPrototype
   :model: pss

.. astb:inheritance-tree:: FunctionImport
   :model: pss

.. astb:inheritance-tree:: NamedScopeChild
   :model: pss

.. astb:inheritance-tree:: MethodParameterList
   :model: pss

Monitor Hierarchy (PSS 3.0)
============================

.. astb:inheritance-tree:: Monitor
   :model: pss

.. astb:inheritance-tree:: SymbolScope
   :model: pss
   :depth: 2

.. astb:inheritance-tree:: MonitorActivityStmt
   :model: pss

.. astb:inheritance-tree:: Scope
   :model: pss

.. astb:inheritance-tree:: CoverStmtReference
   :model: pss

The five braced forms split from MonitorActivityStmt because they introduce a
scope; the two branches meet at ScopeChild. A field holding an arbitrary
monitor activity statement -- ``MonitorActivityEventually.body``, for one --
must therefore be typed ``ScopeChild``. This mirrors the action-activity side,
where ``ActivityLabeledScope`` and ``ActivityLabeledStmt`` split the same way
for the same reason.

An action or monitor traversal inside a monitor activity is an
``ActivityActionHandleTraversal`` / ``ActivityActionTypeTraversal``: the
grammar spells the two identically, so nothing before type resolution can tell
them apart.

``CoverStmtInline`` is a plain ``Scope``, not a ``SymbolScope``, for the same
reason ``Monitor`` and ``Component`` are: a *declaration* body's linked-tree
scope is a synthetic mirror the linker builds, not the AST node. Only nodes
that appear directly in the linked tree -- the activity declaration and the
braced activity forms -- are ``SymbolScope``\ s.

Covergroup Hierarchy
====================

.. astb:inheritance-tree:: NamedScopeChild
   :model: pss

.. astb:inheritance-tree:: CovergroupOption
   :model: pss

.. astb:inheritance-tree:: CovergroupPortmap
   :model: pss

.. astb:inheritance-tree:: CovergroupType
   :model: pss

A covergroup body is not a scope, and a coverpoint name is not resolved through
the symbol table -- so the coverpoint target, the ``iff`` guards and the bin
``with`` expressions all carry ``visit: false``. The one exception is
``CovergroupType``'s ports: those are ``Field`` children in the covergroup's own
scope, because a port's *type* is an ordinary type reference that has to bind.

Override Hierarchy
==================

.. astb:inheritance-tree:: Scope
   :model: pss

.. astb:inheritance-tree:: OverrideStmt
   :model: pss

The two statements differ in what they select -- a type identifier, or a
hierarchical instance path -- which is why they are separate classes rather
than one class with a discriminator. ``OverrideDecl`` declares no names, so it
introduces no scope in the linked tree even though it is a ``Scope``.

Template String Hierarchy (PSS 3.1)
====================================

The scanned body of a triple-quoted string containing special elements
(§4.7.1).  Distinct from the *type* template hierarchy below, which is about
parameterized types and shares only the word.

Note both bases derive from **SymbolScope**.  Only the block elements need a
symbol table -- a ``foreach`` iterator has to be visible inside its own block --
but the resolution machinery erases anything that is not an ``ISymbolScope``
from its scope stack, so one hierarchy is cheaper than two parallel ones.

.. astb:inheritance-tree:: TemplateString
   :model: pss

.. astb:inheritance-tree:: TemplateElem
   :model: pss

``ExprTemplateString`` subclasses ``ExprString``, so every existing consumer
that casts to ``ExprString`` or calls ``getValue()`` keeps working and sees the
raw text.  A triple-quoted string with *no* special elements stays a plain
``ExprString``.

Type Template Hierarchy
=======================

.. astb:inheritance-tree:: TemplateParamDeclList
   :model: pss

.. astb:inheritance-tree:: TemplateParamDecl
   :model: pss

.. astb:inheritance-tree:: TemplateParamValueList
   :model: pss

.. astb:inheritance-tree:: TemplateParamValue
   :model: pss

Symbol Resolution Hierarchy
============================

.. astb:inheritance-tree:: SymbolChild
   :model: pss
   :depth: 2

.. astb:inheritance-tree:: SymbolImportSpec
   :model: pss

.. astb:inheritance-tree:: SymbolRefPath
   :model: pss

***********************
When to Use Which Class
***********************

Traversing the Tree
===================

**Use Scope classes when:**

- You need to iterate over children
- You're building the physical AST structure
- You're walking the parse tree

**Use SymbolScope classes when:**

- You need name resolution
- You're doing semantic analysis
- You need cross-reference information

Creating New Nodes
==================

**For declarations, use:**

- ``Action`` for action declarations
- ``Component`` for components
- ``Struct`` for structs/buffers/resources/streams/states
- ``Field`` for data members
- ``EnumDecl`` for enumerations

**For executable code, use:**

- ``ActivitySequence`` / ``ActivityParallel`` for control flow
- ``ExecBlock`` with ``ProceduralStmt*`` for procedural code
- ``ConstraintBlock`` with ``ConstraintStmt*`` for constraints

**For expressions, use:**

- ``ExprBin`` for binary operations
- ``ExprId`` for identifiers
- ``ExprNumber`` / ``ExprBool`` / ``ExprString`` for literals
- ``ExprRefPath`` for member access

Type Annotations
================

**For field types, use:**

- ``DataTypeInt`` for integers/bits
- ``DataTypeBool`` for booleans
- ``DataTypeString`` for strings
- ``DataTypeUserDefined`` for user-defined types
- ``DataTypeRef`` for reference types

**********************
Common Design Patterns
**********************

Visitor Pattern
===============

Implement ``visit()`` methods for each node type:

.. code-block:: python

    class MyVisitor:
        def visit(self, node):
            # Dispatch to specific visitor method
            method_name = f'visit_{type(node).__name__}'
            method = getattr(self, method_name, self.generic_visit)
            return method(node)
        
        def generic_visit(self, node):
            # Default: visit children (every Scope has getChildren())
            if hasattr(node, 'getChildren'):
                for child in node.getChildren():
                    self.visit(child)
        
        def visit_Action(self, node):
            print(f"Visiting action: {node.getName().getId()}")
            self.generic_visit(node)
        
        def visit_Field(self, node):
            print(f"  Field: {node.getName().getId()}")

Accumulator Pattern
===================

Collect information while traversing:

.. code-block:: python

    class StatisticsCollector:
        def __init__(self):
            self.action_count = 0
            self.constraint_count = 0
            self.field_count = 0
        
        def collect(self, node):
            if isinstance(node, ast.Action):
                self.action_count += 1
            elif isinstance(node, ast.ConstraintBlock):
                self.constraint_count += 1
            elif isinstance(node, ast.Field):
                self.field_count += 1
            
            if hasattr(node, 'getChildren'):
                for child in node.getChildren():
                    self.collect(child)
        
        def report(self):
            return {
                'actions': self.action_count,
                'constraints': self.constraint_count,
                'fields': self.field_count
            }

Finder Pattern
==============

Look for a shape in an expression tree -- here, ``x + 0``:

.. code-block:: python

    def find_add_zero(expr, found):
        if isinstance(expr, ast.ExprBin):
            rhs = expr.getRhs()
            if (ast.ExprBinOp(expr.getOp()) == ast.ExprBinOp.BinOp_Add and
                    isinstance(rhs, ast.ExprUnsignedNumber) and
                    rhs.getValue() == 0):
                found.append(expr)
            find_add_zero(expr.getLhs(), found)
            find_add_zero(rhs, found)
        return found

Rewriting the tree (replacing ``x + 0`` by ``x``) is done in C++:
``IExprBin::setLhs()``/``setRhs()`` replace an operand. The Python binding
reads node-valued fields but has no setters for them; the **In each API**
table of each class in the :doc:`ast/index` shows what each binding
provides.

***********
Next Steps
***********

- See :doc:`ast_usage_guide` for practical examples
- Read :doc:`reference_api_docs` for detailed class documentation
- Explore :doc:`ast_structure` for AST organization details
