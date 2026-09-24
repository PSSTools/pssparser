# Changelog

Version numbers are `<PSS major>.<PSS minor>.<patch>`: the first two components
name the **revision of the PSS LRM this parser targets**, not the parser's own
feature level. A release that adds parser capability without moving to a new LRM
revision advances only the patch component.

## Unreleased

### Added — addr_reg_pkg forwards endianness_e, packed_s and sizeof_s (symbol-resolution 6.3, LRM 21.13)

PSS 2.0 declared `endianness_e`, `packed_s` and `sizeof_s` in `addr_reg_pkg`;
they are now `std_pkg`'s, and LRM 21.13 requires tools to accept either
package "as if they were the same types". `addr_reg_pkg::packed_s<>`,
`import addr_reg_pkg::packed_s;` and `import addr_reg_pkg::*;` now reach
`std_pkg`'s declarations (the enum items `LITTLE_ENDIAN` and `BIG_ENDIAN` come
with a wildcard import). Importing both packages is not ambiguous. Previously a
model that used only `addr_reg_pkg` got "unknown type 'packed_s'".

### Changed — extension members are recorded in the AST

`SymbolTypeScope.ext_members` lists every named member an extension
contributed to a type, with the package of its extension (LRM 17.2.3), as
`SymbolExtMember {name, idx, pkg}` nodes. It replaces a side table that was
private to the linker. Lookup does not consult it yet.

### Changed — an import applies only where it is written (symbol-resolution 6.3a, LRM 18.1.3)

An import now applies only inside the statement that contains it: a `package`
statement, a component declaration or an `extend`. An import in the global
scope applies to the rest of its file. Previously every import of a namespace
applied wherever that namespace was open, so an import in one file reached
other files, and an import in one `package p { }` statement reached every other
`package p { }`. Models that relied on this are now rejected:

- **A global import does not reach another file.** Add the import to each
  file that uses it.
- **An import does not reach another statement of the same package.**
- **A component's imports do not reach an `extend component`, and an
  extension's imports do not reach the component declaration.**

The error names the import the model relied on:
`unknown type 's'; 'import lib::*;' provides it, but an import applies only
inside the statement it is written in, or to its own file (18.1.3) -- add
'import lib::*;' here`, with a note at that import.

Two legal models that used to be rejected now link:

- **An import inside `extend component` reaches the extension's own members**,
  including the types it declares.
- **A wildcard import reaches the items an `extend enum` in that package
  adds** (LRM Example 248).

The same import written in two files is no longer merged into one, so it
applies in both.

### Changed — name lookup follows the LRM order (symbol-resolution 6.2, LRM 17.2, 18.3)

Every name is now looked up by one procedure in the order that 18.3 gives. The
order used to depend on which kind of scope the name was in. Legal models that
used to be rejected now link:

- **An inherited member hides a component import.** In a derived component,
  a member of the base component is found before anything the derived
  component imports (18.3 b.3 before b.4).
- **A type's own template parameter hides a component import.** In
  `component c<type T> { import P::*; ... }`, `T` is the parameter, even when
  `P` declares a `T`.
- **An extension sees its own package first.** Names in an `extend` are looked
  up in the package that encloses the `extend` statement and its outer
  packages, and then globally (17.2). A global name used to shadow the
  extension's package, and outer packages were not searched at all.
- **An enum item declared in a base component** can be used unqualified in a
  derived component.
- **Imports inside `extend component` are resolved** (LRM Example 248). Each
  one used to be reported as unbound.

One model that used to be accepted is now an error: **a base component's
imports no longer reach a derived component.** The LRM searches a base type's
members, not its imports (18.3 b.3). Add the import to the derived component.

A qualified name that reaches an inherited member, such as `der_c::N` where
`N` is declared in `base_c`, now binds to the member itself. Its target used
to stop at `der_c`. An import that names nothing is reported once, not once
per linker pass.

### Changed — the completeness check covers every reference (symbol-resolution 3.5)

After linking, pssparser used to check only user-defined type references for
a missing binding. It now checks every name the resolver is meant to bind:
types, expression names and paths, qualified paths, annotation types and
parameters, and template-string assignment targets. A name left unbound with
nothing said about it is now reported:

- **PSS002** when nothing in the model declares that name. For example,
  `p::f().nosuchmeth()` on a string-returning `f` used to be accepted; the
  unqualified `f().nosuchmeth()` was already an error.
- **New marker PSS042, "Reference left unbound (pssparser defect)"**, when
  something of that name is declared but the resolver did not bind it. This
  is a bug in pssparser; please report it with the input. It is reported only
  on a model that has no other error.

One mistake still gets one message. Nothing new is reported where an error
already exists, inside an `extend` whose target is unknown, or after a name
whose type or base type is unknown. Constructs that pssparser does not resolve
yet are not checked: covergroup bodies and port maps, pool and activity binds,
scheduling constraints, instance overrides, struct-literal member names, and a
generic constraint's parameters.

The old message `type 'X' is never resolved: ...` is gone. The check found
several resolver gaps on legal code, now fixed:

- **Annotations on statements are resolved.** Annotations in activities,
  monitor activities and procedural blocks, and on functions, used to be
  skipped (Example 323). An unknown parameter name in one of them is now
  PSS002, as it already was elsewhere.
- **`{% x = ...; %}` binds `x`** to the template local it assigns.
  Find-references and rename now see it.
- **A qualified array dimension binds every element.** In `a[sizes::N]`, the
  `sizes` part now binds too, not only `N`.

### Fixed — static and instance members (symbol-resolution 7.3, LRM 18.3, 20.2, 20.4)

The linker used to ignore `static`. Models that relied on that now get
errors; each one is fixed by adding `static`, or by going through an
instance.

- **New marker PSS040, "Instance member used without an instance".**
  - `T::m` can name only a type's types, static constants, static functions
    and enum items (18.3). `sub_c::inst_f()` and `sub_c::fld` used to be
    accepted. They are still accepted inside `sub_c`, a subtype of it, or an
    extension of either.
  - A static component function has no instance (20.2). Its body can no
    longer read the component's non-static fields or call its instance
    functions, whether they are its own or inherited. This also applies to
    `{{...}}` in a static target template.
- **Instance functions cannot be imported** (20.4), reported as PSS019.
  - In a component, `import C function void f(int a);` must say `static`,
    whether `f` is declared anywhere else or not (20.4.1.1 b.1).
  - `import C function f;` is an error when no declaration of `f` says
    `static`.
  - Package functions are always static, so they are not affected.
  - LRM Example 289 omits `static` here. The normative text wins, and a
    correction has been filed with the working group.
- **New marker PSS041, "Static member used through 'comp'"** (9.1.4.1 f).
  `comp.f()` or `comp.K` in an action, where `f` or `K` is static, is now an
  error. So is a static member of a sub-component reached through
  `comp.sub`. Name the member without `comp.`, or through its type
  (`sub_c::f`).

### Fixed — function definitions and imports (symbol-resolution 7.2, LRM 20.2, 20.4.1, 20.6)

- **A definition may name its parameters differently from the declaration**
  (20.2). `function int f(int a); function int f(int b) { return b; }` used to
  report "unknown identifier 'b'" and let `a` resolve in the body instead.
  The body now uses its own names, also when the definition comes from an
  extension, and a target template's mustaches use the template's names.
- **A target template is an implementation.** Giving a function both a target
  template and a PSS body, or a target template and an import, is now PSS003
  ("function 'f' is already defined" / "cannot be both defined and
  imported"). It used to be silent.
- **New marker PSS019, "Function cannot be imported here"** (20.4.1). A
  function declared in a component can be imported only in that component
  type or an extension of it, not in a derived component, another component
  or a package. A function declared in a template component cannot be
  imported at all. Both used to be silent.

### Fixed — merging type extensions (symbol-resolution 7.1, LRM 17.2.3, 17.3)

- **A function declared in a type may be defined in an extension**, or the
  other way round (20.3): the two are one function. This used to be "Type
  extension of f conflicts with an existing declaration". Implementing it twice
  is still an error (PSS003, "function 'f' is already defined"), including
  from two packages.
- **Two packages may each add a field or type of the same name** to one type
  (17.2.3), and both are kept. Lookup does not yet tell them apart by package:
  a reference binds to the first one merged (known-issues L-05).
- **Conflicting extension members are PSS003 and say which rule applies**:
  "its initial definition already declares it" or "another extension in
  package 'p' already declares it". A note points at the first declaration.
- **A duplicate enum item in `extend enum` is an error** (PSS003, 7.5.1),
  whether it repeats the enum, another extension in any package, or the same
  extension. It used to be silent.
- **An `extend` inside `extend component` is applied** (17.3). It used to be
  dropped silently. Its target must be a type the component declares (PSS005
  otherwise). An `extend` of an unknown type written directly in a component
  is reported too (PSS002), where it used to be silent.
- **"cannot extend 'x': it is not an extendable type" and "... as an enum: it
  is not an enum type" have a code**, PSS005.

### Fixed — declaration order (symbol-resolution WS9, LRM 18.2)

- **In a block, a name is visible only after its declaration** (18.2a/b,
  4.7.1.2): in exec, activity and monitor-activity blocks and in template
  strings. A use before a local's declaration used to bind to that later
  local; it now binds to whatever the name means outside the block
  (`bit[8] x; exec init_up { x = 1; string x; }` assigns the field), and
  where nothing outside declares it, it is an error (PSS002, "'x' is used
  before its declaration on line N"). This includes `{% x = 1; %}` before
  `{% int x; %}`. Type, package and global scopes are unchanged: a member may
  still be used before it is declared (Example 262).
- **Constant initializers are ordered** (18.2c/d, 4.7.2 Example 1; new
  **PSS118**, error): a constant or enum item used in another constant's
  initializer, template strings included, must be declared first. Across files
  the order the files are given in applies, as it already does for
  `compile if`. A package-level constant may reference only package-level
  constants (`const int A = C::K;` is an error).
- **A constant used in a type width before its declaration is a warning**
  (new **PSS119**): the rule is in the prose under Example 264 only.

### Fixed — built-in members `uid`, `prev` and `comp` (symbol-resolution 5.1, 5.3)

- **`uid` resolves** (clause 9): `comp.uid`, `r.uid` on a resource or flow
  object reference, `h.uid` and `s[1].uid` on action handles, `this.uid`, and
  `uid` unqualified inside the type. It is a `bit[32]` member of every action,
  monitor, component, buffer, stream, state and resource, and not of a plain
  struct. These all used to fail with "Failed to find elem uid".
- **`prev` resolves** in a state type and its extensions (9.3.3.1g, 13.3),
  typed as the state itself, so in a derived state `prev` has the derived
  type. LRM Example 170 now links. `prev` reached as a member of another
  object (`i.prev` on an input) is an error (PSS002).
- `uid` and `prev` are members of the **linked symbol tree only**, flagged
  `FieldAttr.Builtin` with no source location; they are not AST nodes, and
  the occurrence API reports uses of them as `builtin`. A walk of a linked
  type's `children()` now sees one more `Field` (two in a state).
- **Redeclaring a built-in member is PSS003**: a user `uid`, `prev`,
  `initial` or `instance_id` ("duplicate declaration of 'uid': every action
  has a built-in 'uid'"), also through an `extend`. A user `initial` or
  `instance_id` used to replace the built-in silently. The AST-injected
  `initial`/`instance_id` fields now carry `FieldAttr.Builtin`.
- **`comp` is typed in two more places:** an abstract action declared in a
  component (it was left untyped: "root ref-path element comp is not a
  composite scope"), and every action of a specialized template component
  (`c_t<8> c;`), where the type path was built relative to the
  specialization. `comp` in an abstract action declared in a package is
  reported as "'comp' is only valid in an action declared in a component"
  (PSS002).

### Fixed — `super` (symbol-resolution 5.2)

- **`super.x` searches the base type only** (LRM 17.1, Table 27). It was
  looked up like a plain `x`, so the derived type's own `x` won: `super.f(1)`
  in a component that shadows `f` bound to the derived `f` and was
  arity-checked against it ("too many arguments"). Now `super.x` binds to the
  base's `x`, or to one the base inherits, and never to the derived type's
  members or to an enclosing scope. Inside `a with { ... }` it is the
  *containing* action's base, matching `this`.
- **Misuse is reported** (PSS002): `super.x` in a type with no base type
  (it used to find any `x` in an enclosing scope); `super.x` where the base has
  no `x` (with a hint when the derived type declares it); `super` outside a
  type; and a `super;` statement in an activity or exec block of a type with no
  base type.

### Fixed — action traversals and initializer lists (symbol-resolution 4.2)

- **An unknown traversal target is reported** (PSS002): `nosuch;` in an
  activity, a `sequence`, a `parallel`, a monitor activity or a symbol body
  used to link cleanly (it printed a debug line at most). The target now goes
  through the ordinary path resolver, which also reports a bad subscript
  (`aa[NOSUCH];`).
- **What a traversal names is checked** (new **PSS018**, error). LRM 11.3.1
  allows an action or monitor handle -- however declared: action field,
  activity-local handle, symbol parameter, foreach iterator, the label of an
  earlier traversal -- an element, sub-array or whole array of handles, and a
  data field declared with the `action` modifier (Ex. 173); also a generic
  constraint and a symbol. Anything else is an error: an `int` or struct
  variable (`'x' is not an action handle, ...`), a type (`... traverse it by
  type with 'do A'`), a block label, and `do S` on a struct. A **fixed** named
  constraint cannot be traversed (decision Q1).
- **Traversing a `dynamic` constraint is a warning** (new **PSS117**): LRM
  13.1.1 deprecates dynamic constraints in favour of a generic constraint with
  no parameters, `constraint c() { ... }`.
- **Initializer paths resolve** (U3). The `.x` in `a {.x = v}`, `do A {.x = v}`,
  `A a {.x = v};` (action body or activity) now binds to the member of the
  traversed action type, including nested paths (`.s.z`); an unknown one is
  `'A' has no member named 'x'` (PSS002). It is looked up in that type only: a
  same-named field of the enclosing action does not satisfy it. The value side
  is still resolved where it is written. `ActionFieldInitializer.path` now has
  a target, relative to the traversed action as a `with`-block reference is
  (`ElemKind_Inline`).
- A labelled activity block (`L1: sequence { A a; a; }`) was resolved a second
  time from the action's scope, as well as in its place. Harmless until now,
  it would have given a handle traversal inside it a path that skipped the
  block.

### Fixed — locals in procedural `if`, `match` and `while` bodies (symbol-resolution 4.1b)

- A local declared in a braced body of a procedural `if`/`else`, `match`,
  `while` or `repeat`...`while` now has a target path that resolves. It used to
  be bound on paper and dead to every consumer: `pssparser.refs` reported the
  use against nothing. `while` only worked when the loop was the first
  statement of its block. No AST class changed; the path to such a local now
  has one more step, the statement, followed by the body's position in it
  (an `if`'s clauses in order and then its `else`, a `match`'s choices, a
  loop's single body). `ProceduralStmtIfClause.body` and
  `ProceduralStmtMatchChoice.body` now carry that position as their `index`.

### Fixed — `this` (symbol-resolution 5.2)

- **`this` resolves** (LRM 13.1.4). In a type body it is the enclosing type;
  in an inline `with` block it is the *containing* action, so `this.f` reaches
  a containing-action field the traversed action's `f` shadows, and
  `this.comp` is the containing action's component (Examples 143, 243). It
  used to be `unknown identifier 'this'` everywhere. `pssparser.refs` now
  reports the member after `this` as bound; `this` itself stays `builtin`.
- `this` outside any type (a package-level function) is reported as
  `'this' is only valid inside a type ...` (PSS002).
- Declaring anything named `this` -- a field, type, parameter, local or loop
  variable -- is an error (PSS022). The lexer returns `this` as an identifier,
  so the grammar accepted it. An escaped `\this` is still an ordinary name.

### Changed (AST API) — `ElemKind_This`

- New `SymbolRefPathElemKind.ElemKind_This` (value 7, appended; no existing
  value moved). A `this` reference's target path leads to the context type and
  ends in this element, so a consumer can tell `this.x` (an instance) from a
  reference to the type by name. A consumer that switches on the kind needs a
  case for it; see `docs/design/cross-repo-followups.md` X-11.

### Added — pss-scrambler requests (FR-001, FR-002)

- **`pssparser.refs.occurrences(parser)`**: every identifier in the user's
  files, with the declaration it names -- every element of a member path and
  of a qualified name, parameters, `with { ... }` fields, enum items,
  `extend` targets, template references, `compile if` conditions. Works after
  a `link()` that raised. Each occurrence has a `resolution` from a closed
  set (`pssparser.refs.Resolution`: `user`, `library`, `builtin`,
  `unresolved`, `dependent`), and a declaration that overrides or shadows one
  in a base type has `base_decl`. See `docs/refs.rst`.
- **`Parser.inactive_regions()`**: the branches a `compile if` left out, as
  `InactiveRegion(fileid, start_line, start_col, end_line, end_col)`.
- **`ExprId.getDecl()`**: the declaration the linker bound this identifier to,
  recorded for every element of a member path and of a qualified type name.
- **`CompileCond`**, on `Scope.compile_conds`: each `compile if` /
  `compile assert` keeps its condition (bound, never reported) and the source
  range of each branch not elaborated. Branch selection is unchanged.

### Changed (AST API) — pss-scrambler requests

See `docs/design/cross-repo-followups.md` X-10.

- **`ConstraintBlock.name` is an `ExprId`** with its own location (was a
  `str`; FR-002 B). `getName()` returns `None` for an unnamed block (was
  `""`). Applies to `GenericConstraintDeclBool` too. The factory takes an
  `ExprId` (or null).
- **`ExprCompileHas.ref` is an `ExprRefPath`** (was `ExprRefPathStatic`, and
  always null). It is filled in, and is `visit: false`: `compile has(X)` may
  name something that does not exist, so no pass reports it.

### Fixed — pss-scrambler requests (BUG-001, BUG-002; pyastbuilder)

- An exception raised in a Python `VisitorBase` override propagates unchanged
  out of `accept()`, and the traversal stops there. It used to be swallowed and
  replaced by an unrelated `SystemError` or `AttributeError`. Each visitor
  callback also leaked a reference to `None`.
- `pssparser/ast.pyi` is valid Python and matches the module: list accessors
  are typed `ListUtil[T]` (which now also supports `len()` and indexing), the
  duplicate `SymbolRefPath.getPath` is gone, and enum-field setters
  (`ExprBin.setOp`, ...) exist at runtime.

### Changed (AST API) — symbol-resolution R2 schema batch (activity scopes)

Consumers that walk activities need updating; see
`docs/design/cross-repo-followups.md` X-6 to X-8.

- **An action handle or `action` data field declared in an activity is a child
  of the block that declares it,** not of the enclosing action or monitor
  (LRM 11.8.2, plan 2.6). A consumer collecting an action's handles has to
  walk its activity as well; a consumer walking a block's statements now meets
  `ActionHandleField` and `Field` entries among them. `getParent()` is still the
  enclosing action or monitor.
- **Every compound activity statement is a scope.** `ActivityRepeatCount`,
  `ActivityRepeatWhile`, `ActivityForeach`, `ActivityReplicate`,
  `ActivityIfElse`, `ActivitySelect`, `ActivityMatch` and `ActivityAtomicBlock`
  derive from `ActivityLabeledScope` (were `ActivityLabeledStmt`), and
  `MonitorActivityEventually` from `MonitorActivityLabeledScope`. `getLabel()`
  and every existing field are unchanged; the factory methods take a leading
  `name` (pass `""`). A test for "is this an activity statement" that checks
  `ActivityLabeledStmt` or `ActivityStmt` no longer matches them.
- **A loop's variables are its children,** as `ProceduralStmtDataDeclaration`
  (the repeat or replicate index; the foreach iterator, typed from the
  collection's element, and index). They used to be synthetic `int` fields
  injected into a braced body, and were absent for a brace-less one.
- **`ActivityForeach.target` is renamed `path`** (it collided with
  `SymbolScope.target`). `getTarget()` on a foreach now returns the scope
  target, which is null.

### Fixed (symbol-resolution R2)

- Legal code no longer rejected: two blocks each declaring a handle of the same
  name (LRM Ex. 122, 124), a loop index used in a brace-less body (Ex. 113),
  two sibling loops with the same index name.
- Now reported where they were silent: a loop variable used after its loop, an
  action-level reference to a handle declared in the activity (11.8.3), and
  unknown names in the `with` block of a traversal of an activity-declared
  handle or of a foreach iterator.
- Names inside nested activity blocks and loop bodies are now bound to a path
  that resolves; they used to be bound to a path through an unaddressable scope,
  which every consumer read as unbound.
- Annotation parameter names (`@a {.x = 1}`) bind to the member; the binding
  pointed past the annotation type.

### Changed (AST API) — symbol-resolution R1 schema batch

Consumers that read these fields need updating; see
`docs/design/cross-repo-followups.md` X-5 to X-7.

- **Every reference now has somewhere to record its binding** (WS3.2). A new
  node, `ExprRefName` (`id`, `target`, `ctx_unknown`), replaces the bare
  `ExprId` in `ActivitySymbolCall.target`, `AnnotationParam.name`,
  `ComponentBindTarget.field`, `ComponentPathElem.id`,
  `CovergroupCross.coverpoint_names`, `CovergroupCrossBins.target`,
  `CovergroupPortmap.name`, `CoverpointBins.target`, `ExportFunction.name`,
  `ExprAggrStructElem.name` and `TemplateAssign.lhs`. Read the name as
  `x.getId().getId()`; `x.getTarget()` is the binding where one is resolved
  (symbol calls, exported functions and annotation parameters so far).
- **Dotted references are `ExprRefPathContext`, not `ExprHierarchicalId`:**
  `ActionFieldInitializer.path`, `ActivityBindStmt.lhs`/`rhs`,
  `ActivitySchedulingConstraint.targets`, `ConstraintStmtDefault.hid`,
  `ConstraintStmtDefaultDisable.hid`, `ConstraintStmtUnique.list`,
  `CovergroupInstantiation.targets`, `CovergroupPortmap.target` and
  `InstanceOverride.target`. The old value is `getHier_id()`.
- **`ComponentBind.pool_path` is an `ExprRefPathContext`,** not the source text
  of the path.
- **`DataTypeEnum.in_rangelist` is an `ExprDomainOpenRangeList`** (was
  `ExprOpenRangeList`), like an integer type's domain, so it can hold the open
  ranges 7.5.2 allows. It was always null before: the builder dropped it.
- New: `TypeIdentifier.is_global` (`::x`), `Field.initializers` (the
  `{.x = v}` list of a handle declared in an action body), and `ExprMemberCall`
  (a method call on a string or aggregate literal, `"a,b".split(",")`).
- **`ExprBitSlice.rhs` is the slice's lower bound.** It held a second copy of
  the upper bound, so `x[7:0]` read as `x[7:7]`.

### Fixed (symbol-resolution R1)

- Legal code no longer rejected: labelled `do` in a monitor activity (LRM Ex.
  236), enum open-range domains (`in [..B]`, 7.5.2), a method call on a string
  literal (Ex. 10), `action` data fields (Ex. 83, 137, 173), relative import
  paths, a root-level `extend` through a root-level import, `derived_c::a` for
  an inherited `a` (Ex. 242), an explicit import together with a wildcard
  import of the same name (18.1.3), a repeated default parameter value of equal
  value (3.1 20.2.4c), and symbol parameters (Ex. 120-style).
- Now reported where they were silent: unknown names in parameter defaults,
  procedural `repeat` counts, bit-slice bounds, traversal subscripts and
  initializer values, enum base types and domains, generic-constraint parameter
  and return types, `import C function f;` and `export target function f;`,
  symbol calls (name, kind and argument count), `::x` that is not global,
  duplicate named constraints, and a subscript on a static path.
- New codes: PSS017 (ambiguous import, which now resolves to nothing instead of
  to the first import).

### Fixed

- **A generic constraint (13.1.2) is now a symbol in its enclosing scope, so
  references to it resolve.** The declaration linked clean, but every reference
  failed — `lim_lt(20)` with `unknown identifier 'lim_lt'`, `p::gt_zero(x)` with
  `'p' has no member named 'gt_zero'` — so the construct could be declared and
  never used. `IGenericConstraintDeclBool` derives from `IConstraintBlock` and so
  reached `TaskBuildSymbolTree::visitConstraintBlock`, which calls the *unnamed*
  `addChild()`: correct for a fixed constraint block, which is not referenceable,
  and wrong for a generic one, which is called by name. Both declaration forms
  now register their name.

  Two consequences worth noting. A generic constraint that shares a name with a
  field in the same scope is now a duplicate declaration, where before the
  collision was silent. And arity is now checked at the reference: a generic
  constraint has no `IFunctionPrototype`, so it does not go through the ordinary
  call path — without its own check every reference would be rejected as
  "'lim_lt' is not a function". The message names the construct:
  `too many arguments to constraint 'lim_lt': expected 1, got 2`.

### Added

- **Configuration files: `.pssparser.toml` and `pyproject.toml`.** Everything
  that can be set with a flag can now be set in a file, so a project's rules
  travel with the project. Both spellings carry the same tree; `pyproject.toml`
  prefixes every table with `[tool.pssparser]`. Discovery walks upward from the
  working directory — not from the first source file, so
  `pssparser a/x.pss b/y.pss` cannot silently apply two configurations to two
  halves of one run — and stops at the first directory carrying a config, at a
  `.git` directory, or at the filesystem root. A `pyproject.toml` with no
  `[tool.pssparser]` table does not halt the search, and one that fails to parse
  is stepped over: it belongs to the whole project, and pssparser is not
  entitled to refuse to start over another tool's syntax error.

  `--config PATH` replaces discovery rather than layering on it; a missing or
  unparseable PATH is exit 2, never a silent fall-through. `--no-config` ignores
  files entirely. `--show-config` prints every resolved value with the layer
  that set it — with four layers able to set `select`, it is the only
  supportable answer to "why did this rule run?".

  Arrays replace wholesale and tables merge entry by entry: an array that merged
  would give no way to *remove* an entry a lower layer set, and a table that
  replaced would make a one-line `[severity]` override discard the rest.
  Unknown keys are rejected with a did-you-mean rather than ignored — a silently
  dropped `[checker.foo]` is a rule the user believes is configured and is not.
  `checkers = [...]` gets its own explanation, since TOML forbids a key from
  being both an array and a table and the singular/plural split is what keeps
  both spellings available. Requires `tomli` on Python 3.10; `tomllib` is stdlib
  from 3.11.

  Naming something that does not exist is fail-fast, matching `--checker`:
  `select`, `[checker.<name>]`, `[severity]`, and
  `[extensions.<name>] enabled = true` all stop the run if the named thing is
  not installed. `enabled = false` for an absent extension is the exception, so
  one file can serve a dev machine and a leaner CI image.

- **`[severity]`: per-marker severity overrides, including `off`.** Re-level any
  diagnostic by marker ID; `off` drops it entirely, so it is not counted and
  does not affect the exit code. Applied *before* the warning policy, so
  `-Werror` cannot promote something the configuration already turned off. One
  restriction: a core `error` cannot be downgraded, and attempting it is a
  config error naming the key rather than a silent no-op. A core error means the
  model could not be built — the parse and link failure paths return a forced
  exit code of 1 with no linked AST — so silencing one would report success for
  a run that compiled nothing.

- **Per-checker options: `options_schema`, `configure()`, and
  `--describe-checker`.** A checker declares what it accepts (`type`, `default`,
  `help`, optional `choices`) and receives it through an optional `configure()`
  hook; users write `[checker.<name>]`. Validation runs at startup, before any
  source file is read, so an unknown key, a wrong type, a value outside
  `choices`, or options aimed at a checker that declares none is exit 2 with a
  message naming the checker. The table handed to `configure()` is always
  complete — declared defaults filled in — so an implementation never needs
  `options.get(key, default)`, which is how a default and its schema entry drift
  apart. Checkers that declare no schema never have `configure()` called, so
  everything written before options existed behaves exactly as it did.
  `--describe-checker NAME` prints the description, contributing extension,
  markers, and the whole options table. The `naming-convention` example gained
  real `style` and `exempt` options as a worked demonstration.

- **`pssparser.extensions`: installable collections of checkers.** A single
  entry point now contributes a whole rule package, instead of one entry point
  per checker class. The declared module exposes `register(registry)`; the
  registry takes `add_checker()` plus the `version`/`description` shown by the
  new `--list-extensions`. `pip install` is all a user does — the rules then
  run with no flags. The older `pssparser.checkers` group keeps working and is
  adapted internally into a single-checker extension, so one model serves the
  CLI. A worked example lives in `examples/pss_rule_collection/`.

  Extensions carry a version contract: `pssparser.checkers.API_VERSION` is
  bumped only for incompatible changes to the checker-facing surface, an
  extension declares the minimum it needs as `REQUIRES_API`, and it can probe
  `reg.api_version` to support several pssparser releases from one package.

  Discovery never aborts the run: a broken extension is reported as `PSS030`
  and the rest of the registry still loads, since a third-party package is code
  the user did not write. New diagnostics `PSS030`–`PSS033` (extension failed
  to load, entry-point key disagrees with the checker's name, API too new,
  duplicate marker ID) form a `PSS030`–`PSS039` tooling band. They are ordinary
  diagnostics — present in `--json`, counted, and promotable, so
  `-Werror=PSS030` makes a failed extension fatal in CI. Extensions load in
  sorted name order so duplicate-ID reports are reproducible.

- **`--list-extensions` and `--no-extensions`.** The first answers "where did
  this rule come from?"; the second (also `PSSPARSER_NO_EXTENSIONS=1`) runs the
  built-in checks only, which is how a run is made reproducible regardless of
  what is installed alongside pssparser, and the first thing to try when
  diagnosing unexpected output.

- **`-Werror`, `-Werror=ID`, `-Wno-error=ID`, and `--no-warnings`.** Warnings
  can now be promoted to errors, individually or wholesale, and a promoted
  diagnostic names the flag that promoted it (`[-Werror=PSS104]`) so a reader
  can tell "this is an error" from "you asked for this to be an error". In
  `--json`, a promoted diagnostic carries `"original_severity": "warning"`
  next to its `"severity": "error"`, and `summary.errors` counts it.
  Suppression is applied before promotion, so `--no-warnings -Werror` reports
  nothing. Two documented consequences: a warning with no marker ID can only
  be promoted by a blanket `-Werror` (there is no name to put after the `=`),
  and `--max-errors` does not count promoted warnings, because the cap is
  enforced while parsing, long before promotion happens.
- **`--stats` and `--stats-no-timing`.** Report what a run actually did:
  declaration counts by kind, a histogram of the diagnostic codes that fired,
  and per-phase wall times. Only the user's files are counted — neither the
  standard library nor the implicit members the linker grafts onto user types
  (every action gets a `set_executor` prototype) contribute. The
  standard-library load is reported on its own row rather than folded into
  the user's parse time, and the parse row is labelled `parse (incl. read)`
  because the parser reads from the open file and the I/O cannot honestly be
  separated. `--stats-no-timing` drops the wall times, making the output
  byte-stable and therefore usable in goldens and documentation. Under
  `--json` the document gains a top-level `"stats"` key whose `decls` object
  always carries every counter, even at zero. A diagnostic whose message
  matches no entry in the marker-ID pattern table is counted under
  `<uncoded>` rather than dropped — a non-zero `<uncoded>` count means the
  C++ message text has drifted from the table. Neither flag ever changes the
  exit code.
- `docs/cli.rst` now documents the exit codes (`0`/`1`/`2`/`130`) in a table.
  It previously described none of them.
- **`PSS116` — "construct is accepted but not represented in the AST."**
  Constructs the grammar accepts but the AST builder discards were previously
  silent: source using them parsed with an empty marker list, and the consumer
  received a model missing behaviour with nothing to indicate it. Every such
  site now warns, naming the construct, and — where a node is built but
  incomplete — the specific part that is dropped (`the \`with\` constraints are
  dropped`). "Parses clean" now means "is fully represented".

  The marker is informational about the front end, not about the input: the
  source is legal PSS and there is nothing to fix in it. `PSS116` is suppressed
  while loading the standard library, which uses some of these constructs
  itself. See `docs/ast_usage_guide.rst`, and `docs/ast-coverage-gaps.md` /
  `docs/ast-coverage-plan.md` for the catalogue and the work to close it. As
  each construct is implemented its `PSS116` disappears.
- `IAstBuilder::setReportUnrepresented()` / `getReportUnrepresented()`, which
  gate the above.
- **`scripts/check_ast_inventory.py`**, run from the suite as
  `tests/python/test_ast_inventory.py`. Three checks, each catching a defect
  class that is a *silence* rather than a wrong answer, so no ordinary test can
  see it:

  - a class in `ast/*.yaml` the builder never constructs;
  - a class whose declared fields the symbol-tree builder walks with the
    enclosing scope still current, silently duplicating their contents into it;
  - a parser rule in `PSSParser.g4` no input can reach.

  Exemptions live in `scripts/ast_inventory_allowlist.txt` and must carry a
  reason; an entry that no longer names a finding is itself an error, so the
  file cannot decay into a list nobody has re-read.

### Changed

- **Monitor activity bodies are built, and the monitor AST now matches the
  PSS grammar.** Every braced monitor activity form constructed an *empty*
  node: the statement loop in each visitor was commented out. A monitor's
  `activity { ... }` reached a consumer with no children, whatever the source
  said. `concat` and `overlap` additionally built a `MonitorActivitySequence`,
  so a gapless sequence and a strictly-ordered one were indistinguishable;
  `select` and both `constraint` forms had no visitor at all; `eventually` was
  built with a null body; and the monitor traversal was built with a
  hard-coded null target.

  All five braced forms (`sequence`, `concat`, `overlap`, `schedule`,
  `select`) now build their own class, derived from the new
  `MonitorActivityLabeledScope`, and carry their statements in
  `getChildren()`. `eventually` carries its operand. A `constraint` among the
  activity statements builds a `MonitorConstraint`; one in the monitor body
  builds an ordinary `ConstraintBlock`, as it does in an action or struct.

  **Eight AST classes were removed**, none of which was ever constructible.
  `MonitorActivityIfElse`, `MonitorActivityMatch`,
  `MonitorActivityMatchChoice`, `MonitorActivityRepeatCount`,
  `MonitorActivityRepeatWhile` and `MonitorActivitySelectBranch` described an
  imagined SystemVerilog-assertion-like syntax — `req ##1 ack`, `repeat`,
  `if`/`else`, `match`, guarded `select` branches — that PSS does not have.
  `MonitorActivityActionTraversal` and `MonitorActivityMonitorTraversal` went
  because the grammar spells a monitor traversal exactly as it spells an
  action traversal: nothing before type resolution distinguishes them, so both
  build an `ActivityActionHandleTraversal` or `ActivityActionTypeTraversal`.
  `MonitorActivityConcat.lhs`/`.rhs` and `MonitorActivityOverlap.lhs`/`.rhs`
  are gone with the binary operator they modelled, and
  `MonitorActivityEventually.condition` with the expression the grammar has no
  place for.

  Two grammar rules were removed with them:
  `monitor_activity_monitor_traversal_stmt`, unreachable behind
  `activity_action_traversal_stmt`, and `monitor_inline_constraints_or_empty`,
  which nothing referenced. The former was also mistranscribed from LRM B.11 —
  it put the optional marker on the subscript *expression* rather than on the
  subscript — so `h[];` parsed cleanly. It is now a syntax error.

- **Cover statements build AST nodes, and the two classes for them now match
  the grammar.** `cover M;` and `cover { ... }` parsed, reported `PSS116` and
  constructed nothing — the last monitor construct that did. Both now build,
  and both carry the optional `label_identifier :` prefix.

  `CoverStmtReference.target` changed from `ExprRefPath` to `TypeIdentifier`:
  LRM B.12 has `cover monitor_type_identifier ;`, so the statement names a
  monitor *type*. The old shape claimed it named an instance, for which there
  is no syntax. The target is resolved, so `cover NotThere;` is now reported;
  its *kind* is not checked yet, so `cover A;` naming an action is accepted.

  `CoverStmtInline` changed from a `ScopeChild` holding one `body` node to a
  `Scope` holding the body in `getChildren()`: the braces take
  `monitor_body_item*`, the same items a `monitor` body takes. The body is its
  own scope, so a handle declared in one inline cover does not collide with a
  handle of the same name in another, or leak into the enclosing component.

- **Covergroups are represented beyond their names.** The covergroup AST held a
  name, a target expression and a list of crossed names. Everything else — every
  `option.x = y;`, every `bins` / `illegal_bins` / `ignore_bins` specification,
  a coverpoint's explicit sample type and its `iff` guard, a cross's `iff` and
  bins — was reported as a gap and discarded. A covergroup *type*
  (`covergroup cg_t(int a) { ... }`) and an instantiation of one
  (`cg_t cg(.a(x));`) built no node at all.

  New: `CovergroupType`, `CovergroupInstantiation`, `CovergroupPortmap`,
  `CovergroupOption`, `CoverpointBins`, `CovergroupCrossBins`. Existing
  `Covergroup`, `CovergroupCoverpoint` and `CovergroupCross` gained the fields
  that were being dropped. `CoverpointBins.form` says which of the three
  right-hand sides the grammar took — a value list, another coverpoint, or
  `default` — so a null field is never ambiguous.

  A covergroup type's ports are `Field` children in its own scope rather than a
  list beside it: a port's type is an ordinary type reference and has to bind.
  The rest of a covergroup body is not resolved, which is why the coverpoint
  target, the guards and the bin filters carry `visit: false`.

- **`override { ... }` is represented.** The block was walked and discarded, so
  a consumer doing elaboration saw no overrides at all. `OverrideDecl` holds
  `TypeOverride` (`type T with U;`) and `InstanceOverride`
  (`instance p.q with U;`) in source order, which matters — a later statement
  overriding the same target wins.

- **`symbol` declarations and calls are represented.** Both were parse-only.
  `SymbolDeclaration` is a scope named in the symbol table, holding its body as
  ordinary activity statements; `ActivitySymbolCall` keeps the name called and
  the arguments. The call is not resolved here — a symbol may be declared after
  the call that uses it.

- **`export A(...)` and `import class C { ... }` are represented.**
  `ExportFunction` covered only the function form; `ExportAction` now covers the
  action form, with the same platform qualifier and the exported parameter
  signature. `ImportClass` is a `TypeScope`, so an imported class is a type
  others can name; its method prototypes are its children, and `extends` holds
  every base named after `:` (the first also being `super_t`).

- **Activity `constraint` is represented.** `constraint { ... }` and
  `constraint expr;` among the activity statements built nothing.
  `ActivityConstraint` is a statement rather than a block hoisted into the
  action body, because its position in the statement order is what
  distinguishes it.

- **`randomize` keeps its target and its `with` constraints.** Both were
  dropped, leaving a `ProceduralStmtRandomize` that named nothing and
  constrained nothing. A comma-separated target list is still reduced to its
  first element — `target` is one expression — and now says so.

- **`super.x` builds `ExprRefPathSuper`.** It built a plain
  `ExprRefPathContext`, which made it indistinguishable from `x`.
  `ExprRefPathSuper` derives from `ExprRefPathContext`, so a consumer that does
  not care is unaffected.

- **`string in ["a","b"]` keeps its domain values.** `has_range` was set and
  `in_range` left empty: the AST said a range existed and could not say what it
  was.

- **`FunctionPrototype` carries `is_static`.** A `static function` and an
  instance method were indistinguishable; the qualifier is now recorded for
  both the plain and the imported forms.

- **`bind` targets are structured nodes instead of dotted text.**
  `ComponentBind.targets` was a list of strings, which lost every index
  selection in a target path — `bind p { sub[0..3].prod.out }` kept the text but
  no consumer could read the `0..3` or tell it from part of a name — and
  collapsed a mixed list `{ a.x, * }` to a wildcard flag plus a partial list.
  Each target is now a `ComponentBindTarget`: a list of `ComponentPathElem`
  (each with an optional index range), plus either the wildcard flag or the
  `ActionType.field` the bind names with its own optional index.

  **This changes the type of `ComponentBind.getTargets()`** from `List[str]` to
  `List[ComponentBindTarget]`. A wildcard is now a target like any other, so
  `bind p *;` has one target rather than none; `is_wildcard` survives as a
  summary of the list — true if any target is a wildcard — and is unchanged for
  the bare form.

### Removed

- **Fifteen AST classes the builder never constructed have been deleted.**
  `ExprListLiteral`, `ExprStructLiteral`, `ExprStructLiteralItem`,
  `ExprSubscript`, `ExprSubstring`, `ExprRefPathId`, `ExprRefPathElem`,
  `ExprRefPathStaticFunc`, `ExprStaticRefPath`, `ProceduralStmtFunctionCall`,
  `SymbolScopeRef`, and the whole `RefExpr` family (`RefExpr`,
  `RefExprTypeScopeGlobal`, `RefExprTypeScopeContext`, `RefExprScopeIndex`).

  Each was superseded by a differently-named node that *is* built, and nothing
  said so: a consumer writing `visitExprStructLiteral` got a visitor that
  compiled, linked, and never fired. That is worse than a missing class, which
  at least fails at build time.

  **Migration.** Nothing that ever ran needs changing — none of these nodes
  could appear in a tree this parser produced. What each was mistaken for:

  | Deleted | Built instead |
  |---|---|
  | `ExprListLiteral` | `ExprAggrList` |
  | `ExprStructLiteral`, `ExprStructLiteralItem` | `ExprAggrStruct`, `ExprAggrStructElem` |
  | `ExprSubscript` | `ExprMemberPathElem.getSubscript()` |
  | `ExprSubstring` | `ExprSliceRange` in `ExprMemberPathElem.getSubscript()` |
  | `ExprRefPathId`, `ExprRefPathElem` | `ExprRefPathContext` |
  | `ExprStaticRefPath`, `ExprRefPathStaticFunc` | `ExprRefPathStatic`, `ExprRefPathStaticRooted` |
  | `ProceduralStmtFunctionCall` | `ProceduralStmtExpr` |
  | `SymbolScopeRef`, `RefExpr` and subclasses | nothing — the linker resolves through `SymbolRefPath` |

  `scripts/check_ast_inventory.py` now fails the build if a new class joins
  them, so this list cannot grow again unnoticed.
- **Two unreachable parser rules**, `type_identifier_templ_elem` and
  `array_size_expression`. Neither had a reference outside a comment; the same
  script now checks that every rule in `PSSParser.g4` is reachable from
  `compilation_unit`.

### Fixed

- **Diagnostic columns were reported one character past the token they name.**
  `ast::Location.linepos` is documented as 1-based, but three sites in the AST
  builder copied ANTLR's 0-based `getCharPositionInLine()` in unadjusted, and
  the Python marker layer applied a compensating `+1` to *every* marker. The two
  errors cancelled for syntax diagnostics and compounded for all the others, so
  roughly half the tool's output pointed one character to the right: `'hGZ`
  reported the invalid digit `G` at the column of `Z`, `bit[7:1]` reported the
  low bound `1` at the column of `]`, and an unknown-type error underlined one
  character past the type name. **This changes reported columns for non-syntax
  diagnostics** — a consumer pinning them (including `--json` output) will see
  the corrected values. Syntax-error columns are unchanged.
- **`compile if` brace-deprecation warnings underlined too little, and did not
  say which `compile if` they belonged to.** The span came from
  `ParserRuleContext::getText()`, which concatenates token text and so drops
  every space between them — the caret stopped several characters short of the
  branch whenever it was written with ordinary spacing. The warning now spans
  the whole branch, carries a `note:` pointing at the owning `compile if`
  keyword (which disambiguates the pair raised for an `if`/`else`), and reports
  its `PSS104` code directly rather than having it recovered by matching the
  message text. The same measurement bug is fixed for `compile assert`, the
  `foreach` traversal-target error, and the integer-width low-bound error.
- **The caret no longer runs past the end of the source line.** A construct
  spanning several lines has an extent longer than the line it starts on, and
  the renderer drew tildes for the full extent regardless.
- **An `extend enum` no longer declares its items in the enclosing package.**
  `ExtendEnum` is a plain `ScopeChild`, so the generated symbol-tree visitor
  added the extension and then walked its item list with the *enclosing* scope
  still current — and an enum item registers a name. Every enumerator added by
  an extension was therefore declared in the package as well as in the enum, so
  `extend enum a_e {x} extend enum b_e {x}` reported *duplicate declaration of
  'x'* although the two enumerators belong to different enums, and
  `extend enum a_e {x} struct x { }` collided an enumerator with a type. The
  items reach the enum through `TaskApplyTypeExtensions`, which reads them from
  the AST directly, so nothing needed the symbol-tree registration.

  Found by `scripts/check_ast_inventory.py` — the seventh instance of a defect
  whose first six were fixed by hand during the AST-coverage work.

- **An action handle is now reachable by name from a constraint.**
  `ActionHandleField` had no visitor in the symbol-tree builder, so it fell
  through to the generic scope-child path: appended to the scope's children,
  never entered in the symbol table. `monitor M { A a; constraint { a.v < 4; } }`
  reported *unknown identifier 'a'*, as did an activity-declared handle
  (`activity { A h; ... }`) referenced from anywhere. The node's type was also
  added to the enclosing scope as a second, anonymous child. Nothing noticed
  while monitor bodies were discarded, because an action-body `A a;` matches
  `action_field_declaration` and becomes a plain `Field` — `ActionHandleField`
  is reachable only from a monitor body or an activity.
- **A covergroup body no longer leaks into the enclosing scope.** Neither
  `Covergroup` nor the two new covergroup classes had a symbol-tree visitor, so
  the generated ones walked the coverpoint, cross, option and port-map lists
  with the enclosing scope still current. A struct with one covergroup linked to
  a struct holding the covergroup *plus* a loose copy of everything inside it.
  The same defect applied to an exported action's parameter list and to a
  `symbol` body.
- **A monitor's activity statements no longer appear twice in the linked
  tree.** `MonitorActivityDecl` had no visitor in the symbol-tree builder, so
  the generated one added the declaration and then walked its children with the
  enclosing type scope still pushed. `monitor M { A a; activity { a; } }` linked
  to a monitor holding an activity *and* a loose copy of the traversal beside
  it. Surfaced by the same change that made monitor bodies non-empty.
- **A parameterized monitor can be specialized.** `TaskCopyAst` had no visitor
  for `Monitor` or for any monitor activity node, so `monitor M<int N> { ... }`
  failed with *"it contains a construct the AST copier does not support"*.
- **`bind` no longer reports a gap it does not have.** `PSS116` fired on *every*
  object bind, including the wildcard and plain-path forms that were already
  fully represented. Every occurrence in the test corpus was one of those, so
  the marker's entire observed output was false positives.
- **`public:` / `private:` / `protected:` group labels are now applied.** An
  access-modifier label was parsed and discarded, so every field declared after
  one was built with no access attribute at all and read as *public*. A
  consumer enforcing access saw no violation. The label now sets the access
  attribute for the rest of its scope, exactly as the inline form
  (`private int x;`) does; an inline modifier on a declaration still overrides
  the label in force, and a label does not leak into a type declared inside the
  labelled scope. **This changes `Field.attr` for existing input** — code that
  treated group-labelled fields as public will now see `Private`/`Protected`.
- **`default x == v;` and `default disable x;` now build
  `ConstraintStmtDefault` / `ConstraintStmtDefaultDisable`.** Both AST classes
  existed and neither visitor constructed anything, so default-value
  constraints vanished from the model — including the standard library's own
  `default permanent == false;`.
- **The two-step `import function pkg::f;` now builds `FunctionImportType`.**
  The branch handling it was empty, so this import form produced no AST node
  whatsoever.
- **`import <lang> function ...` records the language.** `FunctionImportProto`
  was constructed with `""` for `lang` regardless of what the source declared.
- **Parameterized types in `type_id` were already handled**; what remained was
  a dead `mkTypeId(std::vector<IExprIdUP>&, ...)` overload whose body was
  entirely commented out and which had no callers, plus a stale `TODO` on the
  live overload. Both removed.

### Notes

- `exec_super_stmt` is unreachable: `exec_stmt` tries `procedural_stmt` first
  and it matches `super;`, so `exec body { super; }` has always built a
  `ProceduralStmtSuper` and nothing was ever lost.
- **`monitor_handle_declaration` has been removed from the grammar.** It was
  unreachable — `action_handle_declaration` preceded it in both
  `monitor_field_declaration` and `monitor_activity_stmt` with the same shape,
  `type_identifier identifier-list ;` — so `m1 h1;` inside a monitor has always
  built an `ActionHandleField`, and the builder hook for the monitor form could
  never fire. No parser can separate the two: which kind of handle is being
  declared follows from resolving the type, which happens at link. Keeping a
  production that made the distinction look decidable was the actual defect.
  Behaviour is unchanged — the same nodes are built from the same source — but
  the generated `PSSParserVisitor` no longer declares
  `visitMonitor_handle_declaration`, and `ActionHandleField` is now documented
  as covering both forms.

## 3.0.6 — source tools, PSS 3.1 constructs, and a working release path

**3.0.3, 3.0.4 and 3.0.5 were tagged but never reached PyPI**, so the last
published release is 3.0.2 and this entry covers everything since. The 3.0.3
section below still describes what landed under that number; it is accurate,
it was simply never published. What kept the three of them unpublished was the
release path itself, which is the last item under Build.

### Added

- **`pssparser.tokens`** — lossless tokenization, separate from parsing. The
  tokens of a file concatenate back to that file byte for byte, and the
  guarantee is unconditional: it holds for input that does not lex, for input
  that is not valid UTF-8, and for input carrying a byte-order mark. Trivia
  (whitespace, both comment forms) arrives on its own channels rather than
  being discarded. See `docs/source_tools.rst`.
- **`pssparser.cst`** — the concrete syntax tree, from a parse-only entry point
  that does not build the AST. Nothing the parser matched is folded away, so
  redundant parentheses and both branches of a `compile if` survive, and each
  node's token indices index the accompanying stream. Syntax errors are counted
  rather than raised.

  Together these are the surface a formatter or a source-rewriting tool needs;
  neither existed before.
- **PSS 3.1 constructs**, including target template blocks and template
  specialization. See `docs/pss31_features.rst` and `docs/pss31_migration.rst`.
- `docs/checker_plugin_guide.rst`, `docs/comments.rst`, `docs/sanitizers.rst`.

### Fixed

- Cycle detection and avoidance in type resolution.
- **Iterating a list accessor works on Python 3.13.** `ListIterator`, emitted
  by the AST generator, defined `__next__` but not `__iter__` and so was not a
  valid iterator. On 3.12 nothing noticed, because `list(node.field())` reaches
  `__next__` without calling `iter()` on the iterator itself; on 3.13
  `[x for x in node.field()]` raised `TypeError: 'ListIterator' object is not
  iterable` while `list(...)` on the same object kept working. Fixed upstream
  in pyastbuilder; no change to any API here.

### Build

- **The C++ test executable and the gtest dependency are gone.** The suite is
  pytest. The three gtest files covered rules the Python tests already cover,
  and the dependency had to be fetched and built by every developer and every
  CI job. Nothing about installing or using the package changes.
- The release path works. It had been broken in three separate places at once,
  each of which failed after the tag was pushed: the pinned gtest could not be
  configured under CMake 4, the corpus was fetched twice and the second clone
  died on an existing path, and one unimportable test module took the whole
  pytest run with it as a collection error. All three are fixed; the first is
  fixed by deletion.

## 3.0.3 — doc comments, source extents, and the shipped standard library

The doc-comment subsystem has been replaced. See `docs/doc_comments.rst` for the
association rules, the supported comment forms, and the normalization steps.

### Added

- `Parser(collect_docstrings=True)` enables doc-comment collection through the
  public Python API. Previously the only way to get a docstring was to drive
  `core.Factory` and call `setCollectDocStrings` on the builder directly, so the
  documented entry point could not produce docstrings at all. Default is
  unchanged (off).
- Doc comments now attach to **enum items, function parameters, and template
  parameters**. These are built into typed lists rather than through `addChild`,
  so they never received a docstring before.
- All four comment forms are recognized without marker residue: `//`, `///`,
  `//!`, `/* */`, `/** */`, `/*! */`. Doxygen's trailing markers (`///<`,
  `//!<`, `/**< */`, `/*!< */`) are accepted and the `<` is stripped.
- `setDocCommentTabWidth()` and `setDocCommentStrictMarkers()` on `IAstBuilder`.
  Strict mode restricts documentation to the marked forms; the default remains
  permissive.
- **Trailing comments.** `rand int len;  // how many bytes` documents `len`. A
  leading comment always wins, and a trailing comment never leaks into the next
  declaration.
- **`getDocstring()` works on the linked tree.** The linker copies the doc
  comment — with `getDocRaw()`, `getDocForm()` and `getDocLocation()` — onto
  the symbol scope wrapping each declaration. Previously a `SymbolTypeScope`
  required a `getTarget()` hop, and package, enum and function scopes offered
  no route at all because they set no target: four scope classes, four rules,
  two of them dead ends. One call now answers for all of them.

  Where several declarations contribute to one scope — a package re-opened in
  another file, a function declared and then defined — **the first non-empty
  doc comment in link order wins**. See
  :ref:`docs/doc_comments.rst <multi-declaration-docstrings>`.

- **Symbol scopes carry a source extent.** `endLocation` is copied onto the
  scope alongside `location`, which no site did, so every scope in the linked
  tree reported a start and an end of -1.

- **The full comment on the AST.** `ScopeChild` gains `getDocRaw()` (verbatim
  source), `getDocForm()` (a `DocCommentForm` enum), and `getDocLocation()` (the
  comment's own position, so a bad doc comment can be reported where it was
  written).
- **Source extents.** `endLocation` moved up to `ScopeChild` from the handful of
  subclasses that declared it, and `Location.extent` is populated, so any
  declaration — not just a braced scope — reports a usable range.
- **Every comment, not just the documenting one.** `Parser(collect_comments=True)`
  — `setCollectComments()` on `IAstBuilder` — populates `getComments()` on every
  `ScopeChild`, procedural statements included, with `Comment` nodes carrying
  normalized text, verbatim source, block/line form and a `Leading` /
  `Trailing` / `Orphan` placement. Comments no construct can claim land on the
  enclosing scope's `getTrailing_comments()`. Off by default, and it implies
  `collect_docstrings`. See `docs/comments.rst`.

  Docstring and comment extraction are independent: the docstring is whichever
  comment *documents* a declaration, `getComments()` is everything written
  around it.
- **The standard-library sources ship in the wheel**, with
  `pssparser.get_stdlib_dir()` and `pssparser.get_stdlib_files()` to locate
  them. Note that these must not be handed to `Parser.parse()`: every parser
  loads the compiled-in copy first, so they would arrive as duplicate
  declarations.

### Fixed

- **Enum items and function prototypes had no source location.** `addChild`
  sets a node's location, but both of these are built into a typed list on
  their parent instead — `EnumDecl::items`, `FunctionDefinition::proto` — so
  they kept the default `lineno` of -1. That is the documented marker for a
  compiler-injected node, so a consumer applying it uniformly discarded every
  enum value in the model. An item contributed by `extend enum` reports the
  extend site, not the base declaration. The injected
  `set_executor`/`set_default_executor` prototypes are still marked, which is
  what distinguishes them.

- **A failed `link()` left nothing walkable.** `link()` raised before
  recording its result, so a caller that caught the `ParseException` found
  `user_units()` returning `[]` and `file_map` empty. The units existed —
  ownership moves into the linked root before any error is reported — but the
  Parser never recorded where they went, so a degraded consumer had to parse
  the sources a second time to see anything at all. What a caught failure
  gives you is the per-file view; what it does not give you is a trustworthy
  cross-file view, since that is what the error was about. See
  `docs/ast_usage_guide.rst`.

- **A line-comment run dedented to zero if any line omitted the space after
  `//`.** The conventional space was left to the dedent to remove, which works
  only while *every* line has it: one line written `//text` dropped the common
  prefix to zero and left every other line indented by one, which
  reStructuredText renders as a block quote. Realistic triggers are `//@…`,
  `//---` rules and ASCII diagrams. Relative indentation is unaffected.

- **`SymbolRefPath.path` raised `AttributeError`.** `list<SymbolRefPathElem>`
  is the only value-typed list in the schema, and the code generator had no
  case for that element shape: it emitted the iterator property and none of
  the helpers the property calls. Requires a `pyastbuilder` carrying the
  `PyExtListAccessorGen.visitTypeUserDef` fix.

- **Qualified fields lost their doc comment.** `rand int x;` and
  `static const int y = 1;` got nothing while an unqualified `int z;` in the
  same scope worked: the qualifier sat between the comment and the token the
  lookup was anchored on. The anchor is now the start of the declaration as
  written in source, for every wrapper rule — `attr_field`,
  `component_data_declaration`, `const_field_declaration`,
  `annotation_attr_field`, `activity_data_field`, `abstract_action_declaration`,
  `abstract_monitor_declaration`, and an annotation preceding a body item.
- **Block-comment text was unusable as reStructuredText.** Continuation `*`
  markers were only stripped when preceded by exactly one whitespace character,
  and the body was never dedented, so an indented comment arrived with `*`
  markers and full source indentation. Markers are now stripped at any depth and
  the body is dedented with relative indentation preserved.
- A block comment immediately adjacent to its declaration (`/** doc */int f;`)
  was silently dropped.
- A latent off-by-one in the block-comment line counter bounded the whitespace
  scan by the comment's length.

### Changed — output differs

These make line comments behave the way block comments already did, matching
Doxygen, Javadoc, and Python docstrings. They are fixes, but they change what
`getDocstring()` returns:

- **A blank line now breaks a line-comment association.** The rule was
  previously enforced for block comments only, so a line comment attached across
  any amount of blank space.
- **Separated line-comment blocks are no longer concatenated.** Every line
  comment preceding a declaration used to be joined into one string regardless
  of the blank lines between them; now only the adjacent block documents.
- **A comment on the same line as the preceding construct no longer leads the
  next declaration.** `int a; // bytes` followed by `int b;` used to document
  `b`. It now documents `a`, as a trailing comment.

  The exception is a comment that also *ends* on the following declaration's
  line, which is positionally leading it — this is what keeps
  `function void f(/** how many */ int len)` documenting `len`.
- **A leading space after `//` is stripped by the marker, not by the dedent.**
  `//     indented` still keeps four columns more than `// text`, so relative
  indentation is unchanged; what changes is that a run no longer depends on
  every line spelling the space the same way.
- **`getDocstring()` on a symbol scope returns the doc comment** rather than
  the empty string. Code that reached it through `getTarget()` still works;
  code that relied on the scope being empty does not.

### Build

Requires a `pyastbuilder` carrying two fixes, both of which fail silently
rather than loudly:

- `Linker.visitTypeUserDef`: the target of a user-defined type was resolved
  only on a class's *first* reference to it, so `ScopeChild`'s second and
  third `Location`-typed fields resolved to `None` and code generation died.
  Adding any of the fields above is impossible without it.
- `PyExtListAccessorGen.visitTypeUserDef`: a `list<value-struct>` field
  generated an iterator property whose helpers were never generated. See
  `SymbolRefPath.path` above.

### LRM annotation conformance

- **The LRM annotation form is supported and canonical.**
  `@desc_s {.desc = "text", .weight = 3}` — literal braces, dot-prefixed named
  parameters (PSS 3.1 Syntax 20). The standard defines no positional form.
- **The paren form is retained as a documented extension.**
  `@desc_s("text", weight = 3)` still parses and produces the same
  `AnnotationParam` structure. No deprecation warning: it predates the LRM
  syntax and offers a positional form the standard lacks.
- **Annotations may be applied to procedural statements**, which is what
  `code_doc` is for (PSS 3.1 21.6.1). LRM Example323 now parses verbatim.
- **`code_doc` is declared in `std_pkg`**, per Syntax 124.
- **Standalone annotations are distinguished from element annotations.** An
  annotation terminated by `;` attaches to a lexical location (LRM 7.13) and no
  longer leaks onto the next declaration.
- **An element annotation with no subsequent element in its scope is an error**,
  as LRM 7.13 requires. It was silently discarded.
- **`TOK_COMMENT_AT` (`//@`) removed.** The token had been unreachable since
  `SL_COMMENT` out-matched it, so `//@…` was already an ordinary comment and
  remains one. Nothing can regress.
