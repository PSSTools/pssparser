# Lint rules in pssparser

How pssparser's own `LINT` rules are defined, tested and documented. For the
user-facing side see `docs/lint.rst`; for third-party rules see
`docs/checker_plugin_guide.rst`. Plan and status:
`docs/design/lint-framework-plan.md` (tick boxes there).

## Which namespace a diagnostic belongs in

| Namespace | Meaning | Where it is declared |
|---|---|---|
| `PSS` | The model breaks an LRM rule ("shall") | `checkers/core_checker.py` |
| `LINT` | Legal PSS that is probably not what the author meant | `lint/catalog.py` |
| `PSSP` | pssparser itself: extensions, config, IDs, parser coverage | `checkers/core_checker.py` |

Lint is about consequence, not precedent. The PSS hazard that matters most is
silent stimulus degradation: a constraint, branch or guard that does nothing.
Memory and thread safety are not a PSS concern. A new LRM violation is never
lint, even if pssparser only warns about it: it gets a `PSS` ID. Two migrated
rules break this today, `LINT101` and `LINT402` (LRM rules pssparser tolerates).
If either becomes an error, it gets a new `PSS` ID and the `LINT` row is
retired.

`PSS`, `PSSP`, `PSSX` and `LINT` are reserved (`taxonomy.RESERVED_NAMESPACES`).
Only the bundled `lint` extension may declare `LINT` codes. Any other
extension that does is refused with `PSSP005`.

## Where a rule lives

```text
python/pssparser/lint/
  __init__.py     register(reg): the bundled extension, loaded by manager.discover
  catalog.py      every LINT MarkerDef, as data (CORE_EMITTED)
  rulefiles.py    finding and loading pss-rules files ([lint] rules, --rules)
  ruleview.py     the loaded rules as MarkerDefs, and the pss-rules checker
  examples.py     runs the rules' examples: (--check-rules, tests)
```

- **Core-emitted rules** (`catalog.CORE_EMITTED`): the C++ linker raises the
  message, and the `MarkerDef.patterns` regex assigns the `LINT` ID in Python.
  Each one replaced a retired `PSS` row and sits at that row's position, so
  the order in which patterns are tried is unchanged. The old ID is kept in
  `aliases`. Changing the C++ message text means changing the pattern too.
- **Declarative rules** (`pss-rules` files in `rules/` at the repository
  root, compiled into the core): run by the C++ lint engine
  (`docs/design/lint-core-plan.md`), not by Python. The registry sees them
  through `pssparser.lint.ruleview`, as the checker `pss-rules`, whose
  `check()` calls `LintEngine.run` with the enabled IDs, the
  `[lint.rule.<name>]` options and the gate count. There are no Python
  runner rules any more (`lint/rules/` was deleted in C5.4).

The bundled extension is registered in-process, not through an entry point,
so `PYTHONPATH=python` trees see it (plan §10 Dv-1).

## The MarkerDef

Every field from lint-framework L2. `manager._accept_checker` validates them;
bad metadata refuses the checker with `PSSP201`.

| Field | Rule |
|---|---|
| `id` | `LINT` + 3 digits, in the family band: `1xx` constraint, `2xx` activity, `3xx` exec, `4xx` decl/import, `5xx` register, `6xx` evolution |
| `name` | kebab-case, unique; the fixture directory uses the same name |
| `tier` | one of `taxonomy.LINT_TIERS`. New rules start as `nursery` |
| `family` | one of `taxonomy.FAMILIES` |
| `severity` | the tier default (`taxonomy.TIER_SEVERITY`). Anything else needs a `Severity:` paragraph in `detail` |
| `since` | rules version, `YYYY.N` |
| `lrm` | the clauses the rule rests on |
| `detail` | the consequence, the messages, and the **escape hatch** (how to write the code so the rule stays quiet) |
| `examples` | at least one bad `Example(code, expect=((line, col),))` and one good `Example(code)`. `check_examples` runs them |

Choosing an ID:

- Take the next free number in the family band.
- A core-emitted rule is also a core marker (`CoreChecker.marker_defs` appends
  `CORE_EMITTED`), so its ID goes in `tests/data/core-codes.lock` in the same
  change. The C++ sets the ID where it emits the marker (the `id` argument of
  `ResolveContext::addMarker`), and the `MarkerDef` has no `patterns`;
  regenerate the core's catalogue (`scripts/gen_catalog.py`). `tests/python/test_core_codes_lock.py` fails otherwise, and it also
  fails if a published code disappears or goes from `retired` back to
  `active`. Runner rules are not locked yet; plan F3.1 decides that.
- Add a runner rule's `MarkerDef` to `catalog.ALL`, which feeds `--explain`,
  profile expansion and the generated reference.
- To retire a rule, set `status="retired"` and `replaced_by`. Never delete the
  row or reuse the number.

## Fixtures

One directory per rule, named after the rule's `name`:

```text
tests/lint/<rule-name>/
  l01.pss  l02.pss ...     must report exactly the listed findings
  ok_01.pss ok_02.pss ...  must report nothing (near-misses, the escape hatch)
  fix_01.pss               reserved for rule fixes (F5)
```

Expectations are comments in the file:

```pss no-check
// expect: LINT402 @ 5:3
package lib { struct s {} }
package p {
  struct t {}
  import lib::*;
}
```

- `// expect: ID @ L:C, ID @ L:C`: exact line and column; may repeat.
- `// expect: none`: in every `ok_*` file.
- Matching is exact both ways: a missing finding fails, and so does an extra
  one. Only the rule under test is compared, so an unrelated warning does not
  break the fixture.
- The comment is part of the file, so it counts as line 1. Write the expect
  line last, or recount after editing the header.

`tests/python/lint/test_rule_fixtures.py` runs every directory with
`check_fixture_dir(dir, rules=[dir.name])`; a new directory is picked up with
no test edit. Rule definition of done (plan F3.5): at least 3 `l*` cases (basic,
nested, through `extend` or inheritance) and at least 3 `ok_*` near-misses. Seed
them from the harvest probes in `docs/design/lint-candidates/probes/` where they
exist.

Other helpers in `pssparser.checkers.testing`, shipped in the wheel:

- `run_rules(paths, rules=[...], rule_files=[...])`: parse, link, run only
  the named rules (profile `none` plus the selectors given) and return the
  diagnostics. The built-in rule files are always loaded; `rule_files` adds
  others, as `--rules` does. Selected declarative rules run even under
  `PSSPARSER_NO_LINT`. `check_fixture(_dir)` take `rule_files` too.
- `check_examples(checker_cls)`: runs every `MarkerDef.examples` entry.
- `check_messages(diags)`: the error suite's message lints when
  `pss_errsuite` is importable; otherwise one line, at most 120 characters,
  a code, no grammar jargon. The definition of done also asks that the message
  name the construct and the consequence in one sentence; nothing checks that.

## Declarative rules' examples

A `pss-rules` rule's `examples:` run in `pssparser.lint.examples`
(`run_examples`, `check_examples(engine)`): each example parsed and linked by
a fresh `Parser`, only its rule enabled, options at their defaults, findings
compared with its `// expect:` comments (no `@ L:C`: anywhere on the line).
An example with errors, or one where the rule fails (PSSP220/221), fails.

- `--check-rules` runs the examples of the files it checks (not the built-in
  ones); each problem is a `PSSP222` error at the example.
- `tests/python/lintcore/test_examples.py` runs every built-in rule's
  examples and those of `tests/data/lint-examples/*.yaml`.
- The same examples, plus some whole runs, run in WASM:
  `ts/test/lint-parity.test.ts` against `ts/test/fixtures/lint-parity.json`.
  After changing a built-in rule file or anything under
  `tests/data/lint-examples/`, run `npm run gen:lint-parity-fixture` in
  `ts/`; `tests/python/test_ts_fixtures_current.py` fails until you do.

## Test isolation

`tests/python/conftest.py` sets `PSSPARSER_NO_LINT=1` (autouse), so no
declarative rule (built-in or from `--rules`) runs in the other suites. A lint test opts in with the `lint_enabled`
fixture. `PSSPARSER_NO_LINT` does not affect the core-emitted rules: the lint
profile governs those, and the default profile (`minimal`) is exactly those
nine, so the existing suites keep seeing them.

`PSSPARSER_NO_EXTENSIONS` does not skip the bundled extension; it is not a
third-party extension.

## Documentation

`docs/lint-rules.rst` is generated from the catalogue:

```bash
PYTHONPATH=python python scripts/gen_lint_rules.py
```

`tests/python/lint/test_lint_rules_doc.py` fails when it is stale, and checks
that every rule's anchor matches `taxonomy.RULE_DOC_URL`. A rule that moves a
core warning also changes `docs/markers.rst` (`scripts/gen_marker_docs.py`).
Renaming a published ID breaks downstream users: record it in
`docs/design/cross-repo-followups.md` and the CHANGELOG.

## Checklist for a new rule

> **Direction change (2026-10-10).** New `LINT` rules will be declarative
> `pss-rules` YAML files (`rules/<family>.yaml`) with CEL predicates, run by a
> lint engine in the C++ core, so the CLI and the editor give the same answers.
> See `docs/design/pss-rules-format.md` and plan F3. Until F3.1–F3.3 land there
> is no engine, so don't add Python rule classes in `lint/rules/`: steps 2–3
> below describe the interim Python path and will change.

1. Decide `PSS` vs `LINT` (above). An LRM "shall" is never `LINT`.
2. `MarkerDef` in `lint/catalog.py` with every field, reachable from `ALL`
   (and in the lockfile if core-emitted).
3. Checker class in `lint/rules/`, listed in `rules.CHECKERS`.
4. Fixtures in `tests/lint/<name>/`.
5. Regenerate `docs/lint-rules.rst`.
6. Precision table in `docs/lint/precision/<name>.md` (plan F2.6).
7. Full suite, then tick the rule's row in the plan's §11.
