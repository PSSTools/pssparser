# pss-rules loader fixtures

Rule files for the C++ rule loader (`lint-core-plan.md` C4.1), run by
`tests/python/lintcore/test_rule_loader.py`, natively, and in WASM by
`ts/test/lintcore-parity.test.ts` (each file is a `RuleLoad` case in the parity
fixture).

Each file states what loading it must give, in trailing comments, so adding
them never moves a line that a diagnostic points at:

```
# expect: PSSP212 error @ 6:7 rule 'LINT901' has no 'family', which a built-in rule must have
# loads: LINT903          (the rules that load, in order; `none` for none)
# refused                 (instead of `loads:`: the file as a whole is refused)
```

The diagnostics are compared exactly and in order: code, severity, line, column
and message. A file whose first line is `# builtin` is loaded as a built-in
rule file. A file that cannot carry comments (JSON), or whose diagnostics
the comments would change (a YAML syntax error), keeps its expectations in
`<file>.expect` instead.

After an intended change to a message or position, regenerate the
expectations with `PSS_RULES_BLESS=1 pytest tests/python/lintcore/test_rule_loader.py`
and review the diff.
