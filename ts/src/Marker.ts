/**
 * Diagnostics produced by parsing and linking.
 *
 * The shape mirrors the dict `_collectMarkers` builds in
 * `python/pssparser/parser.py:311-353` field for field. That shape is stable,
 * is already what every pssparser consumer reads, and already carries `code`
 * -- inventing a second vocabulary here would mean two things to keep in step
 * for no gain.
 */

/**
 * Note the absence of `'unknown'`.
 *
 * Python maps an unrecognised `MarkerSeverityE` to the string `"unknown"` and
 * hands it to the caller. This union does not, because a consumer forced to
 * write a branch for `'unknown'` is writing a branch for a core bug, not for
 * anything a PSS source can cause. The C++ binding throws instead
 * (`wasm/bindings.cpp`, `severityName`), which turns it into one failure at
 * the boundary rather than a case in every `switch` downstream.
 */
export type MarkerSeverity = 'error' | 'warning' | 'info' | 'hint';

/** A secondary location attached to a marker -- a prior declaration, a
 *  conflicting definition, the other end of a mismatch. */
export interface MarkerRelation {
  file: string;
  /** 1-based. */
  line: number;
  /** 1-based. */
  col: number;
  label: string;
}

export interface Marker {
  severity: MarkerSeverity;
  message: string;
  file: string;
  /** 1-based. */
  line: number;
  /** 1-based; the core's 0-based `Location.linepos` plus one. */
  col: number;
  /**
   * Length in characters of the primary span.
   *
   * `Location.extent` defaults to -1 and the core does not always set it, so
   * -1 reaches consumers and means "unknown". It is passed through rather than
   * clamped to 0: the Python API does the same (`core.pyx:371-373`), and
   * rewriting it here would invent information the core did not supply.
   */
  extent: number;
  related: MarkerRelation[];
  /**
   * Stable marker id, e.g. `"PSS020"`.
   *
   * Optional because core C++ markers do not all carry one today: `IMarker`
   * has `setId()`, but the Python side recovers ids for the rest by regex
   * matching message text against `MarkerDef.patterns`, which is a second
   * source of truth. When the marker-catalog work lands
   * (`wasm-core-plan.md` §6 step 1) every marker carries an id and this field
   * becomes required -- a breaking change, and the reason to do it before 1.0
   * rather than after (`ts-api-design.md` §5).
   */
  code?: string;
}

/**
 * A marker as it crosses the WASM boundary.
 *
 * The difference from `Marker` is the whole of the C++/TypeScript split: the
 * core reports a `fileid`, and turning that into a path is bookkeeping over
 * values that needs no boundary crossing. See the header comment in
 * `wasm/bindings.cpp`.
 */
export interface RawMarker {
  severity: MarkerSeverity;
  message: string;
  fileid: number;
  line: number;
  col: number;
  extent: number;
  related: Array<{ fileid: number; line: number; col: number; label: string }>;
  code?: string;
}

/**
 * fileid conventions (`ts-api-design.md` §3.2.6):
 *
 *   -1  builtins    synthesised types with no source text
 *    0  stdlib      loaded lazily into unit 0 on first parse
 *   1.. user files  in the order they were passed to parseSources()
 */
export const FILEID_BUILTIN = -1;
export const FILEID_STDLIB = 0;

/** Displayed for a fileid with no known path, matching `_pathOf`'s fallback
 *  (`parser.py:287`). */
export const UNKNOWN_FILE = '<unknown>';

const WELL_KNOWN: ReadonlyMap<number, string> = new Map([
  [FILEID_BUILTIN, '<builtin>'],
  [FILEID_STDLIB, '<stdlib>'],
]);

/** Resolve a fileid to a display path. */
export function pathOf(fileid: number, files: ReadonlyMap<number, string>): string {
  return files.get(fileid) ?? WELL_KNOWN.get(fileid) ?? UNKNOWN_FILE;
}

/** Turn the boundary form into the public form. */
export function resolveMarker(raw: RawMarker, files: ReadonlyMap<number, string>): Marker {
  const m: Marker = {
    severity: raw.severity,
    message: raw.message,
    file: pathOf(raw.fileid, files),
    line: raw.line,
    col: raw.col,
    extent: raw.extent,
    related: raw.related.map((r) => ({
      file: pathOf(r.fileid, files),
      line: r.line,
      col: r.col,
      label: r.label,
    })),
  };
  // Assigned conditionally so the key is absent, not present-and-undefined:
  // `'code' in marker` is how a consumer asks whether the core supplied one,
  // and parser.py:343-344 makes the same distinction.
  if (raw.code !== undefined) {
    m.code = raw.code;
  }
  return m;
}

/**
 * Sort markers by (file, line, col).
 *
 * Different passes -- parse-time syntax errors, link-time resolution, the
 * post-link completeness check -- each emit in their own encounter order, and
 * interleaving those without re-sorting produces diagnostics that jump around
 * the source file.
 *
 * The sort must be **stable**, so markers sharing a location keep their
 * emission order: a cascade at one point reads as a cascade only if its first
 * marker stays first. `Array.prototype.sort` has been required to be stable
 * since ES2019, so this needs no help.
 *
 * The key is the resolved *file name*, not the fileid. That is why sorting
 * happens here rather than in C++: the fileid order and the path order are not
 * the same order, and `parser.py:352` sorts on the path.
 *
 * Sorts in place and returns the same array.
 */
export function sortMarkers(markers: Marker[]): Marker[] {
  return markers.sort((a, b) => {
    if (a.file !== b.file) return a.file < b.file ? -1 : 1;
    if (a.line !== b.line) return a.line - b.line;
    return a.col - b.col;
  });
}

const SEVERITY_PREFIX: Record<MarkerSeverity, string> = {
  error: 'Error: ',
  warning: 'Warning: ',
  info: 'Info: ',
  hint: 'Hint: ',
};

/**
 * The multi-line summary used as `ParseException.message`.
 *
 * Format is `_mkErrorMessage`'s (`parser.py:289-309`), including the trailing
 * newline on every line: consumers print this straight to a terminal.
 */
export function formatMarkers(markers: readonly Marker[]): string {
  let msg = '';
  for (const m of markers) {
    msg += `${SEVERITY_PREFIX[m.severity]}${m.message} ${m.file}:${m.line}:${m.col}\n`;
  }
  return msg;
}
