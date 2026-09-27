# Diagnostics, marker IDs, and the error suites

## Adding or changing a diagnostic

Core diagnostics are emitted by C++ (builder, linker) as plain messages. The
**ID is assigned in Python** by matching the message against the `patterns` of
the `MarkerDef`s in `python/pssparser/checkers/core_checker.py`
(`CoreChecker.marker_defs`). The C++ message text is therefore part of the
contract, and nothing in the build checks it: the tests below do.

To add a diagnostic:

1. Emit it in C++ with a specific message: name the construct and the
   identifier, and say what to write instead where there is one. Keep it under
   120 characters (lint G7). Attach related locations rather than lengthening
   the message.
2. Allocate the next free ID in the right band and add a `MarkerDef`: `id`,
   `severity`, `summary`, `patterns` (anchored regexes), `detail` (what
   `--describe` prints). Bands, per `docs/markers.rst`: the general band
   starts at PSS001 (PSS020–PSS028 is its syntax sub-band); PSS100 onwards
   holds the PSS 3.1 language rules. Check the tracker you are working from for
   the next free code, and grep `core_checker.py` to confirm it is unused.
3. Add a representative message to `REPRESENTATIVE_MESSAGES` in
   `tests/python/test_marker_ids.py`: it proves the message maps to the ID and
   that no other pattern shadows it.
4. Regenerate the reference page:
   `PYTHONPATH=python python scripts/gen_marker_docs.py`
   (`tests/python/cli/test_marker_docs.py` fails if `docs/markers.rst` is stale).
5. Add a test that triggers it from a real model and asserts the code, line and
   column. Then add a CHANGELOG entry naming the code.

Rewording an existing message: check its `MarkerDef` pattern still matches,
then run `tests/python/errors` (goldens, corpus) and the error suite. A message
that no pattern matches surfaces with no code.

The global message lints are `tests/python/errors/test_message_lints.py`. Every
current violation is listed in `tests/python/errors/lint_allowlist.txt` with an
owner and reason; stale entries fail, so delete a line when its violation goes.

## Two corpora

| | `error-suite/` | `tests/python/errors/` |
|---|---|---|
| What | tool-neutral error-reporting suite, its own package (`pss_errsuite`) | pssparser's pytest over the same cases, plus goldens and sweeps |
| Cases | `error-suite/cases/{syntax,semantic,accept}/**.pss` | reads `error-suite/cases/` (`test_corpus.py`) |
| Run | `python3 -m pss_errsuite run --tool tools/pssparser-cli.toml --out runs/pssparser.json` (from `error-suite/`) | `PYTHONPATH=python python -m pytest tests/python/errors` |

The run output under `error-suite/runs/` is not committed. The error suite is
stdlib-only and must stay installable on its own: nothing in it may import
pssparser.

### Case headers

A case is a `.pss` file whose first lines are `//!` directives:

```text
//! case:    SEM-31-ENUM-BASE-01
//! class:   semantic.31
//! expect:  error
//! detect:  required
//! at:      16:14
//! fix:     16:     enum e : int {
//! cause:   enum
//! names:   e
//! pssparser.id:    PSS...
//! pssparser.match: <regex>
```

Neutral keys (`at:`, `also:`, `fix:`, `cause:`, `names:`, `count:`, `lrm:`,
`files:`, `at-file:`, ...) describe the defect. Namespaced keys
(`pssparser.id:`, `pssparser.match:`, `pssparser.at:`, `xfail.pssparser:`,
`pssparser.max-errors:`) are pssparser's expectations and are read only by
`tests/python/errors/corpus_loader.py`. A sibling `<case>.ok.pss` is the
corrected control and must link clean.

The two readers (`pss_errsuite.case` and `corpus_loader.py`) must parse headers
identically; a test asserts they extract the same facts from every case.

### Header edits shift line numbers

The header is part of the file the tool sees, so adding or removing a `//!`
line moves every body line. All of these count from line 1 and must move
together:

- `at:`, `also:`, `fix:`;
- `pssparser.at:` (invisible to the neutral runner, so only
  `tests/python/errors/test_corpus.py` catches it);
- goldens in `tests/python/errors/data/golden/*.txt`;
- the `.ok.pss` control, kept line-aligned.

Exception: when `at-file:` names a *companion* file, `at:` counts from that
file's line 1 and must **not** move.

Do not edit these by hand. Author `cause:`/`names:` terms in
`error-suite/tools/cause_terms.py` (a literal comma in a term is `\,`) and run:

```bash
cd error-suite
python3 tools/backfill_cause.py --dry-run
python3 tools/backfill_cause.py
```

It renumbers every directive (both span forms, `L:C-C` and `L:C-L:C`), honours
the `at-file:` exception, and keeps the control aligned.

Verify with a full error-suite run before and after the edit: zero status
changes, and every primary diagnostic at the same body-relative position. That
does not see `pssparser.at:`, so also run `tests/python/errors`.

### Goldens

`tests/python/errors/test_golden.py` compares rendered CLI output with
`tests/python/errors/data/golden/*.txt`. After a deliberate change, read every
diff, then re-bless:

```bash
PYTHONPATH=python python -m pytest tests/python/errors/test_golden.py --bless-errors
```

The mutation sweep (`test_mutation_sweep.py`) runs a fixed sample by default;
run `pytest tests/python/errors --errors-full` for the
exhaustive sweep. Its invariant is "no crash on any input".

## When a message improves, the case may be the stale one

Many case headers were recorded from what the tool *did*: an `at:` on the
token after a missing `;`, a `pssparser.match:` pinning a cascade rather than
the cause. Before changing a case to match new output, check it against its
own `fix:` line and its `.ok.pss` control. If the case contradicts its own
`fix:`, the case is wrong; fix the case.

Scores from the error-suite rubric are a guide, not a target. A coarser rule
can score higher while swallowing a real second defect. Re-run the pytest
corpus after every rubric change, and report any dimension mean with its `n`.
