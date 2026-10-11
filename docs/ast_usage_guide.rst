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

    from pssparser import Parser

    pss_parser = Parser()

    # parse()/parses() return a bool -- they do NOT return the AST.
    # parse()  takes a list of file paths.
    # parses() takes a list of (filename, source-text) pairs.
    pss_parser.parses([("inline.pss", """
        component my_comp {
            action my_action {
                rand bit[8] value;

                constraint {
                    value >= 10;
                    value <= 100;
                }
            }
        }
    """)])

    # The AST comes from link(), which returns the linked RootSymbolScope.
    root = pss_parser.link()

    # Each parsed file is a GlobalScope unit under the root. Units with a
    # fileid of 0 or -1 are the standard library and the built-ins.
    for i in range(root.numUnits()):
        unit = root.getUnit(i)
        if unit.getFileid() in pss_parser.file_map:
            print(f"{pss_parser.file_map[unit.getFileid()]}: "
                  f"{unit.numChildren()} top-level declarations")

.. note::

   Both phases raise ``ParseException`` when they produce error markers, so
   wrap them in ``try``/``except`` if you want to inspect a model that does
   not parse cleanly.  The exception carries the markers on its ``.markers``
   attribute.

Working with a model that failed to link
----------------------------------------

A caught ``ParseException`` from ``link()`` still leaves a usable model. The
Parser records its result before reporting the failure, so ``user_units()``,
``file_map`` and ``root`` are all populated:

.. code-block:: python

   try:
       root = pss_parser.link()
   except ParseException as e:
       # Degraded, but not empty.
       for unit in pss_parser.user_units():
           path = pss_parser.file_map[unit.getFileid()]
           ...

What this gives you is the **per-file view**: every declaration in every file,
with its location and its doc comment. That is enough to document or index a
model with one bad type reference in it.

What it does not give you is a trustworthy **cross-file view**. A link error
means exactly that some cross-file question could not be answered: a type
reference may be unresolved, and ``extend`` bodies may not have been merged
into their targets. Treat inherited members, resolved type targets and
extension contributions as unavailable on this path.

Before this behavior existed, a caught link failure left ``user_units()``
returning ``[]`` and ``file_map`` empty, and the only way to recover a
degraded view was to parse the sources a second time into a Parser that is
never linked.

.. warning::

   ``Parser.link()`` transfers ownership of each ``GlobalScope`` to the
   returned root, and drops its own references.  Do not hold a ``GlobalScope``
   obtained before ``link()`` and use it afterwards -- the wrapper becomes a
   second owner of the same memory and will crash the interpreter.  Reach the
   units through ``root.getUnit(i)``, as above, or through
   ``Parser.user_units()``, which does this for you and filters out the
   library units.

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
        if hasattr(node, 'getChildren'):
            for child in node.getChildren():
                visit_node(child, depth + 1)
    
    # Start from root
    visit_node(ast_root)

Finding Specific Nodes
======================

Find all actions in the AST:

.. code-block:: python

    import pssparser.ast as ast
    
    def find_actions(node, actions=None):
        if actions is None:
            actions = []
        
        # Check if this node is an Action
        if isinstance(node, ast.Action):
            actions.append(node)
        
        # Recursively search children
        if hasattr(node, 'getChildren'):
            for child in node.getChildren():
                find_actions(child, actions)
        
        return actions
    
    # Find all actions
    all_actions = find_actions(ast_root)
    print(f"Found {len(all_actions)} actions")
    
    for action in all_actions:
        print(f"  Action: {action.getName().getId()}")

Collecting Specific Information
================================

Extract all random fields from actions:

.. code-block:: python

    import pssparser.ast as ast
    
    def collect_rand_fields(action):
        rand_fields = []
        for child in action.getChildren():
            if isinstance(child, ast.Field):
                # Check if field has Rand attribute
                if child.getAttr() & ast.FieldAttr.Rand:
                    rand_fields.append(child)
        return rand_fields
    
    # For each action, show random fields
    for action in all_actions:
        rand_fields = collect_rand_fields(action)
        print(f"Action {action.getName().getId()} has {len(rand_fields)} random fields:")
        for field in rand_fields:
            print(f"  - {field.getName().getId()}")

************************
Working with Expressions
************************

Expression Types
================

PSS expressions follow a class hierarchy:

* **Expr** - Base class for all expressions
* **ExprBin** - Binary operations (a + b, x > y)
* **ExprUnary** - Unary operations (!flag, -value)
* **ExprId** - Simple identifiers
* **ExprRefPathContext** - A reference such as ``value`` or ``a.b`` (a list
  of path elements)
* **ExprNumber** - Numeric literals: **ExprUnsignedNumber** and
  **ExprSignedNumber**
* **ExprBool**, **ExprString**, **ExprNull** - Other literals

Every class and its fields are in the :doc:`ast/expr` reference.

Evaluating Simple Expressions
==============================

.. code-block:: python

    import pssparser.ast as ast
    
    def describe_expr(expr):
        if isinstance(expr, (ast.ExprUnsignedNumber, ast.ExprSignedNumber)):
            return f"Number({expr.getValue()})"
        elif isinstance(expr, ast.ExprBool):
            return f"Bool({expr.getValue()})"
        elif isinstance(expr, ast.ExprId):
            return f"Identifier({expr.getId()})"
        elif isinstance(expr, ast.ExprRefPathContext):
            names = [e.getId().getId() for e in expr.getHier_id().getElems()]
            return f"Ref({'.'.join(names)})"
        elif isinstance(expr, ast.ExprBin):
            lhs = describe_expr(expr.getLhs())
            rhs = describe_expr(expr.getRhs())
            op = ast.ExprBinOp(expr.getOp()).name  # an int; wrap to name it
            return f"({lhs} {op} {rhs})"
        else:
            return f"{type(expr).__name__}"
    
    # Example: Describe constraint expressions
    for child in action.getChildren():
        if isinstance(child, ast.ConstraintBlock):
            for stmt in child.getConstraints():
                if isinstance(stmt, ast.ConstraintStmtExpr):
                    print(describe_expr(stmt.getExpr()))

Building Expressions Programmatically
======================================

``pssparser.ast.Factory.inst()`` has a ``mk<Class>()`` method for every
class (``mkExprBin(lhs, op, rhs)``, ``mkExprId(id, is_escaped)``, ...), but
building a tree with them from Python is **not safe** in this release: a node
passed into a factory method stays owned by its Python object as well as by
its new parent, so it is freed twice, and passing ``None`` for an optional
node argument crashes. Both are known issue AB-2 in
``docs/design/known-issues.md``. Build trees in C++ (``IFactory``), or
generate PSS text and parse it.

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
            for child in activity.getChildren():
                analyze_activity(child, depth + 1)
        
        elif isinstance(activity, ast.ActivityParallel):
            join_type = type(activity.getJoin_spec()).__name__
            print(f"{indent}Parallel ({join_type}):")
            for child in activity.getChildren():
                analyze_activity(child, depth + 1)
        
        elif isinstance(activity, ast.ActivityActionHandleTraversal):
            # Action invocation
            target = activity.getTarget()  # ExprRefPathContext
            print(f"{indent}Invoke action: {describe_expr(target)}")
        
        elif isinstance(activity, ast.ActivityRepeatCount):
            count = describe_expr(activity.getCount())
            print(f"{indent}Repeat {count} times:")
            analyze_activity(activity.getBody(), depth + 1)
    
    # Analyze the activity block of an action: an ActivityDecl is a scope
    # whose children are the activity's statements
    for child in action.getChildren():
        if isinstance(child, ast.ActivityDecl):
            print(f"Activity for {action.getName().getId()}:")
            for stmt in child.getChildren():
                analyze_activity(stmt, 1)

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
        print(f"Constraints in {action.getName().getId()}:")
        
        for child in action.getChildren():
            if isinstance(child, ast.ConstraintBlock):
                name = child.getName()
                print(f"  Block: {name.getId() if name is not None else 'anonymous'}")
                
                # A constraint block holds its statements in `constraints`,
                # not `children`
                for stmt in child.getConstraints():
                    if isinstance(stmt, ast.ConstraintStmtExpr):
                        print(f"    Expression: {describe_expr(stmt.getExpr())}")
                    
                    elif isinstance(stmt, ast.ConstraintStmtForeach):
                        print(f"    Foreach constraint over array")
                        for inner in stmt.getConstraints():
                            if isinstance(inner, ast.ConstraintStmtExpr):
                                print(f"      {describe_expr(inner.getExpr())}")
                    
                    elif isinstance(stmt, ast.ConstraintStmtIf):
                        cond = describe_expr(stmt.getCond())
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
                └── ExprNumber (0)

***************
Advanced Topics
***************

Symbol Resolution
=================

After parsing, the AST can be "linked" to resolve symbol references:

.. code-block:: python

    from pssparser import Parser
    
    p = Parser()
    p.parses([("m.pss", "component pss_top { action a { } }")])
    
    # Link every parsed file (resolves all references)
    symbol_root = p.link()
    
    # symbol_root is a RootSymbolScope with resolved references;
    # p.user_units() are the per-file GlobalScopes

The linked tree uses **SymbolScope** classes instead of regular scopes,
with efficient symbol lookup tables.

Modifying the AST
=================

The same applies to modifying a parsed tree from Python: adding a node made
with the factory (``scope.addChild(node)``) leaves it with two owners (known
issue AB-2). Modify the tree in C++, or edit the source and parse again.

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
                self.constraints.append(node.getExpr())
            
            # Continue traversal
            if hasattr(node, 'getChildren'):
                for child in node.getChildren():
                    self.visit(child)
            
            # Constraint blocks and foreach hold their statements in
            # `constraints`, not `children`
            if isinstance(node, ast.ConstraintScope):
                for constraint in node.getConstraints():
                    self.visit(constraint)
        
        def collect(self, root):
            self.visit(root)
            return self.constraints
    
    # Use the visitor
    collector = ConstraintCollector()
    all_constraints = collector.collect(ast_root)
    print(f"Found {len(all_constraints)} constraint expressions")

**************
Best Practices
**************

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
            if hasattr(node, 'getChildren'):
                for child in node.getChildren():
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
                if current.getName() is not None:
                    parts.append(current.getName().getId())
            current = current.getParent()
        
        return "::".join(reversed(parts))
    
    # Usage
    for action in actions:
        print(f"Action: {get_qualified_name(action)}")

**************
Error Handling
**************

The parser reports errors as markers: ``p.markers`` is a list of dicts
(``severity``, ``message``, ``file``, ``line``, ``col``, and ``code`` when
the message has an ID). A parse or link with errors raises
``ParseException``, which carries the same list:

.. code-block:: python

    from pssparser import Parser, ParseException
    
    p = Parser()
    try:
        p.parses([("bad.pss", "component pss_top { action a { rand bit[8] x } }")])
    except ParseException as e:
        print(f"Found {len(e.markers)} errors:")
        for m in e.markers:
            print(f"  Line {m['line']}: {m['message']}")

*****************************
Coverage Gaps and ``PSSP101``
*****************************

A clean parse does not, on its own, mean the AST holds everything the source
said. Some constructs are accepted by the grammar but are not built into the
AST -- or are built with part of what was written dropped. Walking the AST for
one of those constructs finds nothing, and no error explains why.

Every such site now emits ``PSSP101`` as a warning:

.. code-block:: text

   `override` is accepted but not represented in the AST
   `randomize` is accepted but not represented in the AST: the `with` constraints are dropped

The first form means nothing is built for the construct. The second means a
node *is* built, and the text after the colon names the part that is lost.

``PSSP101`` is not a problem with the input -- the source is legal PSS, and
there is nothing to fix in it. It is a front-end gap. Treat it as a warning
about your own analysis: if you are looking for the named construct, this file
will not show it to you. If the construct is not material to what you are
doing, the marker can be suppressed like any other.

The standard library itself uses some of these constructs; ``PSSP101`` is
suppressed while loading it, so the marker only ever refers to your source.

The catalogue of affected constructs is in ``docs/ast-coverage-gaps.md``, and
``docs/ast-coverage-plan.md`` tracks the work to close them. As each construct
is implemented, its ``PSSP101`` disappears -- so the set of markers a file
produces is a live measure of what the AST does not yet carry.

***********
Next Steps
***********

- Read the :doc:`reference_api_docs` for detailed class documentation
- Explore the :doc:`ast_structure` for physical vs logical AST organization
- See :doc:`pss30_api` for PSS 3.0 specific features
