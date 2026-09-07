/**
 * `ASTUtils` against hand-built trees.
 *
 * Hand-built rather than parsed, because the AST does not cross the WASM
 * boundary yet (impl plan Phase 2/3). That is a limitation of *when* this test
 * was written, but it is also the right shape for these particular functions:
 * the property under test is "does the traversal follow both container
 * classes", and a parsed tree makes that hard to see and easy to get
 * accidentally right.
 *
 * When Phase 3 lands, these stay and a parsed-tree test joins them.
 */
import { describe, expect, it } from 'vitest';
import {
  findNodeAtPosition,
  getNodeName,
  prettyPrint,
  walkScope,
  ast,
} from '../src/index.js';

/** Build an `ExprId` usable as a node name. */
const id = (s: string) => new ast.ExprId(s);

function at<T extends ast.ScopeChild>(node: T, lineno: number, linepos: number): T {
  node.location = { fileid: 1, lineno, linepos, extent: 0 };
  return node;
}

/**
 * A tree with an activity in it.
 *
 * `ActivityDecl` extends `SymbolScope` extends `SymbolChildrenScope`, which
 * holds children *without* extending `Scope`. Every test below exists because
 * a traversal that checks only `instanceof Scope` skips this node's children
 * while looking entirely correct -- which is what happened when these
 * functions were emitted from the schema rather than written
 * (`pyastbuilder-typescript-plan.md` §7.3, and the header of `ASTUtils.ts`).
 */
function buildTree() {
  const inActivity = at(new ast.Action(id('InnerAction')), 5, 8);

  const activity = at(new ast.ActivityDecl(), 4, 4);
  activity.children.push(inActivity);

  const action = at(new ast.Action(id('A')), 3, 4);
  action.children.push(activity);

  const field = at(new ast.Field(), 2, 4);
  field.name = id('f');

  const component = at(new ast.Component(id('pss_top')), 1, 0);
  component.children.push(field, action);

  const root = new ast.GlobalScope(1);
  root.children.push(component);

  return { root, component, field, action, activity, inActivity };
}

describe('walkScope', () => {
  it('visits every node, including through a SymbolChildrenScope', () => {
    const t = buildTree();
    const seen = [...walkScope(t.root)];

    expect(seen).toContain(t.component);
    expect(seen).toContain(t.field);
    expect(seen).toContain(t.action);
    expect(seen).toContain(t.activity);
    // The one that a Scope-only traversal loses.
    expect(seen, 'activity body not traversed').toContain(t.inActivity);
    expect(seen).toHaveLength(5);
  });

  it('yields each node exactly once', () => {
    // Guards the shape of the recursion. An implementation that both yields a
    // subtree and then recurses into it produces every deep node repeatedly,
    // which no assertion about membership would catch.
    const seen = [...walkScope(buildTree().root)];
    expect(new Set(seen).size).toBe(seen.length);
  });

  it('yields a container before its contents', () => {
    const t = buildTree();
    const seen = [...walkScope(t.root)];
    expect(seen.indexOf(t.action)).toBeLessThan(seen.indexOf(t.activity));
    expect(seen.indexOf(t.activity)).toBeLessThan(seen.indexOf(t.inActivity));
  });

  it('yields nothing for an empty scope', () => {
    expect([...walkScope(new ast.GlobalScope(1))]).toEqual([]);
  });
});

describe('getNodeName', () => {
  it('reads a NamedScope name', () => {
    expect(getNodeName(buildTree().component)).toBe('pss_top');
  });

  it('reads a NamedScopeChild name', () => {
    // Field is the other branch: NamedScopeChild, not NamedScope. Neither
    // class is an ancestor of the other, so one test does not cover both.
    expect(getNodeName(buildTree().field)).toBe('f');
  });

  it('returns null for an unnamed node', () => {
    expect(getNodeName(new ast.ActivityDecl())).toBeNull();
  });

  it('returns null when a named node has no name set', () => {
    expect(getNodeName(new ast.Action())).toBeNull();
  });
});

describe('findNodeAtPosition', () => {
  it('finds the node at its own start', () => {
    const t = buildTree();
    // Position is 0-based; Location.lineno is 1-based. The component starts at
    // lineno 1, which is line 0 here.
    expect(findNodeAtPosition(t.root, { line: 0, character: 0 })).toBe(t.component);
  });

  it('finds the last node starting at or before the position', () => {
    const t = buildTree();
    expect(findNodeAtPosition(t.root, { line: 1, character: 10 })).toBe(t.field);
    expect(findNodeAtPosition(t.root, { line: 2, character: 10 })).toBe(t.action);
  });

  it('descends into an activity body', () => {
    const t = buildTree();
    expect(findNodeAtPosition(t.root, { line: 4, character: 8 })).toBe(t.inActivity);
  });

  it('returns null before the first node', () => {
    const t = buildTree();
    // Everything in the tree starts at lineno >= 1, i.e. line >= 0 character
    // >= 0; nothing precedes line 0 character 0 except a node with no
    // location, and there is none here.
    const root = new ast.GlobalScope(1);
    root.children.push(at(new ast.Component(id('c')), 10, 0));
    expect(findNodeAtPosition(root, { line: 0, character: 0 })).toBeNull();
  });

  it('ignores synthesised nodes but still descends through them', () => {
    // A node with lineno -1 is a builtin or a desugaring: it has no place in a
    // position lookup, but its children may.
    const child = at(new ast.Action(id('real')), 2, 0);
    const synthetic = new ast.ActivityDecl(); // location defaults to lineno -1
    synthetic.children.push(child);
    const root = new ast.GlobalScope(1);
    root.children.push(synthetic);

    expect(synthetic.location.lineno).toBeLessThan(0);
    expect(findNodeAtPosition(root, { line: 5, character: 0 })).toBe(child);
  });
});

describe('prettyPrint', () => {
  it('indents by depth and shows names', () => {
    const t = buildTree();
    const out = prettyPrint(t.component);
    expect(out).toContain('Component "pss_top"');
    expect(out).toContain('  Field "f"');
    expect(out).toContain('  Action "A"');
  });

  it('shows activity bodies', () => {
    // The original walked only Scope children and silently omitted these.
    const out = prettyPrint(buildTree().component);
    expect(out).toContain('ActivityDecl');
    expect(out).toContain('Action "InnerAction"');
  });

  it('prints each node once', () => {
    const lines = prettyPrint(buildTree().component).trimEnd().split('\n');
    expect(lines).toHaveLength(5);
  });
});
