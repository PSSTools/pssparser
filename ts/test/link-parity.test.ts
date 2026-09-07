/**
 * The tree `link()` produces is the tree the native parser produces.
 *
 * Expectations come from `scripts/gen-link-parity-fixture.py`, which runs the
 * native Python bindings; see that file for what is recorded and why. This is
 * the counterpart to `ast-parity.test.ts` for the *linked* tree, which is a
 * different tree: the per-unit fixture walks each `GlobalScope` as parsed, and
 * nothing about that constrains the merged symbol tree `TaskBuildSymbolTree`
 * builds on top of it.
 *
 * The `refs` comparison is the load-bearing one. Serialising a unit at a time,
 * a reference whose target lived in another unit had no id to write and was
 * dropped -- the loss `ts-api-design.md` §4 records. Serialising the linked
 * root, every target is in the same buffer. These counts are how that is
 * checked rather than asserted; a regression that put the units back in
 * separate buffers would take `prototypes` from 75 to 0 and nothing else in
 * the suite would notice.
 */
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterEach, describe, expect, it } from 'vitest';
import { ast, childrenOf, createParser, getNodeName, ParseException, type Parser } from '../src/index.js';
import type { ScopeChild } from '../src/ast/generated/index.js';

/** `[class, name, depth, fileid, lineno, linepos, extent]`. */
type SpineEntry = [string, string | null, number, number, number, number, number];

interface UnitSpine {
  fileid: number;
  length: number;
  digest: string;
  spine?: SpineEntry[];
}

interface Case {
  id: string;
  why: string;
  files: Array<{ name: string; content: string }>;
  parseRaised: string | null;
  linkRaised: string | null;
  units?: number[];
  userUnits?: number[];
  fileMap?: Record<string, string>;
  refs?: Record<string, number>;
  spineLength?: number;
  spineDigest?: string;
  spine?: SpineEntry[];
  userUnitSpines?: UnitSpine[];
}

const fixture: { cases: Case[] } = JSON.parse(
  readFileSync(fileURLToPath(new URL('./fixtures/link-parity.json', import.meta.url)), 'utf8')
);

const live: Parser[] = [];
afterEach(() => {
  while (live.length) live.pop()!.dispose();
});

/**
 * The TypeScript side of the fixture's walk.
 *
 * Through the exported `childrenOf` and `getNodeName`, as `ast-parity.test.ts`
 * does, so this compares two parsers rather than two traversals.
 */
function spine(root: { children: ScopeChild[] }): SpineEntry[] {
  const out: SpineEntry[] = [];
  const visit = (node: ScopeChild, depth: number): void => {
    const l = node.location;
    out.push([node.constructor.name, getNodeName(node), depth, l.fileid, l.lineno, l.linepos, l.extent]);
    for (const c of childrenOf(node)) visit(c, depth + 1);
  };
  for (const c of root.children) visit(c, 0);
  return out;
}

/** Must match `digest()` in the generator, separators included. */
function digest(entries: SpineEntry[]): string {
  return createHash('sha256').update(JSON.stringify(entries)).digest('hex');
}

/**
 * Count resolved entries of the schema's two non-owning list fields.
 *
 * `imports` hangs off `SymbolScope` as an owned `SymbolImportSpec` rather than
 * among its children, so it is followed explicitly -- a children-only walk
 * finds no `SymbolImportSpec` at all and would report zero of everything
 * without failing. The generator's `refs()` does the same, for the same reason.
 */
function refs(root: ast.RootSymbolScope): Record<string, number> {
  const counts = { importSpecs: 0, imports: 0, functionScopes: 0, prototypes: 0 };
  const seen = new Set<unknown>();

  const visit = (node: ScopeChild): void => {
    if (seen.has(node)) return;
    seen.add(node);

    if (node instanceof ast.SymbolScope && node.imports !== null) {
      counts.importSpecs++;
      counts.imports += node.imports.imports.length;
    }
    if (node instanceof ast.SymbolFunctionScope) {
      counts.functionScopes++;
      counts.prototypes += node.prototypes.length;
    }
    for (const c of childrenOf(node)) visit(c);
  };

  if (root.imports !== null) {
    counts.importSpecs++;
    counts.imports += root.imports.imports.length;
  }
  for (const c of root.children) visit(c);
  return counts;
}

describe('link() parity with the native parser', () => {
  it('has a fixture with corpus coverage', () => {
    expect(fixture.cases.length).toBeGreaterThan(50);
    expect(fixture.cases.some((c) => c.id.startsWith('corpus:'))).toBe(true);
    expect(fixture.cases.some((c) => c.units !== undefined)).toBe(true);
  });

  for (const c of fixture.cases) {
    it(`${c.id}${c.why ? ` -- ${c.why}` : ''}`, async () => {
      const p = await createParser();
      live.push(p);

      let parseFailed = false;
      try {
        p.parseSources(c.files);
      } catch (e) {
        expect(e).toBeInstanceOf(ParseException);
        parseFailed = true;
      }

      if (c.parseRaised !== null) {
        // The native side never reached link(), so there is nothing to compare
        // beyond agreeing that the source does not parse.
        expect(parseFailed).toBe(true);
        return;
      }
      expect(parseFailed).toBe(false);

      let linkFailed = false;
      try {
        p.link();
      } catch (e) {
        expect(e).toBeInstanceOf(ParseException);
        linkFailed = true;
      }
      expect(linkFailed).toBe(c.linkRaised !== null);

      // A failed link still records its root -- ownership of the units moved
      // into it before the error was reported -- so the comparisons below run
      // either way.
      const root = p.root;
      expect(root).not.toBeNull();
      const r = root!;

      expect(r.units.map((u) => u.fileid), 'units').toEqual(c.units);
      expect(p.userUnits().map((u) => u.fileid), 'userUnits').toEqual(c.userUnits);
      expect(Object.fromEntries([...p.fileMap()].map(([k, v]) => [String(k), v])), 'fileMap').toEqual(
        c.fileMap
      );
      expect(refs(r), 'refs').toEqual(c.refs);

      const s = spine(r);
      expect(s.length, 'spine length').toBe(c.spineLength);
      if (c.spine) {
        expect(s, 'spine').toEqual(c.spine);
      } else {
        expect(digest(s), 'spine digest').toBe(c.spineDigest);
      }

      const units = p.userUnits();
      expect(units.length).toBe(c.userUnitSpines!.length);
      for (const [i, expected] of c.userUnitSpines!.entries()) {
        const u = units[i]!;
        expect(u.fileid, `unit ${i} fileid`).toBe(expected.fileid);
        const us = spine(u);
        expect(us.length, `unit ${expected.fileid} spine length`).toBe(expected.length);
        if (expected.spine) {
          expect(us, `unit ${expected.fileid} spine`).toEqual(expected.spine);
        } else {
          expect(digest(us), `unit ${expected.fileid} spine digest`).toBe(expected.digest);
        }
      }
    });
  }
});
