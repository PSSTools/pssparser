---
name: pssparser-dev
description: Develop pssparser itself, in a pssparser source checkout - change the ANTLR grammar (`PSSParser.g4`), AST definitions (`ast/*.yaml`), the builder, linker, or symbol resolution; regenerate the AST and NodeKind; rebuild; run and bless the test and error suites; update grammar-profiling baselines. Use only when working in the pssparser repository. For using pssparser from another project, use `pssparser-api`.
---

# pssparser-dev

You are working *on* pssparser, in its source checkout. Every path below is
relative to the repository root. Read the reference file for the kind of change
you are making before you start: most mistakes here are stale-artifact
mistakes, and they look like code bugs.

## 1. Orientation

| Path | What lives there |
|---|---|
| `src/PSSLexer.g4`, `src/PSSParser.g4` | ANTLR grammar (C++ target, generated at build time) |
| `src/AstBuilderInt.*` | parse tree → AST |
| `src/AstLinker.cpp` | the link pipeline: the ordered list of `Task*` passes |
| `src/NameLookup.*`, `src/ResolveContext.*`, `src/TaskResolveRef*.*` | symbol resolution |
| `src/include/pssp/impl/NodeKind.h` | generated; replaces `dynamic_cast` on AST nodes |
| `src/stdlib/*.pss` | the PSS core library, compiled in |
| `ast/*.yaml` | AST schema → generated C++ (`build/include/pssp/ast/`), Cython, and `ast.pyi` |
| `python/pssparser/` | Python package: `parser.py`, `cli/`, `checkers/`, `refs.py`, `profiling/` |
| `python/*.pyx`, `python/Py*.cpp` | Cython bindings (`ast.pyx` is generated, then copied here) |
| `ts/`, `wasm/` | TypeScript/WebAssembly package |
| `scripts/` | generators and gates (`gen_ast.py`, `gen_node_kind.py`, `refcov.py`, ...) |
| `tests/python/` | the pytest suite (there is no C++ test target) |
| `error-suite/` | tool-neutral error-reporting corpus, its own package |
| `examples/` | plug-in examples; their tests run with the suite |
| `docs/design/` | design docs, `-plan.md` trackers, `known-issues.md` |
| `packages/` | IVPM-managed dependencies (`packages/python` is the venv) |

## 2. Build-and-test loop

```bash
ivpm update                                   # once: fetch deps into packages/
python setup.py build_ext --inplace           # full build: C++ + Cython (~5 min)
cmake --build build && cmake --install build  # C++-only edit (~20 s)
PYTHONPATH=python python -m pytest tests/python -q
```

Use the venv's interpreter (`packages/python/bin/python`, or run under
`direnv exec .`). The traps, each detailed in `references/build.md`:

- **`cmake --build` alone tests old code.** The extension loads
  `build/lib/libpssparser.so`, which only the *install* step refreshes.
- **A failed `build_ext` leaves the old extension importable.** Tests then pass
  against stale code. Grep the build output for `error:` before trusting a run.
- **`PYTHONPATH=python` is not optional**, for pytest and for `gdb`. Without it
  `import pssparser` may resolve to another checkout's copy.
- **Never run two builds at once.** They share outputs and produce a binary
  that crashes mid-test.

## 3. Change recipes

Pick the row that matches the change, then read its reference.

| Change | Essentials | Read |
|---|---|---|
| Build, rebuild, debug a crash | build modes, stale-library traps, gdb | `references/build.md` |
| Add/rename/remove an AST class or field | edit `ast/*.yaml` → build → `scripts/gen_node_kind.py` → build again | `references/ast-regen.md` |
| Grammar change | edit `.g4` → build → re-bless `docs/profiling/baseline.json` and `tests/python/baselines/grammar.json` | `references/grammar.md` |
| Name resolution, linking, extensions, templates | which pass, `NameLookup`, `NodeKind` instead of `dynamic_cast` | `references/linker.md` |
| New or changed diagnostic | message → core marker ID in `core_checker.py` → `docs/markers.rst` → goldens | `references/error-suites.md` |
| Error-suite case or corpus edit | header edits shift line numbers; use the tools | `references/error-suites.md` |
| Tests: where, how, subprocesses, corpus | suite layout, isolation rules, baselines | `references/testing.md` |
| Recording status, deferring a defect, cross-repo work, CHANGELOG | where each kind of note goes | `references/conventions.md` |

## 4. Rules that apply to every change

1. **Import the core library explicitly.** No core-library package is
   implicitly visible. Any model (test, corpus file, example) that uses
   `print`, `message`, `sizeof_s`, `packed_s`, `urandom`, `@doc`, ... needs
   `import std_pkg::*;`. Importing `addr_reg_pkg` does not re-export them.
2. **No `dynamic_cast` on AST nodes in `src/`.** Use `NodeKind`
   (`tests/python/test_no_ast_dynamic_cast.py` enforces it).
3. **Every diagnostic has an ID.** A new C++ message needs a matching
   `MarkerDef` pattern, or it surfaces without a code.
4. **Messages stay under 120 characters** (lint G7 in
   `tests/python/errors/test_message_lints.py`).
5. **Gates fail on drift in either direction.** When a change legitimately
   moves a baseline (references, occurrences, grammar, profiling, goldens),
   regenerate it in the same change and read the diff first.
6. **Read the LRM from the PDF** (`pdftotext -layout`), never from a Markdown
   conversion: those corrupt Annex B and Table 3.
7. **Full suite before you call it done**, not just the file you touched. Link
   changes routinely break unrelated corpus files.

## 5. Where work is tracked

- A project has a design doc (`docs/design/<topic>.md`) and a separate tracker
  (`docs/design/<topic>-plan.md`). Status goes in the tracker, never in the
  reviewed design.
- Deferred, understood defects go in `docs/design/known-issues.md`.
- Changes another repository needs go in `docs/design/cross-repo-followups.md`.
- User-visible changes get a `CHANGELOG.md` entry under `## Unreleased`.

Details and formats: `references/conventions.md`.
