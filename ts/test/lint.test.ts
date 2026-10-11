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

const ACME = `pss-rules:
  rules:
    - id: ACME001
      name: action-upper
      tier: suspicious
      summary: Action names start upper-case
      message: "action '\${node.name.id}' should start with \${options.first}"
      match: { kind: Action }
      where: "!node.name.id.startsWith(options.first)"
      options:
        first: { type: string, default: "A", help: The first letter }
    - id: ACME002
      name: every-field
      tier: style
      summary: Every field
      message: "field \${node}"
      match: { kind: Field }
`;

const MODEL = 'component pss_top {\n  action A { }\n  action b { int x; }\n}\n';

describe('Parser.runLint (C5.4)', () => {
  it('runs the loaded rules over the linked model', async () => {
    using parser = await createParser();
    expect(parser.loadRules([{ name: 'acme.yaml', text: ACME }])).toEqual([]);
    parser.parseSources([{ name: 'm.pss', content: MODEL }]);
    parser.link();
    const r = parser.runLint();
    expect(r.markers.map((m) => [m.code, m.file, m.line, m.col, m.severity, m.message])).toEqual([
      ['ACME001', 'm.pss', 3, 3, 'warning', "action 'b' should start with A"],
      ['ACME002', 'm.pss', 3, 18, 'hint', 'field x'],
    ]);
    expect(r.stats.map((s) => [s.id, s.matches, s.findings, s.errors])).toEqual([
      ['ACME001', 2, 1, 0],
      ['ACME002', 1, 1, 0],
    ]);
    expect(r.problems).toEqual([]);
  });

  it('runs only the enabled rules, with option values', async () => {
    using parser = await createParser();
    parser.loadRules([{ name: 'acme.yaml', text: ACME }]);
    parser.parseSources([{ name: 'm.pss', content: MODEL }]);
    parser.link();
    const r = parser.runLint({ enabled: ['ACME001'], options: { ACME001: { first: 'b' } } });
    expect(r.markers.map((m) => m.message)).toEqual(["action 'A' should start with b"]);
    expect(r.stats.map((s) => s.id)).toEqual(['ACME001']);
  });

  it('reports ignored request entries', async () => {
    using parser = await createParser();
    parser.loadRules([{ name: 'acme.yaml', text: ACME }]);
    parser.parseSources([{ name: 'm.pss', content: MODEL }]);
    parser.link();
    const r = parser.runLint({ enabled: ['NOPE'], options: { ACME001: { first: 1 } } });
    expect(r.problems).toEqual([
      "enabled: no rule 'NOPE' is loaded",
      'options: ACME001.first must be string',
    ]);
  });

  it('is gated by the error markers the parser holds', async () => {
    using parser = await createParser();
    parser.loadRules([{ name: 'acme.yaml', text: ACME }]);
    parser.parseSources([{ name: 'm.pss', content: 'component pss_top { action b : Missing { } }\n' }]);
    expect(() => parser.link()).toThrow();
    const r = parser.runLint();
    expect(r.markers).toEqual([
      {
        severity: 'info',
        message: 'lint skipped: 1 error',
        file: '<pssparser>',
        line: 0,
        col: 0,
        extent: 0,
        related: [],
        code: 'PSSP230',
      },
    ]);
    expect(r.stats.every((s) => s.matches === 0)).toBe(true);
  });

  it('reports a rule failure', async () => {
    using parser = await createParser();
    parser.loadRules([
      {
        name: 'bad.yaml',
        text:
          'pss-rules:\n  rules:\n    - id: ACME003\n      name: base-elems\n' +
          '      tier: suspicious\n      summary: s\n      message: m\n' +
          '      match: { kind: Action }\n      where: size(node.super_t.elems) > 0\n',
      },
    ]);
    parser.parseSources([{ name: 'm.pss', content: MODEL }]);
    parser.link();
    const [m] = parser.runLint().markers;
    expect([m.code, m.line, m.severity]).toEqual(['PSSP220', 2, 'warning']);
  });
});
