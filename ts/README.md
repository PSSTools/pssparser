# `@psstools/pssparser`

The [pssparser](https://github.com/psstools/pssparser) C++ core compiled to
WebAssembly, with a TypeScript API. Parses PSS (Portable Test and Stimulus
Standard) source. Runs under Node and in a browser; no native build step for
consumers, no filesystem dependency.

Full documentation: `docs/typescript_api.rst` in the repository root.

```typescript
import { createParser, ParseException } from '@psstools/pssparser';

using parser = await createParser();
try {
  parser.parseSources([{ name: 'top.pss', content: src }]);
} catch (e) {
  if (!(e instanceof ParseException)) throw e;
  for (const m of e.markers) {
    console.error(`${m.file}:${m.line}:${m.col}: ${m.severity}: ${m.message}`);
  }
}
```

Without `using`, call `parser.dispose()` in a `finally`. It is required, not an
optimisation: the WASM heap is not reachable by the JavaScript garbage
collector.

## Status

The API is complete: `createParser`, `parseSources`, `markers`,
`clearMarkers`, `setMaxErrors`, `link`, `root`, `userUnits`, `fileMap`,
`enableProfiling`/`getProfileInfo`, `dispose`, the schema-hash check, and the
AST traversal helpers. Nothing throws `not implemented`.

Not published to npm yet, and `Marker.code` is expected to become required
before 1.0 (`ts-wasm-impl-plan.md` Phase 5).

## Building

```bash
ivpm update -d ts-build     # default-dev + the Emscripten toolchain

npm install
npm run generate            # AST classes (astbuilder gen-ts) + the .wasm (emcc)
npm run typecheck
npm test
npm run build               # tsc -> dist/, plus the .wasm
```

Three build products are generated and not committed: `src/ast/generated/`,
`src/wasm/pssparser.{js,wasm}`, and the census walker pair
(`scripts/generated/census_gen.py`, `test/generated/census.ts`). All come from
`npm run generate`.

`ts-build` is `default-dev` plus the Emscripten toolchain, composed with ivpm's
`uses:`. One dep-set, not two: `wasm-build` alone leaves out `packages/python`
and the ANTLR runtime that `wasm/CMakeLists.txt` needs, and ivpm records the
requested set in `packages/ivpm.json` and rejects a later run asking for a
different one. Exercised on a clean clone 2026-09-07: the artifact comes out
byte-identical to the working tree's.

## Consuming pssparser from another project

Two ways, and they are the same package.

**As a released package** — for a consumer that only wants to *use* the parser.
`npm install @psstools/pssparser` ships the prebuilt `.wasm` inside `dist/`, so
there is no Emscripten toolchain and no build.

**As an IVPM source dependency** — for a consumer co-developing pssparser. The
wasm is rebuilt from source automatically on every `ivpm update`:

```yaml
- name: pssparser
  url: https://github.com/psstools/pssparser.git
  dep-set: ts-build
  deps-mode: nested
  type:
  - raw
  - node:
      subdir: ts
```

Each line is load-bearing, and each was established by running it:

- `dep-set: ts-build` — the consumer gets pssparser's build dependencies, not
  just its sources.
- `deps-mode: nested` — those land in `<pssparser>/packages/`, where
  `wasm/CMakeLists.txt` looks. Flattened into the consumer's deps-dir they are
  invisible to it. (The Python venv stays root-scoped either way; both the
  CMake build and `scripts/astbuilder.mjs` search upward for it.)
- `type: [raw, node]` — `raw` stops ivpm auto-detecting the `pyproject.toml`
  and building the *native Python extension*, which a TypeScript consumer does
  not want and which needs a different toolchain.
- `subdir: ts` — this package is one directory inside the repository. Without
  it npm is pointed at the repository root, finds no manifest there, and
  reports success having installed nothing.

The rebuild itself is npm's `prepare` hook (`scripts/prepare.mjs`), which npm
re-runs on every install of a `file:` dependency. Verified end to end: changing
a C++ source and a TypeScript source upstream, then running `ivpm update` in the
consumer with no other action, changes the SHA-256 of both `dist/wasm/pssparser.wasm`
and `dist/index.js` and the new export is reachable. Consuming this way needs
the 298 MB Emscripten toolchain; the released package is the answer for anyone
who does not want it.

Note that `src/ast/generated/deserialize.ts` comes from the **wasm** step, not
from `gen:ast`. It is emitted by `astbuilder gen-wasm` alongside the C++ writer
it has to agree with, in one run from one schema; `gen-ts` owns the rest of that
directory and does not touch it.

## Tests

```
test/parity.test.ts    markers must equal the native Python bindings', field for
                       field, over the whole curated corpus
test/parser.test.ts    Parser semantics: stdlib auto-load, builder reuse,
                       collect-before-throw, fileids, dispose
test/astutils.test.ts  traversal, including the SymbolChildrenScope branch
test/loader.test.ts    module caching, schema hash, session independence
test/serialize.test.ts the AST wire format: round-trip, framing, determinism
test/ast-parity.test.ts the materialised AST must equal the native bindings'
                       node for node, over the same corpus
test/link.test.ts      link() semantics: unconditional collection and re-sort,
                       the root recorded before failure, the builder dropped,
                       userUnits/fileMap/getProfileInfo
test/link-parity.test.ts the *linked* tree must equal the native bindings'.
                       A different tree from the per-unit one, and it carries
                       the cross-unit reference counts
test/census-parity.test.ts every node, every field: the same comparison past
                       the declaration spine, 132k nodes per run
```

All four sets of parity expectations are generated, not written:

```bash
npm run gen:parity-fixture         # markers
npm run gen:ast-parity-fixture     # the AST, per unit
npm run gen:link-parity-fixture    # the linked tree
npm run gen:census-parity-fixture  # every node, every field
```

The output is committed, so the suite needs no Python, no native build and no
corpus checkout.

The parity tests are the ones that matter for the wire format. Round-tripping
proves only that the writer and the reader agree with each other, which they do
by construction — both come from one generator — so it cannot see two same-width
fields emitted in the wrong order. Comparing against an independently-built tree
can, and does: that transposition fails 90 of 100 cases.

The first three walk the declaration spine — `Scope`/`SymbolChildrenScope`
children, with each node's class, name and location. The census walks the whole
ownership graph and records every field, through a walker pair generated from
the schema (`astbuilder gen-census`) rather than transliterated by hand.

None was trusted for passing first time. Mutating the reader so `prototypes`
always deserialises empty fails 91 of the 91 linked cases; perturbing one field
of the spine walk fails the same 91 through the digest comparison; and decoding
`ExprBin.op` one greater than it was written fails 92 of the 100 census cases
and **none** of the 200 spine tests — which is both the liveness check and the
clearest statement of what the census adds. A parity test that passes because it
is comparing nothing looks exactly like one that passes because the code is
right.

For memory questions the suite cannot answer, there is an ASan build:

```bash
source ../scripts/wasm-env.sh
emcmake cmake -S ../wasm -B ../build-wasm-asan -DENABLE_ASAN=ON
cmake --build ../build-wasm-asan -j
node ../wasm/asan-probe.mjs build-wasm-asan
```

It writes to its own directory, never to `src/wasm/`. Three probes: a failed
parse's unit being freed, `link()` moving ownership into the root (with a
second link freeing the first root), and teardown holding a root *and* units
the linker never took. Each names the one-line mutation that makes it fire —
check one before believing a clean run.
