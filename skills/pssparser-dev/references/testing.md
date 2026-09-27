# Testing pssparser

The suite is pytest only (there is no C++ test target). `pytest.ini` collects
`tests/python`, `error-suite/tests` and `examples`.

```bash
PYTHONPATH=python python -m pytest -q                        # everything
PYTHONPATH=python python -m pytest tests/python/linking -q   # one area
PYTHONPATH=python python -m pytest -m "not slow" -q
```

Run the full suite before calling a change done. Linker changes in particular
break corpus files far from the code you touched.

## Layout

| Directory | Covers |
|---|---|
| `tests/python/parsing/` | grammar and builder: does the surface parse into the right AST |
| `tests/python/linking/` | resolution, extensions, templates, imports, occurrences |
| `tests/python/errors/` | diagnostics: codes, locations, messages, goldens, the error corpus, crash safety |
| `tests/python/cli/` | the `pssparser` command, config, JSON output, marker docs |
| `tests/python/checkers/` | checker API, extension discovery and install |
| `tests/python/corpus/` | sweeps over the shared pss-corpus |
| `tests/python/profiling/` | grammar-profiling harness and baseline gate |
| `tests/python/tokens/`, `source_references/` | token stream, CST, source locations |
| `tests/python/skills/` | the agent skills in `skills/` |
| `tests/python/baselines/` | JSON/YAML baselines for refcov, occgate, grammar coverage |
| `tests/python/test_*.py` | cross-cutting lints: marker IDs, NodeKind, generated bindings, AST inventory |

Markers (see `pytest.ini`): `slow`, `corpus`, `profiling`, `needs_install`
(pip-installs into a temp dir), `needs_pssparser` (error-suite tests that need
a build). Strict markers are on: declare a new marker there.

## Writing a test

Prefer a small, complete model inline, parsed with `parses`, and assert on
what matters: the marker code, line and column for a diagnostic; the resolved
target for a resolution. Every model that uses core-library names must
`import std_pkg::*;` (import is not re-export: `import addr_reg_pkg::*;` does
not bring in `packed_s` or `sizeof_s`).

```python
from pssparser import Parser

SRC = """
import std_pkg::*;
component pss_top {
    action A {
        exec post_solve { print("hello"); }
    }
}
"""

p = Parser()
p.parses([("top.pss", SRC)])
root = p.link()          # raises ParseException on error; keep `root` alive
errors = [m for m in p.markers if m["severity"] == "error"]
assert not errors, errors
```

Fixtures in `tests/python/conftest.py`: `parser`, `factory`,
`profiling_parser`, `sample_component`, `multi_file_project`. Template-heavy
tests have helpers in `tests/python/template_helpers.py`.

For a bug fix, confirm the test fails without the fix. Revert the fix, rebuild,
and check the build output for `error:`: a failed build leaves the old
extension importable and the test "passes".

### AST lifetime

- Every accessor returns a new Python wrapper. Never key a visited set on
  `id(node)`: ids are neither stable nor unique over a walk.
- Keep the linked root alive, not only the `Parser`. A helper that parses,
  digs out one node and returns only that node drops the root, and the tree goes
  with it. It shows up as a crash under pytest only (assertion rewriting
  allocates enough to reuse the freed memory).

## Subprocesses must import the parent's pssparser

CI runs the suite against an **installed wheel**, and the source tree there has
no compiled extension. A child process that puts `<repo>/python` first on its
path imports a `pssparser` with no `core` and fails with
`No module named 'pssparser.core'`. Locally it passes, because
`build_ext --inplace` puts the `.so` in the tree.

- In tests, use `tests/python/isolation.py`: `run_isolated`,
  `assert_no_crash`, `assert_clean`, or `_parent_package_root()` for your own
  child environment.
- In scripts, follow `_pssparser_root()` in `scripts/refcov.py` /
  `scripts/occgate.py` (the tree if it has a built `core*.so`, else the
  parent's import).
- Never hard-code `ROOT / "python"` on a child's `PYTHONPATH`, and never
  `sys.path.insert` it in a child.

To reproduce the CI situation locally, copy the repository without `*.so` and
import pssparser from a separate directory holding `python/pssparser` plus the
built extensions.

Crash-freedom tests must be out of process: a segfault takes the interpreter
with it. `IsolatedResult.crashed` handles the sign convention (signal death is
a *negative* return code from `subprocess`).

## Installed extensions pollute tests

Checker extensions are discovered from every `.dist-info`/`.egg-info` on
`sys.path`. A stray `src/*.egg-info` (from building an example; gitignored, so
invisible to `git status`) makes that example's rules fire inside unrelated
tests, which reads as order-dependent flakiness. The autouse fixture in
`tests/python/conftest.py` sets `PSSPARSER_NO_EXTENSIONS=1` for this reason. Do
not remove it. A test that needs real discovery deletes the variable in its own
fixture:

```python no-check
monkeypatch.delenv("PSSPARSER_NO_EXTENSIONS", raising=False)
```

## The shared corpus (pss-corpus)

`packages/pss-corpus` (fetched by `ivpm update`, or a sibling `../pss-corpus`,
or `$PSS_CORPUS`) is a corpus of PSS models shared by several tools (pssparser,
pssfmt, and others). `tests/python/corpus/test_pss_corpus.py` sweeps it
out of process:

- `parses = true` buckets: every file parses. Files that do not parse today
  are listed in `KNOWN_UNPARSEABLE` as strict xfails, so a fix fails the suite
  until the entry is removed (in pssfmt too, via `cross-repo-followups.md`).
- `parses = false` buckets: every file is rejected with a diagnostic, never a
  crash.

When a plan calls for a body of legal models (for example completed LRM
examples), add them to pss-corpus as a new bucket, not as another local example
suite. Record pssparser's current failures on this side (xfail or known-failing
list); the corpus manifest describes the files, not a consumer's bugs.

LRM examples are fragments and must be *completed*, not transcribed:

- wrap bare `action`s in a `component` (a package cannot hold an action;
  check the file's existing idiom);
- expand or delete every `...` elision;
- declare every referenced type, and add `import std_pkg::*;` where needed;
- parse and link the file before committing it.

A corpus addition moves the refcov, occgate and grammar-coverage baselines;
regenerate them (see `linker.md`, `grammar.md`).

## Baseline gates

| Gate | Check | Regenerate |
|---|---|---|
| references bound/reported | `scripts/refcov.py check` | `scripts/refcov.py baseline` |
| occurrences | `scripts/occgate.py check` | `scripts/occgate.py baseline` |
| grammar coverage | (report only) | `scripts/grammar_cov.py baseline` |
| grammar profiling | `tests/python/profiling/test_baseline.py` | `scripts/profile_grammar.py --write-baseline docs/profiling/baseline.json` |
| NodeKind | `tests/python/test_node_kind_generated.py` | `scripts/gen_node_kind.py` |
| marker docs | `tests/python/cli/test_marker_docs.py` | `scripts/gen_marker_docs.py` |
| error goldens | `tests/python/errors/test_golden.py` | `pytest tests/python/errors/test_golden.py --bless-errors` |

Run each script as `PYTHONPATH=python python scripts/<name>.py ...`. Every gate
fails on drift in either direction. Read the diff; regenerate in the same
change.
