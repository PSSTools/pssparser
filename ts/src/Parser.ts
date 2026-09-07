/**
 * The PSS parser.
 *
 * A transliteration of `python/pssparser/parser.py`, not a new design. That
 * file is 380 lines of accumulated judgement about what a pssparser consumer
 * needs -- stdlib auto-loading, builder reuse across parse calls, marker
 * collection on both success and failure, fileid conventions -- and most of
 * its comments record a bug that motivated the current shape. Where this file
 * differs from it, the difference is forced by the runtime and is commented as
 * such; everywhere else the Python source is the specification and the
 * tiebreaker.
 */
import {
  formatMarkers,
  resolveMarker,
  sortMarkers,
  type Marker,
  type RawMarker,
} from './Marker.js';
import { initPssParser, type ParserSessionHandle, type InitOptions } from './wasm/loader.js';

// `using` lowers to a Symbol.dispose lookup, and the well-known symbol is
// absent on runtimes predating the proposal's implementation (Node < 18.18).
// Defining it here rather than depending on a polyfill package keeps the
// published package dependency-free, which is worth a line of setup.
//
// This must run before the class below is *defined*, not merely before it is
// instantiated: a computed method key is evaluated when the class definition
// is evaluated, so a polyfill at the foot of the file would install the symbol
// after `[Symbol.dispose]` had already been keyed on `undefined`.
if (typeof (Symbol as { dispose?: symbol }).dispose === 'undefined') {
  Object.defineProperty(Symbol, 'dispose', {
    value: Symbol.for('Symbol.dispose'),
    configurable: false,
    writable: false,
  });
}

export interface ParserOptions extends InitOptions {
  /** Collect doc comments and attach them to the declarations they document,
   *  reachable as `getDocstring()` on any `ScopeChild`. */
  collectDocstrings?: boolean;
  /** Capture *every* comment, on statements as well as declarations, as
   *  `ScopeChild.comments`. Implies `collectDocstrings`. */
  collectComments?: boolean;
}

/** An in-memory source file. */
export interface SourceFile {
  /** The name reported in markers and in `fileMap()`. Need not be a real
   *  path -- an unsaved editor buffer has no path, and that is the case this
   *  API is shaped for. */
  name: string;
  content: string;
}

/**
 * Thrown when a parse or link produces any error-severity marker.
 *
 * `markers` carries the diagnostics collected *before* the throw, which is the
 * whole reason this class exists rather than a plain `Error`. Both Python
 * parse paths call `_collectMarkers` and then raise (`parser.py:106-109`), so
 * a caught exception is self-describing; `parser.markers` holds the same list.
 */
export class ParseException extends Error {
  readonly markers: readonly Marker[];

  constructor(message: string, markers: readonly Marker[] = []) {
    super(message);
    this.name = 'ParseException';
    this.markers = markers;
  }
}

/**
 * Instantiate the WASM core if it is not loaded yet, and build a `Parser`.
 *
 * Async because WASM instantiation is; there is no synchronous construction
 * path and there will not be one. Use `initPssParser()` to move the cost
 * somewhere you control.
 */
export async function createParser(opts: ParserOptions = {}): Promise<Parser> {
  const module = await initPssParser(opts);
  return new Parser(new module.ParserSession(), opts);
}

/**
 * Warns about a `Parser` that reached garbage collection without `dispose()`.
 *
 * A safety net, never a substitute (`ts-api-design.md` §9 Q1). Finalizers are
 * not guaranteed to run at all -- not on process exit, not under memory
 * pressure, not ever -- so this cannot free anything on a schedule a program
 * may depend on. What it can do is turn a silent leak into a message during
 * development, which is the only thing it is here for.
 *
 * It holds the *name*, never the `Parser`: a registry entry that referenced
 * its own target would keep the target alive and guarantee the callback never
 * fires.
 */
const leakRegistry =
  typeof FinalizationRegistry === 'undefined'
    ? null
    : new FinalizationRegistry<string>((label) => {
        console.warn(
          `pssparser: ${label} was garbage collected without dispose(). ` +
            'The WASM-side parser was leaked. Call dispose(), or declare the ' +
            'parser with `using`.'
        );
      });

let parserSeq = 0;

const NOT_IMPLEMENTED = (what: string): string =>
  `pssparser: ${what} is not implemented yet. It needs the AST to cross the ` +
  'WASM boundary, which arrives with the gen_wasm serialiser ' +
  '(ts-wasm-impl-plan.md Phase 2/3). parseSources() and markers work today.';

export class Parser {
  #session: ParserSessionHandle | null;
  #label: string;

  #collectDocstrings: boolean;
  #collectComments: boolean;

  /**
   * fileid -> source name for user files.
   *
   * Written as sources are parsed and read when markers are resolved. This is
   * `_filenames` (`parser.py:32`); `#fileMap` below is the snapshot `link()`
   * takes of it.
   */
  #filenames = new Map<number, string>();
  #fileMap = new Map<number, string>();

  /**
   * Markers accumulated across every parse and link on this Parser.
   *
   * Accumulation is Python's behaviour and is preserved deliberately, but see
   * `clearMarkers()`: Python's consumers are one-shot CLIs, and a long-lived
   * Parser re-parsing on every keystroke grows this without bound.
   */
  #markers: Marker[] = [];

  /** @internal Use `createParser()`. */
  constructor(session: ParserSessionHandle, opts: ParserOptions = {}) {
    this.#session = session;
    this.#label = `Parser#${++parserSeq}`;

    this.#collectDocstrings = opts.collectDocstrings ?? false;
    this.#collectComments = opts.collectComments ?? false;
    session.setCollectDocstrings(this.#collectDocstrings);
    session.setCollectComments(this.#collectComments);

    leakRegistry?.register(this, this.#label, this);
  }

  /**
   * Stop reporting further errors for a file after `n`. `0` (the default) is
   * unlimited.
   *
   * A library caller wants every diagnostic; the cap is a terminal-output
   * affordance a CLI opts into. Only error-severity markers count against it,
   * and a file that reaches it gets one extra PSS029 marker announcing the
   * cutoff.
   */
  setMaxErrors(n: number): void {
    this.#require().setMaxErrors(n);
  }

  /**
   * Parse in-memory sources.
   *
   * Throws `ParseException` if any source produces an error-severity marker,
   * after collecting the markers -- the exception carries them and `markers`
   * is updated either way.
   *
   * Stops at the first source that fails, as Python does (`parser.py:138-141`).
   * That is not just imitation: one marker collector serves the whole call, so
   * after a failure `hasErrors()` stays true and later sources could not be
   * reported on independently anyway.
   *
   * Sources that parse cleanly join this Parser's environment and are visible
   * to later `parseSources()` calls; a source that fails does not.
   */
  parseSources(files: SourceFile[]): boolean {
    const session = this.#require();
    session.beginParse();

    for (const file of files) {
      // Record the name *before* parsing. The fileid is assigned by the
      // session as the unit is created, and markers emitted during that parse
      // already carry it -- resolving them needs the name to be in the map
      // already.
      const fileid = session.nextFileid();
      this.#filenames.set(fileid, file.name);

      if (session.parseSource(file.content)) {
        // Collect before reporting. A caught ParseException carries the
        // markers (parser.py:106-109), and `markers` is populated too.
        this.#absorbMarkers(session);
        throw new ParseException(formatMarkers(this.#markers), this.#markers);
      }
    }

    this.#absorbMarkers(session);
    return true;
  }

  /**
   * Markers from every parse and link performed on this Parser, sorted by
   * (file, line, col).
   *
   * A copy: the array a consumer holds must not change under it when the next
   * parse runs.
   */
  get markers(): readonly Marker[] {
    return this.#markers.slice();
  }

  /**
   * Drop the accumulated markers.
   *
   * Not in the Python API, and added for the case Python does not have
   * (`ts-api-design.md` §9 Q5). Python accumulates across calls on one Parser
   * and its consumers are one-shot CLIs, so nothing ever noticed. A language
   * server re-parsing the same buffer on every keystroke would notice: the
   * list grows without bound and every entry is a duplicate of the last pass.
   *
   * Accumulation stays the default, because changing it would change what
   * `link()` reports -- link-time markers are appended to parse-time ones on
   * purpose (`parser.py:180-184`).
   */
  clearMarkers(): void {
    this.#markers = [];
  }

  /** Whether doc comments are collected. Set at construction. */
  get collectDocstrings(): boolean {
    return this.#collectDocstrings;
  }

  /** Whether every comment is collected. Set at construction. */
  get collectComments(): boolean {
    return this.#collectComments;
  }

  /**
   * fileid -> source name for the user-supplied files.
   *
   * Populated by `link()` and valid afterwards -- including after a *failed*
   * link, which is the point (`parser.py:186-217`). Built-in and
   * standard-library units are excluded: they carry fileid -1 and 0 and have
   * no user path.
   */
  fileMap(): ReadonlyMap<number, string> {
    return new Map(this.#fileMap);
  }

  /** Enable ANTLR profiling for subsequent parse operations. */
  enableProfiling(enable = true): void {
    this.#require().setEnableProfiling(enable);
  }

  /**
   * Profiling data from the last parse, or null if profiling was off.
   *
   * Typed as an opaque record in v1. `ParseProfileInfo`'s shape is not
   * obviously stable, and publishing a precise type for it would make a change
   * to a diagnostic aid into a breaking API change
   * (`ts-api-design.md` §9 Q4).
   */
  getProfileInfo(): Readonly<Record<string, unknown>> | null {
    this.#require();
    throw new Error(NOT_IMPLEMENTED('getProfileInfo()'));
  }

  //--------------------------------------------------------------------------
  // Below this line: declared, shaped, and not yet implemented.
  //
  // These need the AST to cross the boundary, which needs the serialiser from
  // `gen_wasm` (impl plan Phase 2). They are present rather than absent so
  // that Phase 3 fills bodies in rather than designing a surface, and so a
  // consumer reading the type sees the whole API rather than half of it.
  //--------------------------------------------------------------------------

  /**
   * Link every unit parsed so far and return the linked root.
   *
   * When implemented, must preserve four behaviours that a re-implementation
   * gets wrong by default -- each is a bug `parser.py` records in a comment:
   *
   *  1. Collect markers *unconditionally*, not only on failure. Collecting
   *     inside the error branch dropped every warning from a successful link,
   *     and the CLI printed "0 errors in 0 files" (`parser.py:174-179`).
   *  2. Re-sort the concatenation. Parse-time and link-time markers are each
   *     internally sorted; two sorted lists concatenated are not sorted
   *     (`parser.py:182-184`).
   *  3. Record the root *before* reporting failure. Ownership of the units has
   *     already moved into the root by then, so a failed link must still leave
   *     `userUnits()` and `fileMap()` usable (`parser.py:186-217`).
   *  4. Drop the builder. It holds borrowed pointers to the units as its
   *     compile-time environment, and ownership has just moved away
   *     (`parser.py:224-231`).
   */
  link(): never {
    this.#require();
    throw new Error(NOT_IMPLEMENTED('link()'));
  }

  /** The linked root; null before `link()`. */
  get root(): null {
    return null;
  }

  /**
   * The `GlobalScope` of each user-supplied file, in parse order.
   *
   * Read from the linked root, which owns the units after `link()`. Built-in
   * and standard-library units are filtered out by fileid. Empty before
   * `link()`.
   */
  userUnits(): never[] {
    this.#require();
    throw new Error(NOT_IMPLEMENTED('userUnits()'));
  }

  /**
   * Release the WASM-side parser.
   *
   * Required, not an optimisation: the WASM heap is not reachable by the
   * JavaScript garbage collector, so nothing else will free it. Idempotent --
   * calling it twice is not an error, because a `finally` that runs after an
   * explicit dispose is ordinary code. Every other method throws afterwards.
   *
   * AST objects already materialised are plain JavaScript and survive this.
   * That is deliberate: a language server can hold the last good AST while
   * disposing the parser that produced it.
   */
  dispose(): void {
    if (this.#session) {
      this.#session.delete();
      this.#session = null;
      leakRegistry?.unregister(this);
    }
  }

  /** Explicit resource management: `using parser = await createParser()`. */
  [Symbol.dispose](): void {
    this.dispose();
  }

  #require(): ParserSessionHandle {
    if (!this.#session) {
      throw new Error(`pssparser: ${this.#label} has been disposed`);
    }
    return this.#session;
  }

  /**
   * Pull the session's markers into `#markers`, resolved and re-sorted.
   *
   * Re-sorting the whole list rather than the new markers is not redundant.
   * Each collection is internally sorted, but concatenating two sorted lists
   * does not produce a sorted list -- the bug `parser.py:182-184` records.
   */
  #absorbMarkers(session: ParserSessionHandle): void {
    const raw = JSON.parse(session.markersJson()) as RawMarker[];
    // Markers from this call replace nothing; they are appended to whatever
    // earlier calls left, because `markers` spans the Parser's lifetime.
    for (const r of raw) {
      this.#markers.push(resolveMarker(r, this.#filenames));
    }
    sortMarkers(this.#markers);
  }
}

