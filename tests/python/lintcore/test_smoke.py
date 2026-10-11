"""
The lint engine exists in the native build (lint-core-plan.md C1.1).

`ts/test/lint.test.ts` is the same check for the WASM build. Together they
prove both builds compile `src/lint/`: a source missing from one of the two
globs fails here or there, not at the first parity test.
"""


def test_engine_constructs(factory):
    e = factory.mkLintEngine()
    assert e.rule_format_version == 1
    assert e.num_rule_sets() == 0


def test_engines_are_independent(factory):
    a, b = factory.mkLintEngine(), factory.mkLintEngine()
    assert a is not b
    del a
    assert b.num_rule_sets() == 0
