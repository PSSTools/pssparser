###
CLI
###

The `pssparser` package provides a parser-focused command-line interface.

Basic usage
===========

Parse and link one or more PSS source files:

.. code-block:: bash

   pssparser file1.pss file2.pss

Common options
==============

- ``--syntax-only`` parses without performing linking / symbol resolution
- ``--json`` emits diagnostics as JSON
- ``--dump-ast OUT`` writes a JSON dump of the linked AST
- ``--quiet`` suppresses normal diagnostic output
- ``-Werror`` / ``-Werror=ID`` / ``-Wno-error=ID`` / ``--no-warnings`` control
  how warnings are reported (see `Warning policy`_)
- ``--stats`` / ``--stats-no-timing`` report what the run did (see
  `Run statistics`_)
- ``--max-errors N`` stops reporting further errors for a file after ``N``
  (default 20; ``0`` disables the cap). Only error-severity diagnostics count
  against it — warnings never trigger it, and a clean file never sees it.
  A capped file gets one extra marker, ``PSS029``, announcing the cutoff;
  everything past it is dropped, not merely hidden, so re-run with a higher
  (or ``0``) ``--max-errors`` to see what comes after. The Python API
  (:class:`pssparser.Parser`) defaults to unlimited — the cap is a
  terminal-output affordance the CLI opts into via
  ``Parser.set_max_errors()``, not something a library caller should have to
  ask to disable.

Examples
========

Syntax-only parse:

.. code-block:: bash

   pssparser --syntax-only model.pss

Emit diagnostics as JSON:

.. code-block:: bash

   pssparser --json model.pss

Dump the linked AST:

.. code-block:: bash

   pssparser --dump-ast ast.json model.pss

Diagnostic rendering
=====================

By default (no ``--json``), a diagnostic is rendered Rust/Clang-style: a
``file:line:col: severity: message`` header, the offending source line, and a
caret underlining the exact span. For example, an unterminated ``component``:

.. code-block:: pss

   component C {
       action A {
       }

.. code-block:: text

   model.pss:1:13: error: unclosed '{' for component 'C'
    1 | component C {
      |             ^

Some diagnostics carry one or more **related locations** — a second place in
the source that explains the diagnostic, such as the opening brace an unclosed
construct never closed, (in the example above, run to completion) where the
input actually ran out, or the ``compile if`` that owns a deprecated
brace-less branch. Related locations are not limited to errors: a warning
carries them too, and that is often where they matter most, because a warning
raised twice for one construct needs to say which half it is talking about.
Each related location renders as an indented ``note:`` line under the primary
diagnostic, with its own source line and caret when one is available:

.. code-block:: text

   model.pss:1:13: error: unclosed '{' for component 'C'
    1 | component C {
      |             ^
     note: input ends here
      --> model.pss:4:1

   1 error in 1 file

Here the related location points *past* the last line of the file (there is
nothing left to show a source line for), so only the ``note:`` label and the
``file:line:col`` pointer are printed — the source line and caret are omitted
whenever the related location has no line to render, rather than printing an
empty or misleading one.

``--json`` output carries the same information structurally: each diagnostic
object may include a ``"related"`` array of ``{file, line, col, label}``
entries, so an editor or script can render (or otherwise use) related
locations without re-parsing prose.

Checker flags
=============

The following flags control the checker plug-in system.  See
:doc:`checker_plugin_guide` for a full explanation of the plug-in
architecture.

Query-and-exit flags
---------------------

These flags do **not** require source files.

``--list-checkers``
    Print a table of all registered checkers — name, description, and
    declared marker IDs — then exit with code 0.

    .. code-block:: bash

       pssparser --list-checkers

``--list-markers``
    Print a table of every declared marker ID across all registered checkers
    (including the built-in ``core``), then exit with code 0.  Columns are
    ``ID``, ``SEV``, ``CHECKER``, and ``SUMMARY``.

    .. code-block:: bash

       pssparser --list-markers

``--describe ID``
    Print the full definition (summary, severity, detail, owning checker) for
    the marker with the given ID, then exit with code 0.  Exits with code 2
    and an error message if the ID is not found.

    .. code-block:: bash

       pssparser --describe PSS020

``--list-extensions``
    Print the installed checker extensions — name, version, distribution,
    description, and the checkers each one contributed — then exit with
    code 0.  This is the command that answers "where did this rule come
    from?".

    .. code-block:: bash

       pssparser --list-extensions

    .. code-block:: text

       Installed extensions (1):
         example-rules 0.1.0 [pss-rule-collection]
           Example rule collection: component and package naming
           checkers: component-naming, package-naming

``--describe-checker NAME``
    Print everything known about one checker — its description, the
    extension that provided it, every marker it can emit, and its full
    options table with types, defaults, and permitted values — then exit
    with code 0.  Exits with code 2 and a suggestion if the name is not
    registered.

    This is the answer to "what can I configure here?"; ``--list-checkers``
    is a one-line-per-checker summary and deliberately does not carry it.

    .. code-block:: bash

       pssparser --describe-checker naming-convention

    .. code-block:: text

       naming-convention
         Warn when action or struct type names do not start with uppercase

       Provided by: example-rules 0.1.0

       Markers:
         PSC001     [warning]  Action type name does not follow the configured style
         PSC002     [warning]  Struct type name does not follow the configured style

       Options:
         exempt           string-list  default: []
           Glob patterns for type names to skip, e.g. 'legacy_*'.
         style            string       default: 'PascalCase'
           Naming style required for action and struct types.
           one of: PascalCase, snake_case

``--show-config``
    Print the fully resolved configuration — every value in effect and the
    layer that set it — then exit with code 0.  See `Configuration`_.

    .. code-block:: bash

       pssparser --show-config

Checker selection flags
------------------------

``--checker NAME``
    Run *only* the named checker.  May be repeated to select multiple
    checkers.  ``NAME`` must match a registered checker's ``name`` attribute,
    or a checker previously loaded with ``--load-checker``.  Specifying an
    unknown name produces an error and exits with code 2.

    .. code-block:: bash

       pssparser --checker naming-convention model.pss

``--no-checker NAME``
    Exclude the named checker from the active set.  May be repeated.
    Silently ignored when the name is not in the registry, or when
    ``--checker`` is also specified (explicit selection takes precedence).

    .. code-block:: bash

       pssparser --no-checker deprecated-syntax model.pss

``--load-checker MODULE:CLASS``
    Dynamically import ``CLASS`` from ``MODULE`` and add it to the active
    checker set.  No package installation required.  May be repeated.  The
    loaded checker participates in ``--checker`` / ``--no-checker`` filtering
    using its ``name`` attribute.

    .. code-block:: bash

       pssparser --load-checker myproject.rules:StyleChecker model.pss

``--no-extensions``
    Skip every installed checker extension and run the built-in checks only.
    Equivalent to setting ``PSSPARSER_NO_EXTENSIONS=1`` in the environment.

    Reach for this when a diagnostic is unexpected and you need to know
    whether it came from pssparser or from something installed alongside it,
    and in any context where the result must not depend on what happens to be
    installed.

    .. code-block:: bash

       pssparser --no-extensions model.pss


Where checkers come from
========================

Checkers reach pssparser three ways, in decreasing order of permanence:

1. **An installed extension.**  A distribution declaring a
   ``pssparser.extensions`` entry point contributes a whole collection of
   checkers; installing it is all that is required, and its rules then run
   with no flags.  ``--list-extensions`` shows what is installed.
2. **An installed single checker.**  The older ``pssparser.checkers`` group
   declares one checker class per entry point.  Still supported.
3. **``--load-checker``.**  A one-off for development, requiring no
   installation.

An extension that fails to load is reported as a diagnostic (``PSS030``) and
the run continues with the rest of the registry — so a clean result is not
by itself evidence that every rule ran.  ``-Werror=PSS030`` makes a failed
extension fatal, which is usually what a CI job wants.  See
:doc:`checker_plugin_guide` for the full contract and for ``PSS031``–
``PSS033``.


Configuration
=============

Everything that can be set with a flag can also be set in a file, so a
project's rules travel with the project instead of living in whatever each
developer happens to type.

File discovery
--------------

pssparser looks for a configuration in two places, searching **upward from
the current working directory**:

1. ``.pssparser.toml`` — a dedicated file, keys at the top level.
2. ``pyproject.toml`` — the same keys under ``[tool.pssparser]``.

The walk stops at the first directory that carries either file, at a
directory containing ``.git``, or at the filesystem root.  A
``pyproject.toml`` with no ``[tool.pssparser]`` table does **not** stop the
search — almost every Python project has one, and halting there would make
a repository-root configuration unreachable from any subdirectory.

The search starts at the working directory rather than at the first source
file's directory.  That is what every other linter does, and it is what
stops ``pssparser a/x.pss b/y.pss`` from silently applying two different
configurations to two halves of one run.

``--config PATH``
    Read PATH instead of searching.  A missing or unparseable PATH is a
    usage error (exit 2), never a silent fall-through: a typo in a config
    path must not quietly change which rules run.

    ``--config`` **replaces** discovery rather than layering on top of it.
    A named file is the authoritative answer to "which rules run", and
    letting a stray ``.pssparser.toml`` two directories up keep
    contributing would defeat the point of naming one.

``--no-config``
    Ignore configuration files entirely.

Resolution order
----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Layer
     - Notes
   * - Command-line flags
     - Highest.  A flag that was not given does not count as a value.
   * - ``--config PATH``
     - Replaces the two discovery layers below.
   * - ``.pssparser.toml``
     - Found by upward search.
   * - ``pyproject.toml`` ``[tool.pssparser]``
     - Found by the same search.
   * - Declared defaults
     - ``MarkerDef.severity`` and ``options_schema`` defaults.  Lowest.

Arrays **replace** wholesale; tables **merge** entry by entry.  The
asymmetry is deliberate: an array that merged would give no way to *remove*
an entry a lower layer set, while a table that replaced would make a
one-line ``[severity]`` override silently discard the rest of the table.

``--show-config`` prints the resolved result with the source of every value.
When four layers can set ``select``, that command is the only supportable
answer to "why did this rule run?".

Schema
------

.. code-block:: toml

   # .pssparser.toml  (in pyproject.toml, prefix every table with tool.pssparser)

   version = 1                                     # schema version

   select   = ["core", "naming-convention"]        # like --checker; omit to run all
   disable  = ["acme-rules.experimental-flow"]     # like --no-checker
   load     = ["mypkg.rules:AdHocChecker"]         # like --load-checker

   [severity]
   PSC001 = "error"                                # promote a plug-in warning
   PSS114 = "off"                                  # drop it entirely

   [warnings]
   error    = true                                 # -Werror
   # error  = ["PSS110"]                           # ...or -Werror=PSS110
   no-error = ["PSS111"]                           # -Wno-error=PSS111
   none     = false                                # --no-warnings

   [checker.naming-convention]                     # NOTE: singular "checker"
   style  = "snake_case"
   exempt = ["legacy_*"]

   [extensions.acme-rules]
   enabled = false                                 # skip this extension's checkers

**The singular** ``checker`` **table is not a typo.**  TOML forbids a key
from being both an array and a table, so ``checkers = [...]`` and
``[checkers.naming-convention]`` cannot coexist in one document.  The list
keys are ``select`` / ``disable`` / ``load``; one checker's options live
under the singular ``checker``.  Writing ``checkers`` produces an error that
explains this.

Unknown keys are **rejected**, with a did-you-mean where one is plausible.
A silently ignored ``[checker.foo]`` table is a rule the user believes is
configured and is not, which is the failure this whole layer exists to
prevent.

Severity overrides
------------------

``[severity]`` re-levels a diagnostic by marker ID.  The permitted values
are ``error``, ``warning``, ``info``, ``hint``, and ``off``; ``off`` drops
the diagnostic entirely, so it is not counted and does not affect the exit
code.

Overrides are applied **before** the warning policy, so ``-Werror`` cannot
promote something the configuration already turned off.

One restriction: **a core error cannot be downgraded.**  A core error means
the model could not be built — the parse and link failure paths return a
forced exit code of 1 with no linked AST — so silencing one would report
success for a run that compiled nothing.  Attempting it is a config error
naming the key, not a silent no-op.

Per-checker options
-------------------

``[checker.<name>]`` configures one checker.  What it accepts is declared by
that checker's ``options_schema``; ``--describe-checker <name>`` prints it.
Unknown keys, wrong types, values outside a declared ``choices`` list, and
options aimed at a checker that declares none are all usage errors (exit 2),
reported at startup **before any source file is read**.

Things that stop the run
------------------------

A configuration naming something that does not exist is fail-fast, matching
``--checker``:

* ``select`` naming an uninstalled checker
* ``[checker.<name>]`` for an uninstalled checker
* ``[severity]`` naming an unknown marker ID
* ``[extensions.<name>] enabled = true`` for an uninstalled extension

The cost is real — a configuration listing a locally-installed extension
will fail in a CI job that lacks it — and it is accepted deliberately.  A
rule silently not running is worse, and a hard stop names the missing piece
where a warning gets lost in the diagnostic stream.

``enabled = false`` for an absent extension is the one exception: it asks
for nothing that is not already true, so one configuration file can serve a
development machine that has an optional extension and a CI image that does
not.


Warning policy
==============

Warnings are reported as warnings and do not affect the exit code.  Two
flag families change that.

``-Werror``
    Report every warning as an error.  The rendered message gains a
    ``[-Werror]`` suffix naming the flag responsible, so a reader can tell
    "this is an error" from "you asked for this to be an error".

    .. code-block:: bash

       pssparser -Werror model.pss

``-Werror=ID``
    Promote only the named marker.  The suffix echoes the ID back:
    ``[-Werror=PSS104]``.  May be repeated.

``-Wno-error=ID``
    Exempt the named marker from a blanket ``-Werror``.  A code-specific
    exemption always wins over the blanket promotion — that is the only way
    to spell an exception.

    .. code-block:: bash

       pssparser -Werror -Wno-error=PSS104 model.pss

``--no-warnings``
    Drop warnings entirely.  Applied *before* promotion, so
    ``--no-warnings -Werror`` reports nothing: there is no warning left to
    promote.  Only warning-severity diagnostics are affected; ``info`` and
    ``hint`` are untouched.

In ``--json``, a promoted diagnostic carries ``"severity": "error"``
alongside ``"original_severity": "warning"``, and ``summary.errors`` counts
it.  The flag spelling is a human-rendering concern and does not appear in
the JSON.

Two consequences worth stating outright:

- **A warning with no marker ID can only be promoted by a blanket**
  ``-Werror``.  There is no name to put after the ``=``.
- **``--max-errors`` does not count promoted warnings.**  The cap is enforced
  by the C++ marker collector while parsing, long before promotion happens,
  so ``-Werror --max-errors 3`` can legitimately print more than three
  errors.  The cap exists to stop parser cascades, not to bound the report.

Run statistics
==============

``--stats``
    After the summary line, write a short report to stderr: how many files
    were processed, what was declared, which diagnostic codes fired, and how
    long each phase took.  Never changes the exit code and never suppresses
    a diagnostic.

    .. code-block:: text

       0 errors in 1 file
       stats: 1 file processed
         declarations: 1 package, 1 component, 2 actions, 1 buffer, 4 fields, 1 constraint block
         timing:       stdlib 21.4ms, parse (incl. read) 2.7ms, link 0.8ms, checkers 0.1ms

``--stats-no-timing``
    As ``--stats``, but omit the timing row.  Wall times are not
    reproducible, so this is the form to use in a golden file, a regression
    harness, or documentation: two runs over the same input produce
    byte-identical output.

Counters that are zero are omitted from the human report — a model with no
streams should not have to read a line saying so.  The JSON form does the
opposite on purpose: under ``--json --stats`` the document gains a top-level
``"stats"`` key whose ``decls`` object always contains **every** counter,
even at zero, so a consumer reading ``.stats.decls.actions`` never needs a
missing-key branch.

Three details about what the numbers mean:

- Only the user's files are counted.  The standard library is parsed on
  every run but contributes nothing, and neither do the implicit members the
  linker grafts onto user types (every action gets a ``set_executor``
  prototype, for instance).
- ``parse (incl. read)`` says so because it is: the parser reads from the
  open file, so I/O cannot be separated from parsing without buffering the
  whole source first.  Reporting it as a bare "parse" would be a number that
  gets quoted wrongly.
- The standard-library load gets its own row.  It dominates a small run, and
  folding it into the user's parse time would misattribute most of the
  wall clock.
- A diagnostic whose message matches no entry in the marker-ID pattern table
  is counted under ``<uncoded>`` rather than dropped.  A non-zero
  ``<uncoded>`` count means the C++ message text has drifted from the
  table — it is a signal about the tool, not about the model.

``-q --stats`` is a supported combination: the summary line is suppressed
but the stats block still appears.

Exit codes
==========

.. list-table::
   :header-rows: 1
   :widths: 10 90

   * - Code
     - Meaning
   * - ``0``
     - No error-severity diagnostics.  Warnings may have been reported.
   * - ``1``
     - At least one error.  Includes warnings promoted by ``-Werror``, since
       the code is computed after promotion.
   * - ``2``
     - Usage problem: an unrecognised option, a missing or unreadable source
       file, an unknown ``--load-checker`` spec, or a failed ``--dump-ast``
       write.  No parsing was attempted, or its result was not reported.
   * - ``130``
     - Interrupted (``Ctrl-C``).

``--stats`` never changes the exit code.
