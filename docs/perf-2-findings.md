# perf-2: parsing the `sav/` model set

Command under investigation:

```
pssparser sav/top_only.pss sav/amd_base_model.pss sav/amd_actions.pss sav/r_member.pss
```

## Result

It was not slow. It segfaulted in the linker about 1 s after starting, which looks
like a hang or slow parse from the outside. With the fixes below, the run takes
**0.12 s** and reports 7 diagnostics. All 7 are real gaps in the inputs:

- undefined `amd_core_tag_e`, `amd_mem_block_e`, `NUM_OF_CORES` and `AMD_MAX_BUF_SIZE`
- `memory_ops` declared in two extensions of `pss_top`

## Bug 1 (fixed): crash specializing a generic that contains an `extend`

Trigger: a template type whose own body extends one of its members, then specialized.

```pss
component C<int N=1> {
  action a { }
  extend action a { }
}
component pss_top { C<2> c; }
```

- `TaskGetSpecializedTemplateType::mk` copies the generic's AST.
- `TaskCopyAst` has no copy for `ExtendType` or `ExtendEnum`. `copyChildren` stored the
  null result as a child.
- `mk` reported an internal error, then kept the partial copy.
- `TaskBuildSymbolTree::visitTypeScope` dereferenced the null child.

Fix (`src/include/pssp/impl/TaskCopyAst.h`, `copyChildren`):

- Skip nested `extend` statements. `TaskApplyTypeExtensions::mergeIntoGenericAst` has
  already merged their members into the target's AST, so the members are still copied.
- Never store a null child.

Tests are in `tests/python/linking/test_template_extensions.py`, the three
`*_generic_body_*` cases. They were checked to fail without the fix.

## Bug 2 (fixed): template default resolved in the wrong scope via an instance extension

```pss
package r { struct d_s { } struct g_s<struct T, struct A=d_s> { } }
package p2 { import r::*; struct h_s<struct T=d_s> { g_s<T> x; } struct k_s<struct T=h_s<d_s>> { T t; } }
// another file
import p2::*; import r::*;
extend struct k_s<h_s<d_s>> { int y; }
```

This gave a false `unknown type 'd_s'` against the default inside package `r`. In
the core library it showed up as `<unknown>:87:53: unknown type 'alloc_base_mode_s'`,
which is the `ALLOC_MODE` default of `transparent_addr_claim_s`.

Cause: `bindDefaults` (`src/TaskSpecializeParameterizedRef.cpp`) bound only value
defaults, and dropped the whole list if any default had template arguments. An
instance extension specializes before any generic body has been visited. So a type
default was still unbound when it was copied, and it was then resolved in the
enclosing specialization's scope.

Fix: `bindDefaults` now binds each default, of any kind, in the declaring scope. It
skips a default only if that default may depend on the parameter list.

- Tests: two cases in `tests/python/linking/test_instance_extensions.py`.
- Side effect: `ts/test/fixtures/census-parity.json` was regenerated. The core
  library's `reg_c` default `ACC = READWRITE` is now bound too.

## Follow-up issues (fixed)

All three are fixed, one commit each; see
[perf-2-open-issues-plan.md](perf-2-open-issues-plan.md) for the outcome of each and
what was deferred. The plan also covered a second stdlib location bug found while
planning: every core-library line number was one too high.

1. **Enum extensions don't reach a generic's specializations.** This affects
   `extend enum` inside the generic body, inside `extend component C {...}`, and
   `extend enum C::e` at top level. `TaskApplyTypeExtensions::applyEnumExtension`
   merges items into the symbol scope only, never into the AST that `mk` copies.
   Specializations report `'e' has no member named 'B'`. Before bug 1 was fixed, the
   in-body form crashed instead.
2. **`<unknown>` file name for core-library diagnostics.** All stdlib files share file
   id 0, which has no entry in `python/pssparser/parser.py` `_pathOf`. Line numbers
   are per-file, so the location cannot name the library file. It is only visible
   when the core library itself fails to link.
3. **An expression in a type argument is re-resolved in the generic's scope.** For
   `g_s<bit[N]>`, where `N` is a const in the user's package, the result is a false
   `unknown identifier 'N'`. It does not need an extension to show up, and it predates
   this work.

## Suite

9553 passed, 88 skipped, 6 xfailed, 2 errors. The 2 errors are in
`tests/python/skills/test_skills.py`. The cause is "No package metadata": this
checkout has no egg-info. They fail the same way without these changes.
