/**
 * Phase 1 acceptance (`ts-wasm-impl-plan.md` §1.7), plus the semantics from
 * `ts-api-design.md` §3.2 that are reachable without the AST.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { createParser, ParseException, type Parser } from '../src/index.js';

/**
 * Parsers created by a test, disposed after it.
 *
 * Every test needs this and a test that forgets leaks WASM memory silently --
 * the FinalizationRegistry warning is a development aid, not a test failure.
 * Tracking them centrally means no test has to remember.
 */
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

describe('parseSources', () => {
  it('parses a valid source with no markers', async () => {
    const p = await parser();
    expect(p.parseSources([{ name: 'top.pss', content: VALID }])).toBe(true);
    expect(p.markers).toEqual([]);
  });

  it('throws ParseException on a syntax error and carries the markers', async () => {
    const p = await parser();
    let caught: unknown;
    try {
      p.parseSources([{ name: 'bad.pss', content: 'component pss_top { action }' }]);
    } catch (e) {
      caught = e;
    }

    expect(caught).toBeInstanceOf(ParseException);
    const err = caught as ParseException;

    // Markers are collected *before* the throw, so the exception is
    // self-describing (parser.py:106-109). This is the property that would be
    // lost by a re-implementation that raised first.
    expect(err.markers.length).toBeGreaterThan(0);
    expect(err.markers.every((m) => m.file === 'bad.pss')).toBe(true);

    // ...and the same markers are on the parser.
    expect(p.markers).toEqual(err.markers);

    // The message is the multi-line summary, one line per marker.
    expect(err.message.split('\n').filter(Boolean)).toHaveLength(err.markers.length);
    expect(err.message).toContain('bad.pss:');
  });

  it('loads the standard library without being asked', async () => {
    // `executor_claim_s` is declared in the standard library, which is loaded
    // lazily into unit 0 on first parse (ts-api-design.md §3.2.1). If it were
    // not, this would not resolve.
    const p = await parser();
    expect(() =>
      p.parseSources([
        {
          name: 'uses_stdlib.pss',
          content:
            'component pss_top {\n    action A {\n        executor_claim_s<> claim;\n    }\n}\n',
        },
      ])
    ).not.toThrow();
    expect(p.markers).toEqual([]);
  });

  it('assigns user fileids from 1, with the standard library at 0', async () => {
    // Observable through the marker's `file`: a marker in the first user file
    // resolves to that file's name only if the stdlib took fileid 0 and the
    // user file took 1.
    const p = await parser();
    try {
      p.parseSources([{ name: 'only.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }
    expect(p.markers[0]?.file).toBe('only.pss');
  });

  it('reports the failing file by name across several sources', async () => {
    const p = await parser();
    try {
      p.parseSources([
        { name: 'a.pss', content: 'package p {\n    const int K = 4;\n}\n' },
        { name: 'b.pss', content: 'component pss_top {\n    action }\n}\n' },
      ]);
    } catch {
      /* expected */
    }
    expect(p.markers.length).toBeGreaterThan(0);
    expect(p.markers.every((m) => m.file === 'b.pss')).toBe(true);
  });

  it('stays usable after a caught ParseException', async () => {
    // This asserts the *contract*: a caught ParseException leaves the Parser
    // usable, so parsing can continue.
    //
    // It is also the closest reachable test for a memory-safety fix in
    // `wasm/bindings.cpp`, and it is worth being precise about what it does
    // not do. The builder keeps borrowed pointers to every unit it has
    // processed, and the push into `m_prior_units` is not guarded on whether
    // the parse produced errors (AstBuilderInt.cpp:153). An earlier version of
    // the binding freed a failed unit, leaving that pointer dangling for
    // `resolvePathTargetInPriorUnits` to walk.
    //
    // Building with the free restored, this test still passes -- and so does a
    // probe that deliberately forces the cross-unit lookup with heap churn in
    // between. The freed block simply is not recycled, so the read returns
    // stale-but-intact data and nothing observable differs. **This test cannot
    // distinguish the fixed binding from the broken one.** The justification
    // for the fix is the code, not this assertion; catching a regression here
    // would need an ASan build of the WASM core.
    const p = await parser();
    for (let i = 0; i < 3; i++) {
      expect(() =>
        p.parseSources([{ name: `bad${i}.pss`, content: 'component c { action }' }])
      ).toThrow(ParseException);

      expect(() =>
        p.parseSources([{ name: `good${i}.pss`, content: `component ok${i} { action A { } }` }])
      ).not.toThrow();
    }
  });

  it('does not consume a fileid for a source that failed to parse', async () => {
    // parser.py appends to self._files only after the error check
    // (parser.py:111), so a failed unit is not part of the environment and the
    // next source takes the id it would have had. Observable through the
    // marker's resolved file name: if the ids drifted, this marker would
    // resolve to the *earlier* file's name, or to <unknown>.
    const p = await parser();
    try {
      p.parseSources([{ name: 'first-bad.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }
    p.clearMarkers();
    try {
      p.parseSources([{ name: 'second-bad.pss', content: 'component d { action }' }]);
    } catch {
      /* expected */
    }
    expect(p.markers.length).toBeGreaterThan(0);
    expect(p.markers.every((m) => m.file === 'second-bad.pss')).toBe(true);
  });

  it('keeps one builder across calls, so a later source sees earlier constants', async () => {
    // ts-api-design.md §3.2.2. Compile-time expressions are evaluated during
    // AST construction and may reference constants from a previously
    // processed unit (PSS 3.1 19.1.2). A builder per call would restart that
    // environment and `p::W` would not resolve.
    const p = await parser();
    p.parseSources([{ name: 'consts.pss', content: 'package p {\n    const int W = 8;\n}\n' }]);
    expect(() =>
      p.parseSources([
        {
          name: 'uses.pss',
          content:
            'import p::*;\ncomponent pss_top {\n    action A {\n        rand bit[p::W] f;\n    }\n}\n',
        },
      ])
    ).not.toThrow();
    expect(p.markers).toEqual([]);
  });
});

describe('markers', () => {
  it('accumulates across calls and stays sorted by (file, line, col)', async () => {
    const p = await parser();
    // Parse a clean file first so the failing one is not the only source.
    p.parseSources([{ name: 'z_clean.pss', content: VALID }]);
    try {
      p.parseSources([{ name: 'a_broken.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }

    const ms = p.markers;
    for (let i = 1; i < ms.length; i++) {
      const a = ms[i - 1]!;
      const b = ms[i]!;
      const ordered =
        a.file < b.file ||
        (a.file === b.file && (a.line < b.line || (a.line === b.line && a.col <= b.col)));
      expect(ordered, `markers out of order at ${i}`).toBe(true);
    }
  });

  it('returns a copy, so a held array does not change under the next parse', async () => {
    const p = await parser();
    try {
      p.parseSources([{ name: 'bad.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }
    const held = p.markers;
    const n = held.length;
    expect(n).toBeGreaterThan(0);

    try {
      p.parseSources([{ name: 'bad2.pss', content: 'component d { action }' }]);
    } catch {
      /* expected */
    }
    expect(held).toHaveLength(n);
    expect(p.markers.length).toBeGreaterThan(n);
  });

  it('clearMarkers() drops them', async () => {
    // ts-api-design.md §9 Q5: accumulation is the default and is Python's
    // behaviour, but a language server re-parsing on every keystroke needs a
    // way out.
    const p = await parser();
    try {
      p.parseSources([{ name: 'bad.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }
    expect(p.markers.length).toBeGreaterThan(0);
    p.clearMarkers();
    expect(p.markers).toEqual([]);
  });

  it('caps errors and announces the cutoff when setMaxErrors is used', async () => {
    const capped = await parser();
    capped.setMaxErrors(1);
    try {
      capped.parseSources([
        { name: 'many.pss', content: 'component c { action } action } action }\n' },
      ]);
    } catch {
      /* expected */
    }

    const uncapped = await parser();
    try {
      uncapped.parseSources([
        { name: 'many.pss', content: 'component c { action } action } action }\n' },
      ]);
    } catch {
      /* expected */
    }

    const errs = (p: Parser) => p.markers.filter((m) => m.severity === 'error');
    expect(errs(capped).length).toBeLessThan(errs(uncapped).length);
    expect(capped.markers.some((m) => m.code === 'PSS029')).toBe(true);
  });
});

describe('options', () => {
  it('reports the collection flags it was built with', async () => {
    const plain = await parser();
    expect(plain.collectDocstrings).toBe(false);
    expect(plain.collectComments).toBe(false);

    const rich = await parser({ collectDocstrings: true, collectComments: true });
    expect(rich.collectDocstrings).toBe(true);
    expect(rich.collectComments).toBe(true);
  });

  it('parses with comment collection on', async () => {
    const p = await parser({ collectComments: true });
    expect(() =>
      p.parseSources([
        { name: 'doc.pss', content: '/** An action. */\ncomponent pss_top {\n    action A { }\n}\n' },
      ])
    ).not.toThrow();
    expect(p.markers).toEqual([]);
  });
});

describe('dispose', () => {
  it('is idempotent', async () => {
    const p = await createParser();
    p.dispose();
    expect(() => p.dispose()).not.toThrow();
  });

  it('makes every other method throw', async () => {
    const p = await createParser();
    p.dispose();
    expect(() => p.parseSources([{ name: 'x.pss', content: VALID }])).toThrow(/disposed/);
    expect(() => p.setMaxErrors(1)).toThrow(/disposed/);
    expect(() => p.enableProfiling()).toThrow(/disposed/);
  });

  it('leaves already-collected markers readable', async () => {
    // ts-api-design.md §4: materialised results are plain JavaScript and
    // survive dispose(). Markers are the part of that which exists today.
    const p = await createParser();
    try {
      p.parseSources([{ name: 'bad.pss', content: 'component c { action }' }]);
    } catch {
      /* expected */
    }
    const before = p.markers;
    p.dispose();
    expect(p.markers).toEqual(before);
  });

  it('works as a disposable resource', async () => {
    // The `using` form (ts-api-design.md §8) reduces to this lookup.
    const p = await createParser();
    expect(typeof p[Symbol.dispose]).toBe('function');
    p[Symbol.dispose]();
    expect(() => p.setMaxErrors(0)).toThrow(/disposed/);
  });
});

describe('not yet implemented', () => {
  // These are shaped and declared but need the AST to cross the boundary
  // (impl plan Phase 2/3). Asserting on them keeps the stubs honest: a stub
  // that silently returned a plausible empty value would let a consumer build
  // on nothing.
  it('link/userUnits/getProfileInfo say so, and root is null', async () => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content: VALID }]);
    expect(() => p.link()).toThrow(/not implemented/);
    expect(() => p.userUnits()).toThrow(/not implemented/);
    expect(() => p.getProfileInfo()).toThrow(/not implemented/);
    expect(p.root).toBeNull();
  });
});
