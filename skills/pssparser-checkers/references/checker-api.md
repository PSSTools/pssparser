# Checker API reference

Everything a checker touches is in `pssparser.checkers`:

```python
from pssparser.checkers import (
    API_VERSION, CheckContext, CheckerBase, ExtensionRegistry, MarkerDef)
print(API_VERSION)
```

## `CheckerBase`

Subclass it and set class attributes. pssparser creates a fresh instance per
run, calls `configure()` (only if you declared options), then `check()`.

| Attribute / hook | Required | Meaning |
|---|---|---|
| `name` | yes | Unique slug. Used by `--checker`, `--no-checker`, `--describe-checker`, and `[checker.<name>]`. An empty name is rejected at registration. |
| `description` | yes | One line, shown by `--list-checkers` and `--describe-checker`. |
| `marker_defs` | yes | A list of `MarkerDef`, one per ID the checker can emit. Declare a new list in each subclass; do not mutate the inherited one. |
| `runs_without_link` | no | Default `False`. Set `True` if the checker needs only the parse tree; it then also runs under `--syntax-only`. |
| `options_schema` | no | `{option: spec}`; see below. Default: no options. |
| `configure(self, options)` | no | Receives the validated, complete options dict. The default stores it as `self.options`. |
| `check(self, context)` | yes | Walk the AST and call `context.add_marker(...)`. |

`check()` is not called at all when the parse or link reported an error.

## `MarkerDef`

A frozen dataclass: `MarkerDef(id, severity, summary, detail="")`.

| Field | Meaning |
|---|---|
| `id` | Globally unique ID, e.g. `MPR001`. The `PSS` prefix is pssparser's. |
| `severity` | Default severity: `"error"`, `"warning"`, `"info"`, or `"hint"`. Users can override it per ID. |
| `summary` | One line, shown by `--list-markers` and after the ID in `--describe-checker`. |
| `detail` | Multi-line text printed by `pssparser --describe ID`. Say what is wrong and how to fix it. |

There is a fifth field, `patterns`; it is used only by pssparser's own core
markers. Leave it empty.

Choosing IDs and severities: `marker-ids.md`.

## `CheckContext`

| Field | Meaning |
|---|---|
| `root` | The linked `RootSymbolScope`, or `None` under `--syntax-only`. Contains the core library too. |
| `global_scopes` | One `GlobalScope` per user file, core library excluded. Walk these for per-file rules. |
| `files` | The source paths from the command line, in order. |
| `file_map` | `{fileid: path}`. Map `unit.getFileid()` (and any `Location.fileid`) to the path to report. Do not use `GlobalScope.getFilename()`; it may be empty. |

### `add_marker`

```python no-check
context.add_marker(
    code="MPR010",           # must be declared in marker_defs
    file=path,               # from context.file_map
    line=loc.lineno,         # 1-based
    col=loc.linepos,         # 1-based
    message="field 'addr' differs only in case from 'Addr'",
    extent=len(name),        # optional: characters to underline
    severity="error",        # optional: override MarkerDef.severity
    related=[{               # optional: secondary locations
        "file": path, "line": prev.lineno, "col": prev.linepos,
        "label": "first declared here",
    }],
)
```

- All arguments are keyword-only.
- pssparser prefixes the message with `[ID]`; do not repeat the ID in `message`.
- An undeclared `code` raises `ValueError`. The checker's `check()` ends there,
  and the run reports `warning: checker '<name>' raised an exception: ...` on
  stderr, with exit code 0.
- A marker with severity `error` makes the run exit 1, like a core error.
  Users can change that with `[severity]` and `-W` options; prefer
  `"warning"` for style rules and let them promote it.
- Use `related` for a second location the message depends on (the earlier
  declaration, the base type). The CLI prints each as a `note:` with its own
  source line; `--json` carries it too.

## Options

```python no-check
options_schema = {
    "style": {
        "type": "string",                 # "string" | "int" | "bool" | "string-list"
        "default": "PascalCase",
        "choices": ["PascalCase", "snake_case"],   # "string" only, optional
        "help": "Naming style required for action types.",
    },
    "exempt": {
        "type": "string-list",
        "default": [],
        "help": "Glob patterns for names to skip.",
    },
}
```

What pssparser guarantees:

- The user's table is validated **before any file is parsed**. An unknown key
  (with a "did you mean" suggestion), a wrong type, or a value outside
  `choices` is a usage error: exit code 2, message naming your checker.
- A `[checker.<name>]` table for a checker with no `options_schema` is also an
  error. Declare a schema before documenting any option.
- `configure()` receives **every** declared key, defaults filled in. Read
  `self.options["style"]` directly; do not write `.get(key, default)`, which
  lets the default drift from the schema.
- `configure()` is never called for a checker without `options_schema`, so
  `self.options` does not exist there.

If your tests construct the checker directly, also set a class-level
`options = {...}` equal to the defaults; `configure()` has not run there.

Users see the schema with:

```bash
pssparser --describe-checker field-name-length
```

and set values in `.pssparser.toml`:

```toml
[checker.field-name-length]
min_length = 3
allow = ["i", "j", "k", "x", "y"]
```

or in `pyproject.toml` under `[tool.pssparser.checker.field-name-length]`.

A checker cannot set default severities for other checkers' IDs, or for core
`PSS` IDs; `[severity]` belongs to the user.

## `ExtensionRegistry` (in `register(reg)`)

| Attribute | Direction | Meaning |
|---|---|---|
| `api_version` | in | Checker-API version of the running pssparser. |
| `name` | in | The entry-point key the extension is registered under. |
| `add_checker(cls)` | out | Register one `CheckerBase` subclass. Repeatable. |
| `version` | out | Shown by `--list-extensions`; defaults to the distribution version. |
| `description` | out | One line, shown by `--list-extensions`. |
| `requires_api` | out | Minimum API version needed. Prefer the module-level `REQUIRES_API`. |

`add_checker` raises (reported as `PSS030`) for a non-`CheckerBase` class, an
empty `name`, or the same class added twice. Packaging: `packaging.md`.
