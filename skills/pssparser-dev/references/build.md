# Building pssparser

## Setup

```bash
ivpm update                 # fetches packages/: antlr4, pyastbuilder, pss-corpus, the venv
```

The venv is `packages/python`. `direnv` loads `packages/packages.envrc`, so
under `direnv exec .` (or an allowed `.envrc`) `python` is the venv's. Outside
direnv, call `packages/python/bin/python` explicitly.

`ivpm-build` must be installed in the venv: `setup.py` imports
`ivpm_build.setup` and refuses to fall back to plain setuptools, because only
the IVPM backend runs the AST code generation and copies the generated sources.

## Three build modes

| Mode | Command | Use for | Time |
|---|---|---|---|
| Full | `python setup.py build_ext --inplace` | first build; AST schema changes; any `.pyx`/`Py*.cpp` change | ~5 min |
| C++ only | `cmake --build build && cmake --install build` | edits to `src/*.cpp`/`.h`, grammar | ~20 s |
| Metadata only | `python setup.py egg_info` | entry points or package data changed | seconds |

What the full build does: configures CMake into `build/`, builds antlr4, runs
`scripts/gen_ast.py` (an `ExternalProject` step), builds `libast` and
`libpssparser`, installs them into `build/lib`, copies the generated
`ast.pyx`, `ast.pxd`, `ast_decl.pxd`, `ast.pyi`, `PyBaseVisitor.*` into
`python/`, and compiles the `pssparser.core` and `pssparser.ast` extensions in
place (`python/pssparser/*.so`).

The cost is dominated by the generated `ast.cpp` (hundreds of thousands of
lines). Avoid the full build when a C++-only one is enough.

## Stale-artifact traps

These all produce a green or plausible-looking run against old code.

- **`cmake --build build` without `cmake --install build`.** The Python
  extension loads `build/lib/libpssparser.so`; `cmake --build` updates
  `build/src/` only. You test the previous library.
- **`cmake` alone never builds the Python extensions.** A new AST class is
  invisible from Python until `build_ext --inplace` has run.
- **A failing `build_ext` leaves the previous extension in place.** The suite
  imports it happily. Always check the build output for `error:` before trusting
  a test result, especially when reverting a fix to prove a test guards it.
- **Concurrent builds.** Two `build_ext` (or a `build_ext` and a `cmake
  --build`) write the same outputs. The result links, loads, and segfaults.
- **Stale egg-info.** Entry points (`console_scripts`, `agent.skills`) are read
  from `python/pssparser.egg-info`. After editing `entry_points` in `setup.py`,
  run `python setup.py egg_info`.
- **Adding a new `ast/*.yaml` file** needs CMake to re-run (`cmake -B build -S
  .`): the spec list is globbed at configure time.

## Which pssparser did you import?

Always run with `PYTHONPATH=python`. Other checkouts on the machine (sibling
projects under `packages/` of other repos) may have their own pssparser, and
without the path you import theirs: edits appear to have no effect, and
backtraces name plausible symbols in the wrong binary.

```bash
PYTHONPATH=python python -c "import pssparser, pssparser.core as c; print(pssparser.__file__, c.__file__)"
```

## Debugging a crash

```bash
PYTHONPATH=python gdb -q -batch -ex run -ex bt -ex quit --args python repro.py
```

Before trusting a backtrace, check `info sharedlibrary pssparser` in gdb and
confirm the loaded `.so` paths are under this checkout.

Crashes that appear only under pytest, not standalone, are usually lifetime
bugs in the Python caller: see "AST lifetime" in `testing.md`. A crash in the
linker should instead surface as a PSS000 marker: `AstLinker::link` catches
every exception and reports the pass it escaped from. A process abort means an
exception crossed into Cython without `except +`.

Sanitizer builds are described in `docs/sanitizers.rst`.

## WebAssembly

`scripts/wasm-env.sh` sets up emsdk (project-local `.emsdk/`); the package is
in `ts/` and `wasm/`. It builds the same C++ sources, so a C++ change can break
it without breaking the Python build.
