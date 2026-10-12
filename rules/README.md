# Built-in lint rules

The `pss-rules` files in this directory (`*.yaml`, `*.yml`) are pssparser's
built-in lint rules. The build embeds them in the core
(`src/lint/rules/mk_builtin_rules.py`, lint-core-plan C4.3), so the CLI, the
WASM build and the editor all load the same rules, with no file on disk to
find. They are loaded before any site rule file.

A built-in rule file:

- uses only the `LINT` namespace (`LINT101`), never a team qualifier;
- gives every rule a `family`, a `doc` and `examples`, with at least one
  example that fires and one that does not (pss-rules-format.md §3.1, §4);
- loads with no diagnostics at all:
  `tests/python/lintcore/test_rule_discovery.py` checks that;
- has fixtures in `tests/lint/<name>/` (at least three `l*.pss` and three
  `ok_*.pss`, one of them a waiver) and messages that pass
  `check_messages`: `tests/python/lint/test_builtin_rules.py` checks those.

After editing a file here, rebuild the core (the files are embedded), then
regenerate `docs/lint-rules.rst` (`scripts/gen_lint_rules.py`) and, in `ts/`,
`npm run gen:lint-parity-fixture`: the examples and fixtures also run in the
WebAssembly build.

Name each file after its family: `rules/<family>.yaml`. The format is
`docs/design/pss-rules-format.md` (to be `docs/lint-rule-authoring.rst`).
