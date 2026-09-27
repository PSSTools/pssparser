# Diagnostics reference

How to read pssparser's output, in both forms, and how to ask the tool what a
diagnostic means.

## Contents

- Human output
- JSON output (`--json`)
- Exit codes
- Asking the tool: `--describe`, `--list-markers`, `--list-checkers`
- IDs that mean "pssparser is wrong"
- Run statistics

## Human output

Written to **stderr**. Each diagnostic is a header line, the source line with
a caret under the span, an optional suggestion line, and optional `note:`
blocks for related locations:

```text
b.pss:2:37: error: unknown type 's'; did you mean 'set'?
 2 | component pss_top { action A { rand s v; } }
   |                                     ^
   |                                     set

2 errors in 1 file
```

- `file:line:col` is 1-based.
- Severity is one of `error`, `warning`, `info`, `hint`.
- A suffix `[-Werror]` or `[-Werror=ID]` means a warning was promoted by that
  flag (or by the `[warnings]` table in the configuration).
- A diagnostic with no source location (for example, an extension that failed
  to load) is printed as `pssparser: warning: ...`.
- The last line is the summary, such as `2 errors, 1 warning in 3 files` or
  `0 errors in 1 file`. `-q` suppresses it.
- `did you mean` suggestions are spelling matches only. The one above
  suggests the built-in `set` type; the real cause was a missing file on the
  command line. Check that before taking the suggestion.

The ID (`PSS002` and so on) is **not** printed in human output. Use `--json`
to get it.

Colour is on when stderr is a terminal. Force it with `--color`, turn it off
with `--no-color` or by setting `NO_COLOR` in the environment.

## JSON output (`--json`)

`--json` writes one JSON document to **stdout** after the run, and nothing to
stderr for the diagnostics themselves:

```json
{
  "diagnostics": [
    {
      "file": "syn.pss",
      "line": 3,
      "col": 18,
      "severity": "error",
      "message": "expected ';' after 'x' in action 'A'",
      "end_col": 19,
      "suggestion": ";",
      "fix": {
        "file": "syn.pss", "line": 3, "col": 18,
        "end_line": 3, "end_col": 18, "replacement": ";"
      },
      "code": "PSS020",
      "related": [
        {"file": "syn.pss", "line": 2, "col": 12, "label": "action 'A' begins here"}
      ]
    }
  ],
  "summary": {"errors": 1, "warnings": 0, "files": 1}
}
```

Always present in a diagnostic: `file`, `line`, `col`, `severity`, `message`.
Present only when they apply:

| Field | Meaning |
|---|---|
| `code` | Marker ID. Absent only for a message no pattern matches. |
| `end_col` | Column just past the end of the primary span. |
| `suggestion` | Replacement text, as shown under the caret. |
| `fix` | A machine-applicable edit: replace `line:col`..`end_line:end_col` in `file` with `replacement`. An insertion has `col == end_col`. Apply `fix`, not `suggestion`, when editing. |
| `related` | Secondary locations, each `{file, line, col, label}`. |
| `original_severity` | Set when `-Werror` promoted the diagnostic; `severity` is then `"error"`. |

`summary.errors` counts promoted warnings. With `-q`, `--json` prints nothing
unless `--stats` or `--stats-no-timing` is also given.

Read it with a JSON tool rather than by scraping text, for example:

```bash
pssparser --json top.pss | jq -r '.diagnostics[] | "\(.code) \(.file):\(.line) \(.message)"'
```

## Exit codes

| Code | Meaning |
|---|---|
| `0` | No error-severity diagnostics. Warnings may have been reported. |
| `1` | At least one error, including warnings promoted by `-Werror`. |
| `2` | Usage error: unknown option, missing source file, no source file given, unknown checker name, invalid configuration file, unknown `--describe` ID. Nothing was checked. |
| `3` | Internal error in pssparser (`PSS000`). The result is not trustworthy. |
| `130` | Interrupted. |

`--stats` never changes the exit code.

## Asking the tool

These commands need no source files. Their output is the authoritative list
for the installed version, including any installed extensions; do not rely on
a remembered list.

```bash
pssparser --list-markers              # every ID: ID, SEV, CHECKER, SUMMARY
pssparser --describe PSS002           # summary, severity, owner, full explanation
pssparser --list-checkers             # checker names and the IDs each declares
pssparser --describe-checker core     # one checker's markers and its options
pssparser --list-extensions           # installed extensions and their checkers
```

`--describe` with an unknown ID exits 2 and says so. The explanation it prints
lists the message variants that map to the ID and the usual fix, which is
usually faster than reasoning from the message alone.

## IDs that mean "pssparser is wrong"

Most diagnostics are about the model. These are about the tool:

- `PSS000`: internal error. Exit code 3. Report it with the input that
  triggers it.
- `PSS042`: a reference was left unbound. The summary says "(pssparser
  defect)". The model may be fine.
- `PSS030`: an installed checker extension failed to load, so its rules did
  not run. A clean result does not mean every rule ran. `-Werror=PSS030`
  makes this fatal.

Run `pssparser --describe` on any of them for details. If you suspect a
diagnostic comes from an extension rather than from pssparser itself, rerun
with `--no-extensions`.

## Run statistics

`--stats` adds a report to stderr after the summary: files processed,
declaration counts, which codes fired, and phase timings. `--stats-no-timing`
is the same without the wall times, so its output is reproducible (use it in
golden files and CI logs you compare):

```text
0 errors in 1 file
stats: 1 file processed
  declarations: 1 component, 1 action, 1 field, 1 constraint block, 1 import
```

With `--json`, the document gains a `stats` object: `files`, `decls` (every
counter, including zeros), and `diagnostics_by_code`.

`--dump-ast OUT` writes the linked AST to `OUT` as JSON, for inspection. To
work with the AST programmatically, use the `pssparser-api` skill instead.
