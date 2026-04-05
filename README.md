
# PSSParser
This project provides a ANTLR4-based parser for the Accellera PSS language. 
It also provides an AST (data model) for processing the result of the parser.

[![Build Status](https://dev.azure.com/mballance/psstools/_apis/build/status/PSSTools.pssparser?branchName=master)](https://dev.azure.com/mballance/psstools/_build/latest?definitionId=15&branchName=master)

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
