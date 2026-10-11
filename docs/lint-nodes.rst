Lint Rule Node Reference
========================

The syntax-tree classes a declarative lint rule reads are documented in the
:doc:`ast/index`, which is generated from ``ast/*.yaml`` when the
documentation is built. Every class entry there ends with a table, **In each
API**, whose **Lint rule** column gives how a rule reads each field
(``node.lhs``) and the type the rule checker gives it. A field that a rule
cannot read (a map, or a list of lists) says so in that column.

A class name is a node kind: ``match: { kind: Field }`` matches it,
``n.isa(Field)`` and ``type(n) == Field`` test for it, and a subclass
matches wherever its base does. A rule reads a node's fields by name,
``node.name.id``, including the fields its bases declare: a ``Field`` has
``name`` from ``NamedScopeChild`` and ``location`` from ``ScopeChild``; each
entry lists them under **Inherited fields**. An unset node field is
``null``, an unset list is empty; test with ``has()`` or read it with ``.?``
(see :doc:`lint-rule-authoring`). The functions that move around the tree
and read the linked model are in :doc:`lint-functions`.

The types are as the rule checker gives them. An enum field is an ``int``
compared against its constants (``node.op == ExprBinOp.BinOp_Eq``); a flags
field is a set of flags, tested with ``has_flag``
(``has_flag(node.attr, FieldAttr.Rand)``); it is not a number. A rule names
an enum constant as ``Enum.Value``; each enum's entry lists its values.

Structs are values a node field holds that are not nodes, read by member
(``node.location.lineno``).

The classes, by the part of the language they model:

* :doc:`ast/coretypes` -- scopes and the core classes every node derives from
* :doc:`ast/typescope`, :doc:`ast/struct`, :doc:`ast/field`,
  :doc:`ast/datatype` -- type declarations, structs, fields and data types
* :doc:`ast/template`, :doc:`ast/template_types` -- templates and their
  parameters
* :doc:`ast/expr` -- expressions
* :doc:`ast/constraint` -- constraints
* :doc:`ast/activity` -- activities
* :doc:`ast/exec`, :doc:`ast/functions` -- exec blocks, procedural statements
  and functions
* :doc:`ast/coverage`, :doc:`ast/monitor` -- coverage and monitors
* :doc:`ast/extension`, :doc:`ast/override`, :doc:`ast/annotation` --
  extensions, overrides and annotations
* :doc:`ast/linking` -- the linker's classes. The linker builds these
  alongside the tree; they are not written in the source, and a rule meets
  them only through a field that names one.
