##################
PSS 3.0 Features
##################

This document describes the PSS 3.0 features supported by pssparser,
including behavioral coverage with monitors, string enhancements, reference
collections, and platform qualifiers.

Overview
========

PSS 3.0 (Portable Test and Stimulus Standard Version 3.0, August 2024) adds
several significant enhancements to PSS 2.x:

* **Monitors** - Behavioral coverage constructs for observing action execution
* **String enhancements** - String methods and substring operator
* **Reference collections** - Collections containing reference types
* **Procedural randomization** - Randomize statements in procedural blocks
* **Activity atomic blocks** - Atomic execution blocks in activities
* **Yield statements** - Control flow yield in target execution
* **Platform qualifiers** - Target/solve qualifiers on functions

Monitors and Behavioral Coverage
=================================

Monitors define behavioral coverage constructs that observe and cover the
execution of actions in the test stimulus model.

Basic Monitor Declaration
--------------------------

A monitor is declared using the ``monitor`` keyword:

.. code-block:: pss

    monitor BasicMonitor {
        // Monitor body
    }

Monitors can be used in cover statements to specify behavioral coverage goals:

.. code-block:: pss

    component pss_top {
        action A { }
        
        cover BasicMonitor;
    }

Abstract Monitors
-----------------

Monitors can be declared as abstract, preventing direct instantiation:

.. code-block:: pss

    abstract monitor AbstractMonitor {
        // Abstract monitor body
    }
    
    monitor ConcreteMonitor : AbstractMonitor {
        // Concrete implementation
    }

Monitor Activities
------------------

Monitor activities describe temporal patterns of action execution using
temporal operators:

**Sequence Blocks**

Sequential execution of activities:

.. code-block:: pss

    monitor SequenceMonitor {
        activity {
            sequence {
                // Activity statements
            }
        }
    }

**Concat (Temporal Concatenation)**

Activities that must execute in immediate succession:

.. code-block:: pss

    monitor ConcatMonitor {
        activity {
            concat {
                // First activity
                action_a;
                // Second activity  
                action_b;
            }
        }
    }

**Eventually**

An activity that must eventually occur:

.. code-block:: pss

    monitor EventuallyMonitor {
        activity {
            eventually sequence {
                // Activity that must occur
            }
        }
    }

**Overlap**

Activities that overlap in time:

.. code-block:: pss

    monitor OverlapMonitor {
        activity {
            overlap {
                action_a;
                action_b;
            }
        }
    }

**Schedule**

Unordered concurrent activities:

.. code-block:: pss

    monitor ScheduleMonitor {
        activity {
            schedule {
                action_a;
                action_b;
            }
        }
    }

Cover Statements
----------------

Cover statements specify which monitors to instantiate for behavioral coverage:

**Inline Cover**

.. code-block:: pss

    component pss_top {
        cover MyMonitor;
    }

**Reference Cover**

.. code-block:: pss

    component pss_top {
        cover MyMonitor monitor_ref;
    }

**Labeled Cover**

.. code-block:: pss

    component pss_top {
        cover "coverage_label" MyMonitor;
    }

Monitor Constraints
-------------------

Monitors can include constraints that restrict the covered behavior:

.. code-block:: pss

    monitor ConstrainedMonitor {
        constraint {
            // Constraints on monitor behavior
        }
    }

String Enhancements
===================

PSS 3.0 adds string methods and a substring operator for string manipulation.

String Methods
--------------

The following built-in methods are available on string types:

**size()**

Returns the length of the string as an integer:

.. code-block:: pss

    string s = "hello";
    int len = s.size();  // Returns 5

**find(substring [, start])**

Returns the index of the first occurrence of substring, or -1 if not found:

.. code-block:: pss

    string s = "hello world";
    int idx = s.find("world");      // Returns 6
    int idx2 = s.find("world", 7);  // Returns -1 (not found after index 7)

**find_last(substring [, start])**

Returns the index of the last occurrence of substring:

.. code-block:: pss

    string s = "hello hello";
    int idx = s.find_last("hello");  // Returns 6

**find_all(substring)**

Returns an array of all indices where substring occurs:

.. code-block:: pss

    string s = "hello hello";
    array<int, 1> indices = s.find_all("ll");  // Returns [2, 8]

**lower()**

Returns a lowercase version of the string:

.. code-block:: pss

    string s = "HELLO";
    string lower_s = s.lower();  // Returns "hello"

**upper()**

Returns an uppercase version of the string:

.. code-block:: pss

    string s = "hello";
    string upper_s = s.upper();  // Returns "HELLO"

**split(delimiter)**

Splits the string on the delimiter and returns an array of substrings:

.. code-block:: pss

    string s = "a,b,c";
    array<string, 1> parts = s.split(",");  // Returns ["a", "b", "c"]

**chars()**

Returns an array of single-character strings:

.. code-block:: pss

    string s = "abc";
    array<string, 1> chars = s.chars();  // Returns ["a", "b", "c"]

Substring Operator
------------------

The substring operator ``[start..end]`` extracts a substring:

**Range Syntax**

.. code-block:: pss

    string s = "hello world";
    string sub1 = s[0..4];    // Returns "hello"
    string sub2 = s[6..10];   // Returns "world"

**Open-Ended Range**

.. code-block:: pss

    string s = "hello world";
    string sub1 = s[6..];   // Returns "world" (from index 6 to end)
    string sub2 = s[..4];   // Returns "hello" (from start to index 4)

**Single Character**

.. code-block:: pss

    string s = "hello";
    string ch = s[0];  // Returns "h"

Reference Collections
=====================

PSS 3.0 allows reference types to be used in collections (arrays, lists, maps, sets).

Reference Array
---------------

.. code-block:: pss

    component pss_top {
        action A { }
        
        array<ref A, 10> action_refs;
    }

Reference List
--------------

.. code-block:: pss

    component pss_top {
        action A { }
        
        list<ref A> action_list;
    }

Reference Map
-------------

.. code-block:: pss

    component pss_top {
        action A { }
        
        map<string, ref A> action_map;
    }

Reference Set
-------------

.. code-block:: pss

    component pss_top {
        action A { }
        
        set<ref A> action_set;
    }

Null References
---------------

Reference types can be null:

.. code-block:: pss

    component pss_top {
        action A { }
        
        ref A nullable_ref = null;
    }

Procedural Randomization
========================

The ``randomize`` statement performs procedural randomization in exec blocks.

Basic Randomization
-------------------

.. code-block:: pss

    action my_action {
        int x;
        
        exec body {
            randomize(x);
        }
    }

Randomization with Constraints
-------------------------------

.. code-block:: pss

    action my_action {
        int x;
        
        exec body {
            randomize(x) {
                x > 0;
                x < 100;
            }
        }
    }

Activity Atomic Blocks
======================

Atomic blocks specify that a group of activities must execute atomically
without interleaving.

.. code-block:: pss

    action my_action {
        activity {
            atomic {
                // Activities that must execute atomically
                do A;
                do B;
            }
        }
    }

Yield Statements
================

The ``yield`` statement suspends execution in target exec blocks, allowing
the scheduler to run other activities.

.. code-block:: pss

    action my_action {
        exec target {
            // Do some work
            yield;  // Suspend and allow scheduler to run
            // Continue work
        }
    }

Platform Qualifiers
===================

Functions can be qualified with ``target`` and/or ``solve`` to specify
execution context.

Target Qualifier
----------------

Marks a function as only callable from target execution context:

.. code-block:: pss

    import target function int read_register(int addr);

Solve Qualifier
---------------

Marks a function as only callable during solve (constraint solving):

.. code-block:: pss

    import solve function int compute_checksum(int data);

Combined Qualifiers
-------------------

A function can be marked with both qualifiers:

.. code-block:: pss

    import target solve function int utility_func(int x);

Limitations and Known Issues
=============================

The following limitations currently exist:

1. **Semantic Validation**: While all PSS 3.0 constructs parse correctly,
   some semantic validation is not yet implemented:
   
   - Monitor field restrictions (only action/monitor handles, static const)
   - Yield statement context validation (target exec blocks only)
   - Platform qualifier transitive validation
   
2. **AST Representation**: Some constructs use simplified AST representations:
   
   - Substring operations currently use subscript mechanism
   - May be enhanced in future versions

3. **TaskCopyAst Warnings**: Some operations generate benign warnings about
   AST copying for reference types. These do not affect functionality.

Migration from PSS 2.x
======================

PSS 3.0 is largely backward compatible with PSS 2.x. Key considerations:

1. All PSS 2.x constructs continue to work
2. New keywords (monitor, yield, randomize, atomic) are reserved
3. String methods are additive - no breaking changes
4. Reference collections extend existing collection types

See Also
========

* :doc:`quickstart` - Getting started with pssparser
* :doc:`ast_structure` - Understanding the AST structure
* :doc:`pss30_migration` - Detailed migration guide
