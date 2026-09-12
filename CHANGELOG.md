# Changelog

Version numbers are `<PSS major>.<PSS minor>.<patch>`: the first two components
name the **revision of the PSS LRM this parser targets**, not the parser's own
feature level. A release that adds parser capability without moving to a new LRM
revision advances only the patch component.

## Unreleased

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
