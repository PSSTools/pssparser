/**
 * What the core's parse-and-link session now does for `Parser`
 * (core-in-leaf-plan.md CF1): marker resolution and sorting, file names,
 * inactive `compile if` regions. tests/python/session checks the same
 * session through the Python binding.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { createParser, ParseException, type Parser } from '../src/index.js';

const live: Parser[] = [];

async function parser(): Promise<Parser> {
  const p = await createParser();
  live.push(p);
  return p;
}

afterEach(() => {
  while (live.length) live.pop()!.dispose();
});

const GOOD = 'component pss_top {\n  action A { }\n}\n';
const BAD_TYPE = 'component pss_top {\n  action A { no_such_t f; }\n}\n';

// tests/python/linking/test_compile_if_regions.py's M3.
const M3 =
  'import std_pkg::*;\nconst int WIDTH = 8;\ncomponent pss_top {\n  int a = 0xFF;\n' +
  "  bit[32] b = 32'hDEAD;\n" +
  '  compile if (WIDTH > 16) { int wide_f; } else { int narrow_f; }\n' +
  '  action go_a {\n    rand bit[8] v;\n  }\n}\n';

describe('session', () => {
  it('reports the regions a compile if left out, as Python does', async () => {
    const p = await parser();
    p.parseSources([{ name: 't.pss', content: M3 }]);
    p.link();
    expect(p.inactiveRegions()).toEqual([
      { fileid: 1, startLine: 6, startCol: 27, endLine: 6, endCol: 41 },
    ]);
  });

  it('resolves and sorts markers across files', async () => {
    const p = await parser();
    p.parseSources([
      { name: 'b.pss', content: BAD_TYPE },
      { name: 'a.pss', content: BAD_TYPE },
    ]);
    expect(() => p.link()).toThrow(ParseException);
    const files = p.markers.map((m) => m.file);
    expect(files).toEqual([...files].sort());
    expect(new Set(files)).toEqual(new Set(['a.pss', 'b.pss']));
  });

  it('clearMarkers() clears the session too', async () => {
    const p = await parser();
    p.parseSources([{ name: 't.pss', content: BAD_TYPE }]);
    expect(() => p.link()).toThrow(ParseException);
    p.clearMarkers();
    p.parseSources([{ name: 'u.pss', content: GOOD }]);
    p.link();
    expect(p.markers).toEqual([]);
  });

  it('keeps fileMap() after dispose()', async () => {
    const p = await parser();
    p.parseSources([{ name: 't.pss', content: GOOD }]);
    p.link();
    p.dispose();
    expect([...p.fileMap()]).toEqual([[1, 't.pss']]);
  });
});
