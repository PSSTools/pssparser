---
name: pssparser
description: Check Portable Test and Stimulus Standard (PSS) source files (`.pss`) for syntax and semantic errors, and lint them, with the `pssparser` command. Use when the user wants to validate, compile-check, or lint PSS code; interpret a pssparser diagnostic (an ID like `PSS042`); select or configure checkers; set warning severities or `-Werror`; write a `.pssparser.toml`; or run pssparser in CI.
---

# pssparser: check and lint PSS

`pssparser` is a front end for the Portable Test and Stimulus Standard
(PSS 3.1). It parses and links `.pss` files, reports syntax and semantic
errors, and runs lint checkers over the linked model. Checking and linting are
the same command; flags and a configuration file decide which rules run and
how strictly.

## Check files

Pass every file that makes up the model in one command. All the files form one
compilation unit, so a type declared in `a.pss` is visible in `b.pss`, and
the order of the files does not matter:

```bash
pssparser pkg.pss top.pss
```

Checking a file on its own reports every name it uses from another file as
unknown. When you see `unknown type` for a type you know exists, add the file
that declares it to the command line before changing any code.

The run has three phases, and each runs only if the one before it succeeded:

1. **Parse.** Syntax errors. Parsing stops at the first file that has syntax
   errors, so later files are not reported yet.
2. **Link.** Name resolution and semantic errors (unknown types, duplicate
   declarations, bad calls).
3. **Checkers.** Lint rules over the linked model; usually warnings.

`--syntax-only` stops after phase 1. `--max-errors N` caps the errors
reported per file (default 20; `0` means no limit); a capped file ends with
`PSS029`.

### Import the core library

The PSS core library (`print`, `std_pkg` types, and so on) is **not**
visible by default. Import it in every file or package that uses it:

```pss
import std_pkg::*;

component pss_top {
    action hello {
        exec body {
            print("hello");
        }
    }
}
```

Without the import, pssparser reports
`unknown identifier 'print'; declared in std_pkg -- add 'import std_pkg::*;'`.
This is the most common "unresolved symbol" surprise; fix it by adding the
import, not by declaring the function yourself.

## Read a diagnostic

Human output goes to **stderr**, one block per diagnostic, then a summary:

```text
top.pss:3:18: error: expected ';' after 'x' in action 'A'
 3 |     rand bit[8] x
   |                  ^
   |                  ;
  note: action 'A' begins here
   --> top.pss:2:12
   2 |   action A {
     |            ^

1 error in 1 file
```

- The header is `file:line:col: severity: message`. Lines and columns are
  1-based.
- A line under the caret (here `;`) is a suggested replacement.
- `note:` lines are related locations that explain the error.
- The human output does **not** print the marker ID. To get the ID, run
  with `--json` and read the `code` field.

Explain any ID with `pssparser --describe ID`, for example
`pssparser --describe PSS002`. Prefer this to guessing from the message: the
description lists the message variants and the usual fix. List every ID
with `pssparser --list-markers`.

Exit codes: `0` no errors (warnings allowed), `1` at least one error, `2`
usage error (bad flag, missing file, bad configuration), `3` internal error
in pssparser (`PSS000`; report it, do not work around it in the model).

For the JSON format, every field, and the query commands, read
`references/diagnostics.md`.

## Fix errors: the loop

1. Run pssparser on the whole model.
2. Fix the **first** error only.
3. Run again.

Errors cascade: one missing `;` or unknown type can produce several later
errors that disappear once the first is fixed, and link errors only appear
once every file parses. Do not batch-fix from one run's output. When you read
the output from a script, use `--json` (a single JSON document on stdout) and
apply a `fix` object when one is present: it is an exact edit.

## Lint

The built-in `core` checker is always present. Its warnings (for example
`PSS053`, an import after a declaration) are lint findings. Installed
extensions add more checkers. Find out what is available before configuring:

```bash
pssparser --list-checkers
pssparser --list-extensions
pssparser --describe-checker core
```

Select and tune rules on the command line:

| Goal | Flag |
|---|---|
| Run only some checkers | `--checker NAME` (repeatable) |
| Skip a checker | `--no-checker NAME` (repeatable) |
| Built-in checks only | `--no-extensions` |
| Try a checker without installing it | `--load-checker MODULE:CLASS` |
| All warnings are errors | `-Werror` |
| One warning is an error | `-Werror=ID` |
| Exempt one ID from `-Werror` | `-Wno-error=ID` |
| Drop all warnings | `--no-warnings` |

`--checker` with a name that is not installed is a usage error (exit 2).
`-Werror=ID` does not check that the ID exists, so copy the ID from
`--list-markers` or `--json` output rather than typing it from memory.

For settings that should travel with the project (checker selection,
per-ID severities, checker options), write a `.pssparser.toml` or a
`[tool.pssparser]` table in `pyproject.toml`. Read
`references/lint-config.md` before writing one; `pssparser --show-config`
prints the result with the source of every value.

## CI

Gate on the exit code, add `-Werror` (or a `[warnings]` table) to make
warnings fail the build, and pin the pssparser version. Read
`references/ci.md` for a worked job.

## Going further

- Write a new lint rule, or package a rule collection: use the
  `pssparser-checkers` skill.
- Read a PSS model from Python (generators, analyzers, documentation tools):
  use the `pssparser-api` skill.
