/**
 * The AST wire format (`ts-wasm-impl-plan.md` Phase 2).
 *
 * Two kinds of test here, and they cover different things:
 *
 *   - **Round-trip and framing.** Cheap, and tighter than it looks: every node
 *     is decoded from one stream with no per-node offset, so a single field
 *     width that disagrees between the two halves desynchronises everything
 *     after it and surfaces as an out-of-range tag, an out-of-range node id, or
 *     a failed trailer check. What it cannot catch is a defect that is
 *     *symmetric*, because both halves come from one generator: two same-width
 *     fields swapped in the emitted order are written and read consistently.
 *
 *   - **Parity against the native parser** (`ast-parity.test.ts`). That is the
 *     half with independent ground truth, and the only one that can see a
 *     symmetric defect.
 *
 * Neither reaches the whole tree. Phase 3 owns the full gate.
 */
import { afterEach, describe, expect, it } from 'vitest';
import {
  ast,
  childrenOf,
  deserialize,
  getNodeName,
  initPssParser,
  walkScope,
} from '../src/index.js';
import type { ParserSessionHandle } from '../src/wasm/loader.js';

const live: ParserSessionHandle[] = [];

async function session(): Promise<ParserSessionHandle> {
  const m = await initPssParser();
  const s = new m.ParserSession();
  live.push(s);
  return s;
}

afterEach(() => {
  while (live.length) live.pop()!.delete();
});

/** Parse one source and return a *copy* of the serialised user unit. */
async function serializeOne(content: string): Promise<Uint8Array> {
  const s = await session();
  s.beginParse();
  s.parseSource(content);
  if (s.hasErrors()) {
    throw new Error(`fixture source did not parse: ${s.markersJson()}`);
  }
  // The copy is mandatory, not defensive: serializeUnit returns a view over the
  // WASM heap, and the next call into WASM can both overwrite the buffer and
  // detach the view outright by growing the heap.
  return new Uint8Array(s.serializeUnit(1));
}

const MINIMAL = 'component pss_top {\n    action A { }\n}\n';

describe('serializeUnit / deserialize', () => {
  it('round-trips a minimal unit into the generated classes', async () => {
    const root = deserialize(await serializeOne(MINIMAL));

    expect(root).toBeInstanceOf(ast.GlobalScope);
    const scope = root as ast.GlobalScope;

    const comp = scope.children[0];
    expect(comp).toBeInstanceOf(ast.Component);
    expect(getNodeName(comp!)).toBe('pss_top');

    const action = scope.children[0]!.children.find((c) => c instanceof ast.Action);
    expect(action).toBeDefined();
    expect(getNodeName(action!)).toBe('A');
  });

  it('reconstructs parent back-references as object identity', async () => {
    // `parent` is a raw pointer in the schema and is written as a node id, so
    // this is the test that ids resolve to the *same* object rather than to a
    // structurally equal copy. If they did not, a consumer walking upwards
    // would build an infinite chain of distinct nodes.
    const scope = deserialize(await serializeOne(MINIMAL)) as ast.GlobalScope;

    const comp = scope.children[0]!;
    expect(comp.parent).toBe(scope);

    // Only nodes that came from source. The builder synthesises members that
    // every component gets -- `set_executor`, the `comp` back-reference -- and
    // leaves their `parent` null; checked against the native bindings, which do
    // the same. So a null here is faithful, and asserting otherwise would be
    // asserting against the parser rather than against the wire format.
    const fromSource = childrenOf(comp).filter((c) => c.location.fileid >= 0);
    expect(fromSource.length).toBeGreaterThan(0);
    for (const child of fromSource) {
      expect(child.parent).toBe(comp);
    }
  });

  it('carries locations through unchanged', async () => {
    const scope = deserialize(await serializeOne(MINIMAL)) as ast.GlobalScope;
    const comp = scope.children[0]!;

    // `component` is on line 1 of the source; Location.lineno is 1-based and
    // linepos is 0-based, which is the convention Marker.ts documents.
    expect(comp.location.fileid).toBe(1);
    expect(comp.location.lineno).toBe(1);
    expect(comp.location.extent).toBeGreaterThan(0);

    // Three Location-typed fields sit adjacent in the buffer. Asserting that
    // they are distinct is what would catch two of them being written in the
    // wrong order -- the one same-width transposition reachable from here.
    expect(comp.endLocation.lineno).toBeGreaterThan(comp.location.lineno);
    expect(comp.docLocation.lineno).toBe(-1);
  });

  it('is deterministic: the same source serialises to the same bytes', async () => {
    // Not a nicety. Four fields in the schema are std::unordered_map, whose
    // iteration order is an implementation detail; the writer sorts them by key
    // for exactly this reason. Without that, the emitted Map's insertion order
    // would vary between runs of an identical build.
    const a = await serializeOne(MINIMAL);
    const b = await serializeOne(MINIMAL);
    expect(Array.from(a)).toEqual(Array.from(b));
  });

  it('round-trips the standard library', async () => {
    // Unit 0 is the largest tree available without a corpus, and the only one
    // here that exercises the maps and the deeper nesting. It also runs through
    // a code path no user source does -- loadStandardLibrary, not parseSource.
    const s = await session();
    s.beginParse();
    s.parseSource(MINIMAL);
    expect(s.unitCount()).toBe(2);

    const stdlib = deserialize(new Uint8Array(s.serializeUnit(0)));
    expect(stdlib).toBeInstanceOf(ast.GlobalScope);

    const nodes = [...walkScope(stdlib as ast.GlobalScope)];
    expect(nodes.length).toBeGreaterThan(50);
    // Every node reached through the spine belongs to unit 0 or is synthetic
    // (fileid -1, the builtins). A node claiming a different file would mean a
    // reference had resolved across units.
    for (const n of nodes) {
      expect([0, -1]).toContain(n.location.fileid);
    }
  });

  it('rejects an out-of-range unit index', async () => {
    const s = await session();
    s.beginParse();
    s.parseSource(MINIMAL);
    expect(() => s.serializeUnit(2)).toThrow();
    expect(() => s.serializeUnit(-1)).toThrow();
  });
});

describe('deserialize framing', () => {
  it('rejects a buffer that is too short', () => {
    expect(() => deserialize(new Uint8Array(4))).toThrow(/too short/);
  });

  it('rejects bad magic', () => {
    const bytes = new Uint8Array(16);
    new DataView(bytes.buffer).setUint32(0, 0xdeadbeef, true);
    expect(() => deserialize(bytes)).toThrow(/bad magic/);
  });

  it('returns null for an empty tree rather than throwing', async () => {
    // A zero-node buffer is well-formed: it is what a null root serialises to.
    const real = await serializeOne(MINIMAL);
    const empty = new Uint8Array(8);
    empty.set(real.subarray(0, 4)); // borrow the magic rather than restating it
    expect(deserialize(empty)).toBeNull();
  });

  it('rejects a truncated buffer', async () => {
    const bytes = await serializeOne(MINIMAL);
    // Drop the trailer and a little of the last body. The node count in the
    // header still says how many nodes to expect, so the reader runs off the
    // end or fails the trailer check -- either is a throw, and which one it is
    // depends on where the cut lands.
    expect(() => deserialize(bytes.subarray(0, bytes.length - 6))).toThrow();
  });

  it('rejects trailing bytes after a valid tree', async () => {
    const bytes = await serializeOne(MINIMAL);
    const padded = new Uint8Array(bytes.length + 4);
    padded.set(bytes);
    // The trailer is now four bytes early; the reader reads it where it expects
    // it, so this is caught by the length check rather than the magic check.
    expect(() => deserialize(padded)).toThrow(/trailing bytes/);
  });

  it('rejects an unknown class tag', async () => {
    const bytes = await serializeOne(MINIMAL);
    const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
    view.setUint16(8, 0xffff, true); // first tag in the tag table
    expect(() => deserialize(bytes)).toThrow(/unknown class tag/);
  });
});
