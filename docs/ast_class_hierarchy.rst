######################
AST Class Hierarchy
######################

This document explains the class hierarchy and inheritance relationships
in the PSS AST.

.. contents:: Table of Contents
   :local:
   :depth: 2

*******************
Inheritance Overview
*******************

The PSS AST follows a clear inheritance hierarchy with **ScopeChild** as the
root base class for most nodes.

Key Base Classes
================

**ScopeChild**
    Base class for most AST nodes. Provides:
    
    - ``parent`` pointer to containing scope
    - ``location`` information for error reporting
    - ``index`` within parent's children list
    - ``assocData`` for user-defined metadata

**Scope** (extends ScopeChild)
    Container for child nodes. Provides:
    
    - ``children`` list of contained ScopeChild nodes
    - ``endLocation`` for closing brace position
    
**NamedScope** (extends Scope)
    Scope with an identifier name:
    
    - ``name`` (ExprId) for the scope identifier
    - Used for packages, types, etc.

**NamedScopeChild** (extends ScopeChild)
    Child node with a name but not a scope:
    
    - ``name`` (ExprId) for the identifier
    - Used for fields, parameters, enum items, etc.

************************
Complete Class Hierarchy
************************

Core Structure
==============

::

    ScopeChild (base for all AST nodes)
    ├── Scope (container for children)
    │   ├── GlobalScope (file root)
    │   ├── NamedScope (named container)
    │   │   ├── PackageScope (package)
    │   │   └── TypeScope (named type)
    │   │       ├── Action (action declaration)
    │   │       ├── Component (component declaration)
    │   │       └── Struct (struct/buffer/resource/stream/state)
    │   ├── ConstraintScope (constraint container)
    │   │   └── ConstraintBlock (named constraint)
    │   ├── ExecScope (exec block scope)
    │   └── ExtendType (type extension)
    ├── NamedScopeChild (named node, not a scope)
    │   ├── Field (data field)
    │   ├── FieldRef (reference field)
    │   ├── FieldClaim (resource claim)
    │   ├── FieldCompRef (component reference)
    │   ├── EnumDecl (enum declaration)
    │   ├── EnumItem (enum value)
    │   ├── FunctionParamDecl (function parameter)
    │   └── ExtendEnum (enum extension)
    ├── ScopeChildRef (reference to another node)
    ├── PackageImportStmt (import statement)
    ├── PyImportStmt (Python import)
    └── PyImportFromStmt (Python from..import)

Type System Hierarchy
=====================

::

    ScopeChild
    └── DataType (base type)
        ├── DataTypeBool (boolean)
        ├── DataTypeInt (integer/bit)
        ├── DataTypeString (string)
        ├── DataTypeEnum (enum reference)
        ├── DataTypeUserDefined (user type reference)
        ├── DataTypeRef (reference type)
        ├── DataTypeChandle (C handle)
        └── DataTypePyObj (Python object)

Expression Hierarchy
====================

::

    Expr (base expression)
    ├── ExprBool (boolean literal)
    ├── ExprNumber (numeric literal)
    │   ├── ExprSignedNumber
    │   └── ExprUnsignedNumber
    ├── ExprString (string literal)
    ├── ExprNull (null literal)
    ├── ExprId (identifier)
    ├── ExprHierarchicalId (qualified identifier)
    ├── ExprBin (binary operation)
    ├── ExprUnary (unary operation)
    ├── ExprCond (ternary ? :)
    ├── ExprCast (type cast)
    ├── ExprIn (in operator)
    ├── ExprCompileHas (compile-time has)
    ├── ExprSubscript (array subscript)
    ├── ExprBitSlice (bit slice)
    ├── ExprSubstring (substring)
    ├── ExprRefPath (reference path)
    │   ├── ExprRefPathContext
    │   ├── ExprRefPathStatic
    │   │   ├── ExprRefPathStaticFunc
    │   │   └── ExprRefPathStaticRooted
    │   └── ExprRefPathSuper
    ├── ExprStaticRefPath (static reference)
    ├── ExprAggrLiteral (aggregate literal)
    │   ├── ExprAggrEmpty ({ })
    │   ├── ExprAggrList ({ a, b, c })
    │   ├── ExprAggrMap ({ key: val })
    │   └── ExprAggrStruct ({ .field = val })
    ├── ExprListLiteral (list literal)
    ├── ExprStructLiteral (struct literal)
    ├── ExprDomainOpenRangeList (domain range)
    ├── ExprDomainOpenRangeValue
    ├── ExprOpenRangeList (open range)
    └── ExprOpenRangeValue

Activity Hierarchy
==================

::

    ScopeChild
    ├── ActivityStmt (base activity)
    │   ├── ActivityDecl (activity declaration)
    │   ├── ActivityLabeledStmt (labeled statement)
    │   │   ├── ActivityActionHandleTraversal (action invoke)
    │   │   ├── ActivityActionTypeTraversal (type traverse)
    │   │   ├── ActivityAtomicBlock (atomic)
    │   │   └── ActivitySuper (super call)
    │   └── ActivityLabeledScope (labeled scope)
    │       ├── ActivitySequence (sequential)
    │       ├── ActivityParallel (parallel)
    │       ├── ActivitySchedule (scheduled)
    │       ├── ActivitySelect (select)
    │       ├── ActivityRepeatCount (repeat N)
    │       ├── ActivityRepeatWhile (repeat while)
    │       ├── ActivityForeach (foreach)
    │       ├── ActivityReplicate (replicate)
    │       ├── ActivityIfElse (if-else)
    │       └── ActivityMatch (match)
    ├── ActivitySelectBranch (select branch)
    ├── ActivityMatchChoice (match case)
    ├── ActivityBindStmt (bind)
    ├── ActivityConstraint (constraint)
    ├── ActivitySchedulingConstraint (scheduling constraint)
    └── ActivityJoinSpec (join specification)
        ├── ActivityJoinSpecNone
        ├── ActivityJoinSpecFirst
        ├── ActivityJoinSpecBranch
        └── ActivityJoinSpecSelect

Constraint Hierarchy
====================

::

    ScopeChild
    ├── ConstraintScope (constraint container)
    │   └── ConstraintBlock (named constraint block)
    ├── ConstraintStmt (base constraint)
    │   ├── ConstraintScope (also extends here)
    │   ├── ConstraintStmtExpr (expression constraint)
    │   ├── ConstraintStmtField (field in loop)
    │   ├── ConstraintStmtForeach (foreach loop)
    │   ├── ConstraintStmtForall (forall quantifier)
    │   ├── ConstraintStmtIf (conditional)
    │   ├── ConstraintStmtImplication (implication)
    │   ├── ConstraintStmtUnique (uniqueness)
    │   ├── ConstraintStmtDefault (default value)
    │   └── ConstraintStmtDefaultDisable (disable default)
    └── ConstraintSymbolScope (symbol scope)

Procedural Code Hierarchy
==========================

::

    ScopeChild
    ├── ExecBlock (exec block)
    ├── ExecScope (exec scope)
    ├── ExecStmt (base exec statement)
    │   ├── ProceduralStmtAssignment
    │   ├── ProceduralStmtExpr
    │   ├── ProceduralStmtFunctionCall
    │   ├── ProceduralStmtReturn
    │   ├── ProceduralStmtDataDeclaration
    │   ├── ProceduralStmtBody
    │   ├── ProceduralStmtSymbolBodyScope
    │   ├── ProceduralStmtIfElse
    │   ├── ProceduralStmtIfClause
    │   ├── ProceduralStmtWhile
    │   ├── ProceduralStmtRepeat
    │   ├── ProceduralStmtRepeatWhile
    │   ├── ProceduralStmtForeach
    │   ├── ProceduralStmtMatch
    │   ├── ProceduralStmtMatchChoice
    │   ├── ProceduralStmtBreak
    │   ├── ProceduralStmtContinue
    │   ├── ProceduralStmtYield
    │   └── ProceduralStmtRandomize
    ├── ExecTargetTemplateBlock
    └── ExecTargetTemplateParam

Function Hierarchy
==================

::

    ScopeChild
    ├── FunctionDefinition (function with body)
    ├── FunctionPrototype (function signature)
    ├── FunctionImport (base import)
    │   ├── FunctionImportType
    │   └── FunctionImportProto
    ├── NamedScopeChild
    │   └── FunctionParamDecl (parameter)
    └── MethodParameterList (parameter list)

Monitor Hierarchy (PSS 3.0)
============================

::

    TypeScope
    └── Monitor (monitor declaration)

    ScopeChild
    ├── MonitorActivityDecl (activity declaration)
    ├── MonitorActivityStmt (base monitor activity)
    │   ├── MonitorActivitySequence
    │   ├── MonitorActivityConcat (##)
    │   ├── MonitorActivityEventually
    │   ├── MonitorActivityOverlap
    │   ├── MonitorActivitySchedule
    │   ├── MonitorActivitySelect
    │   ├── MonitorActivityRepeatCount
    │   ├── MonitorActivityRepeatWhile
    │   ├── MonitorActivityIfElse
    │   ├── MonitorActivityMatch
    │   ├── MonitorActivityActionTraversal
    │   └── MonitorActivityMonitorTraversal
    ├── MonitorActivitySelectBranch
    ├── MonitorActivityMatchChoice
    ├── MonitorConstraint
    ├── CoverStmtInline
    └── CoverStmtReference

Template Hierarchy
==================

::

    ScopeChild
    ├── TemplateParamDeclList
    ├── TemplateParamDecl (base parameter)
    │   ├── TemplateValueParamDecl (value param)
    │   ├── TemplateGenericTypeParamDecl (type param)
    │   └── TemplateCategoryTypeParamDecl (constrained type)
    ├── TemplateParamValueList
    └── TemplateParamValue (base value)
        ├── TemplateParamExprValue (expression value)
        └── TemplateParamTypeValue (type value)

Symbol Resolution Hierarchy
============================

::

    ScopeChild
    ├── SymbolChild (symbol tree base)
    │   └── SymbolChildrenScope (with children)
    │       └── SymbolScope (symbol scope)
    │           ├── RootSymbolScope (root)
    │           ├── SymbolTypeScope (type scope)
    │           ├── SymbolEnumScope (enum scope)
    │           ├── SymbolFunctionScope (function scope)
    │           └── SymbolExtendScope (extension scope)
    ├── SymbolScopeRef (scope reference)
    └── SymbolImportSpec (import specification)

    (Internal classes)
    SymbolRefPath (reference path)
    
    RefExpr (reference expression)
    ├── RefExprScopeIndex
    ├── RefExprTypeScopeContext
    └── RefExprTypeScopeGlobal

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
            # Default: visit children
            if hasattr(node, 'children'):
                for child in node.children:
                    self.visit(child)
        
        def visit_Action(self, node):
            print(f"Visiting action: {node.name.id}")
            self.generic_visit(node)
        
        def visit_Field(self, node):
            print(f"  Field: {node.name.id}")

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
            
            if hasattr(node, 'children'):
                for child in node.children:
                    self.collect(child)
        
        def report(self):
            return {
                'actions': self.action_count,
                'constraints': self.constraint_count,
                'fields': self.field_count
            }

Transformer Pattern
===================

Modify the AST while traversing:

.. code-block:: python

    class ExpressionSimplifier:
        def transform(self, expr):
            if isinstance(expr, ast.ExprBin):
                # Simplify: x + 0 => x
                if (expr.op == ast.ExprBinOp.BinOp_Add and
                    isinstance(expr.rhs, ast.ExprNumber) and
                    expr.rhs.val == 0):
                    return expr.lhs
                
                # Recursively simplify operands
                expr.lhs = self.transform(expr.lhs)
                expr.rhs = self.transform(expr.rhs)
            
            return expr

***********
Next Steps
***********

- See :doc:`ast_usage_guide` for practical examples
- Read :doc:`reference_api_docs` for detailed class documentation
- Explore :doc:`ast_structure` for AST organization details
