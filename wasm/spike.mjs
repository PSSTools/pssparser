/****************************************************************************
 * spike.mjs -- Phase 0 measurement harness (ts-wasm-impl-plan.md §Phase 0)
 *
 *   node wasm/spike.mjs [corpus-dir]
 *
 * Reports the numbers the plan's kill criteria are stated against:
 *
 *   compressed artifact   > 8 MB    -> kill
 *   cold start            > 500 ms  -> kill
 *   parse time            > 3x native -> kill
 *
 * "Cold start" is measured in a freshly spawned process, because that is the
 * number a consumer actually pays: an LSP server starting, a browser tab
 * loading. Measuring a second instantiation inside a warm process measures the
 * module cache, which is not the question.
 ****************************************************************************/
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');

const t0 = performance.now();
const { default: createModule } = await import(
  join(root, 'ts', 'src', 'wasm', 'pssparser.js')
);
const tImport = performance.now();
const Module = await createModule();
const tReady = performance.now();

console.log(`schema hash        : ${Module.schemaHash()}`);
console.log(`js import          : ${(tImport - t0).toFixed(1)} ms`);
console.log(`wasm instantiate   : ${(tReady - tImport).toFixed(1)} ms`);
console.log(`cold start (total) : ${(tReady - t0).toFixed(1)} ms`);

/*
 * The first parse pays for the standard library, which is loaded lazily into
 * unit 0 (parser.py:93-97). Reporting it separately matters: it is a one-time
 * cost per Parser, and folding it into a per-file average would overstate
 * every file's parse time by however much the stdlib costs.
 */
function timeParse(sources) {
  const s = new Module.ParserSession();
  try {
    const t = [];
    let mark = performance.now();
    s.beginParse();
    const stdlibMs = performance.now() - mark;

    for (const { name, content } of sources) {
      mark = performance.now();
      const failed = s.parseSource(content);
      t.push({ name, ms: performance.now() - mark, failed, bytes: content.length });
    }
    return { stdlibMs, files: t, markers: JSON.parse(s.markersJson()) };
  } finally {
    s.delete();
  }
}

// -- smoke: does it actually parse PSS? --------------------------------------
const good = `
component pss_top {
    action A { }
}
`;
const bad = `component pss_top { action }`;

let r = timeParse([{ name: 'good.pss', content: good }]);
console.log(`\nstdlib load        : ${r.stdlibMs.toFixed(1)} ms`);
console.log(`valid source       : failed=${r.files[0].failed} markers=${r.markers.length}`);
if (r.files[0].failed || r.markers.length !== 0) {
  console.log(JSON.stringify(r.markers, null, 2));
}

r = timeParse([{ name: 'bad.pss', content: bad }]);
console.log(`syntax error       : failed=${r.files[0].failed} markers=${r.markers.length}`);
console.log(`  ${JSON.stringify(r.markers[0])}`);

// -- corpus ------------------------------------------------------------------
//
// Each file gets its own session. That is not how a consumer uses the API --
// parseSources() feeds many files to one session so the builder's compile-time
// environment spans them (PSS 3.1 19.1.2) -- but it is the only way to time
// files independently. One shared session accumulates markers, so
// hasSeverity(Error) stays true for every file after the first failure and
// every later file is reported as failed. Python has the same property and
// hides it by raising on the first error (parser.py:138-141); a measurement
// harness cannot.
const corpusDir = process.argv[2] ?? join(root, 'packages', 'pss-corpus', 'curated');
let corpus = [];
try {
  const walk = (d) => {
    for (const e of readdirSync(d, { withFileTypes: true })) {
      const p = join(d, e.name);
      if (e.isDirectory()) walk(p);
      else if (e.name.endsWith('.pss')) corpus.push(p);
    }
  };
  walk(corpusDir);
} catch (e) {
  console.log(`\nno corpus at ${corpusDir}: ${e.message}`);
}

if (corpus.length) {
  const sources = corpus.map((p) => ({ name: p, content: readFileSync(p, 'utf8') }));
  const totalBytes = sources.reduce((a, s) => a + s.content.length, 0);
  console.log(`\ncorpus             : ${sources.length} files, ${totalBytes} bytes`);

  const results = [];
  const stdlibTimes = [];
  const t = performance.now();
  for (const s of sources) {
    const r = timeParse([s]);
    stdlibTimes.push(r.stdlibMs);
    results.push({ ...r.files[0], markers: r.markers.length });
  }
  const wall = performance.now() - t;

  const parsed = results.filter((f) => !f.failed);
  const failed = results.filter((f) => f.failed);
  const sum = results.reduce((a, f) => a + f.ms, 0);
  const slowest = [...results].sort((a, b) => b.ms - a.ms)[0];
  const stdlibAvg = stdlibTimes.reduce((a, b) => a + b, 0) / stdlibTimes.length;

  console.log(`  parsed ok        : ${parsed.length}/${results.length}`);
  if (failed.length) {
    console.log(`  failed           : ${failed.map((f) => f.name.split('/').pop()).join(' ')}`);
  }
  console.log(`  stdlib load (avg): ${stdlibAvg.toFixed(1)} ms  <- paid once per session`);
  console.log(`  parse total      : ${sum.toFixed(1)} ms  (wall incl. ${sources.length} stdlib loads: ${wall.toFixed(1)} ms)`);
  console.log(`  throughput       : ${(totalBytes / 1024 / (sum / 1000)).toFixed(0)} KiB/s`);
  console.log(`  slowest file     : ${slowest.name.split('/').pop()} ${slowest.ms.toFixed(1)} ms (${slowest.bytes} bytes)`);

  if (process.env.SPIKE_JSON) {
    const { writeFileSync } = await import('node:fs');
    writeFileSync(
      process.env.SPIKE_JSON,
      JSON.stringify(results.map((r) => ({ name: r.name, ms: r.ms, failed: r.failed, markers: r.markers })), null, 2));
    console.log(`  wrote            : ${process.env.SPIKE_JSON}`);
  }
}

// -- boundary throughput (Phase 0 step 5) ------------------------------------
//
// The design materialises the AST in bulk: one serialised buffer per parse,
// handed across in a single transfer (ts-api-design.md §4). Everything rests
// on that transfer being cheap relative to the parse. This times the transfer
// alone -- not the C++ walk that would fill the buffer, not the JS that would
// turn it into objects -- so it is a lower bound on materialisation cost, and
// the number to compare against parse time before committing to Phase 3.
if (typeof Module.benchBoundaryOut === 'function') {
  console.log('\nboundary transfer (wasm -> JS string):');
  for (const kb of [64, 256, 1024, 4096]) {
    const n = kb * 1024;
    // Warm once: the first call at a size pays allocation the rest do not.
    Module.benchBoundaryOut(n);
    const reps = kb >= 1024 ? 5 : 20;
    const t = performance.now();
    for (let i = 0; i < reps; i++) Module.benchBoundaryOut(n);
    const ms = (performance.now() - t) / reps;
    console.log(
      `  ${String(kb).padStart(5)} KiB : ${ms.toFixed(2)} ms  ` +
        `(${(n / 1024 / 1024 / (ms / 1000)).toFixed(0)} MiB/s)`
    );
  }
}

// -- peak memory -------------------------------------------------------------
const mem = process.memoryUsage();
console.log(`\npeak RSS           : ${(mem.rss / 1024 / 1024).toFixed(1)} MB`);
// HEAPU8 is not on the module object unless it is named in
// EXPORTED_RUNTIME_METHODS, and there is no reason to export it for production
// use. The memory itself is always reachable.
const heap = Module.wasmMemory?.buffer.byteLength;
console.log(`wasm heap          : ${heap ? (heap / 1024 / 1024).toFixed(1) + ' MB' : 'n/a'}`);
