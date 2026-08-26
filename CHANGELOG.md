# Changelog

Version numbers are `<PSS major>.<PSS minor>.<patch>`: the first two components
name the **revision of the PSS LRM this parser targets**, not the parser's own
feature level. A release that adds parser capability without moving to a new LRM
revision advances only the patch component.

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
