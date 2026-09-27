# Changing the grammar

The lexer is `src/PSSLexer.g4`, the parser `src/PSSParser.g4`. Both are ANTLR 4
grammars with the C++ target; `src/CMakeLists.txt` generates the C++ at build
time (`antlr_target`), using `packages/antlr4-tools.jar`. There is nothing to
regenerate by hand: a C++-only build picks the change up.

```bash
# edit src/PSSParser.g4
cmake --build build && cmake --install build
PYTHONPATH=python python -m pytest tests/python -q
```

A new rule or alternative usually also needs:

- a builder change in `src/AstBuilderInt.cpp` (the visitor for the rule);
- possibly an AST change (`ast-regen.md`);
- a test that the new surface parses *and builds the right AST*, not only
  that it produces no syntax error.

## Which grammar is normative

PSS 3.1 Annex B is the reference, but it is not always complete. Where a
syntax box in a clause admits a form that Annex B leaves out (`extend monitor`
is an example), follow the clause and say so in a grammar comment.

Read the LRM from the PDF with `pdftotext -layout`. The Markdown conversions of
the draft tear bold keyword runs out of the BNF, so Annex B read from `.md` is
wrong in ways that look plausible. At least one grammar comment once cited a
production that appears in no draft because of it.

## Baselines a grammar change moves

A deliberate grammar change is expected to move these. Regenerate them in the
same change, and read each diff: the gates cannot tell an intended change from a
regression. That judgement is yours, and regenerating records it.

### Grammar profiling (`docs/profiling/baseline.json`)

`tests/python/profiling/test_baseline.py` re-profiles the good corpus and fails
at zero tolerance on a *new* ambiguity or a new full-LL fallback.

```bash
PYTHONPATH=python python scripts/profile_grammar.py --write-baseline docs/profiling/baseline.json
PYTHONPATH=python python scripts/profile_grammar.py --top 40           # text report
PYTHONPATH=python python scripts/profile_grammar.py --baseline docs/profiling/baseline.json --fail-on-regress
```

The gate *skips* (rather than fails) when the baseline is stale, for example
when the pss-corpus revision has moved. A skipped profiling test is a baseline
to regenerate, not a pass.

Reading the report:

- Rank hotspots on `sll_look` and `look/inv`, never on time. ATN transition
  counts measure cache warmth, not the grammar.
- Counters are exact and deterministic; time is not gated.
- The design and what it departed from: `docs/design/grammar-profiling-harness.md`
  (read §6 first). Triage of known hotspots: `docs/profiling/findings-*.md`.

### Grammar coverage (`tests/python/baselines/grammar.json`)

**Decision counts are not coverage.** ANTLR only profiles decisions that go
through adaptive prediction; an LL(1) decision reports zero invocations even
when the input used it. For "which rules does the corpus exercise", use the
per-rule parse-tree counts:

```bash
PYTHONPATH=python python scripts/grammar_cov.py report
PYTHONPATH=python python scripts/grammar_cov.py baseline   # after a grammar change or corpus addition
```

`ParseProfileInfo.get_rule_invocations` is the underlying API. A rule with zero
contexts is grammar that no corpus file exercises: add a corpus file (in
pss-corpus, see `testing.md`), not a local test only.

### AST inventory

`scripts/check_ast_inventory.py` also reads the grammar. A new alternative that
builds a new node kind needs the node produced; see `ast-regen.md`.

## Error recovery and messages

Syntax-error messages come from the builder's error listener and are mapped to
PSS020–PSS028 (the syntax sub-band) by message pattern. A grammar change can
change which token recovery stops on and so change the message and location of
existing syntax errors. Run `tests/python/errors` and the error suite (see
`error-suites.md`) after any grammar change, and re-bless goldens only after
reading every diff.

## Checklist

- [ ] builder handles the new rule; AST test added
- [ ] `docs/profiling/baseline.json` regenerated and diff read
- [ ] `tests/python/baselines/grammar.json` regenerated
- [ ] `tests/python/errors` green; goldens re-blessed only if the diff is intended
- [ ] corpus coverage for the new surface (pss-corpus)
- [ ] `CHANGELOG.md` entry
