# Packaging checkers as an extension

An **extension** is one installable distribution that contributes any number
of checkers through a single `pssparser.extensions` entry point. Installing it
turns its checkers on for every `pssparser` run in that environment, with no
flags. Start from `assets/extension-template/` in this skill; this file
explains what is in it.

## The entry point

`pyproject.toml`:

```toml
[project]
name = "acme-pss-rules"
version = "2.3.0"
dependencies = ["pssparser"]

[project.entry-points."pssparser.extensions"]
acme-rules = "acme_pss_rules"
```

Or `setup.cfg`:

```ini
[options.entry_points]
pssparser.extensions =
    acme-rules = acme_pss_rules
```

- The **key** (`acme-rules`) is the extension's name. Users see it in
  `pssparser --list-extensions` and use it in `[extensions.acme-rules]`.
- The **value** is a module, not a class. It must expose `register(reg)` (or
  a `CHECKERS` list; see below).

## The module

```python no-check
# acme_pss_rules/__init__.py
REQUIRES_API = 1            # refuse to load on an older checker API
__version__ = "2.3.0"


def register(reg):
    reg.version = __version__
    reg.description = "Acme house rules for PSS"

    # Import rule modules here, not at the top of the file.
    from .naming import NamingChecker
    from .coverage import CoverageChecker
    reg.add_checker(NamingChecker)
    reg.add_checker(CoverageChecker)

    # Feature-probe anything newer than REQUIRES_API promises.
    if reg.api_version >= 2:
        pass
```

Why each piece is there:

- **Imports inside `register()`.** A broken rule module is then reported as
  `PSS030` against your extension when pssparser loads it, while the package
  itself still imports (for your tests, or for other tools that use it).
- **`REQUIRES_API` at module level.** pssparser reads it *before* calling
  `register()`. If it exceeds the running API version, the extension is not
  loaded and `PSS032` names both versions. Use `reg.requires_api = N` only if
  you must decide inside `register()`.
- **`reg.version`.** Defaults to the distribution version; set it only if the
  two differ.
- **`reg.api_version`.** The API version is bumped only for incompatible
  changes, so one release of your extension can serve several pssparser
  releases by probing it.

Shorthand: a module may expose `CHECKERS = [ClassA, ClassB]` instead of
`register()`. You then cannot set a description, and `--list-extensions`
shows `(no description)`. Prefer `register()`.

## Install and verify

```bash
pip install -e .                    # editable, while developing
pssparser --list-extensions
pssparser --list-checkers
pssparser --describe-checker <checker-name>
```

`--list-extensions` prints each extension's name, version, description, and
the checkers it contributed. A checker that is missing there was rejected;
run any `.pss` file and read the `PSS03x` diagnostics at the top.

## Load diagnostics

Discovery never aborts a run. Problems with an extension are ordinary
diagnostics with the file `<pssparser>`, so they appear in `--json`, count in
the summary, and respond to `-W`:

| ID | Severity | Cause |
|---|---|---|
| `PSS030` | warning | Import failed, `register()` raised, or the module has neither `register` nor `CHECKERS`. |
| `PSS031` | warning | A legacy entry-point key differs from the class's `name`. |
| `PSS032` | warning | `REQUIRES_API` is newer than this pssparser. The extension is skipped. |
| `PSS033` | error | Two checkers declare the same marker ID. The core registers first, then extensions in entry-point-name order; the checker that loses is dropped. |

`pssparser --describe PSS030` (and so on) gives the full text. Tell your users
to add `-Werror=PSS030` in CI so a broken install fails the build instead of
silently running fewer rules.

## Turning an extension off

Users, not you, decide this:

```toml
# .pssparser.toml
[extensions.acme-rules]
enabled = false
```

`--no-extensions`, or `PSSPARSER_NO_EXTENSIONS=1` in the environment, skips
every installed extension and runs only pssparser's built-in checks.

## The legacy `pssparser.checkers` group

Older plug-ins register one class per entry point:

```toml
[project.entry-points."pssparser.checkers"]
naming-convention = "acme_pss_rules.naming:NamingChecker"
```

It still works; each entry point is treated as a one-checker extension and
listed as `(single-checker entry point)`. The key must equal the class's
`name`, or you get `PSS031` and the class's name wins. Use it only for a
single rule with no need for `REQUIRES_API`; for anything else use
`pssparser.extensions`.

## Release checklist

- `dependencies` lists `pssparser` (unpinned, or with a floor matching the
  API you use; the API version check protects the rest).
- Marker IDs are stable across releases. Users pin them in `-Werror=ID` and
  `[severity]`; renaming or renumbering one is a breaking change.
- The package's tests run against the pssparser versions you claim to support
  (see `testing.md`).
