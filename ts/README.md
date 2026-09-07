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

Implemented: `createParser`, `parseSources`, `markers`, `clearMarkers`,
`setMaxErrors`, `dispose`, the schema-hash check, and the AST traversal
helpers.

Declared but not yet implemented: `link()`, `root`, `userUnits()`,
`getProfileInfo()`. They need the AST to cross the WASM boundary, which needs
the serialiser described in `ts-wasm-impl-plan.md` Phase 2.

## Building

```bash
ivpm update -d wasm-build   # Emscripten toolchain, 298 MB, separate dep-set

npm install
npm run generate            # AST classes (astbuilder gen-ts) + the .wasm (emcc)
npm run typecheck
npm test
npm run build               # tsc -> dist/, plus the .wasm
```

Two build products are generated and not committed: `src/ast/generated/` and
`src/wasm/pssparser.{js,wasm}`. Both come from `npm run generate`.

## Tests

```
test/parity.test.ts    markers must equal the native Python bindings', field for
                       field, over the whole curated corpus
test/parser.test.ts    Parser semantics: stdlib auto-load, builder reuse,
                       collect-before-throw, fileids, dispose
test/astutils.test.ts  traversal, including the SymbolChildrenScope branch
test/loader.test.ts    module caching, schema hash, session independence
```

The parity expectations are generated, not written:

```bash
PYTHONPATH=../python ../packages/python/bin/python \
    scripts/gen-parity-fixture.py -o test/fixtures/parity.json
```

The output is committed, so the suite needs no Python, no native build and no
corpus checkout.
