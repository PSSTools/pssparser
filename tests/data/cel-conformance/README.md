# CEL conformance tests (converted)

Converted from the [cel-spec](https://github.com/google/cel-spec) conformance suite,
release **v0.25.3**, `tests/simple/testdata/*.textproto`, by
`scripts/import_cel_conformance.py`. Re-run that script after bumping `cel-spec` in
`ivpm.yaml`; do not edit these files by hand.

They test the lint engine's CEL parser, evaluator and checker (`docs/design/lint-core-plan.md`
C2.1, C3.4; `tests/python/lintcore/test_cel_conformance.py`). Tests for features outside the
pss-rules CEL profile are not removed here: the harness excludes them, and lists each with its
reason in `tests/python/lintcore/cel_conformance_excluded.txt`.

Copyright Google LLC. Licensed under the Apache License, Version 2.0, as is cel-spec.
