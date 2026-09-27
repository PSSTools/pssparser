---
name: pssparser-checkers
description: Write custom lint checks for PSS as pssparser checker plug-ins (`CheckerBase`, `MarkerDef`, `CheckContext`) and package them as a `pssparser.extensions` entry point. Use when the user wants a new PSS lint rule, house naming or style rules, a rule collection, configurable checker options, or tests for a checker. For only *running* checks, use the `pssparser` skill.
---

# Writing pssparser checkers

A checker is a Python class that pssparser runs after a model parses and links
cleanly. It walks the AST and emits diagnostics with IDs you own. A package of
checkers ships as one *extension*: one `pssparser.extensions` entry point, and
installing the package is all a user does to turn its rules on.

Know the limits before you start:

- Checkers run **only after a successful parse and link**. If the model has any
  error, no checker runs, so a checker cannot report syntax or resolution
  errors. Those belong to pssparser itself.
- Under `--syntax-only`, only checkers with `runs_without_link = True` run, and
  `context.root` is `None`.
- A checker that raises is reported as a one-line `warning:` on stderr and the
  run still exits 0. Test for it (see `references/testing.md`); do not rely on
  CI noticing.

## 1. Write the checker

```python
import pssparser.ast as pss_ast
from pssparser.checkers import CheckContext, CheckerBase, MarkerDef


class ShortFieldNameChecker(CheckerBase):
    name = "short-field-name"                 # used by --checker / config
    description = "Warn on one-letter field names"
    marker_defs = [                           # every ID you emit, declared
        MarkerDef(id="MPR001", severity="warning",
                  summary="Field name is a single letter",
                  detail="Rename the field to say what it holds."),
    ]

    def check(self, context: CheckContext) -> None:
        # User files only; the core library is already filtered out.
        for unit in context.global_scopes:
            path = context.file_map.get(unit.getFileid(), "")
            unit.accept(_Visitor(context, path))


class _Visitor(pss_ast.VisitorBase):
    def __init__(self, context, path):
        super().__init__()
        self.context, self.path = context, path

    def visitField(self, field):
        name = field.getName()
        loc = name.getLocation()
        if loc.lineno > 0 and len(name.getId()) == 1:   # skip synthetic nodes
            self.context.add_marker(
                code="MPR001", file=self.path,
                line=loc.lineno, col=loc.linepos, extent=len(name.getId()),
                message=f"field '{name.getId()}' has a one-letter name")
        super().visitField(field)             # keep walking
```

The rules that matter:

- `name` must be unique among checkers; `marker_defs` must list every `code`
  you pass to `add_marker`. An undeclared code raises `ValueError`, which
  ends that checker's `check()` for the run.
- Use an ID prefix nobody else uses, never `PSS` (reserved for pssparser). See
  `references/marker-ids.md`.
- Report the location of the *name* (`getName().getLocation()`) and pass
  `extent`, so the CLI underlines the whole identifier.
- Skip nodes whose `lineno` is below 1. The linker adds synthetic nodes, such
  as each action's `comp` field.
- Never print to stdout from a checker: it corrupts `--json` output.

Field reference for `CheckerBase`, `MarkerDef`, `CheckContext`, and
`add_marker` (including `related` locations and severity overrides):
`references/checker-api.md`. Which AST nodes to look for and how to walk them:
`references/ast-for-checkers.md`.

## 2. Try it without packaging

Put the class in a module on `PYTHONPATH` and load it by `module:Class`:

```bash
pssparser --no-extensions --load-checker my_rules:ShortFieldNameChecker model.pss
pssparser --load-checker my_rules:ShortFieldNameChecker --describe-checker short-field-name
pssparser --load-checker my_rules:ShortFieldNameChecker --describe MPR001
```

`--no-extensions` keeps other installed rule packages out of the result.
Iterate on a small `.pss` file that triggers the rule and one that must stay
clean, for example:

```pss
component pss_top {
    action a {
        rand bit[8] x;      // MPR001
        rand bit[8] addr;   // clean
    }
}
```

## 3. Make it configurable (optional)

Declare options instead of hard-coding thresholds or styles:

```python no-check
    options_schema = {
        "min_length": {"type": "int", "default": 2,
                       "help": "Shortest field name accepted."},
    }
    # in check(): self.options["min_length"]  (always present, defaults filled)
```

Users set them under `[checker.<name>]` in `.pssparser.toml`. pssparser
validates the table before parsing and exits 2 on an unknown key or a wrong
type. Details: `references/checker-api.md`.

## 4. Package it as an extension

Copy `assets/extension-template/` out of this skill directory to a new
project and rename it. It holds a `pyproject.toml` with the entry point, a
package with `register(reg)`, one configurable checker (`MPR001`), and pytest
tests that drive the real CLI. Then:

```bash
pip install -e .
pssparser --list-extensions         # your extension, version, checkers
pssparser --list-markers            # your IDs appear, owned by your checker
python -m pytest tests
```

Entry-point details, `REQUIRES_API`, the legacy `pssparser.checkers` group,
and the load diagnostics (`PSS030`-`PSS033`) are in `references/packaging.md`.

## 5. Test it

Test through the CLI with `--json`: it exercises marker declaration,
configuration, and ID uniqueness exactly as a user hits them. Patterns, and
the `PSSPARSER_NO_EXTENSIONS` trap: `references/testing.md`.

## Checklist before shipping

- [ ] A unique ID prefix; no `PSS` IDs; `pssparser --list-markers` shows no clash.
- [ ] Every emitted ID is in `marker_defs`, with a `summary` and a `detail`
      that says how to fix the problem.
- [ ] Every option is in `options_schema` with a `default` and `help`.
- [ ] One test per marker that fires, and one clean model that must not.
- [ ] A test asserts stderr has no `raised an exception` line.
- [ ] `REQUIRES_API` is set; rule modules are imported inside `register()`.

## Going further

- Resolve references, find every use of a declaration, or walk the linked
  model in depth: the `pssparser-api` skill (`pssparser.refs`, the full AST).
- Running checks, selecting checkers, severities, and CI gating for users:
  the `pssparser` skill.
