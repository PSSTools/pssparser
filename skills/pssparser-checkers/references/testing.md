# Testing checkers

Test a checker the way users run it: through the `pssparser` command with
`--json`. That covers what unit tests of `check()` miss: that every emitted ID
is declared, that options validate and reach `configure()`, that IDs do not
clash, and that the checker does not raise.

## Iterate from the command line

Before writing tests, load the class directly (the module only has to be
importable, e.g. from the current directory on `PYTHONPATH`):

```bash
pssparser --no-extensions --load-checker my_rules:ShortFieldNameChecker bad.pss good.pss
pssparser --no-extensions --load-checker my_rules:ShortFieldNameChecker --json bad.pss
```

- `--no-extensions` excludes other installed rule packages, so their
  diagnostics do not mix with yours.
- `--load-checker` still works with `--no-extensions`, and loading a class
  that is already installed is harmless.
- Add `--no-config` so a `.pssparser.toml` in the current or a parent
  directory does not change the result, or `--config FILE` to test options.

## The pytest pattern

The template's `tests/test_field_names.py` uses this helper:

```python no-check
import json, os, subprocess, sys

SPEC = "my_pss_rules.field_names:FieldNameLengthChecker"


def lint(tmp_path, source, config=None):
    """Run pssparser with this checker; return (exit code, diagnostics)."""
    (tmp_path / "model.pss").write_text(source)
    args = ["--no-extensions", "--load-checker", SPEC, "--json"]
    if config is not None:
        (tmp_path / "lint.toml").write_text(config)
        args += ["--config", "lint.toml"]
    else:
        args += ["--no-config"]
    r = subprocess.run(
        [sys.executable, "-m", "pssparser", *args, "model.pss"],
        capture_output=True, text=True, cwd=tmp_path, env=dict(os.environ))
    assert r.returncode in (0, 1), r.stderr        # 2 = usage error, 3 = internal
    assert "raised an exception" not in r.stderr, r.stderr
    return r.returncode, json.loads(r.stdout)["diagnostics"]
```

Each diagnostic in the `--json` output has `file`, `line`, `col`, `severity`,
`message` (with the `[ID]` prefix), and `code`, plus `related` when set.

Write, per marker:

1. a model that triggers it: assert the `code` list **and** the `line`/`col`
   of the first hit (a wrong location is the most common checker bug);
2. a near-miss model that must stay clean;
3. for each option, a model whose result the option changes.

And once per package:

- `register()` contributes the expected checker names
  (`ExtensionRegistry("my-pss-rules", api_version=API_VERSION)`, then
  `.checkers`);
- `REQUIRES_API <= API_VERSION`;
- your IDs do not clash with the core's (see `marker-ids.md`).

Keep models tiny and inline. Each must parse and link without errors, or no
checker runs and the test only proves that.

## Traps

- **A raising checker passes silently.** An exception inside `check()`
  becomes a `warning: checker '<name>' raised an exception` line on stderr,
  and the exit code stays 0. Always assert stderr does not contain
  `raised an exception`.
- **Nothing runs after an error.** If the test model has a syntax or link
  error, the result is the core's error and no checker output. Build the
  model up until `pssparser --no-extensions model.pss` reports 0 errors.
- **`PSSPARSER_NO_EXTENSIONS=1`** in the environment turns off discovery of
  installed extensions (some test harnesses set it to isolate runs). A test
  that expects your *installed* extension to be discovered must remove it
  from the child's environment. Tests using `--load-checker` are unaffected.
- **Printing from a checker** corrupts `--json` output and breaks
  `json.loads`. Report through `add_marker` only.
- **Checkers and `--syntax-only`.** If you set `runs_without_link = True`,
  add a test with `--syntax-only`; `context.root` is `None` there.

## Testing installed discovery

To prove the packaging (entry point, `register()`, metadata), install into a
throwaway directory and run `--list-extensions` from it:

```bash
pip install --no-deps --target /tmp/rules-target .
PYTHONPATH=/tmp/rules-target pssparser --list-extensions
```

(With a venv-installed pssparser, `PYTHONPATH` adds the target alongside it.)
The output lists your extension name, version, description, and checkers.

## CI

- Run the tests against the oldest and newest pssparser you support.
- Fail the job on `PSS030`-`PSS033` in a smoke run:
  `pssparser -Werror=PSS030 -Werror=PSS031 -Werror=PSS032 model.pss`.
