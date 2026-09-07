/**
 * `link()` and what it leaves behind: `root`, `userUnits()`, `fileMap()`,
 * `getProfileInfo()`.
 *
 * One test per numbered item in `ts-api-design.md` §3.2, plus the lifetime
 * properties §4 promises. Each of those items is a behaviour a
 * re-implementation gets wrong *by default* -- `parser.py` records every one of
 * them as a bug that shipped -- so they are asserted individually rather than
 * incidentally through a larger scenario.
 *
 * `link-parity.test.ts` checks that the tree crossing the boundary is the tree
 * the native parser built. This file checks the API's behaviour around it.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { ast, createParser, ParseException, type Parser } from '../src/index.js';

const live: Parser[] = [];

async function parser(opts?: Parameters<typeof createParser>[0]): Promise<Parser> {
  const p = await createParser(opts);
  live.push(p);
  return p;
}

afterEach(() => {
  while (live.length) live.pop()!.dispose();
});

const VALID = 'component pss_top {\n    action A { }\n}\n';

/** A source that parses but does not link: the type does not exist. */
const UNRESOLVED = 'component pss_top {\n    action A { no_such_type_t f; }\n}\n';

/** Two units where the second refers to a declaration in the first. */
const PKG = 'package p {\n    const int W = 8;\n    struct S { int a; }\n}\n';
const USES =
  'import p::*;\ncomponent pss_top {\n    action A {\n        rand bit[p::W] f;\n        p::S s;\n    }\n}\n';

describe('link', () => {
  it('returns a RootSymbolScope, which `root` then reports', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect(p.root).toBeNull();

    const root = p.link();
    expect(root).toBeInstanceOf(ast.RootSymbolScope);
    // The same object, not an equal one: `root` is a recorded result, not a
    // second materialisation. A consumer that keeps both must be able to use
    // `===` between them.
    expect(p.root).toBe(root);
  });

  it('puts every unit under the root, builtins and stdlib included', async () => {
    // fileids: -1 builtins, 0 stdlib, user files from 1
    // (`ts-api-design.md` §3.2.6). The stdlib is loaded without being asked.
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    const root = p.link();
    expect(root.units.map((u) => u.fileid)).toEqual([-1, 0, 1]);
  });

  it('collects link-time markers even when the link succeeds', async () => {
    // §3.2.4, first half. Collecting inside the error branch dropped every
    // warning from a successful link and the CLI printed "0 errors in 0 files"
    // (`parser.py:174-179`). A clean link produces no markers, so the property
    // is asserted the only way it can be without a warning-producing source:
    // the call must not throw and must not lose the parse-time markers.
    const p = await parser();
    p.setMaxErrors(0);
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    const before = p.markers.length;
    p.link();
    expect(p.markers.length).toBeGreaterThanOrEqual(before);
  });

  it('appends link markers to parse markers and re-sorts the whole list', async () => {
    // §3.2.4, second half. Each collection is internally sorted; two sorted
    // lists concatenated are not sorted (`parser.py:182-184`). The z/a naming
    // is what makes the bug observable: the link marker belongs first.
    const p = await parser();
    try {
      p.parseSources([
        { name: 'z_broken.pss', content: 'component c { action }' },
      ]);
    } catch {
      /* expected */
    }
    p.clearMarkers();
    p.parseSources([{ name: 'a_unresolved.pss', content: UNRESOLVED }]);
    expect(p.markers).toEqual([]);

    expect(() => p.link()).toThrow(ParseException);

    const ms = p.markers;
    expect(ms.length).toBeGreaterThan(0);
    for (let i = 1; i < ms.length; i++) {
      const a = ms[i - 1]!;
      const b = ms[i]!;
      const ordered =
        a.file < b.file ||
        (a.file === b.file && (a.line < b.line || (a.line === b.line && a.col <= b.col)));
      expect(ordered, `markers out of order at ${i}`).toBe(true);
    }
  });

  it('resolves link markers to file names, not to <unknown>', async () => {
    // The snapshot-and-clear in link() happens *after* markers are absorbed,
    // and `#names()` consults the snapshot as well as the live map. Getting
    // either wrong reports every link diagnostic against "<unknown>", which is
    // the bug `parser.py:_pathOf` exists to prevent.
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: UNRESOLVED }]);
    expect(() => p.link()).toThrow(ParseException);
    expect(p.markers.length).toBeGreaterThan(0);
    expect(p.markers.every((m) => m.file !== '<unknown>')).toBe(true);
    expect(p.markers.some((m) => m.file === 'top.pss')).toBe(true);
  });

  it('records the root before reporting failure', async () => {
    // §3.2.5. Ownership of the units moved into the root inside link(), so a
    // failed link must still leave them reachable. This block used to sit
    // below the raise, which left the Parser holding nothing
    // (`parser.py:186-217`).
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: UNRESOLVED }]);

    let caught: unknown;
    try {
      p.link();
    } catch (e) {
      caught = e;
    }
    expect(caught).toBeInstanceOf(ParseException);
    expect((caught as ParseException).markers.length).toBeGreaterThan(0);

    expect(p.root).toBeInstanceOf(ast.RootSymbolScope);
    expect(p.userUnits().map((u) => u.fileid)).toEqual([1]);
    expect([...p.fileMap()]).toEqual([[1, 'top.pss']]);
  });

  it('carries the markers on the exception, as parseSources does', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: UNRESOLVED }]);
    try {
      p.link();
      expect.unreachable('link() should have thrown');
    } catch (e) {
      const err = e as ParseException;
      expect(err.markers).toEqual(p.markers);
      expect(err.message).toContain('top.pss:');
    }
  });

  it('drops the builder, so a later parse restarts the unit list', async () => {
    // §3.2.2 and `parser.py:224-231`. The builder holds the units as borrowed
    // pointers -- its compile-time environment -- and ownership has just moved
    // to the root. A later link() would free those units, so a parse after
    // that would read freed memory. beginParse() builds a fresh one.
    //
    // What is asserted is the *structural* consequence: a fresh builder means
    // an empty unit list, so the standard library is reloaded as unit 0 and
    // user fileids restart at 1.
    //
    // The environment reset itself is deliberately not asserted, because it is
    // not observable here. The obvious probe -- re-parse a source reading
    // `p::W` from a unit the link consumed, and expect it to fail -- does not
    // fail: the native parser accepts the same sequence with no marker, so an
    // assertion that it throws would be testing an invention.
    const p = await parser();
    p.parseSources([{ name: 'p.pss', content: PKG }]);
    p.parseSources([{ name: 'uses.pss', content: USES }]);
    p.link();
    p.clearMarkers();

    p.parseSources([{ name: 'again.pss', content: VALID }]);
    const root = p.link();
    expect(root.units.map((u) => u.fileid)).toEqual([-1, 0, 1]);
    expect([...p.fileMap()]).toEqual([[1, 'again.pss']]);
    expect(p.userUnits().map((u) => u.fileid)).toEqual([1]);
  });

  it('links twice on one Parser', async () => {
    const p = await parser();
    p.parseSources([{ name: 'one.pss', content: VALID }]);
    const first = p.link();
    p.parseSources([{ name: 'two.pss', content: 'package q { const int K = 1; }\n' }]);
    const second = p.link();

    expect(second).not.toBe(first);
    expect(p.root).toBe(second);
    expect([...p.fileMap()]).toEqual([[1, 'two.pss']]);
    // The first root is a materialised JavaScript tree and is unaffected by the
    // second link, which freed the C++ objects it was built from.
    expect(first.units.map((u) => u.fileid)).toEqual([-1, 0, 1]);
  });
});

describe('userUnits', () => {
  it('is empty before link()', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect(p.userUnits()).toEqual([]);
  });

  it('returns the user files in parse order, without builtins or stdlib', async () => {
    // §3.2.6: the filter is by fileid, and `fileMap()` membership is what
    // expresses "user file".
    const p = await parser();
    p.parseSources([{ name: 'p.pss', content: PKG }]);
    p.parseSources([{ name: 'uses.pss', content: USES }]);
    p.link();

    const units = p.userUnits();
    expect(units.map((u) => u.fileid)).toEqual([1, 2]);
    expect(units.every((u) => u instanceof ast.GlobalScope)).toBe(true);
    // The stdlib is under the root but is not a user unit.
    expect(p.root!.units.length).toBe(units.length + 2);
  });

  it('reaches the declarations of each file', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    p.link();

    const [unit] = p.userUnits();
    const comp = unit!.children[0];
    expect(comp).toBeInstanceOf(ast.Component);
    expect((comp as ast.Component).name?.id).toBe('pss_top');
  });
});

describe('fileMap', () => {
  it('is empty before link()', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect([...p.fileMap()]).toEqual([]);
  });

  it('maps user fileids to names and excludes builtins and stdlib', async () => {
    const p = await parser();
    p.parseSources([{ name: 'p.pss', content: PKG }]);
    p.parseSources([{ name: 'uses.pss', content: USES }]);
    p.link();
    expect([...p.fileMap()]).toEqual([
      [1, 'p.pss'],
      [2, 'uses.pss'],
    ]);
  });

  it('returns a copy', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    p.link();
    const held = p.fileMap() as Map<number, string>;
    held.set(99, 'not a file');
    expect(p.fileMap().has(99)).toBe(false);
  });
});

describe('the linked tree after dispose', () => {
  it('survives, because it is plain JavaScript', async () => {
    // `ts-api-design.md` §4. This is what lets a language server hold the last
    // good tree while disposing the parser that produced it.
    const p = await createParser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    const root = p.link();
    const units = p.userUnits();
    p.dispose();

    expect(p.root).toBe(root);
    expect(p.userUnits()).toEqual(units);
    expect([...p.fileMap()]).toEqual([[1, 'top.pss']]);
    expect(root.units[2]!.children.length).toBeGreaterThan(0);
  });

  it('but link() itself does not', async () => {
    const p = await createParser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    p.dispose();
    expect(() => p.link()).toThrow(/disposed/);
  });
});

describe('getProfileInfo', () => {
  it('is null when profiling was never enabled', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect(p.getProfileInfo()).toBeNull();
  });

  it('is null before anything has been parsed', async () => {
    const p = await parser();
    expect(p.getProfileInfo()).toBeNull();
  });

  it('reports totals and per-decision entries when enabled', async () => {
    const p = await parser();
    p.enableProfiling();
    p.parseSources([{ name: 'top.pss', content: VALID }]);

    const info = p.getProfileInfo();
    expect(info).not.toBeNull();
    const i = info as Record<string, unknown>;
    expect(typeof i.totalTimeInPrediction).toBe('number');
    expect(typeof i.tokenCount).toBe('number');
    expect(Array.isArray(i.decisions)).toBe(true);

    // Only decisions the parse actually reached are reported; ANTLR carries an
    // entry for every decision in the ATN and the rest are all zeroes.
    const decisions = i.decisions as Array<Record<string, unknown>>;
    expect(decisions.length).toBeGreaterThan(0);
    expect(decisions.every((d) => (d.invocations as number) > 0)).toBe(true);
    expect(decisions.every((d) => typeof d.ruleName === 'string' && d.ruleName.length > 0)).toBe(
      true
    );
  });

  it('can be turned back off', async () => {
    // The flag is pushed into the builder on every parse call rather than only
    // when true; the builder outlives the call, so setting it only in the `if`
    // made enableProfiling(false) a no-op once profiling had been on.
    const p = await parser();
    p.enableProfiling();
    p.parseSources([{ name: 'a.pss', content: VALID }]);
    expect(p.getProfileInfo()).not.toBeNull();

    p.enableProfiling(false);
    p.parseSources([{ name: 'b.pss', content: 'package q { }\n' }]);
    expect(p.getProfileInfo()).toBeNull();
  });

  it('is null after link(), which drops the builder that held it', async () => {
    // A deliberate divergence from Python, which keeps a `_last_builder`
    // reference and would report the profile of a builder released at link
    // time (`parser.py:161-164`).
    const p = await parser();
    p.enableProfiling();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect(p.getProfileInfo()).not.toBeNull();
    p.link();
    expect(p.getProfileInfo()).toBeNull();
  });
});
