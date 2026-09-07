/**
 * WASM instantiation and the schema-hash check (`ts-api-design.md` §7).
 */
import { AST_SCHEMA_HASH } from './schemaHash.js';

/**
 * The subset of the Embind module this package uses.
 *
 * Declared by hand rather than generated: emcc emits no `.d.ts`, and the
 * surface is small enough that a hand-written declaration is the cheaper of
 * the two ways to be wrong. It must stay in step with
 * `EMSCRIPTEN_BINDINGS(pssparser)` in `wasm/bindings.cpp`; there is no
 * compiler that checks that, which is why the binding is deliberately small.
 */
export interface ParserSessionHandle {
  setMaxErrors(n: number): void;
  setCollectDocstrings(c: boolean): void;
  setCollectComments(c: boolean): void;
  setEnableProfiling(e: boolean): void;
  beginParse(): void;
  /** Returns true when the current parse call has produced an error marker. */
  parseSource(content: string): boolean;
  nextFileid(): number;
  markersJson(): string;
  hasErrors(): boolean;
  maxErrorsExceeded(): boolean;
  /** Units accepted so far, standard library included. */
  unitCount(): number;
  /**
   * Serialise unit `idx` and return a view over the WASM heap.
   *
   * A *view*, not a copy: valid only until the next `serializeUnit()` on this
   * session, and detached outright if the heap grows in between. Copy it before
   * doing anything else.
   */
  serializeUnit(idx: number): Uint8Array;
  /**
   * Link every unit parsed so far.
   *
   * Returns true when the link produced an error-severity marker. As with
   * `parseSource`, it reports the fact and leaves reporting to `Parser`, which
   * has to collect markers before it throws.
   */
  link(): boolean;
  /** Whether `link()` has run and left a root. */
  hasRoot(): boolean;
  /** The linked root, serialised. Same heap-view contract as
   *  `serializeUnit()`. Throws before `link()`. */
  serializeRoot(): Uint8Array;
  /** Profiling data from the last parse as JSON, or `''` when there is none
   *  -- profiling off, no parse yet, or `link()` has dropped the builder. */
  profileInfoJson(): string;
  /** Embind's destructor. Frees the C++ object; the handle is dead after. */
  delete(): void;
}

export interface PssParserModule {
  schemaHash(): string;
  ParserSession: { new (): ParserSessionHandle };
}

export interface InitOptions {
  /**
   * Where to fetch `pssparser.wasm` from.
   *
   * Needed when a bundler has relocated the binary away from the glue module,
   * which is the common case in a browser build and never the case under Node.
   */
  wasmUrl?: string | URL;
}

/**
 * The in-flight or completed instantiation.
 *
 * Cached as the *promise*, not the module, so concurrent callers share one
 * instantiation rather than racing to start several -- each one costs the full
 * download and compile.
 */
let modulePromise: Promise<PssParserModule> | null = null;

/**
 * Instantiate the WASM module, once per process.
 *
 * `createParser()` calls this implicitly. Call it directly to control *when*
 * the cost is paid -- an extension activating eagerly, a page preloading --
 * or to supply a `wasmUrl`.
 *
 * Options are honoured only by the call that actually instantiates. A second
 * call with different options returns the already-loaded module rather than
 * reloading it, because there is one WASM instance per process and silently
 * replacing it would invalidate every live `Parser`.
 */
export function initPssParser(opts: InitOptions = {}): Promise<PssParserModule> {
  if (!modulePromise) {
    modulePromise = instantiate(opts).catch((e) => {
      // Do not cache a rejection: a failed load is usually a missing or
      // misplaced .wasm, and a caller that fixes the path and retries should
      // get a real attempt rather than the first error replayed forever.
      modulePromise = null;
      throw e;
    });
  }
  return modulePromise;
}

async function instantiate(opts: InitOptions): Promise<PssParserModule> {
  // The glue is generated (emcc -sMODULARIZE=1 -sEXPORT_ES6=1) and has no
  // type declaration, so this import is the one untyped edge in the package.
  // @ts-expect-error -- pssparser.js is a build product with no .d.ts
  const glue = await import('./pssparser.js');
  const createModule = glue.default as (cfg?: Record<string, unknown>) => Promise<PssParserModule>;

  const config: Record<string, unknown> = {};
  if (opts.wasmUrl !== undefined) {
    const url = String(opts.wasmUrl);
    config.locateFile = (path: string) => (path.endsWith('.wasm') ? url : path);
  }

  const module = await createModule(config);
  checkSchemaHash(module);
  return module;
}

/**
 * Fail loudly when the `.wasm` and the generated TypeScript came from
 * different `ast/*.yaml`.
 *
 * This is the highest-value defensive check in the design. Without it the
 * symptom of a skewed build is a field read from the wrong slot: a string that
 * arrives as an integer, a child list off by one, a node deserialised into the
 * wrong class. Nothing about any of those points at the build, and the time
 * spent not suspecting it is measured in days. With it, the failure is one
 * sentence at startup naming both hashes.
 *
 * Fatal, never a warning. There is no partial correctness to salvage: if the
 * schemas differ at all, no field's position can be trusted.
 */
function checkSchemaHash(module: PssParserModule): void {
  const wasmHash = module.schemaHash();
  if (wasmHash !== AST_SCHEMA_HASH) {
    throw new Error(
      'pssparser: AST schema mismatch between the WASM core and the ' +
        'generated TypeScript classes.\n' +
        `  wasm/pssparser.wasm : ${wasmHash}\n` +
        `  src/ast/generated   : ${AST_SCHEMA_HASH}\n` +
        'The two were built from different ast/*.yaml. Re-run `npm run generate`.'
    );
  }
}

/**
 * Drop the cached module.
 *
 * For tests that need a fresh instantiation. Not part of the public API: live
 * `Parser` objects hold sessions in the old module's heap and keep working,
 * which is correct but is not a property worth promising.
 */
export function resetForTesting(): void {
  modulePromise = null;
}
