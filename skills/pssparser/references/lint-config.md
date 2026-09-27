# Lint configuration reference

Put a project's lint settings in a file so every developer and every CI job
runs the same rules. Everything a flag can set, the file can set.

## Where the file goes

pssparser reads one of:

- `.pssparser.toml`: keys at the top level.
- `pyproject.toml`: the same keys under `[tool.pssparser]` (prefix every
  table, for example `[tool.pssparser.severity]`).

It searches **upward from the current working directory**, not from the
source files. The search stops at the first directory that has either file,
at a directory containing `.git`, or at the filesystem root. A
`pyproject.toml` without a `[tool.pssparser]` table is skipped. If a
directory has both, both are read, and `.pssparser.toml` wins.

So: put the file at the repository root and run pssparser from inside the
repository. Running from outside it finds no configuration.

- `--config PATH` reads `PATH` instead of searching. A missing file is exit 2.
- `--no-config` ignores all configuration files.

Always confirm what is in effect, and where each value came from:

```bash
pssparser --show-config
```

## Schema

```toml
version = 1                       # schema version; optional

select  = ["core", "acme-naming"] # like --checker; omit to run every checker
disable = ["acme-experimental"]   # like --no-checker
load    = ["mypkg.rules:MyRule"]  # like --load-checker (module:Class)

[severity]                        # re-level a diagnostic by ID
PSS053 = "error"                  # error | warning | info | hint | off

[warnings]
error    = true                   # -Werror; or a list of IDs: ["PSS053"]
no-error = ["PSS104"]             # -Wno-error=ID
none     = false                  # --no-warnings

[checker.acme-naming]             # one checker's options (singular "checker")
style = "snake_case"

[extensions.acme-rules]
enabled = false                   # skip every checker from this extension
```

The checker and extension names above are placeholders. Take real names from
`pssparser --list-checkers` and `pssparser --list-extensions`, and a
checker's options from `pssparser --describe-checker NAME`.

### Rules the schema enforces

Configuration mistakes are errors (exit 2) that name the file and key, never
silent no-ops. Expect these:

- **Unknown keys are rejected**, with a did-you-mean. The common trap is
  `checkers = [...]` or `[checkers.x]`: the list keys are
  `select`/`disable`/`load`, and per-checker options go under the
  **singular** `[checker.<name>]`.
- **Names must exist.** `select` or `[checker.<name>]` naming a checker that
  is not installed, `[severity]` naming an unknown ID, and
  `[extensions.<name>] enabled = true` for an extension that is not installed
  all stop the run. `enabled = false` for an absent extension is allowed, so
  one file can serve machines with and without an optional extension.
- **Options are checked** against the checker's declared schema (names,
  types, allowed values). A checker that declares no options rejects any
  `[checker.<name>]` table; `core` is one of those.
- **Core errors cannot be downgraded.** `PSS002 = "warning"` is rejected:
  a core error means the model could not be built.
- `version` greater than this pssparser understands is rejected; omit it or
  set `1`.

## Precedence

Highest first:

1. Command-line flags (only the ones actually given).
2. `--config PATH`, which replaces the two below.
3. `.pssparser.toml`.
4. `pyproject.toml` `[tool.pssparser]`.
5. Declared defaults (each marker's severity, each option's default).

**Arrays replace; tables merge.** A `select` on the command line replaces the
file's `select` entirely. A `[severity]` entry changes only that ID and
leaves the rest of the table in force.

## Severity versus warning policy

The two are applied in order:

1. `[severity]` sets what each diagnostic *is*. `"off"` drops it: not
   printed, not counted, no effect on the exit code.
2. The warning policy (`-Werror`, `-Werror=ID`, `-Wno-error=ID`,
   `--no-warnings`, or `[warnings]`) then acts on whatever is still a
   warning.

Consequences:

- An ID set to `"off"` stays off under `-Werror`.
- An ID set to `"info"` or `"hint"` is not a warning, so `-Werror` does not
  promote it and `--no-warnings` does not drop it.
- `--no-warnings` runs before promotion, so `--no-warnings -Werror` reports
  no warnings at all.
- `-Wno-error=ID` always beats a blanket `-Werror`.

## Silencing a diagnostic

Choose the narrowest tool:

| You want | Use |
|---|---|
| One ID never reported | `[severity]` `ID = "off"` |
| One ID reported but never fatal | `ID = "info"`, or `-Wno-error=ID` under `-Werror` |
| All of one extension's checkers off | `[extensions.<name>] enabled = false` |
| One checker off | `disable = ["<name>"]` or `--no-checker NAME` |
| Only built-in checks | `--no-extensions` |

`--no-checker core` does **not** silence parser or linker diagnostics; they
are produced while building the model, not by a lint pass. Use `[severity]`
for those.

Before silencing, run `pssparser --describe ID`: many warnings point at
real problems (an import after a declaration, an enum item that hides a
declaration).

## Worked example

A project that wants every warning to fail CI, except one it has accepted,
and one rule turned off:

```toml
# .pssparser.toml at the repository root
version = 1

[warnings]
error    = true
no-error = ["PSS104"]

[severity]
PSS053 = "off"
```

Check it:

```bash
pssparser --show-config
pssparser src/*.pss
```

`--show-config` should list `warnings.error = true`, `warnings.no-error =
PSS104`, and `severity.PSS053 = off`, each with `.pssparser.toml` as the
source.
