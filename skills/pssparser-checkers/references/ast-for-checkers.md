# The AST for lint rules

The 20% of `pssparser.ast` that most lint rules need. For everything else
(expressions, activities in depth, templates, reference resolution) use the
`pssparser-api` skill. Exact method signatures are in the type stub that ships
with pssparser:

```bash
python -c "import os, pssparser; print(os.path.join(os.path.dirname(pssparser.__file__), 'ast.pyi'))"
```

## What to walk

| Start from | Contains | Use for |
|---|---|---|
| `context.global_scopes` | One `GlobalScope` per user file, declarations as written. Core library excluded. | Almost every rule: names, structure, style. |
| `context.root` | The linked `RootSymbolScope`: every file **and** the core library, with symbol tables. | Cross-file questions, with `pssparser.refs` (below). Do not visit it for per-declaration rules: you would also lint the core library, and some nodes are reached twice. |

Map a unit to its path with `context.file_map[unit.getFileid()]`.

## Two ways to walk

**Visitor** (recommended): subclass `pssparser.ast.VisitorBase`, override
`visit<NodeClass>` for the nodes you care about, and call the `super()`
method to keep descending. Start it with `unit.accept(visitor)`.

**Direct iteration**: every `Scope` has `children()`. Use it when only the
top level of a scope matters (e.g. "fields directly in this action").

This script shows both, on a model built in memory. It runs as-is, and a
checker does the same thing inside `check()` with `context.global_scopes`:

```python
import pssparser.ast as pss_ast
from pssparser import Parser

SRC = """
package util_pkg {
    enum mode_e { FAST, SLOW }
}
component pss_top {
    import util_pkg::*;
    buffer data_b { rand bit[8] v; }
    struct cfg_s { rand mode_e mode; }
    action write_a {
        output data_b out_d;
        rand bit[32] addr;
        constraint addr_c { addr < 256; }
        exec body { }
    }
    action top_a {
        write_a w;
        activity { w; }
    }
}
"""


class Lister(pss_ast.VisitorBase):
    def visitAction(self, a):
        print("action", a.getName().getId())
        super().visitAction(a)

    def visitStruct(self, s):
        # buffer/stream/state/resource are Structs with a StructKind.
        print(pss_ast.StructKind(s.getKind()).name.lower(), s.getName().getId())
        super().visitStruct(s)

    def visitField(self, f):
        loc = f.getName().getLocation()
        if loc.lineno < 1:
            return                      # synthetic, e.g. an action's `comp`
        rand = bool(f.getAttr() & pss_ast.FieldAttr.Rand)
        owner = f.getParent().getName().getId()
        print(f"  field {owner}.{f.getName().getId()} rand={rand} "
              f"at {loc.lineno}:{loc.linepos}")
        super().visitField(f)


p = Parser()
p.parses([("model.pss", SRC)])
p.link()
for unit in p.user_units():         # what context.global_scopes holds
    unit.accept(Lister())
    for child in unit.children():   # direct iteration, top level only
        print("top-level:", type(child).__name__)
```

## Node classes a lint rule usually needs

Check with `isinstance(node, pss_ast.<Class>)`, or override `visit<Class>`.

| Class | PSS construct | Useful getters |
|---|---|---|
| `GlobalScope` | one source file | `children()`, `getFileid()` |
| `PackageScope` | `package p { }` | `numId()` / `getId(i)` (name segments) |
| `Component` | `component c { }` | `getName()`, `getSuper_t()`, `children()` |
| `Action` | `action a { }` | `getName()`, `getSuper_t()`, `children()` |
| `Struct` | `struct`, `buffer`, `stream`, `state`, `resource` | `getKind()` (a `StructKind`), `getName()`, `getSuper_t()` |
| `Field` | a data field or handle (`rand bit[8] x;`, `write_a w;`) | `getName()`, `getType()`, `getAttr()` (`FieldAttr` bit flags), `getInit()` |
| `FieldRef` | an action's `input`/`output`/`lock`/`share` | `getName()` |
| `EnumDecl` | `enum e { }` | `getName()`, `items()` (the enumerators) |
| `FunctionDefinition` | `function ... { }` | `getProto().getName()` |
| `ConstraintBlock` | `constraint c { }` | `getName()` |
| `ActivityDecl` | `activity { }` | children are activity statements |
| `ExecBlock` | `exec body { }` | `getKind()` (an `ExecKind`) |

`Action`, `Component`, and `Struct` share the base `TypeScope`. Everything
with a body you can descend into (`PackageScope`, the type scopes,
`ExecBlock`) is a `Scope`; `Field` and `EnumDecl` are not. Test against a base
class when a rule applies to all of its subclasses.

## Names and locations

- `node.getName()` returns an `ExprId`; `.getId()` is the text.
- `getLocation()` returns a `Location` with `fileid`, `lineno`, `linepos`
  (1-based column), and `extent`. Report the **name's** location, not the
  declaration's, and pass `extent=len(name)`.
- `lineno < 1` marks a node the linker synthesized. Skip it; there is no
  source to point at.
- `getParent()` returns the enclosing scope, which gives "field X of action Y".

## Things not available in a checker

- **Doc comments.** The CLI parses without collecting them, so
  `getDocstring()` is empty in `check()`. A rule about documentation needs the
  Python API instead (`Parser(collect_docstrings=True)`; see `pssparser-api`).
- **Anything after an error.** Checkers run only on a model that parsed and
  linked without errors.

## Resolved references: `pssparser.refs`

For "is this declaration used?", "what does this name refer to?", or "which
declaration does this override?", do not re-resolve names yourself. Use
`pssparser.refs.occurrences(context.root)`: every identifier in the user files,
with the declaration it binds to.

```python
from collections import Counter

import pssparser.ast as pss_ast
from pssparser import Parser
from pssparser.refs import occurrences

SRC = """
component pss_top {
    action a {
        rand bit[8] used;
        rand bit[8] unused;
        constraint { used < 10; }
    }
}
"""
p = Parser()
p.parses([("model.pss", SRC)])
root = p.link()                      # in a checker: context.root

occs = occurrences(root)
uses = Counter(o.decl for o in occs if not o.is_declaration and o.decl is not None)
for o in occs:
    if o.is_declaration and isinstance(o.decl, pss_ast.Field) and uses[o.decl] == 0:
        print(f"{o.line}:{o.col}: field '{o.text}' is never referenced")
```

Each occurrence has `fileid`, `line`, `col`, `extent`, `text`,
`is_declaration`, `decl`, `decl_location`, `resolution`, and `base_decl`.
Compare declarations with `==` or use them as dict keys; never with `id()`.
`context.root` is `None` under `--syntax-only`, so a checker that uses `refs`
must leave `runs_without_link` at `False`. More: the `pssparser-api` skill.
