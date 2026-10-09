#####################
Checker Plug-in Guide
#####################

.. contents::
   :local:
   :depth: 2

Concept
=======

``pssparser`` ships with built-in syntax and semantic checks implemented in
C++.  The **checker plug-in system** lets you — or any third-party package —
add custom Python checks that run as a third phase, after a successful parse
and link.

Each checker is a Python class that inherits from
:class:`pssparser.checkers.CheckerBase`.  Checkers receive a
:class:`pssparser.checkers.CheckContext` object that provides read access to
the linked AST and an API to emit structured diagnostics.

The built-in ``CoreChecker`` (name ``"core"``) is always registered and
documents every marker the C++ parser and linker can produce.  It cannot be
disabled.

Writing a Checker
=================

Below is a complete, real-world example — a naming-convention checker that
warns when ``action`` or ``struct`` type names do not start with an uppercase
letter.  The full source lives in ``examples/pss_naming_checker/``, walked
through in :doc:`example_single_checker`.

.. code-block:: python

   # pss_naming/checker.py
   from __future__ import annotations
   from typing import TYPE_CHECKING

   import pssparser.ast as pss_ast
   from pssparser.checkers import CheckerBase, MarkerDef

   if TYPE_CHECKING:
       from pssparser.checkers import CheckContext


   class NamingConventionChecker(CheckerBase):
       name = "naming-convention"
       description = "Warn when action or struct type names do not start with uppercase"

       marker_defs = [
           MarkerDef(
               id="PSC001",
               severity="warning",
               summary="Action type name does not start with an uppercase letter",
               detail=(
                   "PSS convention uses PascalCase for action type names.  "
                   "Rename the action so that its first letter is uppercase, "
                   "e.g. rename ``write_data`` to ``WriteData``."
               ),
           ),
           MarkerDef(
               id="PSC002",
               severity="warning",
               summary="Struct type name does not start with an uppercase letter",
               detail=(
                   "PSS convention uses PascalCase for struct type names.  "
                   "Rename the struct so that its first letter is uppercase, "
                   "e.g. rename ``my_packet`` to ``MyPacket``."
               ),
           ),
       ]

       # Name-checking only needs the parse tree; no linked AST required.
       runs_without_link = True

       def check(self, context: "CheckContext") -> None:
           for global_scope in context.global_scopes:
               # context.file_map maps GlobalScope.getFileid() → source path.
               # GlobalScope.getFilename() is not reliably set by the parser.
               filename = context.file_map.get(global_scope.getFileid(), "")
               self._walk(context, global_scope, filename)

       def _walk(self, context, scope, filename: str) -> None:
           """Recursively walk *scope* and emit markers for naming violations."""
           for child in scope.children():
               if isinstance(child, pss_ast.Action):
                   self._check_name(context, child, filename, "PSC001", "Action")
               elif isinstance(child, pss_ast.Struct):
                   self._check_name(context, child, filename, "PSC002", "Struct")
               # Recurse into any child scope (components, packages, …)
               if isinstance(child, pss_ast.Scope):
                   self._walk(context, child, filename)

       @staticmethod
       def _check_name(context, node, filename, code, kind):
           name_expr = node.getName()
           name = name_expr.getId()
           if not name or name[0].isupper():
               return
           loc = name_expr.getLocation()
           context.add_marker(
               code=code,
               file=filename,
               line=loc.lineno,
               col=loc.linepos,
               message=f"{kind} '{name}' should start with an uppercase letter",
           )

Step-by-step walkthrough:

1. **Subclass** :class:`~pssparser.checkers.CheckerBase`.
2. **Set** ``name`` — a short unique slug used on the command line.
3. **Set** ``description`` — shown by ``--list-checkers``.
4. **Declare** ``marker_defs`` — one :class:`~pssparser.checkers.MarkerDef`
   per diagnostic code your checker can emit.
5. **Set** ``runs_without_link = True`` when your checker only needs the raw
   parse tree (faster; works even when ``--syntax-only`` is active).
6. **Implement** ``check(context)`` — walk the AST and call
   :meth:`~pssparser.checkers.CheckContext.add_marker` to emit diagnostics.

.. tip::

   ``context.file_map`` is a ``dict[int, str]`` mapping
   ``GlobalScope.getFileid()`` to the source file path.  Use it instead of
   ``GlobalScope.getFilename()``, which may be empty.

Marker Dict Shape
==================

Whether a marker originates in the C++ parser/linker or from
:meth:`~pssparser.checkers.CheckContext.add_marker`, ``Parser.markers`` and
``CheckContext``'s collected diagnostics share the same dict shape:

``severity``, ``message``, ``file``, ``line``, ``col``
    The core fields every marker has always had.
``extent``
    Length in characters of the primary span. ``0`` means unknown, in which
    case the CLI falls back to underlining a single column. Pass it whenever
    you know the width of the offending token or name — it is the difference
    between an underline that covers ``my_bad_name`` and one that covers only
    its first letter.  It is also what a baseline fingerprint hashes
    (:doc:`lint`, "How findings are matched"): with no extent, only the token
    at ``col`` is hashed, and two findings that start with the same token in
    one declaration are told apart only by counting them.
``related``
    A list of secondary locations, each ``{"file", "line", "col", "label"}``.
    Use this for a diagnostic that only makes sense with a second point of
    reference — the earlier declaration a duplicate collides with, the opener
    of a scope that never closed, the call site of a symbol resolved from an
    import. Pass ``related`` to :meth:`~pssparser.checkers.CheckContext.add_marker`
    rather than folding the second location into ``message`` as prose; the
    CLI renders each entry as its own annotated source line.
``code``
    The marker's stable ID (e.g. ``"PSS020"``). Always present for
    checker-emitted markers (``add_marker`` requires ``code``); for
    C++-emitted markers not yet migrated to carry their own ID, it is filled
    in downstream by pattern-matching against ``core_checker.py``'s
    ``marker_defs`` and may be entirely absent if no pattern matches.

   ``context.global_scopes`` contains only the user-supplied source files;
   the built-in PSS library scopes are filtered out automatically.

Declaring Markers
=================

Every diagnostic your checker may emit must be declared as a
:class:`~pssparser.checkers.MarkerDef` in the class-level ``marker_defs``
list:

.. code-block:: python

   from pssparser.checkers import MarkerDef

   MarkerDef(
       id="PSC001",          # globally unique ID
       severity="warning",   # "error", "warning", "info", or "hint"
       summary="Short description for --list-markers",
       detail="Longer explanation shown by --describe PSC001",
   )

**ID grammar**: a *namespace* of two to five capital letters, then a
three-digit number -- ``PSC001``, ``PRC042``.  Digits never appear in the
namespace, so an ID splits unambiguously, and a user can select every rule
of yours with the namespace alone (``-Werror=PSC``).  An ID that does not
fit still loads, with a ``PSSP006`` warning; it will be refused in a later
release.

**Reserved namespaces**: ``PSS`` (LRM violations), ``LINT`` (pssparser's
lint rules), ``PSSP`` (the tool's own diagnostics) and ``PSSX`` belong to
pssparser.  A checker that declares an ID in one of them is not registered,
with a ``PSSP005`` error.  Choose a namespace of your own and keep it.

The :class:`~pssparser.checkers.CheckerManager` enforces globally unique IDs
across all registered checkers at discovery time.

Rule metadata
-------------

A checker whose markers are *lint* -- legal PSS that is probably a mistake --
should describe each rule fully, so that profiles, ``--explain``, the SARIF
output and selectors work for it the way they do for pssparser's own rules.
Every field is optional, and a ``MarkerDef`` that sets none of them loads
exactly as before.

.. list-table::
   :header-rows: 1
   :widths: 18 82

   * - Field
     - Meaning
   * - ``name``
     - Kebab-case rule name, unique across everything installed.  Accepted
       wherever an ID is.
   * - ``tier``
     - ``correctness``, ``suspicious``, ``portability``, ``simplify``,
       ``style``, ``pedantic``, ``restriction`` or ``nursery``.  Sets the
       default severity and the profiles that enable the rule.
   * - ``family``
     - ``constraint``, ``activity``, ``exec``, ``decl``, ``import``,
       ``register``, ``evolution``, ``naming`` or ``metric``.
   * - ``level``
     - Analysis level ``L0``-``L5``: how much of the model the rule needs.
   * - ``since``
     - The rules version the rule was added in, ``"YYYY.N"``.  Drives
       ``rules-version`` pinning.  Required for ``nursery`` rules.
   * - ``default_enabled``
     - ``False`` keeps the rule out of its tier's profiles until selected.
   * - ``fix``
     - ``"none"``, ``"safe"`` or ``"unsafe"``.  Anything but ``none`` needs
       an example with its ``fixed`` form.
   * - ``lrm``
     - LRM clause references, e.g. ``("11.4.6",)``.
   * - ``examples``
     - :class:`~pssparser.checkers.markerdef.Example` records: ``code``, the
       ``expect`` positions (empty for a "good" example), ``fixed``, ``note``.
   * - ``options_schema``
     - The rule's options, configured under ``[lint.rule.<name>]``.
   * - ``status``, ``replaced_by``, ``aliases``
     - Lifecycle: ``active``, ``deprecated``, ``retired`` or ``reserved``;
       the successor of a retired code; old codes that now mean this one.

Leave ``severity=""`` to take the tier's default:

.. list-table::
   :header-rows: 1

   * - Tier
     - Default severity
   * - ``correctness``, ``suspicious``, ``portability``, ``pedantic``,
       ``restriction``, ``nursery``
     - ``warning``
   * - ``simplify``
     - ``info``
   * - ``style``
     - ``hint``

A severity that differs from the tier's default must say why, in a
paragraph of ``detail`` beginning ``Severity:``.  Metadata that breaks one
of these rules -- an unknown tier, a duplicate name, a fix with no example --
refuses the checker with a ``PSSP201`` warning naming the field.

Skipping disabled rules
-----------------------

A user can turn a rule off (``[severity] ID = "off"``, or by leaving it out
of their lint profile).  A checker whose every ID is off is not called at
all.  A checker with several rules can skip the work for one that is off:

.. code-block:: python

   def check(self, context):
       if context.is_enabled("PSC002"):
           self._check_structs(context)

Asking is optional: ``add_marker`` drops a disabled code anyway, so a
checker that never asks is still correct, only slower.

Where a location is in the model
--------------------------------

``context.facts.decl_path(loc)`` returns the qualified path of the
declaration enclosing a location -- ``pkg::C::A::constraint c``, or ``""`` at
global scope.  *loc* is a marker dict, anything with ``file``, ``line`` and
``col`` attributes, or a ``(file, line, col)`` tuple.  The index behind it is
built the first time a checker asks, and shared for the rest of the run.

A path segment is a declaration's name; a function, constraint block, exec
block, activity or activity symbol is written with its keyword
(``function f``, ``constraint c``, ``exec body``, ``activity``,
``symbol s``); an unnamed constraint is ``constraint``; an extension is
``extend action C::A``, as written.  A segment that repeats in one scope is
numbered from the second: ``constraint#2``, ``exec body#2``.  The same index
is ``pssparser.lint.declpath.index_for(parser, files)`` outside a checker.

.. _core-marker-catalogue:

Built-in Marker Catalogue
=========================

The ``PSS``, ``LINT`` and ``PSSP`` namespaces belong to the built-in
``CoreChecker``.  Because most core diagnostics originate in C++ — where the marker object carries no ID — the ID
is recovered by matching the message text against the ``patterns`` declared on
each :class:`~pssparser.checkers.MarkerDef`.  ID, severity, documentation, and
patterns are therefore all declared together in
``pssparser/checkers/core_checker.py``, and the C++ message strings form part
of that contract.  ``tests/python/test_marker_ids.py`` pins the mapping.

Core IDs are allocated in bands:

``PSS001``–``PSS099``
    General parse and link diagnostics.

``PSS020``–``PSS028``
    Syntax-error sub-band of the general band above: each ID names one shape
    of parser recovery (missing punctuation, unexpected end of input, a
    keyword where an identifier was expected, ...), classified in
    ``AstBuilderInt::syntaxError`` and carried on the marker itself rather
    than recovered from message-pattern matching. ``PSS023`` within the
    sub-band is reserved, not assigned (see ``core_checker.py`` for why).
    ``PSS029``, the ``--max-errors`` cutoff, is now ``PSSP007``.

``PSS100``–``PSS199``
    PSS 3.1 language-rule diagnostics.

``LINT``
    Lint the core linker raises: legal PSS that is probably a mistake.  Nine
    of these were ``PSS`` warnings before lint existed; their old IDs are
    retired rows that point at the new ones.  See :doc:`lint`.

``PSSP``
    The tool's own diagnostics: ``PSSP0xx`` extensions, configuration and
    marker IDs; ``PSSP1xx`` parser coverage; ``PSSP2xx`` lint
    infrastructure.

A ``PSS`` ID is always an error.

The table below is a representative sample, not the full catalogue --
:doc:`markers` is generated straight from ``marker_defs`` and cannot drift.

.. list-table::
   :header-rows: 1
   :widths: 12 12 76

   * - ID
     - Severity
     - Summary
   * - ``PSS001``
     - error
     - Syntax error (unclassified fallback -- see the PSS020 sub-band above
       for the classified cases)
   * - ``PSS020``
     - error
     - Expected specific punctuation before this token
   * - ``PSS002``
     - error
     - Unknown symbol reference
   * - ``PSS003``
     - error
     - Duplicate symbol declaration (the ``duplicate declaration of '...'``
       variant is currently emitted as a warning)
   * - ``PSS004``
     - error
     - Symbol or ref-path resolution failure
   * - ``PSS005``
     - error
     - Cannot extend unknown type or enum
   * - ``PSS006``
     - error
     - Wrong number of arguments in a call (built-in ``string`` methods
       included; collection methods other than ``push_back`` are not yet
       checked)
   * - ``PSS007``
     - error
     - Argument type mismatch in a call (by broad category -- numeric, string,
       aggregate -- not by exact type)
   * - ``PSS008``
     - error
     - Call to something that is not a function (a field, variable, or
       parameter)
   * - ``PSS100``
     - error
     - Annotation is not attached to a model element
   * - ``PSS102``
     - error
     - Annotation initializer is not a constant expression
   * - ``PSS105``
     - error
     - Illegal ``mutable`` qualifier
   * - ``PSS106``
     - error
     - Exec block tag not permitted on this exec kind
   * - ``PSS107``
     - error
     - Member selection on a slice
   * - ``PSS108``
     - error
     - Unterminated ``{{`` mustache in a triple-quoted string
   * - ``PSS109``
     - error
     - Mustache content does not parse as an expression
   * - ``PSS110``
     - error
     - Unterminated or malformed template directive or comment; unclosed
       block at end of string
   * - ``PSS111``
     - error
     - Template block directive out of place (a ``{%%}`` too many, or an
       ``else`` with no ``if``)
   * - ``PSS112``
     - error
     - Template assignment target is not a template local
   * - ``PSS113``
     - error
     - Template expression is not of scalar type
   * - ``PSS114``
     - error
     - Non-pure function called from a template string
   * - ``PSS115``
     - error
     - Non-constant template string where a constant is required

``PSS108``–``PSS115`` are the triple-quoted-string diagnostics (PSS 3.1
§4.7.1); see :doc:`pss31_features`.  ``PSS108`` and ``PSS109`` carry an inline
hint about the ``{{`` collision, because the overwhelmingly common cause is
target code that meant two literal braces -- see :doc:`pss31_migration`.

Two related warnings are lint rather than errors by deliberate design.
``LINT403`` must not be an error because PSS 3.1 §7.13 requires that
unrecognized annotations be *disregarded*, so source using a tool-specific
annotation stays portable.  ``LINT601`` marks a form that remains legal and is
never scheduled for removal.

Run ``pssparser --list-markers`` for the live catalogue and
``pssparser --describe <ID>`` for the full text of any entry.

Registering via entry_points
=============================

The standard way to make your checker available to all ``pssparser``
invocations is to declare it as an ``entry_points`` contribution in your
package's ``setup.cfg`` or ``pyproject.toml``:

``setup.cfg``:

.. code-block:: ini

   [options.entry_points]
   pssparser.checkers =
       naming-convention = mypkg.pss_rules:NamingConventionChecker
       unused-imports     = mypkg.pss_rules:UnusedImportChecker

``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."pssparser.checkers"]
   naming-convention = "mypkg.pss_rules:NamingConventionChecker"
   unused-imports    = "mypkg.pss_rules:UnusedImportChecker"

The left-hand side (e.g. ``naming-convention``) **must match the class's own**
``name`` **attribute**.  The class is authoritative: if the two disagree, the
checker is registered under the name the class declares, the entry-point key
is ignored, and a ``PSSP002`` warning says so.  While they disagree, a command
line written against the key silently selects nothing.

After installation (``pip install .``), your checker is auto-discovered every
time ``pssparser`` runs.

Shipping a collection
=====================

One entry point per checker is fine for one or two rules.  For a package that
ships a dozen, use the **``pssparser.extensions``** group instead: one entry
point for the whole distribution, pointing at a module that exposes
``register(registry)``.

``setup.cfg``:

.. code-block:: ini

   [options.entry_points]
   pssparser.extensions =
       acme-rules = acme_pss_rules

``pyproject.toml``:

.. code-block:: toml

   [project.entry-points."pssparser.extensions"]
   acme-rules = "acme_pss_rules"

.. code-block:: python

   # acme_pss_rules/__init__.py
   REQUIRES_API = 1

   def register(reg):
       reg.version = "2.3.0"
       reg.description = "Acme house rules for PSS"

       from .naming import NamingChecker
       from .coverage import CoverageChecker
       reg.add_checker(NamingChecker)
       reg.add_checker(CoverageChecker)

The key (``acme-rules``) is the *extension* name, shown by
``pssparser --list-extensions``.  Installing the package is all a user has to
do: every checker it contributes runs by default, with no flags.

A working example lives in ``examples/pss_rule_collection/``, walked through
in :doc:`example_rule_collection`.

The registry object
-------------------

``register()`` receives a :class:`pssparser.checkers.ExtensionRegistry`:

.. list-table::
   :header-rows: 1
   :widths: 20 12 68

   * - Attribute
     - Direction
     - Meaning
   * - ``api_version``
     - in
     - Checker-API version of the *running* pssparser.
   * - ``name``
     - in
     - The entry-point key this extension was registered under.
   * - ``add_checker(cls)``
     - out
     - Register one ``CheckerBase`` subclass.  Repeatable.
   * - ``version``
     - out
     - Shown by ``--list-extensions``; defaults to the distribution version.
   * - ``description``
     - out
     - One line, shown by ``--list-extensions``.
   * - ``requires_api``
     - out
     - Minimum API version this extension needs.

As a shorthand, a module may expose a ``CHECKERS`` list instead of
``register()``; it is synthesized into the equivalent ``register()`` call.
Prefer the function when you need either of the version mechanisms below.

API versioning
--------------

``pssparser.checkers.API_VERSION`` is an integer, bumped only when the
checker-facing surface changes *incompatibly* -- a ``CheckContext`` field
removed, a ``MarkerDef`` field renamed, ``check()``'s signature altered.
Adding a field or an optional hook does not bump it.

Declare ``REQUIRES_API`` at module level to refuse an incompatible build
outright.  pssparser checks it *before* importing your rule modules and
reports ``PSSP003`` naming both versions -- one clear message instead of an
``AttributeError`` from inside a checker halfway through a user's run.

To support several pssparser releases from one package, probe instead:

.. code-block:: python

   def register(reg):
       reg.add_checker(StableChecker)
       if reg.api_version >= 2:
           reg.add_checker(CheckerNeedingTheNewerAPI)

What happens when an extension breaks
-------------------------------------

Discovery never aborts the run.  A third-party extension is code the user did
not write, so one broken package must not stop the rest of the registry from
loading:

.. list-table::
   :header-rows: 1
   :widths: 12 12 76

   * - Code
     - Severity
     - Cause
   * - ``PSSP001``
     - warning
     - Import failed, ``register()`` raised, or neither ``register`` nor
       ``CHECKERS`` is exposed.
   * - ``PSSP002``
     - warning
     - Entry-point key disagrees with the class's ``name``.
   * - ``PSSP003``
     - warning
     - ``requires_api`` exceeds this build's ``API_VERSION``.
   * - ``PSSP005``
     - error
     - A checker declares an ID in a reserved namespace.
   * - ``PSSP006``
     - warning
     - A checker declares an ID outside the ID grammar.
   * - ``PSSP008``
     - error
     - Two checkers declare the same ``MarkerDef`` ID.
   * - ``PSSP201``
     - warning
     - A checker's rule metadata is invalid.

These are ordinary diagnostics: they appear in ``--json``, they are counted,
and ``-Werror`` promotes the warnings among them.  ``-Werror=PSSP001`` is the
usual way to make a failed extension fatal in CI.

``PSSP008`` is an error rather than a warning because two rules wearing one ID
make ``--describe``, ``-Werror=ID``, and every per-ID override ambiguous.  The
checker that lost the collision is not registered; the rest of its extension
still loads.  Pick an unused namespace -- see *ID grammar* above.

Two practices worth copying from the example:

1. **Import rule modules inside** ``register()``, not at module scope, so a
   failure in one rule is reported as ``PSSP001`` against your extension rather
   than breaking the import of the package that declares the entry point.
2. **Keep marker IDs stable.**  Users pin them in ``-Werror=ID`` and in
   suppression config; renaming one is a breaking change for them.

Turning extensions off
----------------------

``--no-extensions`` (or ``PSSPARSER_NO_EXTENSIONS=1``) loads the built-in
checks and nothing else.  It is the first thing to try when diagnosing
unexpected output, and the way to make a run reproducible regardless of what
is installed alongside pssparser.

``pssparser --list-extensions`` shows what did load: name, version,
distribution, and the checkers each one contributed.

A configuration file can turn off one extension without turning off the
rest:

.. code-block:: toml

   [extensions.acme-rules]
   enabled = false

Configuring a checker
=====================

A rule that every project wants to tune slightly — a naming style, a
threshold, a list of exemptions — should be one checker with options, not
two checkers or a hardcoded choice.  Declare what you accept in
``options_schema``:

.. code-block:: python

   class NamingConventionChecker(CheckerBase):
       name = "naming-convention"

       options_schema = {
           "style": {
               "type": "string",
               "default": "PascalCase",
               "choices": ["PascalCase", "snake_case"],
               "help": "Naming style required for action and struct types.",
           },
           "exempt": {
               "type": "string-list",
               "default": [],
               "help": "Glob patterns for type names to skip, e.g. 'legacy_*'.",
           },
       }

       def configure(self, options):
           self.options = options       # always complete; see below

Users then write:

.. code-block:: toml

   [checker.naming-convention]
   style  = "snake_case"
   exempt = ["legacy_*"]

``type`` is one of ``string``, ``int``, ``bool``, or ``string-list``.
``choices`` is optional and applies to ``string``.  ``help`` is one line,
printed by ``--describe-checker``.

Three properties of the contract are worth relying on:

**Options are validated before any source file is read.**  An unknown key,
a wrong type, a value outside ``choices``, or a ``[checker.<name>]`` table
aimed at a checker that declares no options are all usage errors (exit 2)
reported at startup.  Your ``configure()`` never sees an invalid table.

**The table is always complete.**  Declared defaults are filled in for
anything the user did not set, so an implementation never needs
``options.get(key, default)`` — which is exactly how a default and its
schema entry drift apart.  Mutable defaults are copied per instance, so one
checker cannot mutate the class-level schema.

**The hook is optional.**  A checker that declares no ``options_schema``
never has ``configure()`` called, so every checker written before options
existed behaves exactly as it did.

Declaring a schema is also what makes the feature discoverable:

.. code-block:: bash

   pssparser --describe-checker naming-convention

prints the description, the contributing extension, every marker, and the
whole options table with types, defaults, and permitted values.

A checker cannot supply default severities for markers it does not own.
Shipping an opinionated profile for your own IDs is reasonable; a
``pip install`` silently changing the severity of a *core* marker is a large
amount of authority for a third-party package, so ``[severity]`` remains the
user's to write.

Ad-hoc Loading
==============

For development or one-off use you can load a checker without installing it:

.. code-block:: bash

   pssparser --load-checker mypkg.pss_rules:NamingConventionChecker model.pss

The ``--load-checker`` flag may be repeated to load multiple checkers.  The
loaded checker participates in all ``--checker`` / ``--no-checker`` filtering
using its ``name`` attribute.

Combine with ``--list-checkers`` to inspect what will run before doing an
actual parse:

.. code-block:: bash

   pssparser --load-checker mypkg.pss_rules:NamingConventionChecker \
             --list-checkers

Checker Selection
=================

By default, all registered (non-builtin) checkers run.  Use these flags to
change that:

``--checker NAME``
    Run **only** the named checker(s).  May be repeated.  ``NAME`` must match
    a registered checker name (from ``entry_points``) or a checker previously
    loaded with ``--load-checker``.  Specifying an unknown name is an error.

    .. code-block:: bash

       pssparser --checker naming-convention model.pss

``--no-checker NAME``
    **Exclude** the named checker.  May be repeated.  Ignored when
    ``--checker`` is also specified (explicit selection takes precedence).
    Unknown names are silently ignored.

    .. code-block:: bash

       pssparser --no-checker deprecated-syntax model.pss

Precedence rules:

1. Start with all registered + ``--load-checker`` checkers.
2. If ``--checker`` is present, keep *only* those names.
3. Otherwise, remove any names listed in ``--no-checker``.

Querying the Registry
=====================

``--list-checkers``
    Print a table of all registered checkers and their declared marker IDs,
    then exit with code 0.  No source files are required.

    .. code-block:: bash

       pssparser --list-checkers

``--list-markers``
    Print a table of every declared :class:`~pssparser.checkers.MarkerDef`
    across all checkers (including the built-in core), then exit with code 0.

    .. code-block:: bash

       pssparser --list-markers

``--describe ID``
    Print the full :class:`~pssparser.checkers.MarkerDef` record (summary,
    severity, detail text, and owning checker) for a single marker ID, then
    exit with code 0.  Exits with code 2 if the ID is not found.

    .. code-block:: bash

       pssparser --describe PSS002

Accessing the AST
=================

Inside ``check(context)``, the linked AST is available as
``context.root`` (a ``RootSymbolScope``) and the per-file ``GlobalScope``
nodes are in ``context.global_scopes``.  See :doc:`ast_usage_guide` for a
full guide to navigating the AST.

To resolve a ``GlobalScope`` to its source path, use ``context.file_map``::

    filename = context.file_map.get(gs.getFileid(), "")

``context.file_map`` is a ``dict[int, str]`` (fileid → path).
``GlobalScope.getFilename()`` is not reliably populated by the parser, so
always prefer ``file_map``.

``context.global_scopes`` contains only the user-supplied source files;
the built-in PSS library scopes are filtered out automatically.

If your checker only needs the *parse tree* (not the linked AST), set
``runs_without_link = True`` on the class.  The checker will then run even
when ``--syntax-only`` is passed.  When ``runs_without_link = False``
(the default), the checker is skipped in ``--syntax-only`` mode.

Testing your rules
==================

``pssparser.checkers.testing`` ships in the wheel, so an extension's own
test suite can use the harness pssparser tests its lint rules with.

Write **fixture files**: ``.pss`` sources whose expected findings are stated
in them.  ``l*.pss`` files must report exactly what their ``// expect:``
lines say -- same IDs, same line and column, nothing more -- and
``ok_*.pss`` files must report nothing:

.. code-block:: pss

   // expect: PSC001 @ 4:10, PSC002 @ 5:10
   component pss_top {
     action Good { }
     action write_data { }
     struct packet { }
   }

.. code-block:: pss

   // expect: none
   component pss_top {
     action WriteData { }
   }

Only the IDs of the rules under test are compared, so an unrelated core
warning does not break a fixture.  A malformed ``expect`` line fails with its
file and line.

Then check a directory of them:

.. code-block:: python

   from pssparser.checkers.testing import check_fixture_dir
   from my_rules.checker import NamingConventionChecker

   def test_fixtures():
       check_fixture_dir("tests/lint", checkers=[NamingConventionChecker])

``check_fixture_dir`` raises ``AssertionError`` listing every failing file,
with the missing and unexpected findings of each.  ``checkers=`` registers a
checker that is not installed; ``rules=`` takes selectors for lint rules to
enable, since tiered lint rules otherwise report only when their profile
does.

Also available:

``run_rules(paths, rules, checkers=..., config_text=...)``
    Parse, link and run, returning the diagnostics as JSON-shaped dicts.
``check_examples(CheckerClass)``
    Run every ``MarkerDef.examples`` entry: a "bad" example must report its
    ID at exactly its ``expect`` positions, a "good" one nothing.  This keeps
    the examples ``--explain`` prints honest.
``check_messages(diagnostics)``
    The message-quality rules core diagnostics are held to: one line, at
    most 120 characters, a code, no parser jargon.

With pytest, ``-p pssparser.checkers.testing`` provides the same function as
a ``lint_fixture`` fixture.
