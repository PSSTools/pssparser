/**
 * `Parser.targetOf()`: resolved references shipped from the core.
 *
 * A reference's `target` is a `SymbolRefPath`, index steps from the root, and
 * only the core can interpret one. The core resolves every path when it ships
 * the tree and sends a (path id -> target id) table beside it
 * (`docs/design/rust-binding.md` §1a). These tests pin the cases that shaped
 * that table: identity across units, a built-in template's specialization, and
 * a path through a `with` block, which the path alone cannot resolve.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { ast, createParser, type Parser } from '../src/index.js';

const live: Parser[] = [];

async function parser(): Promise<Parser> {
  const p = await createParser();
  live.push(p);
  return p;
}

afterEach(() => {
  while (live.length) live.pop()!.dispose();
});

const PKG = 'package p {\n    struct S { int a; }\n}\n';
const TOP =
  'import p::*;\n' +
  'component pss_top {\n' +
  '    action A {\n' +
  '        p::S s1;\n' +
  '        S s2;\n' +
  '        list<int> l;\n' +
  '        rand int x;\n' +
  '    }\n' +
  '    action B {\n' +
  '        A a;\n' +
  '        activity { a with { x < 5; }; }\n' +
  '    }\n' +
  '}\n';

/** Every node reachable from `root` through anything but `parent`. */
function reachable(root: object): object[] {
  const out: object[] = [];
  const seen = new Set<object>();
  const walk = (o: unknown): void => {
    if (!o || typeof o !== 'object' || seen.has(o)) return;
    seen.add(o);
    out.push(o);
    for (const [k, v] of Object.entries(o)) {
      if (k === 'parent') continue;
      if (Array.isArray(v)) v.forEach(walk);
      else if (v instanceof Map) v.forEach(walk);
      else walk(v);
    }
  };
  walk(root);
  return out;
}

async function linked(): Promise<{ p: Parser; nodes: object[] }> {
  const p = await parser();
  p.parseSources([
    { name: 'p.pss', content: PKG },
    { name: 'top.pss', content: TOP },
  ]);
  const root = p.link();
  return { p, nodes: reachable(root) };
}

function typeIds(nodes: object[], spelled: string): ast.TypeIdentifier[] {
  return nodes.filter(
    (n): n is ast.TypeIdentifier =>
      n instanceof ast.TypeIdentifier &&
      n.elems.map((e) => e.id?.id).join('::') === spelled
  );
}

describe('targetOf', () => {
  it('is null before link(), and for null', async () => {
    const p = await parser();
    expect(p.targetOf(null)).toBeNull();
    expect(p.targetOf(undefined)).toBeNull();
    expect(p.refTargetStats).toBeNull();
  });

  it('resolves a qualified and an imported name to the same object', async () => {
    const { p, nodes } = await linked();
    const [q] = typeIds(nodes, 'p::S');
    const [u] = typeIds(nodes, 'S');
    expect(q).toBeDefined();
    expect(u).toBeDefined();

    const tq = p.targetOf(q!.target);
    expect(tq).toBeInstanceOf(ast.SymbolTypeScope);
    expect((tq as ast.SymbolTypeScope).name).toBe('S');
    // Identity, not equality: one declaration, one object.
    expect(p.targetOf(u!.target)).toBe(tq);
    // And it leads to the declaration in the other unit.
    const decl = (tq as ast.SymbolTypeScope).target;
    expect(decl).toBeInstanceOf(ast.Struct);
    expect(decl!.location.fileid).toBe(1);
  });

  it('resolves a built-in template use to its specialization', async () => {
    const { p, nodes } = await linked();
    const uses = typeIds(nodes, 'list');
    const spec = uses
      .map((t) => p.targetOf(t.target))
      .find((t) => t instanceof ast.SymbolTypeScope && t.name === 'list<int>');
    expect(spec).toBeDefined();
    // The specialization is a node of the tree: it has the built-in's methods
    // bound to its arguments.
    expect((spec as ast.SymbolTypeScope).children.length).toBeGreaterThan(0);
  });

  it('resolves a reference in a `with` block, which the path alone cannot', async () => {
    const { p, nodes } = await linked();
    const ref = nodes.find(
      (n): n is ast.ExprRefPathContext =>
        n instanceof ast.ExprRefPathContext &&
        n.hier_id?.elems.map((e) => e.id?.id).join('.') === 'x'
    );
    expect(ref).toBeDefined();
    expect(ref!.target!.path.some((e) => e.kind === ast.SymbolRefPathElemKind.ElemKind_Inline)).toBe(
      true
    );
    const t = p.targetOf(ref!.target);
    expect(t).toBeInstanceOf(ast.Field);
    expect((t as ast.Field).name?.id).toBe('x');
  });

  it('reports counts that account for every path', async () => {
    const { p } = await linked();
    const s = p.refTargetStats!;
    expect(s.resolved + s.unresolved).toBe(s.total);
    expect(s.unresolved).toBe(0);
    expect(s.inline_total).toBeGreaterThan(0);
    expect(s.inline_resolved).toBe(s.inline_total);
    // The resolver and the linker's own record never disagree; a template use
    // names the generic type on one side and the specialization on the other.
    expect(s.decl_disagree).toBe(0);
    expect(s.decl_generic).toBeGreaterThan(0);
    expect(s.target_unshipped).toBe(0);
  });
});
