/**
 * `@psstools/pssparser` -- the public API.
 *
 * What this file exports *is* the API. Anything reachable only by a deeper
 * import path is an implementation detail and may change without a major
 * version; `package.json` has a single `"exports"` entry to keep that from
 * being merely a convention.
 */

export {
  Parser,
  ParseException,
  createParser,
  type ParserOptions,
  type ProfileInfo,
  type SourceFile,
} from './Parser.js';

export {
  FILEID_BUILTIN,
  FILEID_STDLIB,
  type Marker,
  type MarkerRelation,
  type MarkerSeverity,
} from './Marker.js';

export { initPssParser, type InitOptions } from './wasm/loader.js';

export { AST_SCHEMA_HASH } from './wasm/schemaHash.js';

export {
  childrenOf,
  findNodeAtPosition,
  getNodeName,
  prettyPrint,
  walkScope,
  type Position,
} from './ast/ASTUtils.js';

/**
 * The generated AST classes, enums and flags.
 *
 * Re-exported as a namespace rather than flattened into this module: there are
 * over 230 class names in it, several of which (`Component`, `Field`, `Action`)
 * are words a consumer is likely to have already.
 *
 * These are what `Parser` hands back. They are plain JavaScript objects, not
 * proxies over WASM memory: an AST is materialised once per parse and survives
 * `dispose()`, which is what lets a language server hold the last good tree
 * while re-parsing. The costs of that choice are stated in
 * `ts-api-design.md` §4 and are worth restating here, because they are
 * observable:
 *
 *   - AST objects are **snapshots**. Re-parsing produces new ones; nothing
 *     mutates in place, so a node held across a parse is stale.
 *   - **Identity is not preserved** across parses. `===` between nodes from
 *     two different parses is always false. Key on `(fileid, location)`.
 */
export * as ast from './ast/generated/index.js';

/**
 * The AST wire-format reader, and the node type it produces.
 *
 * Not how a consumer should be reading an AST: `Parser.link()`, `Parser.root`
 * and `Parser.userUnits()` sit on top of this and are the API. It stays
 * exported because it is the only way to interpret the bytes
 * `ParserSessionHandle.serializeUnit()` hands out -- a consumer that wants one
 * unit without linking, or that is storing the wire format, has no other
 * route. This is the seam underneath the API, not a second one beside it.
 */
export { deserialize, type AstNode } from './ast/generated/deserialize.js';
