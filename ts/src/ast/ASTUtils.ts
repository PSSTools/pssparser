/**
 * Traversal and naming helpers for the generated AST.
 *
 * Moved here from `vscode-pss-support/server/src/core/ast/ASTUtils.ts`, which
 * had 90 call sites across the language server. The split was by whether a
 * function is about the *schema* or about *PSS presentation*: `getNodeName`,
 * `walkScope`, `findNodeAtPosition` and `prettyPrint` are schema questions and
 * belong to the package that owns the schema. `getNodeSignature` stayed behind
 * -- it hardcodes PSS spellings (`action`, `component`, `package a::b`), which
 * is language-server presentation, not parsing.
 *
 * **Hand-written, and deliberately not generated.**
 * `pyastbuilder-typescript-plan.md` §7.3 records an attempt to emit these from
 * the schema as `support.ts`, and why it was reverted. `walkScope` recurses on
 * `child instanceof Scope` *and* on `child instanceof SymbolChildrenScope`,
 * which holds children without being a `Scope`. A schema-generic emitter
 * cannot infer that second branch: "which classes are containers" is not
 * something `ast/*.yaml` expresses. The emitted version typechecked, passed
 * every test, and silently skipped every activity body across 27 call sites.
 *
 * That reasoning bars *emitting* them. It does not bar shipping them as
 * ordinary source, which is what this file is.
 */
import { Scope, ScopeChild, NamedScope, NamedScopeChild, SymbolChildrenScope } from './generated/index.js';

/**
 * A zero-based source position.
 *
 * Declared locally rather than imported from an LSP package. The types are
 * structurally identical to `vscode-languageserver`'s `Position` and to the
 * language server's own `SourcePosition`, so a consumer can pass either
 * without a conversion -- and this package acquires no dependency on an editor
 * protocol it has nothing to do with.
 *
 * Zero-based on both axes, which is the LSP convention and *not* the
 * convention the AST uses: `Location.lineno` is 1-based. The conversion is in
 * `findNodeAtPosition` and is the only place it belongs.
 */
export interface Position {
  /** 0-based. */
  line: number;
  /** 0-based. */
  character: number;
}

const NO_CHILDREN: readonly ScopeChild[] = Object.freeze([]);

/**
 * The immediate children of *node*, whichever container form it takes.
 *
 * **This function is the whole of the traversal knowledge in this file**, and
 * it is why the file is hand-written. There are two unrelated container
 * classes:
 *
 *   `Scope`                extends ScopeChild
 *   `SymbolChildrenScope`  extends SymbolChild extends ScopeChild
 *
 * Neither is an ancestor of the other, and `ActivityDecl` -- via `SymbolScope`
 * -- is on the second branch. A traversal that tests only `instanceof Scope`
 * typechecks, runs, and silently returns nothing for every activity body.
 *
 * The original had this test duplicated in each of `walkScope`,
 * `walkSymbolScope` and `findNodeAtPosition`, which is what let `prettyPrint`
 * drift and lose the second branch. One definition, three callers.
 */
function childrenOf(node: ScopeChild): readonly ScopeChild[] {
  if (node instanceof Scope || node instanceof SymbolChildrenScope) {
    return node.children;
  }
  return NO_CHILDREN;
}

/**
 * Depth-first iterator over every node beneath *scope*.
 *
 * Yields each node before descending into it (pre-order), so a consumer that
 * stops early has seen the containers of everything it has not seen.
 */
export function* walkScope(scope: Scope): Generator<ScopeChild> {
  for (const child of scope.children) {
    yield child;
    yield* walkNode(child);
  }
}

function* walkNode(node: ScopeChild): Generator<ScopeChild> {
  for (const child of childrenOf(node)) {
    yield child;
    yield* walkNode(child);
  }
}

/**
 * The deepest node at or before *pos*.
 *
 * "At or before" rather than "containing": nodes carry a start location but
 * not reliably an end, so containment cannot be tested. The traversal is
 * depth-first in source order and keeps the last node that starts at or before
 * the position, which is the node a cursor is inside for every case where the
 * start locations are ordered.
 *
 * Returns null when *pos* precedes every node in the scope.
 */
export function findNodeAtPosition(root: Scope, pos: Position): ScopeChild | null {
  let best: ScopeChild | null = null;

  const visit = (node: ScopeChild): void => {
    const loc = node.location;
    // A node with no location is synthesised -- a builtin, or a desugaring.
    // It has no place in a position lookup, but its children may.
    if (loc.lineno >= 0) {
      const startLine = loc.lineno - 1; // Location is 1-based; Position is 0-based.
      const startChar = loc.linepos;
      if (pos.line > startLine || (pos.line === startLine && pos.character >= startChar)) {
        best = node;
      }
    }
    for (const child of childrenOf(node)) {
      visit(child);
    }
  };

  for (const child of root.children) {
    visit(child);
  }

  return best;
}

/**
 * The declared name of *node*, or null if it has none.
 *
 * Both named forms are checked because the schema has two: `NamedScope` for
 * containers (an action, a component) and `NamedScopeChild` for leaves (a
 * field). Neither is a subclass of the other.
 */
export function getNodeName(node: ScopeChild): string | null {
  if (node instanceof NamedScope || node instanceof NamedScopeChild) {
    return node.name?.id ?? null;
  }
  return null;
}

/**
 * Indented dump of a subtree, for debugging.
 *
 * Goes through `childrenOf`, so it shows activity bodies. The original walked
 * only `Scope` children and did not -- the drift `childrenOf` exists to
 * prevent.
 */
export function prettyPrint(node: ScopeChild, indent = 0): string {
  const name = getNodeName(node);
  let out = '  '.repeat(indent) + node.constructor.name + (name ? ` "${name}"` : '') + '\n';
  for (const child of childrenOf(node)) {
    out += prettyPrint(child, indent + 1);
  }
  return out;
}
