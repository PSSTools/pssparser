#!/usr/bin/env node
/**
 * Lint cost against parse + link in the WebAssembly build (lint-core-plan.md
 * C8). Run by `scripts/bench_lint.py --wasm`, which generates the model;
 * needs `npm run build` first (it loads `dist/`).
 *
 *   node scripts/bench-lint.mjs [--repeat N] --rules FILE... -- MODEL.pss...
 *
 * Prints a JSON list, one entry per run: {parse, link, lint, index: ms,
 * rules: [{id, ms, steps, findings}]}. Each run is a fresh parser, as an
 * editor's full re-lint is.
 */
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const { createParser } = await import(join(here, '..', 'dist', 'index.js'));

const argv = process.argv.slice(2);
let repeat = 5;
const rules = [];
const models = [];
let into = null;
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--repeat') {
    repeat = Number(argv[++i]);
  } else if (a === '--rules') {
    into = rules;
  } else if (a === '--') {
    into = models;
  } else if (into) {
    into.push(a);
  } else {
    throw new Error(`unexpected argument: ${a}`);
  }
}

const sources = models.map((name) => ({ name, content: readFileSync(name, 'utf8') }));
const ruleFiles = rules.map((name) => ({ name, text: readFileSync(name, 'utf8') }));
const selection = { lint: { profile: 'all' } };
const ms = (t0) => performance.now() - t0;

const runs = [];
for (let r = 0; r < repeat; r++) {
  const parser = await createParser();
  const diags = parser.loadRules(ruleFiles);
  if (diags.some((d) => d.severity === 'error')) {
    throw new Error(`rule files: ${JSON.stringify(diags)}`);
  }
  let t0 = performance.now();
  if (!parser.parseSources(sources)) {
    throw new Error('parse failed');
  }
  const parse = ms(t0);
  t0 = performance.now();
  parser.link();
  const link = ms(t0);
  t0 = performance.now();
  const res = parser.runLint({ selection });
  const lint = ms(t0);
  runs.push({
    parse, link, lint, index: res.indexNs / 1e6,
    rules: res.stats.map((s) => ({ id: s.id, ms: s.ns / 1e6, steps: s.steps, findings: s.findings })),
  });
  parser.dispose();
}
process.stdout.write(JSON.stringify(runs) + '\n');
