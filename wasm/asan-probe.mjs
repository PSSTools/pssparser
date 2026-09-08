/****************************************************************************
 * asan-probe.mjs -- exercise the lifetimes the test suite cannot see
 *
 *   emcmake cmake -S wasm -B build-wasm-asan -DENABLE_ASAN=ON
 *   cmake --build build-wasm-asan -j
 *   node wasm/asan-probe.mjs build-wasm-asan
 *
 * The TypeScript suite can tell a correct binding from one that returns wrong
 * answers. It cannot tell a correct binding from one that reads freed memory:
 * a freed block that has not been recycled returns stale-but-intact data and
 * every assertion still passes. That is the gap this file exists for, and it
 * only means anything under -DENABLE_ASAN=ON.
 *
 * It came out of getting exactly this wrong once. Phase 1 recorded, as an
 * invariant, that `AstBuilderInt::build` pushes every unit into `m_prior_units`
 * unconditionally, so a failed parse's unit had to be retained or the builder
 * would hold a dangling pointer -- and bindings.cpp retired failed units on
 * that basis, leaking a GlobalScope per failed parse. The push at
 * AstBuilderInt.cpp:153 is in fact *inside* the `if (no errors)` guard at :142.
 * The claim was reached by reading, was known to be untestable, and was written
 * down anyway. Probe 1 below is the test that should have been built first.
 *
 * **Every probe here must be checked for liveness before a clean run is worth
 * anything.** Each carries the mutation that makes it fire; a probe that
 * reports nothing because it never reached the interesting code looks exactly
 * like a probe that reports nothing because the code is correct.
 ****************************************************************************/
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
const buildDir = process.argv[2] ?? 'build-wasm-asan';

const { default: createModule } = await import(join(root, buildDir, 'pssparser.js'));
const Module = await createModule();

/*
 * `p::W` is a compile-time constant in a previously-parsed unit, so evaluating
 * `bit[p::W]` forces the cross-unit lookup that walks m_prior_units. A source
 * that resolves entirely within itself would never touch a stale pointer and
 * the probes would report nothing whatever the binding did.
 */
const CONSTS = 'package p {\n    const int W = 8;\n}\n';
const USES =
  'import p::*;\ncomponent pss_top {\n    action A {\n        rand bit[p::W] f;\n    }\n}\n';
const BROKEN = 'component c { action }';

let failures = 0;
const fail = (msg) => {
  console.log(`  ${msg}`);
  failures++;
};

/** Allocate and free a few hundred sessions, so a freed block is unlikely to
 *  still be intact under a non-ASan build too. */
function churn() {
  const junk = [];
  for (let i = 0; i < 200; i++) junk.push(new Module.ParserSession());
  for (const j of junk) j.delete();
}

/****************************************************************************
 * Probe 1: a unit whose parse failed is freed, not retained.
 *
 * Liveness: free a *successful* unit instead -- one that genuinely is in
 * m_prior_units -- and this reports heap-use-after-free in round 0, naming
 * GlobalScope::~GlobalScope and Factory::mkGlobalScope.
 ****************************************************************************/
function probeFailedUnits() {
  console.log('probe 1: failed-parse units');
  const s = new Module.ParserSession();
  try {
    s.beginParse();
    s.parseSource(CONSTS);

    for (let round = 0; round < 8; round++) {
      // beginParse() per step, so each gets a fresh marker collector. One
      // collector serves a whole parse call by design (parser.py:120), so
      // without this hasSeverity(Error) stays true after the first broken
      // source and every later parse reports as failed whether or not it was.
      s.beginParse();
      if (!s.parseSource(`${BROKEN} // round ${round}`)) {
        fail(`round ${round}: expected the broken source to fail, it did not`);
      }

      churn();

      // The read: this resolves p::W through m_prior_units.
      s.beginParse();
      if (s.parseSource(USES)) {
        fail(`round ${round}: cross-unit resolution failed: ${s.markersJson()}`);
      }
    }
  } finally {
    s.delete();
  }
}

/****************************************************************************
 * Probe 2: link() moves the units, and a second link() frees the first root.
 *
 * link(marker_l, scopes, own_scopes=true) hands ownership of every unit to the
 * root it returns. Three things follow, and none is visible to a test that only
 * reads values:
 *
 *   - m_units must be *cleared*, not freed. Leaving the pointers there makes
 *     ~ParserSession a second owner of memory the root already freed.
 *   - the builder must be dropped. It holds those units as borrowed pointers,
 *     and they are no longer the session's.
 *   - a second link() deletes the first root, and everything under it. Anything
 *     still reaching into the old tree reads freed memory here.
 *
 * The sequence walks all three, with a serializeRoot() after each link so the
 * whole tree is actually traversed rather than merely held.
 *
 * Liveness: comment out the `m_units.clear()` in ParserSession::link(). The
 * session stays a second owner, the next link() frees the units through the old
 * root, and this reports heap-use-after-free inside probe 2 naming
 * `Field::~Field` and `Factory::mkField`. (Removing `delete m_root` instead
 * leaves the probe green: that defect is a leak, not a fault, so the clear() is
 * the mutation worth checking with.)
 ****************************************************************************/
function probeLink() {
  console.log('probe 2: link() ownership transfer');
  const s = new Module.ParserSession();
  try {
    for (let round = 0; round < 4; round++) {
      s.beginParse();
      if (s.parseSource(CONSTS)) {
        fail(`round ${round}: CONSTS failed to parse: ${s.markersJson()}`);
      }
      if (s.parseSource(USES)) {
        fail(`round ${round}: USES failed to parse: ${s.markersJson()}`);
      }

      // Ownership of every unit moves into the root here. On rounds after the
      // first this also frees the *previous* root and its whole subtree.
      s.link();
      if (!s.hasRoot()) {
        fail(`round ${round}: link() left no root`);
      }

      // Traverse the tree that was just built, and the one that replaced a
      // freed one. serializeRoot() walks every node twice -- index, then write.
      const bytes = s.serializeRoot();
      if (bytes.length < 1024) {
        fail(`round ${round}: serialised root is ${bytes.length} bytes, expected a real tree`);
      }

      churn();

      // Parse again after the link, on the fresh builder link() forced. If the
      // old builder were still in use it would resolve against units the root
      // now owns -- or, after the next link, has freed.
      s.beginParse();
      if (s.parseSource(CONSTS)) {
        fail(`round ${round}: post-link parse failed: ${s.markersJson()}`);
      }
    }
  } finally {
    s.delete();
  }
}

/****************************************************************************
 * Probe 3: a session destroyed with a root and unlinked units in hand.
 *
 * ~ParserSession frees the units the linker never took, then the root, then the
 * builder. The interesting case is a session holding all three at once, which
 * is what a language server looks like when the editor closes mid-parse.
 *
 * Liveness: delete the units in link() rather than clearing them, as in
 * probe 2, and this faults at s.delete() rather than at the next link.
 ****************************************************************************/
function probeTeardown() {
  console.log('probe 3: teardown with a root and unlinked units');
  for (let round = 0; round < 4; round++) {
    const s = new Module.ParserSession();
    s.beginParse();
    s.parseSource(CONSTS);
    s.parseSource(USES);
    s.link();

    // Parsed after the link, so these units belong to the session, not the
    // root: the destructor has to free exactly these and not the linked ones.
    s.beginParse();
    s.parseSource(CONSTS);
    s.parseSource(USES);

    churn();
    s.delete();
  }
}

probeFailedUnits();
probeLink();
probeTeardown();

console.log(
  failures === 0
    ? '\nprobe completed with no unexpected failures.\n' +
        'Under -DENABLE_ASAN=ON, a clean exit here is the result that means something:\n' +
        'ASan saw no invalid access across all three probes. Each probe names the\n' +
        'mutation that makes it fire; check one before trusting this line.'
    : `\nprobe completed with ${failures} unexpected failures.`
);
process.exit(failures === 0 ? 0 : 1);
