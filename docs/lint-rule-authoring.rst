####################
Writing lint rules
####################

A site can add its own lint rules without writing Python: a *rule file*
declares rules in YAML, with their conditions written as expressions. The
same file works in the command line, the editor and CI, because pssparser's
core loads it in every one of them.

A first rule file
=================

.. code-block:: yaml

   # lint/rules/acme-naming.yaml
   pss-rules:
     defaults:
       family: naming
       tier: style

     rules:
       - id: ACME001
         name: action-name-upper-camel
         summary: Action type names are UpperCamelCase.
         message: >-
           action '${node.name.id}' is not UpperCamelCase; the ACME style guide
           names action types like 'WriteBurst'
         match: { kind: Action }
         where: >-
           !node.name.id.matches(options.pattern)
         options:
           pattern:
             type: string
             default: "^[A-Z][A-Za-z0-9]*$"
             help: The regular expression an action type name must match.
         examples:
           - name: lower-case name
             code: |
               component pss_top {
                 action write_burst { }   // expect: ACME001
               }
           - name: UpperCamelCase is fine
             code: |
               component pss_top {
                 action WriteBurst { }
               }

Name it in the configuration, and check it:

.. code-block:: toml

   # .pssparser.toml
   [lint]
   rules = ["lint/rules/"]

.. code-block:: console

   $ pssparser --check-rules
   0 errors in 1 file
   pssparser: 1 rule loaded from 1 file

That also ran the rule's two examples, and both gave what their
``// expect:`` comments say (see `Examples`_).

Then turn it on. A rule runs when the lint selection enables it, like any
other lint rule: by its tier through a profile, or by name. The default
profile, ``minimal``, enables none of a site's rules, so select them:

.. code-block:: toml

   [lint]
   rules = ["lint/rules/"]
   select = ["ACME"]          # every ACME rule; or "action-name-upper-camel"

.. code-block:: console

   $ pssparser top.pss
   top.pss:2:10: hint: [ACME001] action 'write_burst' is not UpperCamelCase; the ACME style guide names action types like 'WriteBurst'
    2 |   action write_burst { }
      |          ^~~~~~~~~~~

   0 errors in 1 file

To try the rules without a configuration file, give the same things on the
command line. ``--select`` and ``--ignore`` take the selectors that
``[lint] select`` and ``ignore`` do, and are applied on top of the
configuration:

.. code-block:: console

   $ pssparser --rules lint/rules/ --select ACME top.pss

A ``style`` rule reports hints, which the output hides unless asked
(``--show-hints``, or ``show-hints = true`` under ``[output]``) -- except
for a rule selected by its ID, name, ID band or namespace, as ``ACME`` is
here: naming a rule is a request to see it. Selected only by a tier or a
profile, its findings are counted (``0 errors in 1 file (1 hint hidden)``)
but not shown. A rule left out of the selection is never evaluated.
``pssparser --rules-for FILE`` lists the rules a file gets, with no model
parsed (:doc:`lint`, *Per-directory settings*). Rules run only on a model that
parsed and linked without errors. ``--stats`` lists what each rule did (see
:doc:`cli`).

The file
========

Everything is under one top-level key, ``pss-rules``. Its presence is what
makes a YAML file a rule file, and nothing else may sit beside it.

``rules`` (required)
   The list of rules. An empty list is allowed.
``defaults``
   Fields applied to every rule in the file that does not set them itself:
   ``tier``, ``family``, ``since``, ``status``, ``severity`` and
   ``default_enabled``.
``define``
   Helper expressions shared by the file's rules: ``name(param, ...)`` maps
   to one expression. A rule's own ``define:`` may shadow one; that is
   reported as a note (``PSSP219``).
``version``
   The format version, ``1``. A file declaring a later version is refused
   as a whole.
``x-*``
   Ignored: for your own annotations (an owner, a ticket).

The YAML is YAML 1.2: ``yes``, ``no``, ``on`` and ``off`` are strings, not
booleans. One document per file, and no custom tags. A ``.json`` file with
the same shape is accepted. Write expressions as block scalars (``>-``) or
quoted strings, because ``:``, ``?`` and ``#`` mean something to YAML.

A rule
======

``id``, ``name``
   The rule's ID (see `IDs`_) and a unique kebab-case name. Either one works
   wherever pssparser takes a rule: ``--select``, ``-Werror=``,
   ``[lint] select``, waivers,
   baselines.
``tier``
   ``correctness``, ``suspicious``, ``portability``, ``simplify``,
   ``style``, ``pedantic``, ``restriction`` or ``nursery``. The tier decides
   the default severity and which profiles include the rule (see
   :doc:`lint`).
``summary``
   One line, shown in rule lists.
``message``
   The diagnostic, with ``${expression}`` for values from the model.
   ``$${`` is a literal ``${``. A declaration is shown by its declaration
   path (``pss_top::A::x``, as ``decl_path`` gives it), an identifier, type
   name or literal by its text, and any other node by its kind and position.
``match``
   Which syntax-tree nodes the rule looks at: ``kind`` (one node kind or a
   list; subclasses match), and optionally ``inside`` and ``not_inside`` (an
   ancestor of a kind), each bounded by ``stop``. Ancestors are searched
   nearest first, and the search ends at the first one of a ``stop`` kind,
   after that ancestor's own ``kind`` test: ``inside: {kind: Action, stop:
   Action}`` is true inside the nearest action.
``where``
   An expression on ``node`` that must be true for a finding.
``let``
   Named expressions for use in ``where``, ``report`` and the message. Each
   may use the ones before it. A binding is evaluated the first time
   something reads it, once per matched node: one only the message reads
   costs nothing for a node that is not reported, so name a costly
   sub-expression freely.
``report``
   The nodes to report at, when that is not the matched node itself. In the
   message, ``finding`` is the reported node. An unset field in the list
   (``[node.super_t]`` on a type with no base) reports nothing, and a rule
   reports one node only once, however many matches name it.

   A named declaration -- an action, component, struct, field, enum, enum
   item, function prototype, package, anything whose ``name`` is an
   identifier -- is reported at its name, not across its body, whether it is
   the matched node or one ``report`` gives. ``component dma { ... }`` is
   underlined under ``dma``; a package ``a::bb`` from ``a`` to ``bb``. Other
   nodes are reported at where they start.
``options``
   Settings a user can change, each with a ``type`` (``string``, ``int``,
   ``bool`` or ``string-list``), a ``default`` and ``help``. Expressions
   read them as ``options.<name>``.
``examples``
   Small models, each with ``// expect: ID`` on the lines that must report.
   An example without an ``expect`` must report nothing. Use ``code:`` for
   one file, or ``files:`` for several. ``--check-rules`` runs them (see
   `Examples`_).
``family``, ``doc``, ``lrm``, ``since``, ``status``, ``aliases``, ``replaced_by``, ``severity``, ``default_enabled``
   Metadata, as for the built-in rules.

Expressions are a subset of CEL, the Common Expression Language. The
operators and functions are listed in :doc:`lint-functions`. They are
type-checked when the file loads, so a misspelt field or function is
reported at its line and column in the YAML file. pssparser works out each
rule's analysis level and scope from the functions it calls; a rule does not
declare them.

Every node kind, its base and its fields, with their types, are in
:doc:`lint-nodes`. A field declared on a base class is read on every
subclass: a ``Field``'s ``name`` comes from ``NamedScopeChild``.

Besides a node's own fields, the library's navigation functions move around
the tree: ``parent(n)``, ``ancestors(n)``, ``children(n)``,
``descendants(n)``, ``siblings(n)``, ``index_of(n)``, and
``enclosing(n, Action)``, the nearest enclosing action. ``n.isa(K)`` tests a
node's class, subclasses included. After ``n.isa(K) &&``, or
``type(n) == K &&``, the expression can read ``K``'s fields:

.. code-block:: yaml

   where: >-
     enclosing(node, Action) != null
     && enclosing(node, Action).name.id.endsWith("_test")

``descendants(n, K)`` keeps a subtree's nodes of class ``K``, already typed:
``descendants(node, Field).map(f, f.name.id)``. Prefer it to
``descendants(n).filter(d, d.isa(K))``, which pays for every node the
comprehension looks at.

The symbol functions read the linked model: ``resolves_to(r)`` is the
declaration a reference names (``resolves_to(node.type)``,
``resolves_to(node.super_t)``), ``decl_path(n)`` a node's qualified path, and
``is_owned(n)`` and ``in_library(n)`` say whose file it is in.
``refs(d)`` lists the uses of a declaration across the whole model, and
``is_read(r)`` and ``is_written(r)`` say what a use does; a rule that calls
``refs`` is re-run on any change to the model, not only to its file.
``const_int(e)`` and ``const_bool(e)`` give an expression's value when it is
a constant, and ``optional.none()`` otherwise; so
``const_bool(node.expr).orValue(true) == false`` finds a constraint that can
never hold. Like every
rule, one that calls them runs only on a model that parsed and linked
without errors.

``is_pure(f)`` says whether a function is pure, as the template-string check
decides it: ``f`` is a call (``is_pure(node)`` on the ``ExprMemberPathElem``
with the arguments, or on the whole path) or a function declaration. A
function is pure when any of its declarations says ``pure``, or when a
``pure component`` declares it.

``file_of(n)`` is the file a node is in, as a ``FileInfo`` record:
``path``, ``dir``, ``name``, ``stem`` and ``ext`` (``.pss``). The path is
relative to the configuration file's directory, so a rule reads the same
path in every checkout (``file_of(node).path.matches("^ip/")``); with no
configuration it is the path as given on the command line.
``decls_in(file_of(node))`` lists the file's top-level declarations, in
source order: "one component per file" is
``decls_in(file_of(node)).filter(d, type(d) == Component)``.

``dups(l)`` gives the indexes of a list's elements that equal an earlier
one, so ``dups(inits.map(i, resolves_to(i.path)))`` finds a field initialised
twice in one list, and ``.map(k, inits[k])`` gives the nodes to report.

``same_tree(a, b)`` compares two pieces of code rather than two nodes: the
same kinds, operators, names and literals, however they are laid out. So
``same_tree(node.lhs, node.rhs)`` finds ``x == x`` and ``x = x``.
``import_uses(i)`` lists the names an ``import`` provides in its scope, and
``core_library_name(name)`` says whether ``std_pkg``, ``addr_reg_pkg`` or
another core library package declares a name.

``branches(n)`` lists the alternatives of a ``select``, ``match``,
``if``/``else``, ``parallel`` or ``schedule`` the same way for each:
a ``Branch`` record with the branch's ``node``, ``index``, ``guard``,
``weight``, ``body`` and ``is_default``. ``ranges(n)`` folds the values a
match choice covers into ``Range`` records (``lo``, ``hi``), or gives
``optional.none()`` when one does not fold. Together they find a branch that
can never be taken, and a match choice that overlaps an earlier one:

.. code-block:: yaml

   match: { kind: ActivitySelect }
   report: >-
     branches(node).filter(b, !const_bool(b.guard).orValue(true)
       || const_int(b.weight).orValue(1) == 0).map(b, b.body)

A field's attributes are flags: ``has_flag(node.attr, FieldAttr.Rand)`` is
true for a ``rand`` field. A flags value is not a number. ``int()``,
``string()``, arithmetic and ordering on one are errors when the file loads,
because its bit values belong to the syntax tree, not to the rule format.

``type_decl(node.type)`` is the declaration a field's type names. It follows
typedefs, and for a template use it gives the specialization (``S<4>``, with
its arguments bound), where ``resolves_to`` gives the generic ``S``.
``type_named("pkg::name")`` is the type a PSS name names in the model, and
``derives_from(t, "pkg::name")`` tests inheritance, ``t`` itself included. A
generic template's name matches every specialization of it. Together they
let a rule talk about library types. This rule finds an address or executor
claim that is not ``rand``:

.. code-block:: yaml

   pss-rules:
     rules:
       - id: ACME002
         name: claim-not-rand
         tier: suspicious
         summary: An address or executor claim is not declared 'rand'.
         message: "claim '${node.name.id}' is not 'rand', so it is not allocated as written"
         match: { kind: Field, inside: { kind: Action } }
         let:
           t: type_decl(node.type)
         where: >-
           !has_flag(node.attr, FieldAttr.Rand) && t.hasValue() &&
           (derives_from(t.value(), "addr_reg_pkg::addr_claim_base_s") ||
            derives_from(t.value(), "executor_pkg::executor_claim_s"))
         examples:
           - code: |
               import addr_reg_pkg::*;
               component pss_top {
                 transparent_addr_space_c<> mem;
                 struct my_claim_s : addr_claim_s<> { }
                 action my_action {
                   transparent_addr_claim_s<> c1;   // expect: ACME002
                   my_claim_s c2;                   // expect: ACME002
                   rand my_claim_s c3;
                 }
               }

The ``where`` is a block scalar (``>-``) because it starts with ``!``, which
YAML reads as a tag. A type name is written without template arguments, and
a literal one is checked when the file loads. A name the model does not have
(a typo, or a package that is not compiled in) gives ``optional.none()`` and
``false``, and the run reports it once per rule as a ``PSSP223`` note.

The tree is the source as written. An ``extend``'s members belong to the
``extend``, not to the type it extends, and nodes that pssparser adds itself,
such as each action's ``comp`` handle, are not in it.

IDs
===

An ID is a namespace of two to five capital letters, an optional team
qualifier, and three digits: ``ACME001``, or ``ACME-NET001`` for one team's
rules. ``ACME`` in a selector covers every ``ACME-*`` team; ``ACME-NET``
covers only that team.

``PSS``, ``PSSP``, ``PSSX`` and ``LINT`` belong to pssparser and may not be
used, with or without a qualifier. Every ID, alias and name must be unique
across everything loaded: the built-in rules, every rule file, and installed
Python checkers. When two claim the same one, the one loaded later is
refused and the message points at the other.

Where rule files come from
==========================

In this order:

1. pssparser's built-in rules;
2. ``[lint] rules`` in the configuration, in order. Paths are relative to
   the configuration file;
3. ``--rules PATH`` on the command line, in order (repeatable).

A path may name a file or a directory.

* **A named file** must be a rule file; otherwise that is an error.
* **A named directory** contributes every ``*.yaml``, ``*.yml`` and
  ``*.json`` file directly in it (not in subdirectories) that has a
  top-level ``pss-rules`` key. Other files are skipped; ``--verbose`` lists
  them with the reason, which is how a misspelt ``pss-rules`` is found.

A path that does not exist is a usage error (exit 2).

Examples
========

A rule's ``examples:`` are its tests, and its documentation. Each one is a
complete model: give it a component scope, and ``import std_pkg::*;`` when
it uses the standard library.

.. code-block:: yaml

   examples:
     - name: two fields in one action
       code: |
         component pss_top {
           action A {
             rand bit[8] m_ok;
             rand bit[8] bad;                // expect: ACME002 @ 4:17
             rand bit[8] x; rand bit[8] y;   // expect: ACME002, ACME002
           }
         }
     - name: types in two files
       files:
         types.pss: |
           package p {
             struct Pq { }   // expect: ACME003
           }
         top.pss: |
           import p::*;
           component pss_top { action Abc { Pq s; } }

* ``// expect: ID`` expects one finding of the rule on that line, at any
  column; ``ID @ line:col`` expects it at that position of the example's
  text (line 1 is the first line of ``code:``, or of that file). One
  comment may list several, separated by commas, and ``/* expect: ID */``
  works too, which leaves the rest of the line to code.
* An example with no ``expect`` comment, or with ``// expect: none``, must
  report nothing: a near miss, which is how a rule shows what it leaves
  alone.
* An ``expect`` may name only the rule's own ID.

``pssparser --check-rules`` runs every example of the rules in the files it
checks. An example runs on its own: its files are parsed and linked by a
fresh parser, only its rule runs, and the rule's options are at their
defaults. It passes when the rule reports exactly what the ``expect``
comments say: a finding missing, or one too many, fails it. So does an
example that does not parse or link, and one on which the rule fails
(``PSSP220``, ``PSSP221``). Each problem is a ``PSSP222`` error at the
example, and the message says what went wrong where in the example's text.
Had the first rule's firing example named its action ``WriteBurst``:

.. code-block:: console

   $ pssparser --check-rules lint/rules/acme-naming.yaml
   lint/rules/acme-naming.yaml:22:11: error: [PSSP222] example 'lower-case name' of ACME001: expected ACME001 at line 2, but it was not reported
    22 |         - name: lower-case name
       |           ^

   1 error in 1 file
   pssparser: 1 rule loaded from 1 file

Built-in rules need at least one example that reports and one that does
not.

For larger sets of cases, write fixture files and run them from pytest with
``pssparser.checkers.testing``, which loads rule files with ``rule_files=``
(see :doc:`checker_plugin_guide`, "Testing your rules"). From Python,
``pssparser.lint.examples.check_examples(engine)`` runs the examples of the
rules loaded in a :class:`~pssparser.core.LintEngine` and raises
``AssertionError`` listing every failure.

Writing a rule, step by step
============================

1. Write the rule and its ``examples:``: at least one model that must report
   and one near miss that must not.
2. Run ``pssparser --check-rules FILE``. Every diagnostic gives its line and
   column in the rule file: a misspelt field (``type 'Field' has no field
   'nme'``), an expression that needs quoting, an example that reported too
   much or too little.
3. Fix, and repeat until it exits 0.
4. Run the rule on a real model with ``--rules FILE --select ID
   --show-hints``, and look at what it reports there.

pssparser ships an agent skill, ``pssparser-checkers``, that teaches a coding
agent this loop and the rule format, so "write a rule that flags ..." gives
a rule file with examples rather than a Python checker. It is registered
in the ``agent.skills`` entry-point group, so ``ivpm update`` installs it
into ``.claude/skills/`` and the other agent directories; its source is
``skills/pssparser-checkers/`` in the repository.

Checking rule files
===================

``pssparser --check-rules [PATH...]`` loads rule files, reports every
problem, runs their rules' examples, and exits. With PATHs it checks those;
without, it checks ``[lint] rules`` and ``--rules``. The built-in rules are
always loaded first, so a clash with one of them is found.

* exit 0: no errors (notes do not count);
* exit 1: a rule file has an error, or an example fails;
* exit 2: a usage error, such as a path that does not exist, or nothing to
  check.

``--format json``, ``sarif`` and ``github`` work as for a model, so a rules
repository can annotate its pull requests:

.. code-block:: yaml

   - run: pssparser --check-rules --format github lint/rules/

An ordinary run loads the same rule files and reports their problems with
the model's diagnostics. A bad rule is left out; the rest of its file still
loads.

Rules from rule files are known everywhere a Python checker's rules are
-------------------------------------------------------------------------------

Once loaded, a rule from a rule file is in pssparser's rule registry beside
the built-in and installed ones, so:

* ``pssparser --explain no-plus`` and ``--describe ACME001`` print it, with
  the file and line it is defined in, the node kinds it matches, and the
  analysis level and scope pssparser computed for it;
* ``--list-markers`` lists it, under the checker ``pss-rules``;
* selectors (``--select`` and ``--ignore``, ``-Werror=``, ``[lint] select``
  and ``ignore``, ``[severity]``) may
  name its ID, name, namespace (``ACME``, ``ACME-NET``), tier or family;
* the lint profile enables it by tier, as for any rule (``default_enabled:
  false`` keeps it out);
* ``[lint.rule.<name>]`` sets its options, checked against its
  ``options:`` when the configuration loads.

The command line loads the rule files before it checks the configuration,
so a configuration may name rules that only a rule file defines. A query
(``--explain``, ``--describe``, ``--list-markers``) also prints the rule
files' problems, since a rule that failed to load is missing from its
answer.

Editor support
==============

pssparser publishes a JSON Schema for rule files,
`pss-rules.schema.json <_static/pss-rules.schema.json>`_, generated from
the same field table the loader checks against. An editor with a YAML
language server (VS Code's YAML extension, for one) uses it for completion,
hover text and shape errors when the file names it in its first line:

.. code-block:: yaml

   # yaml-language-server: $schema=https://psstools.github.io/pssparser/_static/pss-rules.schema.json
   pss-rules:
     rules: []

The schema knows every field, its type and allowed values, the ID and name
grammar, and every node kind ``match:`` accepts. It cannot check
expressions, or what a built-in rule must also have; ``--check-rules``
does both.

When a rule fails while running
===============================

A rule can still go wrong on a model it was not tested on. The usual cause
is reading a field through one that is unset: ``node.super_t.elems`` on an
action with no base type is an error, not an empty list. Guard such reads
with ``has(node.super_t)``, or read it optionally with ``.?``.

* If ``where``, ``report`` or a message part evaluates to an error, that is
  one ``PSSP220`` warning at the node, naming the rule and the part. The
  rule is skipped for the rest of that file; the other rules still run. A
  finding whose message failed is kept, with ``?`` for the failed part.
* Each rule has a budget of evaluation steps per file, shared by all its
  expressions over every node it matches. A rule that runs out gets one
  ``PSSP221`` warning and is skipped for the rest of the file; its earlier
  findings stand.
* Rules run only on a model without errors. If parsing, linking or the
  semantic checks reported any, lint does not run, and a ``PSSP230`` note
  says "lint skipped: N errors".

What is reported
================

.. list-table::
   :header-rows: 1
   :widths: 12 88

   * - ID
     - Problem
   * - ``PSSP210``
     - The file is not a rule file: empty, not a mapping, no ``pss-rules``,
       no ``rules`` list, or a ``version`` this pssparser does not read.
       The file is refused as a whole.
   * - ``PSSP211``
     - An unknown key, in a rule or under ``pss-rules``, or a key beside
       ``pss-rules``.
   * - ``PSSP212``
     - A field is missing, has the wrong type, or is not one of its allowed
       values; a malformed ID; a malformed example; ``fix:``, which is
       reserved.
   * - ``PSSP213``
     - An unknown node kind in ``match:``.
   * - ``PSSP214``
     - An expression does not parse, or uses something outside the
       supported CEL subset.
   * - ``PSSP215``
     - An expression does not type-check: an unknown field, function or
       option, or the wrong type.
   * - ``PSSP216``
     - An expression is too deeply nested, a ``define:`` helper calls
       itself, or a regular expression is rejected.
   * - ``PSSP217``
     - An ID in a reserved namespace, or an ID, alias or name that something
       else loaded already has.
   * - ``PSSP218``
     - The YAML does not parse: a syntax error, a duplicate key, a tag, or
       more than one document.
   * - ``PSSP219``
     - A note: a rule's ``define:`` helper shadows the file's.
   * - ``PSSP220``
     - A warning: a rule failed while running on the model (see above).
   * - ``PSSP221``
     - A warning: a rule used up its evaluation budget for a file.
   * - ``PSSP222``
     - An example does not give the findings it expects (see `Examples`_).
   * - ``PSSP223``
     - A note: a rule names a type (``type_named``, ``derives_from``) that
       the model does not have.
   * - ``PSSP230``
     - A note: lint did not run, because the model has errors.

``pssparser --explain PSSP215`` (any of them) says more.
