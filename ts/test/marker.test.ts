import { describe, expect, it } from 'vitest';

import { resolveLocation, resolveMarker, type CoreLibraryFile, type RawMarker } from '../src/Marker.js';

// Two files back to back in unit 0, as the core builds them.
const STDLIB: CoreLibraryFile[] = [
  { name: 'a_pkg.pss', firstLine: 1, numLines: 10, text: '' },
  { name: 'b_pkg.pss', firstLine: 11, numLines: 5, text: '' },
];
const FILES = new Map([[1, 't.pss']]);

describe('resolveLocation', () => {
  it('maps a core-library line to its file and local line', () => {
    expect(resolveLocation(0, 1, FILES, STDLIB)).toEqual({ file: '<stdlib>/a_pkg.pss', line: 1 });
    expect(resolveLocation(0, 10, FILES, STDLIB)).toEqual({ file: '<stdlib>/a_pkg.pss', line: 10 });
    expect(resolveLocation(0, 12, FILES, STDLIB)).toEqual({ file: '<stdlib>/b_pkg.pss', line: 2 });
  });

  it('falls back to a bare <stdlib> without the table, or past its end', () => {
    expect(resolveLocation(0, 12, FILES)).toEqual({ file: '<stdlib>', line: 12 });
    expect(resolveLocation(0, 99, FILES, STDLIB)).toEqual({ file: '<stdlib>', line: 99 });
  });

  it('leaves a user location alone', () => {
    expect(resolveLocation(1, 12, FILES, STDLIB)).toEqual({ file: 't.pss', line: 12 });
  });
});

describe('resolveMarker', () => {
  it('maps a related core-library location', () => {
    const raw: RawMarker = {
      severity: 'error',
      message: "duplicate declaration of 's'",
      fileid: 1,
      line: 1,
      col: 3,
      extent: 1,
      related: [{ fileid: 0, line: 13, col: 5, label: 'first declared here' }],
    };
    const m = resolveMarker(raw, FILES, STDLIB);
    expect(m.file).toBe('t.pss');
    expect(m.related).toEqual([{ file: '<stdlib>/b_pkg.pss', line: 3, col: 5, label: 'first declared here' }]);
  });
});
