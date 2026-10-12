
# PSSParser
This project provides a ANTLR4-based parser for the Accellera PSS language. 
It also provides an AST (data model) for processing the result of the parser.

## Supported standard

pssparser supports **PSS 3.1** (the Public Review Draft of 2026-08-28). PSS 3.0
syntax that 3.1 removed is rejected; see
[docs/pss31_migration.rst](docs/pss31_migration.rst).

The pssparser version is not the LRM revision. Major releases are for large
changes, including support for a new LRM revision; minor releases for medium
changes; patch releases for small changes and fixes. To check from a program,
read `pssparser.SUPPORTED_LRM`; `pssparser --version` prints it on its second
line.

[![Build Status](https://dev.azure.com/mballance/psstools/_apis/build/status/PSSTools.pssparser?branchName=master)](https://dev.azure.com/mballance/psstools/_build/latest?definitionId=15&branchName=master)

## Agent skills

The wheel ships agent skills that teach a coding agent to use pssparser:
`pssparser` (check and lint PSS), `pssparser-checkers` (write lint rules: a
rule file first, a Python checker when a rule file cannot express the check)
and `pssparser-api` (build tools on the Python API).  They are registered in the
`agent.skills` entry-point group, so `ivpm update` installs them into
`.claude/skills/` and the other agent directories.  The sources are in
[skills/](skills/), with `pssparser-dev`, a fourth skill for work on
pssparser itself that is not shipped.

## Checker Plug-ins

`pssparser` supports a plug-in system for custom Python-based checkers that
run after a successful parse and link.  Plug-ins can be contributed by any
installed Python package via the `pssparser.checkers` `entry_points` group,
or loaded on the fly with `--load-checker MODULE:CLASS`.

```bash
# List all registered checkers
pssparser --list-checkers

# List all marker IDs (built-in + plug-in)
pssparser --list-markers

# Describe a specific marker
pssparser --describe PSS001

# Run only a specific checker
pssparser --checker naming-convention model.pss

# Load and run a local checker (no install needed)
pssparser --load-checker myproject.rules:StyleChecker model.pss
```

See [docs/checker_plugin_guide.rst](docs/checker_plugin_guide.rst) for a
full guide to writing and registering checker plug-ins.
