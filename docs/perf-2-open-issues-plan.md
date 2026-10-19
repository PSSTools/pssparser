# perf-2: plan for the open issues

This plan follows up [perf-2-findings.md](perf-2-findings.md), which lists three
open issues. File:line references are to the tree as of this plan, with the two
perf-2 fixes applied but not yet committed. All PSS examples here are self-written.

## Status

| # | Issue | Severity | Status |
|---|---|---|---|
| 1 | Expression in a type argument resolved in the generic's scope | High: can bind to the wrong symbol without any error | Not started |
| 2 | Enum extensions don't reach a generic's specializations | Medium: a false error | Not started |
| 3 | Core-library diagnostics show `<unknown>`, and their lines are off by one | Low to medium: wrong locations | Not started |

The order is by severity, and each step is independent of the others. Do one
issue per commit. Every issue ends with the same gate:

- build: `cmake --build build -j16 && cmake --install build`, plus `build_ext` for step 3;
- the full pytest suite, with output to a log;
- `scripts/refcov.py check` and `scripts/occgate.py check`;
- a `CHANGELOG.md` entry under `## Unreleased`.

`docs/design/` does not exist in this checkout. Status therefore lives in this
file, and deferred defects go in its "Deferred" section.

---

## 1. Expression in a type argument is resolved in the generic's scope

### What goes wrong

```pss
package r { struct g_s<type T> { T f; } }
package p { import r::*; const int N = 8; struct u_s { g_s<bit[N]> x; } }
```

This reports a false `unknown identifier 'N'`. Variants were reproduced:

- **Same false error:**
  - nested: `g_s<g_s<bit[N]>>`;
  - pass-through: `k_s<bit[N]>` forwarded to `g_s<T>`;
  - domains: `int in [0..N]`, `bit[N] in [1..N]`.
- **Reported as "left unbound … a pssparser defect":**
  - qualified names: `bit[q::M]`, `bit[e_t::B]`, `e_t in [e_t::A]`;
  - a generic and `N` that are both in the same package.
- **Probably a silent wrong binding:** `r` also declares its own `N`. The copy then
  likely binds to `r::N`. This was inferred from the code, not confirmed by a run.
- **Not affected:** value arguments (`h_s<N+1>`), typedef arguments, and `string`.
- **Works only by accident:** `w_s<int W> { g_s<bit[W]> x; }`. When the specialization
  depth is above 0, `mk` keeps the caller's scope stack.

### Cause

1. `TaskResolveRef::visitTemplateParamTypeValue` (`src/TaskResolveRef.cpp:223`) never
   binds the references inside a type argument:
   - `visitExprRefPathContext` (:179) sets `m_ref` but never calls `setTarget`;
   - `visitExprRefPathStatic` (:205) is a TODO.

   Value arguments go through the local `ArgRefs` walker (:301–387), which does bind.
2. `TaskBuildParamValList::build` (`src/TaskBuildParamValList.cpp:263`) copies the type
   argument with `setPreserveExprTargets` off, so a target would be lost anyway. Value
   arguments set it on (:125).
3. `TaskGetSpecializedTemplateType::mk` (:219–249) resolves the copy in the generic's
   declaring scope.

### Design: bind at the use site and keep the targets

Recommended. This reuses the tested `ArgRefs` logic: the lookup-only
`resolveStaticArgPath`, the "unknown identifier" report, and the `unresolvable` sentinel.

Rejected: folding `bit[N]` to `bit[8]` before copying. That loses the reference
targets, which refs and occurrences need. It also cannot handle an enclosing
generic's parameter, and it would need a new rewriter.

`bindDefaults` is the wrong tool here. Its rule is the opposite one: it binds in the
declaring scope.

**Cache key.** `TaskCompareTypeRefs::widthEqual` (`src/TaskCompareTypeRefs.cpp:199`)
evaluates both widths.

- Today `N` has no target, so the result is `Unsure`, and each use creates a new
  specialization.
- After the fix, `bit[N]` with `N == 8` will share a specialization with `bit[8]`.
  This is intended, and a test will pin it.
- Check whether `TaskCompareTypeRefs::equal` compares domains (`in [..]`) at all. If it
  does not, domains need a fix too.

### Steps

1. **Factor out the walker.** In `src/TaskResolveRef.cpp` and its header, move
   `ArgRefs` out of `visitTemplateParamExprValue` into a file-scope class.
   - Give it no-op `visitDataTypeUserDefined` and `visitTypeIdentifier`.
   - Nested generics must not be walked here. They bind their own arguments through
     `resolveArgs`.
2. **Bind type arguments.** In `TaskResolveRef::visitTemplateParamTypeValue`, after the
   existing `accept`, run the walker over `getValue()`. Skip a bare
   `DataTypeUserDefined`.
3. **Keep the targets.** In `TaskBuildParamValList::build`, put
   `setPreserveExprTargets(true)` and then `(false)` around the type copy at :263, the
   same way :125 does.
4. **Optional.** At :376, apply the `!dependsOnParams` preserve rule to type defaults,
   as :347 already does for value defaults.
5. **Comment.** Update the comment at `TaskCopyAst.h:75`. It says value arguments are
   the only copy that keeps its targets.
6. **Watch one stdlib use.** `list<bit[SZ]>` at `src/stdlib/addr_reg_pkg.pss:173` will now
   bind at the use site. Watch the register tests.

### Tests (`tests/python/linking/test_template_binding.py`)

Assert which declaration each name binds to (`resolveSymbolPathRef`, the way
`_arg_lhs_binding` does), not just that the model links.

- The repro links cleanly, and the `N` in `T`'s width binds to `p::N`.
- **Shadowing:** `r` also declares `const int N = 2;`. `f` must be 8 bits wide.
- **Nested and pass-through:** `g_s<g_s<bit[N]>>` and `k_s<bit[N]>`.
- **Qualified names:** `bit[q::M]`, `bit[e_t::B]`, `e_t in [e_t::A]` and `int in [0..N]`.
- **Sharing:**
  - `g_s<bit[N]> a; g_s<bit[8]> b;` gives one specialization (`assert_specialization_count`);
  - with `N = 4` instead, there are two.
- **Varying caller:** `w_s<4>` and `w_s<8>` give two specializations of `g_s`. Also vary
  an element type, so that a shared specialization cannot hide a bug.
- **Errors** (`run_isolated`): `g_s<bit[M]>` with no `M` at all, and with `M` declared
  only in `r`. Each gives exactly one `unknown identifier 'M'`, at the line and column
  where it is written.

Expected gate movement: none. No symbolic-width type argument was found in the curated
corpus.

---

## 2. Enum extensions don't reach a generic's specializations

### What goes wrong

```pss
component C<int N=1> {
  enum e { A }
  extend enum e { B }
  action a { rand e v; constraint v == e::B; }
}
component pss_top { C<2> c; }
```

The specialization reports `'e' has no member named 'B'`. The same happens in two other
forms:

- an `extend enum e` inside `extend component C { ... }`;
- a top-level `extend enum C::e`.

### Cause

- `TaskApplyTypeExtensions::applyEnumExtension` (`src/TaskApplyTypeExtensions.cpp:518–543`)
  adds each item only to the `ISymbolEnumScope` (:531). The generic's
  `IEnumDecl::items` never gets it.
- `mk` copies `IEnumDecl::items` (`TaskCopyAst.h:1033–1045`) and builds symbols from the
  copy only (`TaskBuildSymbolTree.cpp:402–451`). So `B` is lost.
- The comment at `TaskCopyAst.h:267`, from the perf-2 fix, says the members of a skipped
  `IExtendEnum` were already merged. That is true for `IExtendType`, but not yet for enums.

### Design: merge the items into the generic's AST, non-owning

Recommended. Do it the same way `mergeIntoGenericAst` (:621–677) does for type members.
All three forms go through `applyEnumExtension`, so one change covers them. The copier
and the symbol builder then need no change.

Rejected: re-applying the enum extensions inside `mk`. That needs a registry of
extensions per generic and a pass to fix up child indices after the copy, and it
duplicates the instance-extension machinery.

How the design handles each concern:

- **Ownership.** Push `IEnumItemUP(item, false)`. The `IExtendEnum` keeps the only owning
  reference, and each specialization owns its own copy.
- **Duplicates.** Merge only in the branch where the name was not found (:528–531).
  `reportDuplicate` reports a duplicate once, at the extension, and the duplicate never
  reaches a copy.
- **Value expressions.** No rebinding is needed. `B = N+1` resolves per specialization,
  inside the copy.
- **Location.** `TaskCopyAst::fin` copies locations, so an error points at the
  `extend enum` line. It may be repeated once per specialization, which is how type
  members already behave.
- **Ordering.** A specialization can be built during the apply pass:
  - through `TaskResolveRef.cpp:546`, for example `extend enum C<2>::e`;
  - for an instance extension, through `buildParams`.

  If the owning generic already has `getSpec_types()`, report a marker instead of dropping
  the items silently.
- **Side effect.** Python API walkers and the census will see extension items in a
  generic's `EnumDecl.items`. Type members already behave this way since
  `mergeIntoGenericAst`.

### Steps

1. In `TaskApplyTypeExtensions.cpp`, move the in-generic walk (:648–657) into a helper,
   `bool inGeneric(ast::IScopeChild*)`. Use it from `mergeIntoGenericAst`.
2. In `applyEnumExtension`, in the not-found branch, push the item non-owning into
   `target_s->getDecl()->getItems()` when the declaration is inside a generic.
3. Ordering hazard: when specializations already exist, report a new diagnostic.
   - Pick a message under 120 characters.
   - Add a `MarkerDef` in `core_checker.py`.
   - Document it in `docs/markers.rst`, and update the goldens.
4. Fix the comments at `TaskCopyAst.h:267` and `TaskBuildSymbolTree.cpp:534`, and the
   `items` documentation in `ast/datatype.yaml`.

### Tests (`tests/python/linking/test_template_extensions.py`)

1. The three forms, parametrized, each for `C<2>`.
2. `C<2>` and `C<4>` both see `B`. Vary an element type as well.
3. `extend enum e { B = N }`: `C<5>` and `C<7>` each satisfy `v == e::B` with their own value.
4. A duplicate (`enum e {A}` and `extend enum e {A}`) gives one diagnostic, at the
   extension, not one per specialization.
5. Distinct values across an extension are checked per specialization (LRM 7.5.1e).
6. `e::Z`, which no extension adds, is still rejected.
7. An extension in another package, with an unqualified reference to `B`.
8. Ordering: an early specialization followed by `extend enum C::e`. The result must be
   either the item or the new marker, never silence.

Expected gate movement: none in `census-parity.json`, since no fixture combines a
generic with `extend enum`. Refs and occurrences may bind references that were
unbound before. Read any drift before regenerating.

### Deferred

The names declared in an extension's own package (CL-N1) are not recorded for enum
items, which is unchanged by this work. Add a test that pins the current behavior, and
note it here.

---

## 3. Core-library locations: `<unknown>` file and an off-by-one line

### What goes wrong

```pss
package addr_reg_pkg { struct addr_trait_s {} }
```

This gives PSS003, but its related location is `{'file': '<unknown>', 'line': 13}`. The
real declaration is at line 12 of `src/stdlib/addr_reg_pkg.pss`. So there are two bugs:

- **The file name is missing.** All five stdlib files are built into the same
  `GlobalScope`, and `mkGlobalScope(len(self._files))` is always 0 (`parser.py:147,193`;
  `wasm/bindings.cpp:694`). `_pathOf` (`parser.py:397`) knows only user files. TS maps id 0
  to a bare `<stdlib>` (`ts/src/Marker.ts:118`).
- **Every line is one too high.** `src/stdlib/mk_pssstdlib.py` writes `R"(\n<data>)"`, and
  the leading `\n` shifts every line by one.
- **A latent lookup bug.** `NameLookup::appliesAt` (`NameLookup.cpp:1269–1287`) compares
  (id, line) pairs. The five files overlap on id 0, so their packages' line ranges
  overlap too.

The LSP (`vscode-pss-support`) has its own stdlib loader and is not affected.

### Design: keep id 0, give each file its own line band

Recommended.

- `mk_pssstdlib.py` writes one combined source with no leading newline, plus a table of
  `{name, first_line, num_lines, text}`.
- `TaskLoadStandardLibrary::load` calls `build()` once.
- (0, line) pairs no longer collide, which also fixes `appliesAt`. The roughly 20 places
  that treat id 0 as "the stdlib" do not change.
- Python and TS translate (0, line) to `<stdlib>/addr_reg_pkg.pss:12:5` through the table.
- If a single build behaves differently, the fallback is to keep five builds and start
  each file's lexer at the first line of its band.

Rejected: a separate id per stdlib file. It breaks the contract, used across TS, Python
and pssfmt/sphinx-pss, that user ids start at 1, and it needs about 20 changes to id
checks.

Add-on: the table carries each file's text, so an editor can open the embedded source,
even under WASM where there is no file system.

### Steps

1. `src/stdlib/mk_pssstdlib.py` `main()`:
   - drop the leading `\n`;
   - make sure each file ends in a newline;
   - write the combined source and a `pss_stdlib_files[]` table.
2. `TaskLoadStandardLibrary::load`: one `build()`.
3. `IFactory.h` and `Factory.cpp`: add `getCoreLibrarySources()`. Expose it in
   `python/core.pyx` (`Factory`).
4. `parser.py`:
   - add `_resolveLoc(fileid, line)`;
   - use it in `_mkErrorMessage` and in `_collectMarkers`, for the main location,
     related locations and fixes;
   - add a public `resolve_location()`.
5. `refs.py`: add a helper that maps a stdlib location to its path. Update the `file_map`
   docstring.
6. `wasm/bindings.cpp`: add `coreLibrarySources()`. `ts/src/Marker.ts` `pathOf()` and
   `toMarker` use the table.
7. Do a full `build_ext`, then re-run the profiling gates. The stdlib warm-up changes
   from five builds to one.

### Tests

- The PSS003 example above reports `<stdlib>/addr_reg_pkg.pss`, line 12, column 5.
  Check it in Python, in the CLI's text and JSON output, and in TS.
- Each stdlib package resolves to the real `package` line of its source file.
- The embedded text equals what `get_stdlib_files()` returns.
- A `message` reference translates to `<stdlib>/std_pkg.pss`.
- A regression test for `appliesAt` across stdlib packages.

Expected movement:

- the docstring at `test_instance_extensions.py:249`;
- the `Marker.ts` tests that expect a bare `<stdlib>`;
- any assertion of a stdlib line number, which moves by −1.

No error-suite golden contains `<unknown>`. `references.json` and `occurrences.json`
cover only user files.
