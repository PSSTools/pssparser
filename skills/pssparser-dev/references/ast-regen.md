# Changing the AST

The AST is generated. `ast/*.yaml` is the schema; `scripts/gen_ast.py` runs
pyastbuilder (`packages/pyastbuilder`) over it and writes, under
`build/pssparser_ast/`:

- C++ interfaces and implementations → installed to `build/include/pssp/ast/`;
- `ext/ast.pyx`, `ast.pxd`, `ast_decl.pxd`, `ast.pyi`, `PyBaseVisitor.{h,cpp}`
  → copied into `python/` and `python/pssparser/` by `setup.py build_ext`.

The generated files under `python/` are checked in. Commit them with the yaml
change.

## Adding or changing a class or field

```bash
# 1. edit ast/<file>.yaml
python setup.py build_ext --inplace     # regenerates, rebuilds, copies bindings
python scripts/gen_node_kind.py         # NodeKind.h from the new headers
python setup.py build_ext --inplace     # rebuild with the new NodeKind.h
PYTHONPATH=python python -m pytest tests/python -q
```

NodeKind is generated from the *built* headers, so the order is build →
generate → build. `tests/python/test_node_kind_generated.py` fails until you do
it (`scripts/gen_node_kind.py --check` is the same check).

### When the generator does not re-run

CMake re-runs the generator when an `ast/*.yaml` file or `gen_ast.py`
changes. If the generated headers still look stale (a missing accessor on a
generated class, reported as if the yaml were wrong), force it. `AST-stamp` is
a directory of stamp files, and `AST-download` is the one that gates
`gen_ast.py`:

```bash
rm -f build/pssparser_ast/src/AST-stamp/AST-{done,build,download}
python setup.py build_ext --inplace
```

Removing only `AST-done`/`AST-build` re-links without regenerating.

## Removing a class

`gen_ast.py` writes files but never deletes them, so the orphaned header keeps
compiling and fails with "`IVisitor` has no member named `visitX`", pointing at
a generated file. Clean the generated tree and re-configure (the stamp
directory lives inside it, so ninja otherwise fails with "missing and no known
rule to make it"):

```bash
rm -rf build/pssparser_ast/src build/pssparser_ast/ext
cmake -B build -S .
python setup.py build_ext --inplace
python scripts/gen_node_kind.py && python setup.py build_ext --inplace
```

Then check `scripts/check_ast_inventory.py` (run by
`tests/python/test_ast_inventory.py`) and remove any stale entry from
`scripts/ast_inventory_allowlist.txt`.

## Inventory checks

`scripts/check_ast_inventory.py` keeps `ast/*.yaml` and the grammar a truthful
map of what the parser produces. Among others, it reports:

- a class the builder never constructs (a visitor for it compiles and never
  fires);
- a class whose children would be registered into the *enclosing* symbol
  scope by `TaskBuildSymbolTree`.

A new class must be produced by `AstBuilderInt` or be an abstract base (named
as another class's `super`). Exemptions go in
`scripts/ast_inventory_allowlist.txt`, each with a reason.

## Generator facts that bite

- A member named `numChildren` generates an accessor `getChild(i)`: the
  generator strips `ren` before a trailing `s`. `getChildren()` takes no index.
  A reflective walk that guesses the name wrong stops at the first scope with no
  error.
- `float` and `double` are valid member types.
- pyastbuilder's own test suite is not usable. Generator behaviour is covered
  from here: `tests/python/test_astbuilder_codegen.py` (asserts on emitted
  source) and `tests/python/test_generated_bindings.py` (through a parsed AST).
  Add there when you change the generator.
- Some pyastbuilder sources are CRLF (`gen_cpp.py`, `parser.py`,
  `type_scalar.py`). Round-tripping one through `git show > file` converts it to
  LF and produces a whole-file diff.

## Compiler-injected nodes

A node the builder injects has `lineno == -1`. Injected nodes change the child
indices of their scope without appearing in any source, which can mask
index-based resolution bugs. When removing a synthetic node breaks unrelated
things, suspect index-based resolution rather than the removal; and treat a
long-lived injected node that no diagnostic mentions as a candidate mask.

## Python-side AST lifetime

Every accessor returns a *fresh* Python wrapper. Never key a visited set on
`id(node)`. Keep both the `Parser` and the linked root alive while any node is
in use; see "AST lifetime" in `testing.md`.
