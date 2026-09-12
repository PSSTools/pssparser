/**
 * Two linker resolution bugs, pinned.
 *
 * Both were found by moving `vscode-pss-support` onto this parser, and both
 * are the kind that a test suite built around valid input does not reach: one
 * made a legal construct silently do nothing, the other crashed the linker on
 * input a person types by accident. An editor runs `link()` on every keystroke
 * over half-written source, so neither stayed hidden for long there.
 *
 * `link.test.ts` covers the API around the link. This file covers what the
 * link resolves.
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

/** Two sibling structs in a package, so an import can name one and not the other. */
const PKG = 'package p {\n    struct S { int a; }\n    struct T { int b; }\n}\n';

function errors(p: Parser): string[] {
  return p.markers.filter((m) => m.severity === 'error').map((m) => m.message);
}

describe('single-symbol import', () => {
  it('resolves the symbol it names', async () => {
    // `searchImport` used to skip the wildcard check entirely and look the
    // name up *inside* the scope the import path resolved to -- that is, it
    // searched for `S` in `S`, found nothing, and returned. Every
    // `import p::S;` in a workspace resolved to nothing at all, with no
    // marker to say so: the reference simply failed elsewhere, as though the
    // import had not been written.
    const p = await parser();
    p.parseSources([
      { name: 'p.pss', content: PKG },
      {
        name: 'top.pss',
        content: 'import p::S;\ncomponent pss_top {\n    action A { S s; }\n}\n',
      },
    ]);
    expect(() => p.link()).not.toThrow();
    expect(errors(p)).toEqual([]);
  });

  it('does not bring in the rest of the package', async () => {
    // The other half of the same fix, and the reason it is not simply "treat
    // it as a wildcard": `import p::S;` names S. `T` is still out of scope,
    // and a fix that resolved the import by opening its parent package would
    // pass the test above while quietly making every single-symbol import
    // mean `p::*`.
    const p = await parser();
    p.parseSources([
      { name: 'p.pss', content: PKG },
      {
        name: 'top.pss',
        content: 'import p::S;\ncomponent pss_top {\n    action A { T t; }\n}\n',
      },
    ]);
    expect(() => p.link()).toThrow(ParseException);
    expect(errors(p).join('\n')).toMatch(/T/);
  });

  it('leaves a wildcard import resolving the whole package', async () => {
    // The regression guard for the fix above: the wildcard path is the one
    // that already worked, and the new branch returns before reaching it.
    const p = await parser();
    p.parseSources([
      { name: 'p.pss', content: PKG },
      {
        name: 'top.pss',
        content: 'import p::*;\ncomponent pss_top {\n    action A { S s; T t; }\n}\n',
      },
    ]);
    expect(() => p.link()).not.toThrow();
    expect(errors(p)).toEqual([]);
  });
});

describe('extending something that cannot be extended', () => {
  it('reports `extend enum` of a non-enum instead of crashing', async () => {
    // `visitExtendEnum` dereferenced the result of a `dynamic_cast` to
    // `ISymbolEnumScope` without checking it. Against a struct the cast
    // yields null and the read went through it -- which in WebAssembly is
    // `RuntimeError: memory access out of bounds`, taking the whole parser
    // session down rather than producing a diagnostic. A language server
    // links on every edit, so this was reachable by typing `enum` where
    // `struct` was meant.
    const p = await parser();
    p.parseSources([
      { name: 'top.pss', content: 'struct s { int a; }\nextend enum s { A }\n' },
    ]);
    expect(() => p.link()).toThrow(ParseException);
    expect(errors(p).join('\n')).toMatch(/not an enum/);
  });

  // `visitExtendType` grew the same null check as `visitExtendEnum`, for the
  // same `dynamic_cast` -- there to `ISymbolTypeScope` rather than to
  // `ISymbolEnumScope`. It is NOT asserted directly here, because no source
  // reaching it has been found: a qualified target like `p::W` is diverted by
  // the template-instance check above it, and an unqualified one that names a
  // non-type fails to resolve and takes the `!target_p` branch first. It is a
  // defensive guard on a cast that can return null, and it stays.
  //
  // What is asserted is the property that actually matters to a caller, and
  // the one the enum crash violated: a bad `extend` ends the link, not the
  // session. `link()` may throw ParseException -- that is a report -- but the
  // parser has to still be usable afterwards.
  it.each([
    ['a const', 'package p { const int W = 8; }\nextend action p::W { int x; }\n'],
    ['a field', 'component c { int f; }\nextend action c::f { int x; }\n'],
    ['an enum, as an action', 'enum e { A }\nextend action e { int x; }\n'],
    ['a name that does not exist', 'extend action nope_t { int x; }\n'],
    ['a struct, as an enum', 'struct s { int a; }\nextend enum s { A }\n'],
  ])('survives extending %s', async (_label, content) => {
    const p = await parser();
    p.parseSources([{ name: 'top.pss', content }]);
    try {
      p.link();
    } catch (e) {
      expect(e).toBeInstanceOf(ParseException);
    }
    // The session is intact: a memory fault would have taken the whole
    // WebAssembly instance with it and this would throw RuntimeError.
    expect(() => p.fileMap()).not.toThrow();
  });
});
