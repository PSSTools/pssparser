/**
 * The AST the WASM core builds is the AST the native core builds.
 *
 * Expectations come from `scripts/gen-ast-parity-fixture.py`, which runs the
 * native Python bindings; see that file for why they are generated rather than
 * written. This is the only test of the wire format with ground truth
 * independent of the generator: `serialize.test.ts` proves the two halves agree
 * with *each other*, which they would even if both were wrong in the same way,
 * because one generator emits both.
 *
 * What is compared is the declaration spine -- `ASTUtils.walkScope`'s pre-order
 * walk -- with each node's class, declared name, depth and location. It does not
 * descend into expressions or exec bodies. Phase 3's gate is the whole tree.
 */
import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { ast, childrenOf, deserialize, getNodeName, initPssParser } from '../src/index.js';
import type { ScopeChild } from '../src/ast/generated/index.js';

interface Fixture {
  cases: Array<{
    id: string;
    why: string;
    files: Array<{ name: string; content: string }>;
    raised: string | null;
    units: Array<{ fileid: number; spine: SpineEntry[] }>;
  }>;
}

/** `[class, name, depth, fileid, lineno, linepos, extent]`. */
type SpineEntry = [string, string | null, number, number, number, number, number];

const fixture: Fixture = JSON.parse(
  readFileSync(fileURLToPath(new URL('./fixtures/ast-parity.json', import.meta.url)), 'utf8')
);

/**
 * The TypeScript side of the same walk.
 *
 * Goes through the exported `childrenOf` and `getNodeName` rather than
 * reproducing their tests, so this stays a comparison of two *parsers* and does
 * not quietly become a comparison of two traversals.
 */
function spine(root: ast.GlobalScope): SpineEntry[] {
  const out: SpineEntry[] = [];
  const visit = (node: ScopeChild, depth: number): void => {
    const l = node.location;
    out.push([
      node.constructor.name,
      getNodeName(node),
      depth,
      l.fileid,
      l.lineno,
      l.linepos,
      l.extent,
    ]);
    for (const c of childrenOf(node)) visit(c, depth + 1);
  };
  for (const c of root.children) visit(c, 0);
  return out;
}

describe('AST parity with the native parser', () => {
  it('has a fixture with corpus coverage', () => {
    expect(fixture.cases.length).toBeGreaterThan(50);
    expect(fixture.cases.some((c) => c.id.startsWith('corpus:'))).toBe(true);
  });

  for (const c of fixture.cases) {
    it(`${c.id}${c.why ? ` -- ${c.why}` : ''}`, async () => {
      const m = await initPssParser();
      const s = new m.ParserSession();
      try {
        s.beginParse();
        let failed = false;
        for (const f of c.files) {
          if (s.parseSource(f.content)) {
            failed = true;
            break;
          }
        }

        if (c.raised !== null) {
          // The native side threw, so it recorded no units. The WASM side must
          // agree that this source does not parse -- a serialiser tested only on
          // sources that parse is tested on the easy half.
          expect(failed || s.hasErrors()).toBe(true);
          return;
        }

        expect(s.hasErrors()).toBe(false);

        for (const unit of c.units) {
          const bytes = new Uint8Array(s.serializeUnit(unit.fileid));
          const root = deserialize(bytes);
          expect(root, `unit ${unit.fileid} deserialised to null`).toBeInstanceOf(
            ast.GlobalScope
          );
          expect(spine(root as ast.GlobalScope), `unit ${unit.fileid}`).toEqual(unit.spine);
        }
      } finally {
        s.delete();
      }
    });
  }
});
