############################
PSS 3.0 Migration Guide
############################

This guide helps users migrate from PSS 2.x to PSS 3.0 with pssparser.

Backward Compatibility
======================

PSS 3.0 is designed to be largely backward compatible with PSS 2.x. Existing
PSS 2.x code should continue to work without modification in most cases.

Breaking Changes
================

Reserved Keywords
-----------------

The following keywords are newly reserved in PSS 3.0:

* ``monitor`` - Used for behavioral coverage
* ``yield`` - Control flow in target execution
* ``randomize`` - Procedural randomization
* ``atomic`` - Atomic activity blocks
* ``eventually`` - Monitor temporal operator
* ``concat`` - Monitor temporal concatenation
* ``overlap`` - Monitor temporal overlap
* ``schedule`` - Monitor temporal scheduling

**Action Required**: If your PSS 2.x code uses any of these as identifiers,
you must rename them.

.. code-block:: pss

    // PSS 2.x - May need updating if 'monitor' is used as identifier
    action monitor { }  // ERROR in PSS 3.0
    
    // PSS 3.0 - Use different identifier
    action monitor_action { }  // OK

New Features
============

Monitors for Behavioral Coverage
---------------------------------

PSS 3.0 introduces monitors as a first-class construct for behavioral coverage.
This replaces ad-hoc coverage approaches.

**PSS 2.x Approach** (manual coverage):

.. code-block:: pss

    component pss_top {
        action A { }
        action B { }
        
        // Manual tracking via constraints or actions
        covergroup my_coverage {
            // Manual coverage points
        }
    }

**PSS 3.0 Approach** (monitors):

.. code-block:: pss

    monitor SequenceMonitor {
        activity {
            concat {
                A;
                B;
            }
        }
    }
    
    component pss_top {
        action A { }
        action B { }
        
        cover SequenceMonitor;
    }

**Migration Strategy**:

1. Identify behavioral patterns you're tracking manually
2. Create monitor declarations for those patterns
3. Use cover statements to instantiate monitors
4. Remove manual coverage tracking code

String Enhancements
-------------------

PSS 3.0 adds built-in string methods and substring operator.

**PSS 2.x Approach** (limited string operations):

.. code-block:: pss

    // String operations were limited
    action my_action {
        string s = "hello";
        // No way to get length, search, or manipulate strings
    }

**PSS 3.0 Approach** (rich string API):

.. code-block:: pss

    action my_action {
        string s = "hello world";
        
        int len = s.size();              // 11
        int idx = s.find("world");       // 6
        string sub = s[0..4];            // "hello"
        string upper_s = s.upper();      // "HELLO WORLD"
    }

**Migration Strategy**:

1. Review string handling code
2. Replace workarounds with built-in methods
3. Use substring operator for extraction
4. Leverage string methods in constraints

Reference Collections
---------------------

PSS 3.0 allows reference types in collections.

**PSS 2.x Approach** (handles only):

.. code-block:: pss

    component pss_top {
        pool[10] A actions;
        
        // No direct collection of references
    }

**PSS 3.0 Approach** (explicit reference collections):

.. code-block:: pss

    component pss_top {
        action A { }
        
        array<ref A, 10> action_refs;
        list<ref A> action_list;
        map<string, ref A> action_map;
    }

**Migration Strategy**:

1. Identify action handle usage patterns
2. Consider using explicit reference collections
3. Leverage null reference capability for optional references

Procedural Randomization
-------------------------

PSS 3.0 adds ``randomize`` statement for procedural randomization.

**PSS 2.x Approach** (declarative only):

.. code-block:: pss

    action my_action {
        rand int x;
        
        constraint {
            x > 0;
            x < 100;
        }
    }

**PSS 3.0 Approach** (procedural randomization):

.. code-block:: pss

    action my_action {
        int x;  // Non-rand field
        
        exec body {
            randomize(x) {
                x > 0;
                x < 100;
            }
        }
    }

**Migration Strategy**:

1. Identify cases where procedural randomization is beneficial
2. Use ``randomize`` for dynamic constraint-based randomization
3. Keep declarative ``rand`` for static randomization

Activity Atomic Blocks
-----------------------

PSS 3.0 adds ``atomic`` blocks for atomic activity execution.

**PSS 2.x Approach** (no atomic guarantee):

.. code-block:: pss

    action my_action {
        activity {
            // No way to guarantee atomic execution
            do A;
            do B;
        }
    }

**PSS 3.0 Approach** (explicit atomic):

.. code-block:: pss

    action my_action {
        activity {
            atomic {
                do A;
                do B;
            }
        }
    }

**Migration Strategy**:

1. Identify activities that require atomic execution
2. Wrap them in ``atomic`` blocks
3. Document atomicity requirements

Yield Statements
----------------

PSS 3.0 adds ``yield`` for explicit scheduling points in target execution.

**PSS 2.x Approach** (implicit scheduling):

.. code-block:: pss

    action my_action {
        exec target {
            // Scheduler decides when to suspend
        }
    }

**PSS 3.0 Approach** (explicit yield):

.. code-block:: pss

    action my_action {
        exec target {
            // Do work
            yield;  // Explicit scheduling point
            // Continue work
        }
    }

**Migration Strategy**:

1. Identify long-running target exec blocks
2. Insert ``yield`` statements at appropriate points
3. Test scheduling behavior

Platform Qualifiers
-------------------

PSS 3.0 adds ``target`` and ``solve`` qualifiers for functions.

**PSS 2.x Approach** (no context specification):

.. code-block:: pss

    import function int utility_func(int x);

**PSS 3.0 Approach** (explicit context):

.. code-block:: pss

    import target function int read_hw(int addr);
    import solve function int compute_value(int x);
    import target solve function int utility_func(int x);

**Migration Strategy**:

1. Review imported functions
2. Add appropriate platform qualifiers
3. Validate usage contexts

Common Migration Patterns
==========================

Pattern 1: Coverage to Monitors
--------------------------------

**Before (PSS 2.x)**:

.. code-block:: pss

    component pss_top {
        action A { }
        action B { }
        
        // Manual coverage tracking
        int coverage_counter;
        
        constraint {
            // Complex constraints to track patterns
        }
    }

**After (PSS 3.0)**:

.. code-block:: pss

    monitor ABSequence {
        activity {
            concat {
                A;
                B;
            }
        }
    }
    
    component pss_top {
        action A { }
        action B { }
        
        cover ABSequence;
    }

Pattern 2: String Processing
-----------------------------

**Before (PSS 2.x)**:

.. code-block:: pss

    // Limited string operations
    action my_action {
        string filename;
        // No way to extract extension or validate format
    }

**After (PSS 3.0)**:

.. code-block:: pss

    action my_action {
        string filename;
        
        exec body {
            int dot_pos = filename.find_last(".");
            if (dot_pos != -1) {
                string extension = filename[dot_pos..];
                // Process extension
            }
        }
    }

Pattern 3: Dynamic Reference Management
----------------------------------------

**Before (PSS 2.x)**:

.. code-block:: pss

    component pss_top {
        pool[10] A actions;
        // Limited reference handling
    }

**After (PSS 3.0)**:

.. code-block:: pss

    component pss_top {
        action A { }
        
        list<ref A> active_actions;
        map<string, ref A> action_registry;
        
        exec init {
            // Dynamic reference management
            active_actions.clear();
        }
    }

Testing Your Migration
======================

Validation Checklist
--------------------

1. **Parse Check**: Verify all files parse without errors

   .. code-block:: python
   
       from pssparser import Parser
       
       parser = Parser()
       try:
           parser.parses([("file.pss", content)])
           print("✓ Parse successful")
       except Exception as e:
           print(f"✗ Parse error: {e}")

2. **Keyword Check**: Ensure no reserved keywords used as identifiers

   .. code-block:: bash
   
       # Search for potential conflicts
       grep -E '\b(monitor|yield|randomize|atomic)\b' *.pss

3. **Feature Check**: Verify new features work as expected

4. **Regression Check**: Run existing test suite

Known Migration Issues
======================

Issue 1: Monitor Keyword Conflicts
-----------------------------------

**Symptom**: Parse errors on identifiers named "monitor"

**Solution**: Rename identifiers

.. code-block:: pss

    // Before
    action monitor { }
    
    // After  
    action monitor_action { }

Issue 2: Implicit String Operations
------------------------------------

**Symptom**: Code expected string operations that weren't available

**Solution**: Use new string methods

.. code-block:: pss

    // Now available
    int len = my_string.size();
    string sub = my_string[0..10];

Issue 3: Reference Type Cloning
--------------------------------

**Symptom**: Warnings about "TaskCopyAst: Error: copy(DataType) failed"

**Impact**: Benign - does not affect functionality

**Solution**: No action required - will be addressed in future release

Performance Considerations
==========================

The PSS 3.0 parser maintains performance characteristics similar to PSS 2.x:

* Parse time: No significant change
* Memory usage: Minimal increase for new AST nodes
* Linking time: Comparable to PSS 2.x

Getting Help
============

If you encounter migration issues:

1. Check this guide for common patterns
2. Review the :doc:`pss30_features` documentation
3. Examine the test suite in ``tests/src/TestPSS30Grammar.cpp``
4. File an issue on the project repository

Best Practices
==============

1. **Incremental Migration**: Migrate one feature at a time
2. **Test Early**: Validate changes frequently
3. **Document Changes**: Note PSS 3.0 features used
4. **Leverage New Features**: Don't just maintain compatibility - use new capabilities
5. **Review Monitors**: Consider behavioral coverage opportunities

Example: Complete Migration
============================

**Original PSS 2.x Code**:

.. code-block:: pss

    component pss_top {
        action ReadReg {
            rand bit[31:0] addr;
            constraint { addr % 4 == 0; }
        }
        
        action WriteReg {
            rand bit[31:0] addr;
            rand bit[31:0] data;
            constraint { addr % 4 == 0; }
        }
    }

**Migrated PSS 3.0 Code**:

.. code-block:: pss

    // Add behavioral coverage
    monitor ReadWriteSequence {
        activity {
            concat {
                ReadReg;
                WriteReg;
            }
        }
    }
    
    component pss_top {
        action ReadReg {
            rand bit[31:0] addr;
            constraint { addr % 4 == 0; }
        }
        
        action WriteReg {
            rand bit[31:0] addr;
            rand bit[31:0] data;
            constraint { addr % 4 == 0; }
        }
        
        // Enable behavioral coverage
        cover ReadWriteSequence;
        
        // Use reference collection for tracking
        list<ref ReadReg> read_history;
        
        exec init {
            read_history.clear();
        }
    }

Summary
=======

PSS 3.0 migration is straightforward for most codebases:

* ✅ High backward compatibility
* ✅ Minimal breaking changes (reserved keywords only)
* ✅ Significant new capabilities (monitors, strings, references)
* ✅ Clear migration patterns
* ✅ Good performance characteristics

See Also
========

* :doc:`pss30_features` - Complete feature reference
* :doc:`quickstart` - Getting started guide
* :doc:`ast_structure` - AST structure details
