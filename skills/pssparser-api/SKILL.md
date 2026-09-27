---
name: pssparser-api
description: Use the pssparser Python API to build tools that read PSS (Portable Test and Stimulus Standard) models - `Parser.parse`/`parses`/`link`, walking the linked AST with `pssparser.ast` visitors, resolving references (`pssparser.refs`), tokens and CST, comments and doc comments, and the standard-library sources. Use when writing Python that consumes a PSS model (generators, documentation tools, analyzers, formatters). For lint rules, use `pssparser-checkers`.
---

# pssparser Python API

`pssparser` is a PSS 3.1 front end. From Python you parse source files, link
them into one model, then walk the linked AST. This skill covers tools that
*read* a model. To add a lint rule, use the `pssparser-checkers` skill. To only
check files for errors, run `pssparser FILE...` (the `pssparser` skill).

## 1. The lifecycle

```python
from pssparser import Parser, ParseException

src = """
import std_pkg::*;
component pss_top {
    action run { rand bit[8] len; }
}
"""

p = Parser()
try:
    p.parses([("top.pss", src)])   # or p.parse(["a.pss", "b.pss"])
    root = p.link()                # the linked RootSymbolScope
except ParseException as e:
    for m in e.markers:
        print(f'{m["file"]}:{m["line"]}:{m["col"]}: {m["severity"]}: {m["message"]}')
    raise

print(p.markers)       # [] -- warnings land here even when nothing raises
print(p.file_map)      # {1: 'top.pss'}
for unit in p.user_units():              # one GlobalScope per user file
    print(p.file_map[unit.getFileid()], unit.numChildren())
```

Rules:

- `parse()` takes paths, `parses()` takes `(name, text)` pairs. Both return
  `True` and **raise `ParseException`** on a syntax error. Pass every file of
  the model to one `Parser`, then call `link()` once.
- `link()` returns the root and raises `ParseException` on a semantic error.
- `markers` and `root` are **properties**, not methods. Each marker is a dict
  with `severity`, `message`, `file`, `line`, `col`, `extent`, `related`, and
  usually `code` (`"PSS020"`) and sometimes `fix`.
- Read `references/parser.md` for multi-file models, error recovery,
  `max_errors`, timings, and ownership rules.

## 2. Walking the AST

Subclass `pssparser.ast.VisitorBase`. Override `visit<Class>` and call
`super()` to keep descending. Visit `p.user_units()`, not `root`: the root also
holds the standard library, so a visitor started there reports its types too.

```python
from pssparser import Parser
import pssparser.ast as A

p = Parser()
p.parses([("m.pss", """
component pss_top {
    action run {
        rand bit[8] len;
        int count;
        constraint { len > 4; }
    }
}
""")])
p.link()

class ListFields(A.VisitorBase):
    def visitAction(self, i):
        print("action", i.getName().getId())
        super().visitAction(i)

    def visitField(self, i):
        rand = bool(i.getAttr() & A.FieldAttr.Rand)
        print("  field", i.getName().getId(), type(i.getType()).__name__,
              "rand" if rand else "")
        super().visitField(i)

    def visitExprBin(self, i):
        print("  constraint op", A.ExprBinOp(i.getOp()).name)
        super().visitExprBin(i)

for unit in p.user_units():
    unit.accept(ListFields())
```

Also iterate directly: every `Scope` has `children()`, `numChildren()` and
`getChild(i)`. Names are `ExprId` nodes, so a declaration's name is
`node.getName().getId()`. Read `references/ast.md` for the node taxonomy, the
linked symbol tree (`symtabAt`), locations, and enum pitfalls.

## 3. What does this name refer to?

Do not re-implement name lookup. Use `pssparser.refs.occurrences()`: it
reports every identifier in the user files with the declaration the linker
bound it to.

```python
from pssparser import Parser, refs

p = Parser()
p.parses([("m.pss", """
struct cfg_s { rand bit[8] depth; }
component pss_top {
    action run { rand cfg_s cfg; constraint { cfg.depth < 10; } }
}
""")])
p.link()

for o in refs.occurrences(p):
    if not o.is_declaration:
        print(f"{o.line}:{o.col} {o.text} -> {o.resolution.value}",
              type(o.decl).__name__, o.decl_location)
```

Read `references/refs.md` for grouping by declaration, mapping an AST node to
its declaration, and the `Resolution` values.

## 4. Gotchas

- **Imports are explicit.** The core library packages (`std_pkg`,
  `executor_pkg`, `addr_reg_pkg`, `sync_pkg`) are not visible unless the
  source imports them: `import std_pkg::*;`. Without it, `message(...)` is
  "unknown identifier". The error message names the package to import.
- **A failed link still gives a per-file view.** After a caught
  `ParseException` from `link()`, `root`, `user_units()` and `file_map` are
  populated, but cross-file facts (resolved types, merged `extend`s) are not
  trustworthy.
- **Never keep a `GlobalScope` across `link()`.** The linker takes ownership
  of the units. A wrapper held from before `link()` crashes the interpreter.
  Reach units through `p.user_units()` or `root.getUnit(i)` afterwards.
- **Check `symtabHas(name)` before `symtabAt(name)`.** `symtabAt` on a missing
  name crashes the process instead of raising.
- **Compare nodes with `==`, never `is` or `id()`.** Every access creates a
  new wrapper object; wrappers compare and hash by the underlying node.
- **Compare enums against the runtime members** (`A.FieldAttr.Rand`,
  `A.ExprBinOp.BinOp_Gt`). Some getters return a plain `int`, and the
  `auto()` values printed in `ast.pyi` do not match the runtime values.
- **The AST is not the source.** It folds parentheses and drops the losing
  branch of `compile if`. For formatters and highlighters, use `tokens` and
  `cst` (`references/source-tools.md`).

## 5. Map of references/

| File | Read it when you need to |
|---|---|
| `references/parser.md` | load multi-file models, handle errors, recover from a failed link, understand ownership |
| `references/ast.md` | find the node class for a construct, navigate the linked symbol tree, read locations |
| `references/refs.md` | resolve references, find all uses of a declaration, go-to-definition, rename |
| `references/source-tools.md` | tokens, concrete syntax trees, comments, doc comments, annotations, `compile if` regions |
| `references/stdlib.md` | read the core-library `.pss` sources, or know what each package declares |
| `references/other-bindings.md` | use pssparser from C++ or from TypeScript / WebAssembly |

Exact method signatures live in the `ast.pyi` stub installed next to the
package. Find it with:

```python
import os, pssparser
print(os.path.join(os.path.dirname(pssparser.__file__), "ast.pyi"))
```
