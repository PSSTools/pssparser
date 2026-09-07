/****************************************************************************
 * asan-probe.mjs -- exercise the use-after-free the test suite cannot see
 *
 *   emcmake cmake -S wasm -B build-wasm-asan -DENABLE_ASAN=ON
 *   cmake --build build-wasm-asan -j
 *   node wasm/asan-probe.mjs build-wasm-asan
 *
 * There is exactly one thing being probed. `AstBuilderInt::build` pushes every
 * unit it processes into `m_prior_units` *unconditionally* -- the push at
 * AstBuilderInt.cpp:153 is not guarded on whether the parse emitted errors --
 * and `resolvePathTargetInPriorUnits` walks those borrowed pointers on every
 * cross-unit lookup. So a unit handed to build() must outlive the builder
 * whether or not its parse succeeded. bindings.cpp retires failed units for
 * that reason.
 *
 * The sequence below is the one that reads a freed unit if they are not
 * retired: fail a parse, then parse a source whose resolution has to search
 * prior units. Under a normal build it passes either way -- the freed block is
 * not recycled and the read returns stale-but-intact data -- which is why this
 * needs ASan to mean anything.
 *
 * To confirm the probe is live, revert the fix (delete the failed unit in
 * ParserSession::parseSource instead of pushing it to m_retired), rebuild, and
 * run this. It should report a heap-use-after-free.
 ****************************************************************************/
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const buildDir = process.argv[2] ?? 'build-wasm-asan';

const { default: createModule } = await import(
  join(root, buildDir, 'pssparser.js')
);
const Module = await createModule();

/*
 * `p::W` is a compile-time constant in a previously-parsed unit, so evaluating
 * `bit[p::W]` forces exactly the cross-unit lookup that walks m_prior_units.
 * A source that resolves entirely within itself would never touch the freed
 * pointer and the probe would report nothing whatever the binding did.
 */
const CONSTS = 'package p {\n    const int W = 8;\n}\n';
const USES =
  'import p::*;\ncomponent pss_top {\n    action A {\n        rand bit[p::W] f;\n    }\n}\n';
const BROKEN = 'component c { action }';

const s = new Module.ParserSession();
let failures = 0;

try {
  s.beginParse();
  s.parseSource(CONSTS);

  for (let round = 0; round < 8; round++) {
    // beginParse() per step, so each gets a fresh marker collector. One
    // collector serves a whole parse call by design (parser.py:120), so
    // without this hasSeverity(Error) stays true after the first broken source
    // and every later parse reports as failed whether or not it was --
    // the same harness artifact wasm/spike.mjs documents for the corpus loop.
    s.beginParse();

    // A failed parse. Its unit is the one that must not be freed.
    if (!s.parseSource(`${BROKEN} // round ${round}`)) {
      console.log(`round ${round}: expected the broken source to fail, it did not`);
      failures++;
    }

    // Churn the heap between the free and the read. Without this a freed block
    // is very likely still intact; with ASan it is poisoned either way, but the
    // churn is what makes a *non*-ASan run occasionally interesting.
    const junk = [];
    for (let i = 0; i < 200; i++) junk.push(new Module.ParserSession());
    for (const j of junk) j.delete();

    // The read: this resolves p::W through m_prior_units.
    s.beginParse();
    if (s.parseSource(USES)) {
      console.log(`round ${round}: cross-unit resolution failed: ${s.markersJson()}`);
      failures++;
    }
  }
} finally {
  s.delete();
}

console.log(
  failures === 0
    ? 'probe completed with no parse failures.\n' +
        'Under -DENABLE_ASAN=ON, a clean exit here is the result that means something:\n' +
        'ASan saw no invalid access across 8 free/read rounds.'
    : `probe completed with ${failures} unexpected parse failures.`
);
process.exit(failures === 0 ? 0 : 1);
