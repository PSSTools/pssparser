# pss-errsuite — a tool-neutral PSS error-reporting suite

A corpus of deliberately-broken (and deliberately-valid) PSS, plus a harness
that runs it against **any** PSS tool and records what the tool said. It does
not grade your tool against a standard of ours: it produces one JSON file
saying, per case, *did you react to this defect, where did you point, and what
did you say* — and leaves the judgement to whoever reads it.

Apache-2.0. Stdlib-only, Python ≥ 3.11. No build step.

## Run it against your tool in two commands

```bash
cp tools/faketool.toml tools/mytool.toml   # then edit: argv, output pattern
python3 -m pss_errsuite run --tool tools/mytool.toml --out runs/mytool.json
```

That's it. The second command prints a summary and writes a self-contained run
file — sources, expectations, your tool's verbatim diagnostics, and the derived
status for every case.

Useful next:

```bash
python3 -m pss_errsuite validate                    # check the corpus itself
python3 -m pss_errsuite list --class syntax.punct   # what is in here
python3 -m pss_errsuite run --tool tools/mytool.toml --filter syntax.braces -j8
```

`pip install -e .` gets you a `pss-errsuite` entry point instead of
`python3 -m pss_errsuite`; nothing else changes.

## Describing your tool

A descriptor is ~20 lines of TOML and no Python. `tools/faketool.toml` is the
worked example for a tool whose diagnostics have to be scraped out of
human-readable output; `tools/pssparser-cli.toml` is the structured-output
case.

```toml
[tool]
name        = "mytool"
version_cmd = ["mytool", "--version"]    # captured once per run
version_re  = 'mytool (\S+)'             # optional; group 1 is the version
pss         = "3.0"                      # language version you implement

[invoke]
argv      = ["mytool", "-compile", "{files}"]
file_argv = ["{file}"]                   # how ONE input file is spelled
cwd       = "case"                       # "case" = the case's directory
timeout_s = 30
env       = { MYTOOL_NO_COLOR = "1" }
max_errors_argv = ["-max-errors", "{maxerrors}"]   # if you have such a flag

[output]
kind    = "regex"                        # "regex" | "json"
stream  = "both"                         # stdout | stderr | both
pattern = '^(?P<severity>Error|Warning)-\[(?P<code>[^\]]+)\] (?P<file>[^:]+):(?P<line>\d+):(?P<col>\d+): (?P<message>.*)$'
continuation = '^\s{4}(?P<message>.*)$'  # folded into the previous diagnostic

[capabilities]
multifile          = true
max_errors         = true
json_output        = false
exit_code_on_error = 1
```

Placeholders usable in `argv`, `file_argv`, `version_cmd` and `env` values:
`{python}` (this interpreter), `{suite_root}`, `{repo_root}`. `{files}` must
appear in `argv` as its own element to support multi-file cases; `{maxerrors}`
goes in `max_errors_argv`.

**Tools that want a flag before each file.** `{files}` marks *where* the input
files go; `file_argv` says how *one* of them is spelled. The whole `file_argv`
list is repeated once per input file, with `{file}` replaced by the path. It
defaults to `["{file}"]` — a bare list of paths — so omit it unless you need
something else:

| your command line            | `file_argv`            |
|------------------------------|------------------------|
| `mytool a.pss b.pss`         | omit (the default)     |
| `mytool -pss a.pss -pss b.pss` | `["-pss", "{file}"]`   |
| `mytool --file=a.pss --file=b.pss` | `["--file={file}"]` |
| `mytool -f a.pss -lang pss -f b.pss -lang pss` | `["-f", "{file}", "-lang", "pss"]` |

Note the singular `{file}` in `file_argv` versus the plural `{files}` in
`argv`; mixing them up is rejected at load time rather than passed through to
your tool as a literal.

`[output] kind = "json"` reads a document shaped like
`{"diagnostics": [{file, line, col, severity, message, end_col?, code?,
suggestion?, related?}]}`. If yours differs, remap the names with
`[output] fields`.

**Capabilities are how the suite avoids scoring you on things you structurally
cannot do.** A case that needs a capability you do not declare is `skipped` and
reported as such — never silently counted as a miss. Same for `pss`: a case
targeting a newer language version than you claim is `skipped_version`.

## What the run file says

Per case, one of these statuses:

| status | meaning |
|---|---|
| `detected` | error reported, within the location tolerance |
| `detected_mislocated` | reported, but pointing somewhere else (or nowhere) |
| `detected_wrong_severity` | reported as a warning where an error was expected |
| `missed` | nothing reported |
| `clean` | valid input, nothing reported — the good outcome |
| `spurious` | valid input, error reported (a false positive) |
| `control_failed` | the *repaired* version of the case errored too, so this result says nothing |
| `crash` / `timeout` / `tool_error` | the tool died, hung, or would not run |
| `skipped` / `skipped_version` | capability or language version not declared |

`control_failed` is the one worth understanding. Every broken case ships with a
repaired twin that must parse clean. If your tool rejects the repaired file, we
cannot tell whether it found *this* defect or simply dislikes something in the
scaffolding — so the result is excluded rather than counted. Without that, a
tool that rejects our preamble would score 100% detection.

Counts are *observations*, never pass/fail: a tool that emits two well-located
errors where the case declares one is different, not wrong.

A run file is evidence, so it is large — every case's full source, both output
streams verbatim, the control result. For reading rather than processing:

```bash
python3 -m pss_errsuite digest runs/mytool.json --out runs/mytool-digest.json
```

That is the same run at about a fifth the size: per case, what was asked and
what came back, and nothing else.

```json
{ "case": "SYN-TYPE-ENUM-COMMA-01",
  "class": "syntax.type",
  "title": "enum item list with a missing separator",
  "file": "syntax/type/enum_missing_comma_01.pss",
  "expect": "error", "detect": "required", "status": "detected", "at": "14:9",
  "reported": [ { "severity": "error", "at": "14:9-14", "code": "PSS026",
                  "message": "unexpected keyword 'GREEN' in this context",
                  "primary": true } ],
  "rubric": { "composite": 0.0, "scores": "032222",
              "flags": ["accuracy_gate_applied"] } }
```

Every field is *copied* from the run file, never recomputed, so a digest can
never disagree with the run it came from — and anything you would want to
recompute (a different tolerance, a newer rubric) has to go back to the run
file. Safe to read, useless to argue from.

## Comparing two tools

```bash
python3 -m pss_errsuite compare runs/mytool.json runs/other.json \
        --out runs/compare.json --md runs/compare.md
```

The **first** run file is the baseline — "we" in every tag name — so the output
reads as a work queue for one tool rather than as a scoreboard. Each shared
case gets one tag:

| tag | meaning |
|---|---|
| `we_miss` | we missed it, they diagnosed it — **read this list first** |
| `we_catch` | we diagnosed it, they missed it |
| `we_mislocate` / `they_mislocate` | both diagnosed it; one points worse, or reports the wrong severity |
| `we_noisier` / `they_noisier` | error counts differ by more than one |
| `we_vaguer` / `they_vaguer` | both diagnosed it; rubric composites differ by ≥ 0.25 |
| `both_miss` | neither diagnosed it — a tooling gap, or a bad case |
| `incomparable` | a skip, a control failure, a crash, or a tool error on either side |
| `agree` | none of the above |

Tags are assigned in that order of seriousness and a case gets exactly one, so
the counts partition the shared cases. Two things it deliberately will not do:

- **It refuses to join runs measured under different policies.** `tolerance`
  decides `detected` vs `detected_mislocated` and `severity_floor` decides
  `clean` vs `spurious`; comparing across them would report a difference
  between two *measurements* as a difference between two *tools*. There is no
  override — re-run one side.
- **A missing rubric score is `unscored`, never zero.** Until both sides carry
  rubric blocks, the `we_vaguer` axis is simply inert, and an absent score is
  not a finding about anyone's messages.

`--md` renders the human report, which opens with this banner:

> **Internal — do not publish.** This file names tools and reports how they diagnose a shared corpus. Several PSS tool licences prohibit publishing benchmark results, and the value of this comparison is the internal work queue (the `we_miss` list), not a scoreboard. Keep it out of version control and off the web.

That is not boilerplate. The corpus is public and the harness never needs a
network; the *results* are another matter, and several PSS tool licences
prohibit publishing them. `runs/` and `compare.*` are in `.gitignore`, and a
test fails if a run file is ever tracked.

For one case in detail — the source, where the defect is, and what a tool said
about it:

```bash
python3 -m pss_errsuite show SYN-PUNCT-SEMI-01 --tool tools/mytool.toml
python3 -m pss_errsuite show SYN-PUNCT-SEMI-01 --run runs/mytool.json
```

## How messages are scored

Detection says *did the tool react to the defect*. The rubric says *was what it
said any good* — six dimensions, 0–3 each, scored only on `detected` and
`detected_mislocated` cases (there is no message to grade on a `missed`, and
the right message on a valid file is silence).

| | dimension | what moves it |
|---|---|---|
| D1 | accuracy | naming the defect that is there, not a downstream symptom |
| D2 | location | pointing at the offending construct, with a span |
| D3 | specificity | the user's own identifiers and types, not the grammar's |
| D4 | actionability | what edit fixes this |
| D5 | clarity | one sentence a PSS *user* can read |
| D6 | economy | one defect, one diagnostic |

`run` scores every case automatically and writes a `rubric` block per case;
`grade` re-scores an existing run file with no tool invocation. Reading the
output:

```bash
python3 -m pss_errsuite triage runs/mytool.json --notes   # the work queue
python3 -m pss_errsuite triage runs/mytool.json --missing cause
python3 -m pss_errsuite grade  runs/mytool.json --tier b --rater you
```

`triage` sorts ascending by D1 then D4, because accuracy is the only dimension
that can zero a composite on its own: **if D1 = 0 the composite is 0 regardless
of the other five.** A precisely-located, fix-it-carrying, well-worded message
about the *wrong thing* is worse than a crude message about the right thing.

Three things about the numbers are deliberate and easy to misread:

- **A dimension with nothing to measure against is `null`, never 0.** D1 reads
  the case's `cause:` / `not_cause:` terms and D3 reads `names:`; where the
  case header does not declare them the dimension is unscored and the composite
  averages the rest. `triage --missing cause` lists exactly those cases. A low
  mean over few measured dimensions is a thin corpus, not bad messages, and the
  `coverage` block in the run file says which.
- **Automatic scoring cannot reach 3 on every dimension.** D5 = 3 requires
  reading the message with the source hidden and D3 = 3 requires judging
  whether it names both sides of the relationship. Those need a person
  (`grade --tier b`), so a fully automatic composite of 1.0 is unreachable by
  construction — a corpus graded entirely by proxy measures conformance to the
  proxies.
- **D4 = 3 is earned, not asserted.** If a diagnostic carries a span and a
  replacement, the harness applies it and runs the tool again. Clean result,
  D4 = 3. Not clean, and the case is flagged `fixit_invalid` and scored *down*:
  a fix that does not fix is worse than none. This is the only check that tests
  a message's claim rather than its shape, and it is why `run` may invoke the
  tool more than once per case (`--no-verify-fixit` turns it off).

Scores are never rolled into one headline number per tool. They are reported
per class and per dimension, because the useful question is *which class of
message is bad*, not whether a tool scores 0.71.

## Authoring a case

```pss
//! case:    SYN-PUNCT-SEMI-01        stable id; never renumbered
//! class:   syntax.punct             taxonomy path (see pss_errsuite/taxonomy.py)
//! title:   missing ';' after a struct field declaration
//! expect:  error                    error | warning | accept
//! detect:  required                 required | recommended | optional
//! at:      16:14                    where a *good* diagnostic points
//! count:   1                        expected primary errors (observation only)
//! lrm:     B.11                     LRM clause; mandatory for `required`
//! pss:     3.1                      language version, if not 3.0
//! fix:     16:         int a;       the repaired line → generates the control
//! cause:   ;                        terms an accurate message contains (D1)
//! not_cause: unknown type           the plausible misdiagnosis (D1)
//! names:   a                        identifiers a specific message names (D3)
//! tags:    struct, field
//! requires: multifile               capabilities the case needs
//! pssparser.id: PSS020              tool-specific; ignored by every other tool
```

Rules, all enforced by `validate`:

* **One defect per case**, under 40 lines, no assumed context.
* **Every `expect: error` case has a control**: a `fix:` line, or a
  `<name>.ok.pss` sibling when the repair is not a single-line edit.
* **`detect: required` needs an `lrm:` citation.** `required` means the LRM
  says *shall* / *is an error*, and the clause is attached so the claim is
  checkable. Syntax cases cite Annex B: the input is not in the language the
  grammar generates. Everything else starts `recommended`.
* **Write `cause:` and `not_cause:` while the defect is still in your head.**
  `not_cause:` is the plausible *mis*diagnosis — the thing a parser would say
  if it blamed the symptom instead of the cause — and it is the only input that
  can score a message 0 for accuracy. Reconstructing either one a year later
  means re-reading the case.
* Line and column numbers **count the header**, because the header is part of
  the file the tool is handed. Recount after editing a header.

`//!` lines are PSS comments, so every case can be handed to a tool directly
while you debug it.

## Layout

```
cases/          the corpus
tools/          tool descriptors
pss_errsuite/   the harness
tests/          the harness's own tests, plus a scripted fake tool
runs/           output — gitignored, never committed
```

Run files are **not** published. Several tool EULAs prohibit publishing
benchmark results, and the value here is an internal work queue, not a
scoreboard. The suite is meant to be shared; its output is not.

See `docs/design/error-suite-design.md` for the reasoning and
`docs/design/error-suite-plan.md` for what is built and what is next.
