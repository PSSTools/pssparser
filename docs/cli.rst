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

Checker selection flags
------------------------

``--checker NAME``
    Run *only* the named checker.  May be repeated to select multiple
    checkers.  ``NAME`` must match a registered entry-point name or a checker
    previously loaded with ``--load-checker``.  Specifying an unknown name
    produces an error and exits with code 2.

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
