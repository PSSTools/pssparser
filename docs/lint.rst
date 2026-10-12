####
Lint
####

pssparser reports three kinds of diagnostic, told apart by the namespace of
their ID:

``PSS``
   The model violates the language reference manual.  These are errors;
   they cannot be turned off, and a run with one exits 1.
``LINT``
   The model is legal PSS, but something in it is probably not what the
   author meant: a constraint that cannot fire, an import in the wrong
   place, a deprecated form.  This page is about these.
``PSSP``
   pssparser itself has something to say: an extension failed to load, a
   construct is accepted but not represented in the AST, a configuration
   uses an old ID.

Every lint rule is listed, with examples, in :doc:`lint-rules`.
``pssparser --explain <ID or name>`` prints one entry at the command line.

Enabling lint
=============

Lint runs with every parse.  Which rules report is chosen by a **profile**:

.. list-table::
   :header-rows: 1

   * - Profile
     - Enables
   * - ``minimal`` (default)
     - The warnings pssparser reported before lint existed (``LINT101``,
       ``LINT301``, ``LINT401``-``404``, ``LINT501``, ``LINT601``-``602``).
       The default output is what it always was.
   * - ``recommended``
     - ``minimal`` plus the ``correctness``, ``suspicious``,
       ``portability`` and ``simplify`` tiers.
   * - ``library``
     - As ``recommended``; reserved for rules that judge a library
       differently from a top-level model.
   * - ``strict``
     - ``recommended`` plus ``pedantic``.
   * - ``all``
     - Every tier except ``nursery``.
   * - ``none``
     - No lint at all.  LRM errors and ``PSSP`` diagnostics still report.

Every profile except ``none`` includes ``minimal``, so moving to a larger
profile never drops a warning you already saw.  ``nursery`` rules are new
and not yet measured; select them by name to try one.

Choose a profile on the command line or in the configuration file:

.. code-block:: bash

   pssparser --lint-profile recommended model.pss
   pssparser --no-lint model.pss            # same as --lint-profile none

.. code-block:: toml

   # .pssparser.toml
   [lint]
   profile = "recommended"
   select  = ["pedantic"]                 # add a tier
   ignore  = ["import-after-declaration"] # remove one rule

``select`` and ``ignore`` take any selector -- an ID, a rule name, a tier,
``family:<name>``, an ID prefix -- and the most specific one wins (see
*Selecting rules* in :doc:`cli`).

Severity
========

Each rule's **tier** gives its default severity:

* ``correctness``, ``suspicious``, ``portability``, ``pedantic``,
  ``restriction`` and ``nursery`` rules are ``warning``;
* ``simplify`` rules are ``info`` (reported as *notes*);
* ``style`` rules are ``hint``, hidden unless ``--show-hints`` -- or unless
  the rule is selected by its ID, name, ID band or namespace (``select =
  ["ACME"]``, ``--select LINT301``): naming a rule is a request to see it.

Lint never defaults to ``error``: an error means the LRM says so.  To make
lint fail a build, promote it -- for everything, a tier, or one rule:

.. code-block:: bash

   pssparser -Werror model.pss
   pssparser -Werror=correctness model.pss

.. code-block:: toml

   [severity]
   suspicious = "error"
   LINT402    = "off"        # "off" means the rule does not run

Pinning the rule set
====================

A new pssparser release can add rules to a profile.  So that an upgrade
never fails a CI job by itself, pin the rule set:

.. code-block:: toml

   [lint]
   profile = "recommended"
   rules-version = "2026.1"

Every rule records the rules version it was added in (``since``).  A rule
newer than the pin is left out of the profile -- though it can still be
selected by name -- and ``pssparser --show-config`` lists what the pin is
holding back.  Bump the pin when you are ready to see the new rules.

Per-directory settings
======================

Different parts of a project can lint differently: generated code, tests,
vendored IP.  An ``[[lint.overrides]]`` table gives the files its ``files``
globs match their own ``profile``, ``select``, ``ignore`` and rule options:

.. code-block:: toml

   [lint]
   profile = "recommended"
   select  = ["ACME"]

   [[lint.overrides]]
   files  = ["tests/**", "*_gen.pss"]
   ignore = ["ACME", "style"]

   [[lint.overrides]]
   files   = ["lib/"]
   profile = "library"
   rule.comp-suffix = { suffix = "_lib" }

For each file, the profile is the last matching override's ``profile`` (else
the project's); the project's ``select`` and ``ignore`` apply to it; then
each matching override's ``select`` and ``ignore``, in order, decide again
the rules they match; then ``--select`` and ``--ignore``.  Options merge,
the later value winning.

Globs are relative to the configuration file's directory, wherever pssparser
runs from.  ``*`` and ``?`` stay within one directory and ``**`` crosses
them; ``[a-z]`` is a class.  A glob without ``/`` matches a file or
directory name at any depth (``*_gen.pss``, ``vendor``); one with ``/`` is
anchored at the configuration's directory.  A glob that matches a directory
takes everything under it, so ``lib``, ``lib/`` and ``lib/**`` mean the
same.  Matching is case-sensitive.

A rule that is on for any of the files runs, and reports only in the files
it is on for.  To see what a file gets:

.. code-block:: console

   $ pssparser --rules-for tests/dma_test.pss      # one line per rule
   $ pssparser --rules-for --format json ip/dma/new_block.pss
   $ pssparser --show-config --for tests/dma_test.pss

``--rules-for`` parses nothing, so the file need not exist yet: ask before
writing it.  Its JSON (``"schema": "pssparser-rules/1"``) adds each rule's
documentation, effective options and examples.  ``--show-config`` lists the
overrides and the rule files loaded, and with ``--for FILE``, which
overrides match the file and the rules it gets.

Which files are linted
======================

Lint findings are reported only in the files named on the command line.
A finding in the built-in standard library is never reported: it is not
yours to fix.  LRM errors and ``PSSP`` diagnostics are reported wherever
they occur.

IDs that moved out of PSS
=========================

Before lint existed, nine warnings about legal code carried ``PSS`` IDs, and
seven diagnostics about pssparser itself did too -- including the internal
error, ``PSS000``, now ``PSSP000``.  They moved, so that a ``PSS`` ID always
means an LRM violation:

.. list-table::
   :header-rows: 1

   * - Old
     - New
     - Name
   * - ``PSS046``
     - ``LINT101``
     - ``enum-item-type-mismatch``
   * - ``PSS120``
     - ``LINT301``
     - ``exported-instance-function``
   * - ``PSS044``
     - ``LINT401``
     - ``enum-item-hides-declaration``
   * - ``PSS053``
     - ``LINT402``
     - ``import-after-declaration``
   * - ``PSS101``
     - ``LINT403``
     - ``unknown-annotation``
   * - ``PSS119``
     - ``LINT404``
     - ``width-references-later-constant``
   * - ``PSS016``
     - ``LINT501``
     - ``reg-width-no-access-function``
   * - ``PSS104``
     - ``LINT601``
     - ``deprecated-braceless-compile-if``
   * - ``PSS117``
     - ``LINT602``
     - ``deprecated-dynamic-constraint-traversal``
   * - ``PSS030``
     - ``PSSP001``
     - ``extension-load-failed``
   * - ``PSS031``
     - ``PSSP002``
     - ``entry-point-name-mismatch``
   * - ``PSS032``
     - ``PSSP003``
     - ``extension-api-too-new``
   * - ``PSS116``
     - ``PSSP101``
     - ``construct-not-represented``
   * - ``PSS000``
     - ``PSSP000``
     - ``internal-error``
   * - ``PSS029``
     - ``PSSP007``
     - ``too-many-errors``
   * - ``PSS033``
     - ``PSSP008``
     - ``duplicate-marker-id``

The messages and locations are unchanged; only the ID is new.  The old IDs
still work wherever you type an ID -- ``[severity]``, ``[warnings]``,
``-Werror=``, ``--describe``, ``--explain`` -- and each use prints one
``PSSP004`` note naming where to update it.  Output always shows the new ID.
The old IDs are retired and will never be reused.

Waiving a finding
=================

To accept one finding where it is, rather than turning its rule off
everywhere, waive it in the source:

.. code-block:: pss

   @lint_pkg::waive {.id = "import-after-declaration", .reason = "generated"}
   import vendor::*;

   import other::*;   // pssparser waive LINT402: vendor header order

:doc:`waivers` covers both forms, what each covers, and the markers that
keep waivers honest.

Adopting lint on an existing model
==================================

Switching a profile on over a model that already exists usually reports
more findings than anyone will fix in one go.  A *baseline* records the
findings you have today, so that CI fails only on new ones while the old
ones are worked off.

1. Choose the profile, and check that the model has no errors: a baseline
   records lint findings, never errors.

   .. code-block:: toml

      # .pssparser.toml
      [lint]
      profile = "recommended"

2. Record today's findings:

   .. code-block:: bash

      pssparser --write-baseline lint-baseline.json src/*.pss

   This writes every finding the run reports to ``lint-baseline.json`` and
   exits 0.  Commit the file.

3. Point the configuration at it.  The path is relative to the
   configuration file, so it works from any directory:

   .. code-block:: toml

      [lint]
      profile = "recommended"
      baseline = "lint-baseline.json"

4. Gate CI as usual.  Findings the baseline records are not printed, not
   counted and not promoted by ``-Werror``; anything new is:

   .. code-block:: yaml

      - run: pssparser -Werror src/*.pss

How findings are matched
------------------------

A finding is recorded by its rule, its file and a *fingerprint*: a hash of
the declaration that contains it (such as ``pkg::C::A::constraint c``) and
the code it flags, with whitespace and comments ignored.  It does not
include the line number, so a recorded finding stays recorded when code is
added above it, when the file is reformatted, or when a comment is added
inside it.  It becomes a new finding when the flagged code itself changes,
or when it moves into another declaration.

Identical findings in one declaration have the same fingerprint, and the
baseline records how many there were.  If it recorded three and the run
finds four, one is reported: the last in the file.

Keeping the baseline current
----------------------------

When a recorded finding is fixed, its entry no longer matches anything, and
the run reports a ``PSSP206`` note at that entry in the baseline file.
Re-run ``--write-baseline`` to drop it, so that the finding cannot return
unnoticed.  The note appears only when the run checked the entry's file and
ran its rule: checking a subset of the files, or turning a rule off, does
not make entries stale.  ``[severity] PSSP206 = "off"`` silences it.

The file lists one finding per line, sorted, so a pull request that changes
it shows exactly which findings were added or removed.  Paths in it are
relative to the baseline file.

The summary line counts what the baseline hid, ``1 warning in 3 files (12
baselined)``, and ``--stats`` adds a ``baselined:`` row with a count per ID.
``--no-baseline`` ignores the configured baseline for one run, to see every
finding.  ``--baseline PATH`` uses another file.  In JSON output the
baselined findings are in a separate ``baselined`` array; SARIF reports
them as results with ``baselineState: "unchanged"`` (see
:doc:`diagnostics-json` and :doc:`cli`).

What a baseline never covers
----------------------------

LRM errors and pssparser's own diagnostics (``PSSP``) are never recorded and
never matched.  ``--write-baseline`` refuses to write anything, and exits 1,
when the model has errors.

Site rules
==========

A project can add rules of its own, in YAML rule files, without writing
Python: name the files or directories in ``[lint] rules`` (or with
``--rules``), and check them with ``pssparser --check-rules``.  A site rule
uses the site's own namespace (``ACME001``, or ``ACME-NET001`` for one team)
and is selected, waived and baselined like any other rule; ``--explain``
describes it, and the profile enables it by tier.  :doc:`lint-rule-authoring`
describes the format, and the JSON Schema that gives editors completion.

CI integration
==============

GitHub code scanning, from SARIF:

.. code-block:: yaml

   - run: pssparser --format sarif --lint-profile recommended src/*.pss > pssparser.sarif
     continue-on-error: true
   - uses: github/codeql-action/upload-sarif@v3
     with:
       sarif_file: pssparser.sarif

Plain pull-request annotations, with no upload step:

.. code-block:: yaml

   - run: pssparser --format github --lint-profile recommended src/*.pss
