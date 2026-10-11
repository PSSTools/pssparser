AST Model Reference
===================

The classes, fields and enums of pssparser's abstract syntax tree, and how
each one is spelled in every API: C++ (``pssp::ast``), Python
(``pssparser.ast``), TypeScript, and a lint rule (:doc:`../lint-rule-authoring`).
Every page is generated from ``ast/*.yaml``, the same files the code is
generated from, when the documentation is built.

Reading an entry
----------------

Each class entry gives, in order:

* **Inherits** -- the chain of base classes, and **Subclasses**.
* What the class represents, from its ``doc:`` in the YAML.
* A diagram of its neighbourhood: its base, its subclasses, what it holds,
  and the classes whose fields are declared as it. Click a class to go to it.
* **Fields** -- each field's type, how it relates the two classes (owns,
  owns a list of, refers to, back-pointer to), whether the linker rather
  than the parser sets it, and what it means. Fields of base classes are
  listed under **Inherited fields**.
* **Appears in** -- every field that can hold the class: those declared as
  the class itself, and those declared as one of its bases (a field declared
  as ``Expr`` can hold an ``ExprBin``). This is what the schema allows, which
  is wider than what the grammar produces: most scopes hold
  ``list<UP<ScopeChild>>``.
* **In each API** -- how each field is read and written in C++, Python,
  TypeScript and a lint rule.

Diagram conventions
-------------------

.. astb:legend:: pss

Map of the model
----------------

One box per group of classes (one YAML file, one page); an arrow where
classes in one group own classes in another, labelled with the number of
fields that do. Click a box, or a name in the list, to go to its page.

.. astb:model-map:: pss

.. toctree::
   :hidden:

   coretypes
   typescope
   struct
   field
   datatype
   template
   template_types
   expr
   constraint
   activity
   exec
   functions
   coverage
   monitor
   extension
   override
   annotation
   linking

Class hierarchy
---------------

Every class, by inheritance, from each class that has no base. Almost
everything that can appear in a scope derives from ``ScopeChild`` (175
classes); its direct subclasses are listed here, and each one's entry lists
its own.

.. astb:inheritance-tree:: ScopeChild
   :model: pss
   :depth: 1

Expressions:

.. astb:inheritance-tree:: Expr
   :model: pss

Template parameter values:

.. astb:inheritance-tree:: TemplateParamValue
   :model: pss

Classes with no base and no subclasses:
:astb:class:`ActivityMatchChoice`, :astb:class:`ActivitySelectBranch`,
:astb:class:`AssocData`, :astb:class:`CompileCond`,
:astb:class:`ExprAggrMapElem`, :astb:class:`ExprAggrStructElem`,
:astb:class:`SymbolExtMember`, :astb:class:`SymbolImportSpec`,
:astb:class:`SymbolRefPath`, :astb:class:`TemplateParamDeclList`,
:astb:class:`TemplateParamValueList`.
