# Running pssparser in CI

## The rules

1. **Gate on the exit code.** `0` passes. `1` means the model has errors
   (or warnings promoted by `-Werror`). `2` means the job itself is wrong: a
   bad flag, a missing file, or an invalid configuration. `3` is an internal
   error in pssparser. Fail the job on any non-zero code, but report `2` and
   `3` differently from `1` if you can: they are not problems in the model.
2. **Check the whole model in one command.** All files form one compilation
   unit. Checking files one at a time reports cross-file names as unknown.
   Checking two unrelated models together reports their shared names (two
   `pss_top` components, for example) as duplicates. Run one command per
   model.
3. **Decide what warnings mean.** Without `-Werror`, warnings are printed
   and the job passes. Put the policy in the configuration file (the
   `[warnings]` table, see `lint-config.md`) rather than in the CI script, so
   developers get the same result locally.
4. **Pin the pssparser version.** A newer release can add checks, and
   extensions can add rules, so an unpinned job can go red with no change to
   the model. Pin pssparser and every checker extension you install.
5. **Run from the repository.** The configuration file is found by searching
   upward from the working directory, so run pssparser from inside the
   checkout. Confirm with `pssparser --show-config` in the job log.
6. **Make a failed extension fatal.** If an installed extension fails to
   load, pssparser warns (`PSS030`) and runs without its rules. Add
   `-Werror=PSS030`, or list it under `[warnings] error`, so a broken install
   cannot pass silently.

## Install

pssparser is on PyPI and needs Python 3.10 or newer:

```bash
python -m pip install "pssparser==X.Y.Z"
python -m pip show pssparser
```

Replace `X.Y.Z` with the version the project has tested against.

## A minimal job

```bash
set -e
python -m pip install "pssparser==X.Y.Z"
pssparser --show-config
pssparser -Werror=PSS030 src/pkg.pss src/top.pss
```

## Machine-readable output

`--json` writes one document to stdout; the exit code is unchanged. Save it
as an artifact, or turn it into annotations. For GitHub Actions:

```bash
set +e
pssparser --json src/pkg.pss src/top.pss > pssparser.json
rc=$?
set -e
jq -r '.diagnostics[] | "::\(if .severity == "error" then "error" else "warning" end) file=\(.file),line=\(.line),col=\(.col),title=\(.code // "pssparser")::\(.message)"' pssparser.json
exit $rc
```

The `diagnostics` array, the `summary` counts, and each field are described
in `diagnostics.md`.

## Reproducible logs

`--stats-no-timing` appends declaration counts and the codes that fired,
without wall-clock times, so two runs on the same input give identical
output. Use it when a job compares output against a stored golden file:

```bash
pssparser --stats-no-timing src/pkg.pss src/top.pss 2> pssparser.log
diff -u expected.log pssparser.log
```

Human diagnostics and the stats block go to stderr; hence `2>`.

## Isolating extensions

`--no-extensions` (or `PSSPARSER_NO_EXTENSIONS=1` in the environment) runs
the built-in checks only. Use it for a job that must not depend on what is
installed, or to tell whether a finding comes from pssparser or from an
extension. Note that a configuration file that selects or configures an
extension's checkers fails with exit `2` when that extension is absent;
`[extensions.<name>] enabled = false` is the one setting that tolerates it.

## Colour

Output is coloured only when stderr is a terminal, which it usually is not in
CI. Force it with `--color` if the CI log viewer renders ANSI colour; disable
it everywhere with `NO_COLOR=1`.
