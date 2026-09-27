# Other bindings: C++ and TypeScript

The Python package wraps a C++ core. You can reach the same core from C++ and,
through WebAssembly, from TypeScript. This file only points to them. Build
with Python unless you have a reason not to.

## C++

The wheel ships the native libraries (`libpssparser`, `libast`) and the C++
headers. The package tells a build system where they are:

```python
import os
import pssparser

print("libs:   ", pssparser.get_libs())       # ['pssparser']
print("libdirs:", pssparser.get_libdirs())    # the package directory
for d in pssparser.get_incdirs():
    print("incdir: ", d)
    assert os.path.isdir(d), d
```

In an installed wheel `get_incdirs()` is `<package>/share/include`, holding
`pssp/` for the parser and `antlr4-runtime/` for ANTLR.

The entry point is `extern "C" pssp::IFactory *pssparser_getFactory()`,
declared in `pssp/FactoryExt.h`. From the factory, `mkAstBuilder()` parses,
`mkAstLinker()` links, and `mkMarkerCollector()` collects diagnostics. This
mirrors the Python `Parser`. The builder also has settings that Python does not
expose, such as `setDocCommentStrictMarkers(true)`, which accepts only
`///`, `//!`, `/**` and `/*!` as doc comments.

## TypeScript / WebAssembly

`@psstools/pssparser` on npm is the same C++ core compiled to WebAssembly,
with a TypeScript API that mirrors the Python one. It runs under Node and in a
browser, with no native build step.

```typescript
import { createParser, ParseException } from '@psstools/pssparser';

using parser = await createParser();
try {
  parser.parseSources([{ name: 'top.pss', content: src }]);
  parser.link();
} catch (e) {
  if (!(e instanceof ParseException)) throw e;
  for (const m of e.markers) {
    console.error(`${m.file}:${m.line}:${m.col}: ${m.severity}: ${m.message}`);
  }
}
```

The differences from Python:

| | Python | TypeScript |
|---|---|---|
| construct | `Parser()` | `await createParser()` |
| sources | `parses([(name, text)])` | `parseSources([{ name, content }])` |
| cleanup | garbage collection | `using`, or `parser.dispose()` in a `finally` (required: the WASM heap is not garbage-collected) |
| units / files | `user_units()`, `file_map` | `userUnits()`, `fileMap()` |
| AST | live wrappers over C++ nodes | plain JavaScript objects built per parse |

The package README describes the full API.
