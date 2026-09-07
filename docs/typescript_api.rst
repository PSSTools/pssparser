TypeScript API
==============

``@psstools/pssparser`` is the pssparser C++ core compiled to WebAssembly,
with a TypeScript API. It runs under Node and in a browser, with no native
build step for consumers and no filesystem dependency.

The API is a transliteration of the Python :class:`~pssparser.parser.Parser`
(see :doc:`quickstart`). Method names are camelCase, return types and error
behaviour match, and the marker shape is the same. Where the two differ, the
runtime forced it:

.. list-table::
   :header-rows: 1
   :widths: 20 30 30 40

   * -
     - Python
     - TypeScript
     - Why
   * - Construction
     - ``Parser()``
     - ``await createParser()``
     - WebAssembly instantiation is asynchronous
   * - Cleanup
     - garbage collection
     - ``parser.dispose()`` / ``using``
     - the WASM heap is not reachable by the JavaScript collector
   * - AST access
     - live Cython proxies
     - JavaScript objects materialised per parse
     - boundary cost; see `The AST boundary`_

.. note::

   **Implementation status.** ``parseSources()``, ``markers`` and the
   ``ASTUtils`` helpers are implemented and tested. The AST serialiser is in
   place and verified against the native parser (`The AST boundary`_), but is
   not yet wired to the ``Parser`` methods that would expose it: ``link()``,
   ``root``, ``userUnits()`` and ``getProfileInfo()`` still throw
   ``not implemented``. The shape is settled; only the bodies are outstanding.


Getting started
---------------

Install
^^^^^^^

The package is not yet published to npm. Build it from a checkout:

.. code-block:: bash

   ivpm update -d default-dev
   ivpm update -d wasm-build      # the Emscripten toolchain; see Building below

   cd ts
   npm install
   npm run generate               # AST classes + the .wasm
   npm test

Once published, consumers will need only:

.. code-block:: bash

   npm install @psstools/pssparser

The published package carries the ``.wasm`` binary and has no runtime
dependencies. Node 18 or later.

A first parse
^^^^^^^^^^^^^

.. code-block:: typescript

   import { createParser, ParseException } from '@psstools/pssparser';

   const parser = await createParser();
   try {
     parser.parseSources([
       { name: 'top.pss', content: 'component pss_top { action A { } }' },
     ]);
     console.log('parsed cleanly');
   } catch (e) {
     if (!(e instanceof ParseException)) throw e;
     for (const m of e.markers) {
       console.error(`${m.file}:${m.line}:${m.col}: ${m.severity}: ${m.message}`);
     }
   } finally {
     parser.dispose();
   }

The ``finally`` is the one piece of ceremony the Python API does not have. With
TC39 explicit resource management it collapses to:

.. code-block:: typescript

   using parser = await createParser();
   parser.parseSources([{ name: 'top.pss', content: src }]);

``Symbol.dispose`` is on the class from day one, so ``using`` works wherever the
runtime supports it.


Parser
------

``createParser(opts?)``
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

   function createParser(opts?: ParserOptions): Promise<Parser>;

   interface ParserOptions {
     /** Collect doc comments, reachable as getDocstring() on any ScopeChild. */
     collectDocstrings?: boolean;
     /** Collect every comment, on statements as well as declarations.
      *  Implies collectDocstrings. */
     collectComments?: boolean;
     /** Where to fetch pssparser.wasm from; see Loading below. */
     wasmUrl?: string | URL;
   }

Both collection flags default off: collection costs time and memory that a
consumer which never reads a comment should not pay.

The first call instantiates the WebAssembly module and caches it. Later calls
reuse it, so a ``Parser`` is cheap after the first.

``parseSources(files)``
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

   parseSources(files: SourceFile[]): boolean;

   interface SourceFile {
     name: string;      // reported in markers; need not be a real path
     content: string;
   }

Parses in-memory sources. Throws :ref:`ts-parse-exception` if any source
produces an error-severity marker, having collected the markers first — so the
exception carries them and ``parser.markers`` is populated either way.

Parsing **stops at the first source that fails**, as the Python API does. One
marker collector serves the whole call, so after a failure later sources could
not be reported on independently anyway.

Sources that parse cleanly join the parser's environment and are visible to
later ``parseSources()`` calls. A source that fails does not.

.. admonition:: There is no ``parse(paths)``

   The Python ``Parser.parse`` opens paths itself. The TypeScript API
   deliberately omits it:

   * it is the only method that would need a filesystem, and omitting it lets
     the WebAssembly build use ``-sFILESYSTEM=0``;
   * that is what makes the package work unchanged in a browser;
   * a language server already has content in hand — editor buffers are
     unsaved text with no path — so it would use ``parseSources`` regardless.

   Under Node, path semantics are four lines:

   .. code-block:: typescript

      import { readFile } from 'node:fs/promises';

      const files = await Promise.all(
        paths.map(async (p) => ({ name: p, content: await readFile(p, 'utf8') }))
      );
      parser.parseSources(files);

``markers``
^^^^^^^^^^^

.. code-block:: typescript

   readonly markers: readonly Marker[];

Markers from every parse and link performed on this parser, sorted by
``(file, line, col)``. Returns a copy, so an array a consumer holds does not
change under the next parse.

Markers **accumulate** across calls, which is the Python behaviour. For a
one-shot tool that is what you want. For a language server re-parsing a buffer
on every keystroke it is not — the list grows without bound and every entry
duplicates the last pass. Call ``clearMarkers()`` between parses:

.. code-block:: typescript

   parser.clearMarkers();
   parser.parseSources([{ name: uri, content: document.getText() }]);

``setMaxErrors(n)``
^^^^^^^^^^^^^^^^^^^

Stop reporting further errors for a file after *n*. ``0`` (the default) is
unlimited: a library caller wants every diagnostic, and the cap is a
terminal-output affordance a CLI opts into. Only error-severity markers count
against it, and a file that reaches it gets one extra ``PSS029`` marker
announcing the cutoff.

``dispose()``
^^^^^^^^^^^^^

Releases the WebAssembly-side parser. **Required, not an optimisation**: the
WASM heap is not reachable by the JavaScript garbage collector, so nothing else
will free it.

Idempotent — calling it twice is not an error, so a ``finally`` that runs after
an explicit dispose is fine. Every other method throws afterwards.

Markers and (once implemented) AST objects already materialised are plain
JavaScript and survive disposal. That is deliberate: a language server can hold
the last good tree while disposing the parser that produced it.

A ``FinalizationRegistry`` warns on the console when a parser is collected
without being disposed. That is a development aid and never a substitute:
finalizers are not guaranteed to run at all, so nothing may depend on it.

.. _ts-parse-exception:

``ParseException``
^^^^^^^^^^^^^^^^^^

.. code-block:: typescript

   class ParseException extends Error {
     readonly markers: readonly Marker[];
   }

Thrown when a parse or link produces any error-severity marker. ``message`` is
the multi-line summary, one line per marker, in the same format the Python API
produces.

Everything else that can go wrong is a plain ``Error``: a schema-hash mismatch,
use after ``dispose()``, or a trap escaping WebAssembly.


Markers
-------

.. code-block:: typescript

   type MarkerSeverity = 'error' | 'warning' | 'info' | 'hint';

   interface Marker {
     severity: MarkerSeverity;
     message: string;
     file: string;
     line: number;      // 1-based
     col: number;       // 1-based
     extent: number;    // characters in the primary span; -1 if unknown
     related: MarkerRelation[];
     code?: string;     // "PSS020"
   }

   interface MarkerRelation {
     file: string;
     line: number;
     col: number;
     label: string;
   }

Field for field this is what the Python API returns; see :doc:`markers` for the
catalogue of codes.

Two differences worth knowing:

``severity`` has no ``'unknown'``
   Python maps an unrecognised severity to the string ``"unknown"``. This union
   does not, because a consumer forced to write a branch for ``'unknown'`` is
   writing a branch for a core bug, not for anything a PSS source can cause.
   The binding throws at the boundary instead.

``code`` is optional, for now
   Not every core marker carries an id yet. When the marker-catalogue work
   lands, every marker will, and ``code`` becomes required — a breaking change,
   and the reason to make it before 1.0 rather than after.

Mapping to LSP diagnostics is direct, remembering that LSP is 0-based on both
axes and markers are 1-based:

.. code-block:: typescript

   import { DiagnosticSeverity } from 'vscode-languageserver';

   const SEVERITY = {
     error: DiagnosticSeverity.Error,
     warning: DiagnosticSeverity.Warning,
     info: DiagnosticSeverity.Information,
     hint: DiagnosticSeverity.Hint,
   } as const;

   const diagnostic = {
     severity: SEVERITY[m.severity],
     message: m.message,
     code: m.code,
     range: {
       start: { line: m.line - 1, character: m.col - 1 },
       end:   { line: m.line - 1, character: m.col - 1 + Math.max(m.extent, 0) },
     },
     relatedInformation: m.related.map((r) => ({
       message: r.label,
       location: {
         uri: r.file,
         range: {
           start: { line: r.line - 1, character: r.col - 1 },
           end:   { line: r.line - 1, character: r.col - 1 },
         },
       },
     })),
   };

File ids
^^^^^^^^

Units are numbered as they are created:

.. list-table::
   :header-rows: 1
   :widths: 10 20 60

   * - fileid
     - Unit
     - Notes
   * - ``-1``
     - builtins
     - synthesised types with no source text
   * - ``0``
     - standard library
     - loaded lazily on the first parse; see below
   * - ``1..``
     - user files
     - in the order passed to ``parseSources()``

The constants ``FILEID_BUILTIN`` and ``FILEID_STDLIB`` are exported.

The standard library loads itself
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A caller never asks for the PSS standard library and never has to. The first
parse on a ``Parser`` loads it into unit 0 before touching user input, which is
why user file ids start at 1. It is compiled into the ``.wasm`` as bytes, not
read from disk — which is what lets the build run with no filesystem at all.

The load costs a few milliseconds and is paid **once per Parser**. Creating a
parser per document pays it per document; that is the trade-off against reusing
one parser, discussed under `Reusing a parser`_.


AST helpers
-----------

The AST classes are generated from the same ``ast/*.yaml`` as the C++ and
Python bindings, and are re-exported as a namespace:

.. code-block:: typescript

   import { ast, walkScope, childrenOf, getNodeName, findNodeAtPosition,
            prettyPrint } from '@psstools/pssparser';

   if (node instanceof ast.Action) { /* ... */ }

``walkScope(scope)``
   Depth-first generator over every node beneath *scope*, yielding each node
   before descending into it.

``getNodeName(node)``
   The declared name, or ``null``. Handles both named forms in the schema —
   ``NamedScope`` for containers, ``NamedScopeChild`` for leaves — which are
   unrelated classes.

``findNodeAtPosition(root, pos)``
   The deepest node at or before a **0-based** ``{line, character}``. "At or
   before" rather than "containing", because nodes carry a start location but
   not reliably an end.

``prettyPrint(node)``
   Indented debug dump of a subtree.

``childrenOf(node)``
   The immediate children of *node*, whichever container form it takes. Use
   this rather than reaching for ``.children`` when writing your own traversal
   — see the warning below for why. ``walkScope`` cannot express a walk that
   needs depth or that prunes; this can.

.. warning::

   **Two container classes, not one.** ``Scope`` and ``SymbolChildrenScope``
   both hold children and neither is an ancestor of the other. ``ActivityDecl``
   is on the second branch. A traversal written against ``instanceof Scope``
   alone typechecks, runs, passes tests, and silently returns nothing for every
   activity body.

   These helpers handle both. If you write your own traversal, drive it from
   ``childrenOf`` rather than reproducing the test.

Position types are declared locally rather than imported from an LSP package,
so this package has no dependency on an editor protocol. They are structurally
identical to ``vscode-languageserver``'s ``Position``, so either can be passed
without conversion.


The AST boundary
----------------

**The AST is materialised into JavaScript objects, once per parse.** It is not
proxied over WebAssembly memory.

The alternative — a proxy per node — would put a WASM call under every
``.location.lineno``, and consumers walk the AST by field access.

Materialisation costs **about a fifth of parse time**, measured over the curated
corpus (92 files, 84 of which parse; 623 KiB serialised):

.. list-table::
   :header-rows: 1
   :widths: 40 20 40

   * - Step
     - Corpus pass
     - What it is
   * - Parse
     - 71.3 ms
     - the baseline this is measured against
   * - C++ serialise
     - 7.2 ms
     - walking the tree and filling the buffer
   * - Copy across the boundary
     - 0.18 ms
     - 623 KiB out of the WASM heap
   * - JavaScript deserialise
     - 8.2 ms
     - constructing the generated classes
   * - **Total**
     - **16.0 ms**
     - **22% of parse**

Both columns are warm: five passes over the corpus, of which these are the mean.
The 197 ms cold-pass figure in `Build characteristics`_ is the same work
measured on first execution, and dividing one by the other would overstate the
ratio by nearly 3×. Materialisation itself is stable to ±0.3 ms across runs.

The transfer is 1% of the total, which settles the design question: the cost of
bulk materialisation is the walk and the rebuild, not the boundary. Re-run it
with ``node wasm/spike.mjs``.

The wire format is generated from the AST schema by ``astbuilder gen-wasm``,
which emits both halves — the C++ writer and the TypeScript reader — in one run
from one schema. That is the whole reason it is generated: a writer and a reader
from different schema revisions put values in the wrong fields, silently. The
schema hash (`Loading`_) catches the case where the two were nonetheless
built apart.

Three consequences are observable and worth stating:

Returned AST objects are plain class instances
   They are not backed by WASM memory and survive ``dispose()``. This is a
   feature: a language server can hold the last good AST while re-parsing.

They are snapshots
   Re-parsing produces new objects; nothing mutates in place. A node held
   across a parse is stale.

Identity is not preserved across parses
   ``===`` between nodes from two parses is always false. Key on
   ``(fileid, location)``, never on object identity.

The **symbol table stays behind the boundary**. It is already an interface, the
structure is large, and materialising it would be the largest transfer for the
smallest benefit.


Loading
-------

.. code-block:: typescript

   function initPssParser(opts?: { wasmUrl?: string | URL }): Promise<PssParserModule>;

``createParser()`` instantiates the module on first call and caches it;
concurrent calls share one in-flight instantiation rather than racing to start
several.

Call ``initPssParser()`` directly to control *when* that cost is paid — an
extension activating eagerly, a page preloading — or to supply a ``wasmUrl``
when a bundler has relocated the binary:

.. code-block:: typescript

   // during activation, before the first document arrives
   await initPssParser({ wasmUrl: new URL('./pssparser.wasm', import.meta.url) });

Options are honoured only by the call that actually instantiates. There is one
module per process, and silently replacing it would invalidate every live
parser.

The schema hash
^^^^^^^^^^^^^^^

The ``.wasm`` and the generated TypeScript classes are built from the same
``ast/*.yaml`` and each carries a hash of it. **The hashes are compared at load
and a mismatch is fatal.**

This is the single highest-value defensive check in the package. Without it,
the symptom of a skewed build is a field read from the wrong slot: a string
that arrives as an integer, a child list off by one, a node deserialised into
the wrong class. Nothing about any of those points at the build. With it, the
failure is one sentence naming both hashes:

.. code-block:: text

   pssparser: AST schema mismatch between the WASM core and the generated
   TypeScript classes.
     wasm/pssparser.wasm : 15d0a733...
     src/ast/generated   : 8b1c40f2...
   The two were built from different ast/*.yaml. Re-run `npm run generate`.

The fix is always ``npm run generate``.


Reusing a parser
----------------

One builder serves a ``Parser`` for its lifetime, and that is deliberate rather
than an optimisation. Compile-time expressions are evaluated during AST
construction and may reference types and constants declared by a
previously-parsed unit (PSS 3.1 §19.1.2). A builder per call would restart that
environment, so a second call could not see the first call's constants:

.. code-block:: typescript

   const parser = await createParser();
   parser.parseSources([{ name: 'consts.pss', content: 'package p { const int W = 8; }' }]);
   // `p::W` resolves here only because the same builder saw consts.pss
   parser.parseSources([{ name: 'uses.pss',   content: 'import p::*; ... bit[p::W] f; ...' }]);

For a language server this cuts both ways, and the trade-off is not yet settled
by measurement:

* A **long-lived parser** amortises the standard-library load and keeps the
  cross-unit environment, which is what a workspace needs.
* A **parser per document version** is unambiguously correct and pays the
  standard-library load on every parse.

Whether a long-lived parser handles workspace edits cleanly is untested in
every existing consumer, including the Python one. Until it is measured, prefer
a fresh parser per document version if correctness matters more than latency,
and remember ``clearMarkers()`` if you do reuse one.


Building
--------

Two build products are generated and not committed: the TypeScript AST classes
and the WebAssembly binary. Both are reproducible from a clean checkout.

.. code-block:: bash

   ivpm update -d wasm-build     # Emscripten toolchain (298 MB, separate dep-set)

   cd ts
   npm install
   npm run gen:ast               # astbuilder gen-ts  -> src/ast/generated/
   npm run gen:wasm              # emcc               -> src/wasm/pssparser.{js,wasm}
   npm run generate              # both of the above

   npm run typecheck
   npm test
   npm run build                 # tsc -> dist/, plus the .wasm

The Emscripten toolchain is a dedicated ``wasm-build`` ivpm dep-set rather than
part of ``default-dev``: 298 MB is not a cost a developer building only the
Python extension should pay.

``scripts/wasm-env.sh`` puts the toolchain on ``PATH`` and points ``EM_CONFIG``
and ``EM_CACHE`` inside the deps directory. That last part is not cosmetic —
``emcc`` compiles sysroot libraries on first use, and a ``$HOME``-relative
cache is how a build ends up warm on a workstation and cold in every CI runner.

To build without the npm wrapper:

.. code-block:: bash

   source scripts/wasm-env.sh
   emcmake cmake -S wasm -B build-wasm -DCMAKE_BUILD_TYPE=Release
   cmake --build build-wasm -j

The WebAssembly build is a separate CMake configuration (``wasm/CMakeLists.txt``),
not a variant of the native one: the native build's ``ExternalProject`` chain,
install rules, RPATH handling and MSVC workarounds do not apply, and one link
step produces the whole deliverable.

Build characteristics
^^^^^^^^^^^^^^^^^^^^^

Measured on the pss-corpus curated set (92 files, 176 KB), Linux x86-64,
Node 22:

.. list-table::
   :header-rows: 1
   :widths: 40 30 30

   * - Metric
     - Value
     - Notes
   * - ``pssparser.wasm``
     - 3.45 MiB raw
     - 641 KiB gzip, 439 KiB brotli
   * - Cold start
     - ~11 ms
     - import plus instantiation, fresh process
   * - Parse throughput
     - ~885 KiB/s
     - ~2.2× the native Python bindings
   * - Standard-library load
     - ~6 ms
     - once per ``Parser``
   * - Materialisation
     - ~16 ms / corpus
     - serialise, transfer and rebuild the AST; see `The AST boundary`_

The core is built single-threaded. ANTLR's synchronisation primitives are
``std::mutex`` wrappers and Emscripten's libc++ provides single-threaded
implementations, so no threading build is needed — which avoids a
``SharedArrayBuffer`` requirement and the cross-origin isolation headers that
come with it, for a parser that is single-threaded anyway.


Verification
------------

The suite includes a **parity test against the native parser**. For every file
in the curated corpus and a set of targeted cases, the markers the WebAssembly
core reports must equal the markers the native Python bindings report — field
for field, including ``code``, ``extent`` and ``related``.

The expectations are generated, not written:

.. code-block:: bash

   PYTHONPATH=python packages/python/bin/python \
       ts/scripts/gen-parity-fixture.py -o ts/test/fixtures/parity.json

The output is committed, so the TypeScript suite needs no Python, no native
build and no corpus checkout — the three things a Node developer cloning the
package will not have. Regenerate it when the corpus or the parser's
diagnostics change; the diff is then a reviewable record of what changed.

A hand-written expectation would only show that the WebAssembly core agrees
with whatever the author believed while reading the same source twice.

The same applies to the **AST**. For every corpus file, the tree materialised in
TypeScript is compared node for node against the tree the native bindings build
— class, declared name, depth and location — over the pre-order walk
``ASTUtils.walkScope`` performs:

.. code-block:: bash

   PYTHONPATH=python packages/python/bin/python \
       ts/scripts/gen-ast-parity-fixture.py -o ts/test/fixtures/ast-parity.json

This is the test that matters for the wire format, and the reason is worth
stating. Both halves of the format come from one generator, so a round-trip test
shows only that they agree with each other — two same-width fields emitted in
the wrong order are written and read consistently and round-trip perfectly. Only
a comparison against an independently-built AST can see that, and this is it.
It covers the declaration spine rather than every node; expressions and exec
bodies are not yet compared.

A diagnostic build with AddressSanitizer is available for memory questions the
suite cannot answer:

.. code-block:: bash

   source scripts/wasm-env.sh
   emcmake cmake -S wasm -B build-wasm-asan -DENABLE_ASAN=ON
   cmake --build build-wasm-asan -j
   node wasm/asan-probe.mjs build-wasm-asan

It writes to its own build directory, never to ``ts/src/wasm``: the ASan
artifact is ~25× larger and uses a different allocator, and shipping it by
accident would be hard to notice.


Roadmap
-------

Implemented and tested
   ``createParser``, ``parseSources``, ``markers``, ``clearMarkers``,
   ``setMaxErrors``, ``dispose``/``Symbol.dispose``, the schema-hash check, the
   ``ASTUtils`` helpers, and the AST wire format in both directions.

Declared, not yet implemented
   ``link()``, ``root``, ``userUnits()``, ``fileMap()`` (populated by ``link``)
   and ``getProfileInfo()``. The serialiser these need is now in place and
   verified against the native parser; what remains is the ``Parser`` plumbing
   on top of it, and the link semantics — unconditional marker collection and a
   re-sort, the root recorded before failure — that ``link()`` has to preserve.

Before 1.0
   The marker-catalogue work, which makes ``Marker.code`` required. That is a
   breaking change, which is the argument for doing it before the package is
   published rather than after.


See also
--------

* :doc:`quickstart` — the Python API this one mirrors
* :doc:`markers` — the marker catalogue and codes
* :doc:`ast_structure` and :doc:`ast_usage_guide` — the AST these classes model
* :doc:`doc_comments` — what ``collectDocstrings`` collects
