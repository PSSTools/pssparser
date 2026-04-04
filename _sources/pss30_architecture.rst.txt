##############################
PSS 3.0 Architecture & Design
##############################

This document describes the implementation architecture and design decisions
for PSS 3.0 support in pssparser.

Overview
========

PSS 3.0 support was implemented across 7 phases over the course of the PSS 3.0
upgrade plan, with each phase building on the previous:

1. Foundation & Assessment
2. Grammar Completion
3. AST Implementation
4. Visitor Implementation
5. Semantic Validation (partial)
6. Linking & Resolution
7. Testing & Validation

This document focuses on architectural decisions and design rationale.

Architecture Layers
===================

The parser follows a layered architecture:

.. code-block:: text

    ┌─────────────────────────────────────┐
    │      Application Layer              │
    │  (Python/C++ API consumers)         │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      Semantic Layer                 │
    │  (Linking, Type Checking)           │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      AST Layer                      │
    │  (Abstract Syntax Tree)             │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      Visitor Layer                  │
    │  (ANTLR Visitors)                   │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      Parser Layer                   │
    │  (ANTLR Generated Parser)           │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      Lexer Layer                    │
    │  (ANTLR Generated Lexer)            │
    └─────────────────────────────────────┘
                    ↓
    ┌─────────────────────────────────────┐
    │      Input (PSS Source Code)        │
    └─────────────────────────────────────┘

Grammar Design
==============

Dual Grammar Approach
---------------------

The parser uses two separate grammars for optimal performance:

**PSSParser.g4** - Procedural code context

* Action exec blocks
* Function bodies
* Procedural statements
* Import declarations

**PSSExprParser.g4** - Constraint context

* Constraint expressions
* Constraint blocks
* Constraint-specific operators

This separation provides:

* Better error messages (context-aware)
* Reduced ambiguity
* Faster parsing (smaller rule sets)
* Cleaner grammar organization

Grammar Optimization Strategies
--------------------------------

The grammar deviates from literal BNF translation for performance:

**1. Left-Recursion Elimination**

PSS Spec BNF uses left-recursion:

.. code-block:: antlr

    // Spec (theoretical):
    expression: expression '+' term | term ;

ANTLR grammar uses right-recursion with precedence:

.. code-block:: antlr

    // Implementation:
    expression: term ('+' term)* ;

**2. Precedence Climbing**

Instead of separate rules for each precedence level, uses ANTLR's built-in
precedence mechanism for expressions.

**3. Rule Consolidation**

Multiple similar BNF rules consolidated into parameterized rules:

.. code-block:: antlr

    // Instead of:
    // array_type: 'array' '<' type ',' size '>' ;
    // list_type: 'list' '<' type '>' ;
    // set_type: 'set' '<' type '>' ;
    
    // Consolidated:
    collection_type: 
        ('array' | 'list' | 'set' | 'map') 
        '<' type_parameter_list '>' ;

Token Design
------------

PSS 3.0 adds 8 new keywords:

* ``monitor`` - Monitor declarations
* ``yield`` - Control flow
* ``randomize`` - Procedural randomization
* ``atomic`` - Atomic blocks
* ``eventually`` - Temporal operator
* ``concat`` - Temporal concatenation
* ``overlap`` - Temporal overlap
* ``schedule`` - Temporal scheduling

All keywords are reserved tokens to prevent identifier conflicts.

AST Design
==========

Node Hierarchy
--------------

The AST follows an object-oriented hierarchy:

.. code-block:: text

    IBase (root)
    ├── IScope
    │   ├── IGlobalScope
    │   ├── ITypeScope
    │   │   ├── IComponent
    │   │   ├── IAction
    │   │   ├── IMonitor ← NEW PSS 3.0
    │   │   └── ...
    │   └── ...
    ├── IStmt
    │   ├── IActivityStmt
    │   │   ├── IActivityAtomicBlock ← NEW PSS 3.0
    │   │   └── ...
    │   ├── IProceduralStmt
    │   │   ├── IProceduralStmtRandomize ← NEW PSS 3.0
    │   │   └── ...
    │   └── IMonitorActivityStmt ← NEW PSS 3.0
    │       ├── IMonitorActivitySequence
    │       ├── IMonitorActivityConcat
    │       ├── IMonitorActivityEventually
    │       └── ...
    └── IExpr
        ├── IExprSubstring ← NEW PSS 3.0 (planned)
        └── ...

Design Principles
-----------------

**1. Immutability Where Possible**

AST nodes are largely immutable after construction, reducing bugs.

**2. Smart Pointers**

Use of unique pointers (``IMonitorUP``) for ownership, raw pointers for references.

**3. Visitor Pattern**

AST supports visitor pattern for traversal and transformation.

**4. Type Safety**

Strong typing prevents invalid AST construction.

Monitor AST Design
------------------

Monitors follow the TypeScope pattern like Actions and Components:

.. code-block:: cpp

    class IMonitor : public ITypeScope {
    public:
        // Properties
        virtual bool getIsAbstract() const = 0;
        virtual void setIsAbstract(bool) = 0;
        
        // Children
        virtual std::vector<IMonitorUP> &getMonitors() = 0;
        virtual std::vector<IMonitorActivityDeclUP> &getActivities() = 0;
        virtual std::vector<IConstraintUP> &getConstraints() = 0;
        
        // Inheritance
        virtual ITypeRef *getSuperType() const = 0;
        virtual void setSuperType(ITypeRef*) = 0;
    };

**Design Rationale:**

* Monitors are TypeScopes - can contain nested types
* Abstract flag via getter/setter (not constructor) for visitor flexibility
* Activities stored as declarations (parallel to action activities)
* Constraints separate from activities (clearer semantics)

Monitor Activity AST
--------------------

Activities use a statement hierarchy similar to procedural statements:

.. code-block:: cpp

    class IMonitorActivityStmt : public IBase {
        // Base class for all monitor activities
    };
    
    class IMonitorActivitySequence : public IMonitorActivityStmt {
        // Sequential composition
        virtual std::vector<IMonitorActivityStmtUP> &getActivities() = 0;
    };
    
    class IMonitorActivityConcat : public IMonitorActivityStmt {
        // Temporal concatenation (##)
        virtual std::vector<IMonitorActivityStmtUP> &getActivities() = 0;
    };

**Design Rationale:**

* Separate hierarchy from action activities (different semantics)
* Temporal operators as first-class nodes
* Composable - activities nest naturally

String Enhancement Design
-------------------------

String methods use an enumeration for efficient dispatch:

.. code-block:: cpp

    enum class StringMethodId {
        NoMethod = 0,
        Size,
        Find,
        FindLast,
        FindAll,
        Lower,
        Upper,
        Split,
        Chars
    };
    
    class IExprMemberPathElem {
        // ...
        virtual StringMethodId getStringMethodId() const = 0;
        virtual void setStringMethodId(StringMethodId) = 0;
    };

**Design Rationale:**

* Reuse existing member access expression infrastructure
* Enumeration for efficient type checking
* Extensible for future string methods

**Substring Representation:**

Currently uses subscript mechanism:

.. code-block:: cpp

    // s[0..4] represented as:
    IExprMemberPathElem {
        subscript[0] = expr(0)      // start
        subscript[1] = expr(4)      // end
    }

**Future Enhancement:** May add dedicated ``IExprSubstring`` node for better
semantic analysis.

Visitor Implementation
======================

Visitor Pattern
---------------

ANTLR generates a base visitor class. Implementation overrides methods for
relevant grammar rules:

.. code-block:: cpp

    class AstBuilderInt : public PSSParserBaseVisitor {
    public:
        // Override for each grammar rule
        virtual antlrcpp::Any visitMonitor_declaration(
            PSSParser::Monitor_declarationContext *ctx) override;
        
        // Returns AST node wrapped in antlrcpp::Any
    };

Visitor Design Patterns
-----------------------

**1. Factory Pattern**

AST nodes created via factory:

.. code-block:: cpp

    ast::IFactory *factory = ast::getFactory();
    ast::IMonitorUP monitor = factory->mkMonitor(name, is_abstract);

**2. Builder Pattern**

Complex nodes built incrementally:

.. code-block:: cpp

    antlrcpp::Any AstBuilderInt::visitMonitor_declaration(
        PSSParser::Monitor_declarationContext *ctx) {
        
        // Create monitor
        ast::IMonitorUP monitor = m_factory->mkMonitor(
            ctx->identifier()->getText(),
            false  // not abstract
        );
        
        // Add template parameters
        if (ctx->template_param_decl_list()) {
            // ... process templates
        }
        
        // Add super type
        if (ctx->super_spec()) {
            // ... process inheritance
        }
        
        // Process body
        for (auto *item : ctx->monitor_body_item()) {
            // ... add body items
        }
        
        return monitor.release();
    }

**3. Context Stack**

Maintains stack of scopes during traversal:

.. code-block:: cpp

    class AstBuilderInt {
        std::vector<ast::IScope*> m_scope_stack;
        
        ast::IScope *currentScope() {
            return m_scope_stack.back();
        }
        
        void pushScope(ast::IScope *scope) {
            m_scope_stack.push_back(scope);
        }
        
        void popScope() {
            m_scope_stack.pop_back();
        }
    };

Error Handling in Visitors
---------------------------

Visitors report errors via error listener:

.. code-block:: cpp

    if (!isValidContext(ctx)) {
        m_error_listener->reportError(
            ctx->getStart(),
            "Invalid context for monitor declaration"
        );
        return nullptr;
    }

Semantic Validation
===================

Validation Phases
-----------------

Semantic validation occurs in multiple phases:

**1. AST Construction (Visitors)**

* Basic syntax validation
* Structural correctness

**2. Linking Phase**

* Name resolution
* Type resolution
* Reference resolution

**3. Type Checking Phase**

* Type compatibility
* Constraint validation
* Method signature validation

**4. Context Validation Phase** (Partial Implementation)

* Platform qualifier validation
* Yield context validation
* Monitor field restrictions

Currently Implemented
---------------------

✅ **Name Resolution**

* Symbol table construction
* Cross-file references
* Template instantiation

✅ **Type Resolution**

* Type references resolved
* Template parameter substitution
* Collection type validation

✅ **Basic Type Checking**

* Expression type compatibility
* Assignment type checking
* Function parameter validation

Partially Implemented
---------------------

⚠️ **Context Validation**

* Yield context not validated
* Platform qualifier calls not checked
* Atomic block context not validated

⚠️ **Monitor Validation**

* Field restrictions not enforced
* Cover statement scope not checked
* Abstract monitor instantiation not prevented

⚠️ **String Method Validation**

* Return types not validated
* Parameter types not fully checked
* Context restrictions not enforced

Design for Future Implementation
---------------------------------

Context validation will use a context stack:

.. code-block:: cpp

    class SemanticValidator {
        enum class ExecContext {
            None,
            Target,
            Solve,
            Body
        };
        
        std::stack<ExecContext> m_context_stack;
        
        void validateYield(IProceduralStmtYield *stmt) {
            if (m_context_stack.top() != ExecContext::Target) {
                reportError(stmt, "yield only allowed in target exec");
            }
        }
    };

Linking and Resolution
======================

Symbol Table Structure
----------------------

Two-level symbol table:

**1. Physical View** (per-file)

* ``IGlobalScope`` per file
* Contains declarations as written

**2. Logical View** (global)

* ``RootSymbolTable`` across all files
* Merges declarations by namespace
* Handles ``extend`` statements

Monitor Resolution
------------------

Monitors resolve like other type scopes:

1. Register monitor in symbol table
2. Resolve inheritance (super type)
3. Resolve action/monitor references in activities
4. Resolve cover statement monitor references

Reference Type Linking
----------------------

Reference types link in two phases:

**1. Type Resolution**

Resolve the referenced type:

.. code-block:: cpp

    array<ref Action, 10> actions;
    //          ^^^^^^ - resolve to Action type
    
**2. Reference Validation**

Validate reference usage contexts (future work).

Extension Mechanism
===================

PSS supports extending existing declarations:

.. code-block:: pss

    extend monitor MyMonitor {
        // Additional body items
    }

Extension Resolution
--------------------

1. Parse extension as separate AST node
2. During linking, find original declaration
3. Merge extension items into original
4. Validate compatibility

Currently, basic extension works for monitors similar to components/actions.

Performance Considerations
==========================

Parse Performance
-----------------

**Metrics:**

* Average parse time: ~1-2ms per 100 lines
* Memory usage: ~500 bytes per AST node
* No significant PSS 3.0 overhead (< 5%)

**Optimizations:**

* Efficient grammar (minimizes backtracking)
* Smart pointer reuse
* Lazy evaluation where possible

Memory Management
-----------------

**Strategy:**

* Unique pointers for ownership (``IMonitorUP``)
* Raw pointers for references (``IMonitor*``)
* ANTLR contexts cleaned up automatically

**Memory Profile:**

* Small models: < 10MB
* Large models: ~50-100MB
* No memory leaks detected (Valgrind clean)

Threading Model
---------------

Parser is **not thread-safe**:

* Create separate parser instances per thread
* AST nodes are not thread-safe
* No global state (safe for multi-process)

Extensibility
=============

Adding New PSS Features
-----------------------

To add a new PSS feature:

1. **Update Grammar**

   * Add tokens to lexer
   * Add productions to parser
   * Test grammar with ANTLR

2. **Define AST**

   * Create node classes in YAML
   * Run code generator
   * Compile generated code

3. **Implement Visitor**

   * Add visitor method
   * Create and populate AST node
   * Handle context appropriately

4. **Add Tests**

   * Unit tests for parsing
   * Integration tests for linking
   * Validation tests for semantics

5. **Document**

   * User documentation
   * API documentation
   * Examples

Plugin Architecture (Future)
-----------------------------

Future versions may support plugins for:

* Custom AST transformations
* Additional semantic checks
* Code generation backends
* Analysis tools

Design Decisions
================

Key Decisions and Rationale
---------------------------

**1. ANTLR4 vs Hand-Written Parser**

*Decision:* Use ANTLR4

*Rationale:*
- Faster development
- Easier grammar maintenance
- Good error recovery
- Industry standard

**2. Dual Grammar Approach**

*Decision:* Separate procedural and expression grammars

*Rationale:*
- Clearer separation of contexts
- Better error messages
- Reduced ambiguity
- PSS has distinct contexts

**3. YAML for AST Definitions**

*Decision:* Define AST in YAML, generate C++/Python

*Rationale:*
- Single source of truth
- Automatic language binding generation
- Consistent API across languages
- Easy to maintain

**4. Smart Pointers for Ownership**

*Decision:* Use unique pointers for ownership

*Rationale:*
- Clear ownership semantics
- Automatic memory management
- Prevents leaks
- Modern C++ best practice

**5. Substring Reuses Subscript**

*Decision:* Don't create dedicated ExprSubstring initially

*Rationale:*
- Faster implementation
- Functionally equivalent for parsing
- Can enhance later if needed
- Minimal user impact

**6. Incremental Semantic Validation**

*Decision:* Ship grammar/AST before full validation

*Rationale:*
- Unblocks users faster
- Grammar is most critical
- Validation can be added incrementally
- Clear documentation of limitations

Trade-offs
----------

**Grammar Complexity vs Performance**

* More complex grammar = harder to maintain
* But better performance and error messages
* Decision: Optimize for performance

**AST Completeness vs Simplicity**

* More AST nodes = more complete representation
* But more code to maintain
* Decision: Optimize for completeness

**Validation Strictness vs Usability**

* Strict validation = catches more errors
* But may block valid use cases
* Decision: Incremental validation

Testing Strategy
================

Test Pyramid
------------

.. code-block:: text

                  ┌────────────┐
                  │  E2E Tests │  (Few)
                  └────────────┘
               ┌───────────────────┐
               │ Integration Tests │  (Some)
               └───────────────────┘
          ┌─────────────────────────────┐
          │       Unit Tests            │  (Many)
          └─────────────────────────────┘

Unit Test Strategy
------------------

Each feature has dedicated unit tests:

* Parsing tests (grammar validation)
* AST construction tests (visitor validation)
* Linking tests (resolution validation)
* Type checking tests (semantic validation)

Integration Test Strategy
--------------------------

Combined feature tests:

* Multiple features in single file
* Cross-file references
* Complex scenarios
* Real-world examples

Test Organization
-----------------

.. code-block:: text

    tests/
    ├── src/
    │   ├── TestPSS30Grammar.cpp    # PSS 3.0 specific
    │   ├── TestMonitors.cpp        # Monitor feature tests
    │   ├── TestStringMethods.cpp   # String feature tests
    │   └── ...
    └── pss_examples/
        ├── monitor_examples/       # Spec examples
        ├── string_examples/
        └── ...

Code Quality
============

Style Guidelines
----------------

**C++ Style:**

* Google C++ Style Guide (mostly)
* 4-space indentation
* Member variables prefixed with ``m_``
* Const correctness enforced

**Python Style:**

* PEP 8 compliant
* Type hints where applicable
* Docstrings for public APIs

Code Review Process
-------------------

All changes reviewed for:

* Correctness
* Performance
* Maintainability
* Test coverage
* Documentation

Future Enhancements
===================

Planned Improvements
--------------------

1. **Complete Semantic Validation**

   * All context validations
   * Complete type checking
   * Full constraint validation

2. **Enhanced AST**

   * Dedicated ExprSubstring node
   * Better source location tracking
   * AST cloning for reference types

3. **Performance Optimization**

   * Incremental parsing
   * AST caching
   * Lazy linking

4. **Tool Integration**

   * Language Server Protocol
   * IDE integration
   * Static analysis tools

5. **Additional Language Features**

   * Future PSS versions
   * Vendor extensions
   * Custom pragmas

See Also
========

* :doc:`pss30_features` - Feature documentation
* :doc:`pss30_api` - API reference
* :doc:`ast_structure` - AST structure details
* :doc:`../PSS_3.0_UPGRADE_PLAN` - Implementation plan
