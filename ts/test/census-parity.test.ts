/**
 * Every node, every field: the AST the WASM core builds is the AST the native
 * core builds, past the declaration spine.
 *
 * `ast-parity.test.ts` and `link-parity.test.ts` walk `ASTUtils.walkScope` --
 * `Scope` and `SymbolChildrenScope` children, with each node's class, name and
 * location. That is the containment structure and three fields per node. It
 * never enters an expression, a constraint body or an exec block, so a defect
 * confined to `ExprBin.op` passes both of them.
 *
 * This suite compares the *census*: a pre-order walk of the ownership graph
 * recording every field of every node. Both walkers are generated from the
 * schema in one run by `astbuilder gen-census` -- `scripts/generated/census_gen.py`
 * produced the fixture from the native AST, `test/generated/census.ts` walks the
 * tree the deserializer built here. See `astbuilder/gen_census.py` for what the
 * pair covers and for the two things it does not (map fields, and integer
 * values above 2^53).
 *
 * The ground truth is independent in the way `serialize.test.ts`'s is not: that
 * one proves the two halves of the wire format agree with each other, which
 * they would even if both were wrong in the same way, because one generator
 * emits both. Here the expectation comes from the native AST read through the
 * Cython accessors -- a different interface, not a different opinion about the
 * same buffer.
 */
import { describe, expect, it } from 'vitest';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { deserialize, initPssParser } from '../src/index.js';
import { census } from './generated/census.js';

interface Summary {
  count: number;
  classes: Record<string, number>;
  digest: string;
  /** Present only for the inline cases' user units; see the fixture generator. */
  records?: unknown[][];
}

interface UnitSummary extends Summary {
  fileid: number;
}

interface Fixture {
  cases: Array<{
    id: string;
    why: string;
    files: Array<{ name: string; content: string }>;
    parseRaised: string | null;
    linkRaised: string | null;
    units: UnitSummary[];
    root: Summary | null;
  }>;
}

const fixture: Fixture = JSON.parse(
  readFileSync(fileURLToPath(new URL('./fixtures/census-parity.json', import.meta.url)), 'utf8')
);

/**
 * sha256 of the record stream as compact JSON.
 *
 * `JSON.stringify` is the shape the Python side reproduces with
 * `separators=(',', ':')` and `ensure_ascii=False`; either default would make
 * the digests differ for reasons that have nothing to do with the AST.
 */
function digest(records: unknown[][]): string {
  return createHash('sha256').update(JSON.stringify(records), 'utf8').digest('hex');
}

/**
 * Compare one census against its fixture entry.
 *
 * Count and histogram are checked before the digest, and separately, because a
 * digest tells you only that two streams differ. The histogram usually names
 * the class that gained or lost nodes, and `records` -- carried for the inline
 * cases -- puts the first divergence in the diff.
 */
function expectCensus(actual: ReturnType<typeof census>, want: Summary, where: string): void {
  expect(actual.count, `${where}: node count`).toBe(want.count);
  expect(actual.classes, `${where}: nodes by class`).toEqual(want.classes);
  if (want.records !== undefined) {
    expect(actual.records, `${where}: records`).toEqual(want.records);
  }
  expect(digest(actual.records), `${where}: record digest`).toBe(want.digest);
}

describe('AST census parity with the native parser', () => {
  it('has a fixture with corpus coverage and full records for the inline cases', () => {
    expect(fixture.cases.length).toBeGreaterThan(50);
    expect(fixture.cases.some((c) => c.id.startsWith('corpus:'))).toBe(true);
    expect(fixture.cases.some((c) => c.units.some((u) => u.records !== undefined))).toBe(true);
  });

  it('descends past the declaration spine', () => {
    // The suite's whole reason for existing, asserted rather than assumed: if
    // the census were still a spine walk it would pass every case below while
    // covering nothing new. `ExprBin` is not reachable by `ASTUtils.walkScope`.
    const c = fixture.cases.find((x) => x.id === 'expressions');
    expect(c, 'the expressions case is missing from the fixture').toBeDefined();
    const unit = c!.units.find((u) => u.fileid === 1);
    expect(unit?.classes['ExprBin'] ?? 0).toBeGreaterThan(3);
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

        if (c.parseRaised !== null) {
          // The native side threw and recorded nothing. The WASM side has to
          // agree that this source does not parse -- a census taken only on
          // sources that parse is taken on the easy half.
          expect(failed || s.hasErrors()).toBe(true);
          return;
        }

        expect(s.hasErrors()).toBe(false);

        // Units first: link() consumes them, and after it `serializeUnit` has
        // nothing left to serialise.
        for (const unit of c.units) {
          const root = deserialize(new Uint8Array(s.serializeUnit(unit.fileid)));
          expect(root, `unit ${unit.fileid} deserialised to null`).not.toBeNull();
          expectCensus(census(root), unit, `${c.id} unit ${unit.fileid}`);
        }

        if (c.root === null) {
          return;
        }

        // A failed link still produces a root -- ownership of every unit moved
        // into it before the error was reported -- and the fixture took its
        // census from exactly that root.
        s.link();
        expect(s.hasRoot(), 'link() produced no root').toBe(true);
        const linked = deserialize(new Uint8Array(s.serializeRoot()));
        expect(linked, 'linked root deserialised to null').not.toBeNull();
        expectCensus(census(linked), c.root, `${c.id} linked root`);
      } finally {
        s.delete();
      }
    });
  }
});
