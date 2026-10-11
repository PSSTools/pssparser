/**
 * The lint engine in the WASM build (lint-core-plan.md C1.1, C4.3).
 *
 * `tests/python/lintcore/test_smoke.py` and `test_rule_discovery.py` are the
 * same checks natively; the loader itself is compared fixture by fixture in
 * `lintcore-parity.test.ts`.
 */
import { describe, expect, it } from 'vitest';
import { createParser, initPssParser } from '../src/index.js';

const rule = (id: string, name: string) =>
  `    - id: ${id}\n      name: ${name}\n      summary: s\n      message: m\n` +
  `      match: { kind: ExprBin }\n`;
const ruleFile = (...rules: [string, string][]) =>
  'pss-rules:\n  defaults:\n    tier: style\n  rules:\n' +
  rules.map(([id, name]) => rule(id, name)).join('');

describe('lint engine', () => {
  it('is reachable from a ParserSession', async () => {
    const module = await initPssParser();
    const session = new module.ParserSession();
    try {
      const info = JSON.parse(session.lintEngineInfoJson());
      expect(info.rule_format_version).toBe(1);
      // The built-in rule files, loaded when the engine is created.
      expect(typeof info.rule_sets).toBe('number');
    } finally {
      session.delete();
    }
  });
});

describe('Parser.loadRules', () => {
  it('loads rule files in order and returns their diagnostics', async () => {
    using parser = await createParser();
    expect(parser.ruleDiagnostics).toEqual([]);
    expect(parser.loadRules([{ name: 'a.yaml', text: ruleFile(['ACME001', 'a']) }])).toEqual([]);
    const diags = parser.loadRules([
      { name: 'b.yaml', text: ruleFile(['ACME001', 'b']) },
      { name: 'c.yaml', text: 'steps: []\n' },
    ]);
    expect(diags.map((d) => [d.code, d.file, d.line, d.col])).toEqual([
      ['PSSP217', 'b.yaml', 5, 11],
      ['PSSP210', 'c.yaml', 1, 1],
    ]);
    expect(diags[0].related).toEqual({ file: 'a.yaml', line: 5, col: 11 });
    expect(diags[0].rule).toBe('ACME001');
    expect(parser.ruleDiagnostics).toHaveLength(2);
  });

  it('probes a text without loading it', async () => {
    using parser = await createParser();
    expect(parser.probeRules(ruleFile(['ACME001', 'a']))).toBe('rule-file');
    expect(parser.probeRules('pss-rules:\n  rules: [\n')).toBe('rule-file');
    expect(parser.probeRules('a: [\n')).toBe('not-yaml');
    expect(parser.probeRules('- 1\n')).toBe('not-mapping');
    expect(parser.probeRules('steps: []\n')).toBe('no-key');
    expect(parser.probeRules('# nothing\n')).toBe('empty');
    expect(parser.ruleDiagnostics).toEqual([]);
  });
});
