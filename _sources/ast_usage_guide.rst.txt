##################
AST Usage Guide
##################

This guide explains how to work with the PSS Abstract Syntax Tree (AST) generated
by the pssparser.

.. contents:: Table of Contents
   :local:
   :depth: 2

***************
Getting Started
***************

Basic Parsing
=============

To parse PSS code and generate an AST:

.. code-block:: python

    from zuspec.fe.pss import parser
    
    # Create a parser instance
    pss_parser = parser.Factory.inst().getParser()
    
    # Parse a PSS file
    ast_root = pss_parser.parse("""
        component my_comp {
            action my_action {
                rand int<8> value;
                
                constraint {
                    value >= 10;
                    value <= 100;
                }
            }
        }
    """, "inline.pss")
    
    # The result is a GlobalScope containing all declarations
    print(f"Parsed {len(ast_root.children)} top-level declarations")

Understanding the AST Structure
================================

The PSS AST follows a hierarchical structure:

* **GlobalScope** - Root of each parsed file
* **PackageScope** - Package declarations
* **TypeScope** - Types (Action, Component, Struct)
* **Scope** - Any node that can contain children
* **ScopeChild** - Base class for most AST nodes

Example hierarchy::

    GlobalScope (file root)
    └── PackageScope (package my_pkg)
        ├── Component (component my_comp)
        │   ├── Action (action my_action)
        │   │   ├── Field (rand int value)
        │   │   ├── ConstraintBlock (constraint)
        │   │   │   └── ConstraintStmtExpr (value >= 10)
        │   │   └── ActivityDecl (activity)
        │   │       └── ActivitySequence (...)
        │   └── Field (other fields)
        └── Struct (struct my_struct)

********************
Traversing the AST
********************

Simple Visitor Pattern
======================

Walk the entire AST tree:

.. code-block:: python

    def visit_node(node, depth=0):
        indent = "  " * depth
        print(f"{indent}{type(node).__name__}")
        
        # Visit children if this is a Scope
        if hasattr(node, 'children'):
            for child in node.children:
                visit_node(child, depth + 1)
    
    # Start from root
    visit_node(ast_root)

Finding Specific Nodes
======================

Find all actions in the AST:

.. code-block:: python

    from zuspec.fe.pss import ast
    
    def find_actions(node, actions=None):
        if actions is None:
            actions = []
        
        # Check if this node is an Action
        if isinstance(node, ast.Action):
            actions.append(node)
        
        # Recursively search children
        if hasattr(node, 'children'):
            for child in node.children:
                find_actions(child, actions)
        
        return actions
    
    # Find all actions
    all_actions = find_actions(ast_root)
    print(f"Found {len(all_actions)} actions")
    
    for action in all_actions:
        print(f"  Action: {action.name.id}")

Collecting Specific Information
================================

Extract all random fields from actions:

.. code-block:: python

    from zuspec.fe.pss import ast
    
    def collect_rand_fields(action):
        rand_fields = []
        for child in action.children:
            if isinstance(child, ast.Field):
                # Check if field has Rand attribute
                if child.attr & ast.FieldAttr.Rand:
                    rand_fields.append(child)
        return rand_fields
    
    # For each action, show random fields
    for action in all_actions:
        rand_fields = collect_rand_fields(action)
        print(f"Action {action.name.id} has {len(rand_fields)} random fields:")
        for field in rand_fields:
            print(f"  - {field.name.id}")

*********************
Working with Expressions
*********************

Expression Types
================

PSS expressions follow a class hierarchy:

* **Expr** - Base class for all expressions
* **ExprBin** - Binary operations (a + b, x > y)
* **ExprUnary** - Unary operations (!flag, -value)
* **ExprId** - Simple identifiers
* **ExprNumber** - Numeric literals
* **ExprBool**, **ExprString**, **ExprNull** - Other literals

Evaluating Simple Expressions
==============================

.. code-block:: python

    from zuspec.fe.pss import ast
    
    def describe_expr(expr):
        if isinstance(expr, ast.ExprNumber):
            return f"Number({expr.val})"
        elif isinstance(expr, ast.ExprBool):
            return f"Bool({expr.value})"
        elif isinstance(expr, ast.ExprId):
            return f"Identifier({expr.id})"
        elif isinstance(expr, ast.ExprBin):
            lhs = describe_expr(expr.lhs)
            rhs = describe_expr(expr.rhs)
            op = expr.op.name  # ExprBinOp enum
            return f"({lhs} {op} {rhs})"
        else:
            return f"{type(expr).__name__}"
    
    # Example: Describe constraint expressions
    for constraint_block in find_constraints(action):
        for stmt in constraint_block.children:
            if isinstance(stmt, ast.ConstraintStmtExpr):
                print(describe_expr(stmt.expr))

Building Expressions Programmatically
======================================

Create a new constraint expression:

.. code-block:: python

    from zuspec.fe.pss import ast, parser
    
    factory = parser.Factory.inst()
    
    # Create: value > 10
    lhs = factory.mkExprId("value")
    rhs = factory.mkExprNumber(10)
    comparison = factory.mkExprBin(lhs, ast.ExprBinOp.BinOp_Gt, rhs)
    
    # Wrap in constraint statement
    constraint_stmt = factory.mkConstraintStmtExpr(comparison)

*************************
Working with Activities
*************************

Activity Structure
==================

Activities define the control flow of actions:

* **ActivitySequence** - Sequential execution (default)
* **ActivityParallel** - Parallel execution with join
* **ActivitySchedule** - Flexible ordering
* **ActivitySelect** - Random branch selection
* **ActivityRepeatCount**, **ActivityRepeatWhile** - Loops
* **ActivityIfElse** - Conditionals

Analyzing Activity Flow
=======================

.. code-block:: python

    def analyze_activity(activity, depth=0):
        indent = "  " * depth
        
        if isinstance(activity, ast.ActivitySequence):
            print(f"{indent}Sequential execution:")
            for child in activity.children:
                analyze_activity(child, depth + 1)
        
        elif isinstance(activity, ast.ActivityParallel):
            join_type = type(activity.join_spec).__name__
            print(f"{indent}Parallel ({join_type}):")
            for child in activity.children:
                analyze_activity(child, depth + 1)
        
        elif isinstance(activity, ast.ActivityActionHandleTraversal):
            # Action invocation
            target = activity.target  # ExprRefPath
            print(f"{indent}Invoke action: {describe_expr(target)}")
        
        elif isinstance(activity, ast.ActivityRepeatCount):
            count = describe_expr(activity.count)
            print(f"{indent}Repeat {count} times:")
            analyze_activity(activity.body, depth + 1)
    
    # Analyze the activity block of an action
    for child in action.children:
        if isinstance(child, ast.ActivityDecl):
            print(f"Activity for {action.name.id}:")
            analyze_activity(child.activity)

*************************
Working with Constraints
*************************

Constraint Types
================

Constraints randomize fields within specified limits:

* **ConstraintStmtExpr** - Expression constraints (most common)
* **ConstraintStmtForeach** - Array element constraints
* **ConstraintStmtIf** - Conditional constraints
* **ConstraintStmtImplication** - Implication constraints (->)
* **ConstraintStmtUnique** - Uniqueness constraints

Analyzing Constraints
=====================

.. code-block:: python

    def analyze_constraints(action):
        print(f"Constraints in {action.name.id}:")
        
        for child in action.children:
            if isinstance(child, ast.ConstraintBlock):
                print(f"  Block: {child.name if hasattr(child, 'name') else 'anonymous'}")
                
                for stmt in child.children:
                    if isinstance(stmt, ast.ConstraintStmtExpr):
                        print(f"    Expression: {describe_expr(stmt.expr)}")
                    
                    elif isinstance(stmt, ast.ConstraintStmtForeach):
                        print(f"    Foreach constraint over array")
                        for inner in stmt.constraints:
                            if isinstance(inner, ast.ConstraintStmtExpr):
                                print(f"      {describe_expr(inner.expr)}")
                    
                    elif isinstance(stmt, ast.ConstraintStmtIf):
                        cond = describe_expr(stmt.cond)
                        print(f"    If ({cond}):")
                        # Analyze true/false branches...

***************************
PSS to AST Mapping Examples
***************************

This section shows how PSS constructs map to AST classes.

Action Declaration
==================

PSS Code:

.. code-block:: pss

    action my_action {
        rand int<8> value;
        
        constraint {
            value >= 10;
        }
        
        activity {
            do_something();
        }
    }

AST Structure:

.. code-block:: text

    Action (name="my_action")
    ├── Field (name="value", type=DataTypeInt, attr=Rand)
    ├── ConstraintBlock
    │   └── ConstraintScope
    │       └── ConstraintStmtExpr
    │           └── ExprBin (op=BinOp_Ge)
    │               ├── ExprId ("value")
    │               └── ExprNumber (10)
    └── ActivityDecl
        └── ActivitySequence
            └── ActivityActionHandleTraversal
                └── ExprRefPath ("do_something")

Parallel Activity
=================

PSS Code:

.. code-block:: pss

    parallel {
        action1;
        action2;
    }

AST Structure:

.. code-block:: text

    ActivityParallel
    ├── join_spec: ActivityJoinSpecNone
    ├── ActivityActionHandleTraversal ("action1")
    └── ActivityActionHandleTraversal ("action2")

Constraint with Foreach
========================

PSS Code:

.. code-block:: pss

    rand int arr[10];
    
    constraint {
        foreach (arr[i]) {
            arr[i] > 0;
        }
    }

AST Structure:

.. code-block:: text

    ConstraintStmtForeach
    ├── it: ConstraintStmtField (iterator)
    ├── idx: ConstraintStmtField (index variable)
    ├── expr: ExprId ("arr")
    └── constraints:
        └── ConstraintStmtExpr
            └── ExprBin (op=BinOp_Gt)
                ├── ExprSubscript (arr[i])
                └── ExprNumber (0)

**************
Advanced Topics
**************

Symbol Resolution
=================

After parsing, the AST can be "linked" to resolve symbol references:

.. code-block:: python

    from zuspec.fe.pss import linker
    
    # Create a linker
    pss_linker = linker.Factory.inst().mkLinker()
    
    # Link the AST (resolves all references)
    symbol_root = pss_linker.link([ast_root])
    
    # symbol_root is a RootSymbolScope with resolved references

The linked tree uses **SymbolScope** classes instead of regular scopes,
with efficient symbol lookup tables.

Modifying the AST
=================

You can programmatically modify the AST:

.. code-block:: python

    from zuspec.fe.pss import ast, parser
    
    factory = parser.Factory.inst()
    
    # Add a new field to an action
    new_field = factory.mkField(
        factory.mkExprId("new_value"),
        factory.mkDataTypeInt(True, None, None),  # signed int
        ast.FieldAttr.Rand,
        None  # no initializer
    )
    
    action.children.append(new_field)

Note: After modification, you may need to re-run the linker to update
symbol references.

Custom Visitors
===============

For complex traversals, implement a visitor class:

.. code-block:: python

    class ConstraintCollector:
        def __init__(self):
            self.constraints = []
        
        def visit(self, node):
            # Collect constraint expressions
            if isinstance(node, ast.ConstraintStmtExpr):
                self.constraints.append(node.expr)
            
            # Continue traversal
            if hasattr(node, 'children'):
                for child in node.children:
                    self.visit(child)
            
            # Handle other node types with children
            if isinstance(node, ast.ConstraintStmtForeach):
                for constraint in node.constraints:
                    self.visit(constraint)
        
        def collect(self, root):
            self.visit(root)
            return self.constraints
    
    # Use the visitor
    collector = ConstraintCollector()
    all_constraints = collector.collect(ast_root)
    print(f"Found {len(all_constraints)} constraint expressions")

**********
Best Practices
**********

1. **Always check node types** - Use `isinstance()` before accessing type-specific attributes
2. **Handle optional fields** - Many AST nodes have optional children (e.g., `init` expression on Field)
3. **Use factory methods** - When creating AST nodes, use the Factory class methods
4. **Understand scoping** - The `parent` pointer links child to parent, `children` links parent to children
5. **Preserve source locations** - When modifying AST, maintain `location` information for error reporting
6. **Link before analysis** - Symbol-dependent analysis should work on the linked SymbolScope tree

********************
Common Patterns
********************

Find All Declarations of a Type
================================

.. code-block:: python

    def find_all(root, node_type):
        results = []
        
        def visit(node):
            if isinstance(node, node_type):
                results.append(node)
            if hasattr(node, 'children'):
                for child in node.children:
                    visit(child)
        
        visit(root)
        return results
    
    # Find all actions
    actions = find_all(ast_root, ast.Action)
    
    # Find all constraints
    constraints = find_all(ast_root, ast.ConstraintBlock)

Get Qualified Name of a Node
=============================

.. code-block:: python

    def get_qualified_name(node):
        parts = []
        current = node
        
        while current is not None:
            if isinstance(current, (ast.NamedScope, ast.NamedScopeChild)):
                if hasattr(current, 'name') and current.name:
                    parts.append(current.name.id)
            current = current.parent
        
        return "::".join(reversed(parts))
    
    # Usage
    for action in actions:
        print(f"Action: {get_qualified_name(action)}")

*************
Error Handling
*************

The parser reports errors through a marker listener:

.. code-block:: python

    from zuspec.fe.pss import parser
    
    class ErrorCollector(parser.IMarkerListener):
        def __init__(self):
            self.errors = []
        
        def marker(self, m):
            self.errors.append({
                'severity': m.severity(),
                'message': m.msg(),
                'location': (m.location().lineno, m.location().linepos)
            })
    
    # Use custom error handler
    pss_parser = parser.Factory.inst().getParser()
    error_collector = ErrorCollector()
    pss_parser.getMarkerListener().addListener(error_collector)
    
    # Parse (errors will be collected)
    ast_root = pss_parser.parse(pss_code, filename)
    
    # Check for errors
    if error_collector.errors:
        print(f"Found {len(error_collector.errors)} errors:")
        for error in error_collector.errors:
            print(f"  Line {error['location'][0]}: {error['message']}")

***********
Next Steps
***********

- Read the :doc:`reference_api_docs` for detailed class documentation
- Explore the :doc:`ast_structure` for physical vs logical AST organization
- See :doc:`pss30_api` for PSS 3.0 specific features
