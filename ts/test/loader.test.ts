/**
 * Module loading and the schema-hash check (`ts-api-design.md` §7).
 */
import { describe, expect, it } from 'vitest';
import { AST_SCHEMA_HASH, createParser, initPssParser } from '../src/index.js';

describe('initPssParser', () => {
  it('returns the same module to concurrent callers', async () => {
    // Cached as the in-flight promise, not the resolved module: callers that
    // race must share one instantiation rather than each paying a full
    // compile.
    const [a, b] = await Promise.all([initPssParser(), initPssParser()]);
    expect(a).toBe(b);
  });

  it('returns the same module to sequential callers', async () => {
    expect(await initPssParser()).toBe(await initPssParser());
  });
});

describe('schema hash', () => {
  it('agrees between the wasm core and the generated TypeScript', async () => {
    // The check itself runs at load and throws on mismatch, so reaching this
    // line already proves it passed. Asserting the equality directly makes the
    // failure legible when it does not: the message names both hashes rather
    // than reporting that some unrelated test could not create a parser.
    const module = await initPssParser();
    expect(module.schemaHash()).toBe(AST_SCHEMA_HASH);
  });

  it('is a sha256 digest', () => {
    expect(AST_SCHEMA_HASH).toMatch(/^[0-9a-f]{64}$/);
  });
});

describe('createParser', () => {
  it('instantiates the module implicitly', async () => {
    const p = await createParser();
    try {
      expect(p).toBeDefined();
    } finally {
      p.dispose();
    }
  });

  it('gives each parser an independent session', async () => {
    // One WASM module, many ParserSessions. Markers accumulated by one must
    // not appear on another -- they hold separate collectors and separate
    // builders, and a shared one would leak a document's diagnostics into
    // every other document in a language server.
    const a = await createParser();
    const b = await createParser();
    try {
      try {
        a.parseSources([{ name: 'bad.pss', content: 'component c { action }' }]);
      } catch {
        /* expected */
      }
      expect(a.markers.length).toBeGreaterThan(0);
      expect(b.markers).toEqual([]);
    } finally {
      a.dispose();
      b.dispose();
    }
  });
});
