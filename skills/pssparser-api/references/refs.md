# Resolving references: `pssparser.refs`

`refs.occurrences(p)` lists every identifier in the user files, together with
the declaration the linker bound it to. It is the building block for
go-to-definition, find-references, rename, cross-reference docs, and "which
type is this field?". It reports what the linker decided. It never re-resolves
a name, so do not write your own lookup.

```python no-check
from pssparser import refs
occs = refs.occurrences(p)      # p: a Parser after link(), or the linked root
```

It works after a failed `link()` as well. Names that the error left unbound
come back `unresolved`.

## `Occurrence` fields

| Field | Meaning |
|---|---|
| `fileid`, `line`, `col`, `extent` | where the name is (1-based); `o.location` bundles them |
| `text` | the identifier as written |
| `is_declaration` | `True` where this is the name being declared |
| `decl` | the declaring node as its most-derived class (`Field`, `Action`, `Struct`, `FunctionPrototype`, ...), or `None` |
| `decl_location` | `refs.Location(fileid, line, col, extent)` of the declaration's name, or `None` |
| `resolution` | a `refs.Resolution`; see below |
| `base_decl` | for an override or shadowing declaration: the one it overrides, one level up |
| `node` | the `ExprId` node itself |

Results are sorted by `(fileid, line, col)`. Names that have no source
location, such as the implicit `pss_top` and `comp`, are not reported.

## `Resolution`

A closed set. If you meet a value you do not know, fail rather than guess.
Members compare equal to their strings (`Resolution.USER == "user"`).

| Value | Meaning |
|---|---|
| `user` | bound to a declaration in a user file |
| `library` | bound to a standard-library declaration (fileid 0) |
| `builtin` | a built-in with no source declaration: `comp`, `this`, `push_back`, `list`, ... |
| `unresolved` | not bound; `decl` is `None` |
| `dependent` | inside a generic template body, where the meaning depends on a template parameter |

## Find all uses of each declaration

`decl` is the same node for every occurrence of one declaration, so you can
group by it with `==` or as a dict key.

```python
from collections import defaultdict
from pssparser import Parser, refs

p = Parser()
p.parses([("m.pss", """
struct cfg_s { rand bit[8] depth; }
component pss_top {
    action run {
        rand cfg_s cfg;
        constraint { cfg.depth < 10; cfg.depth > 2; }
    }
}
""")])
p.link()

uses = defaultdict(list)
for o in refs.occurrences(p):
    if o.decl is not None and not o.is_declaration:
        uses[o.decl].append(f"{o.line}:{o.col}")

for decl, where in uses.items():
    print(type(decl).__name__, decl.getName().getId(), where)
```

## From an AST node to its declaration

Walking the AST gives you names as `ExprId` nodes. For example, a field's type
is `field.getType().getType_id().getElem(0).getId()`. Index the occurrences by
`node` and look the name up:

```python
from pssparser import Parser, refs
import pssparser.ast as A

p = Parser()
p.parses([("m.pss", """
package cfg_pkg { struct cfg_s { rand bit[8] depth; } }
import cfg_pkg::*;
component pss_top { action run { rand cfg_s cfg; } }
""")])
p.link()

by_node = {o.node: o for o in refs.occurrences(p)}

class FieldTypes(A.VisitorBase):
    def visitField(self, i):
        t = i.getType()
        if isinstance(t, A.DataTypeUserDefined):
            ti = t.getType_id()
            last = ti.getElem(ti.numElems() - 1).getId()   # cfg_s in a::b::cfg_s
            o = by_node[last]
            print(i.getName().getId(), "->", type(o.decl).__name__,
                  o.decl.getName().getId(), p.file_map.get(o.decl_location.fileid))
        super().visitField(i)

for u in p.user_units():
    u.accept(FieldTypes())
```

Each element of a qualified name (`cfg_pkg::cfg_s`) and of a member path
(`cfg.depth`) is its own occurrence.

## Go-to-definition by position

```python no-check
def definition_at(p, fileid, line, col):
    for o in refs.occurrences(p):
        if o.fileid == fileid and o.line == line and o.col <= col < o.col + o.extent:
            return o.decl_location
    return None
```

Build the occurrence list once per link and reuse it. The call walks the whole
model.

## Templates and gaps

- A member reached through a specialization (`t<8> a; ... a.depth`) binds to
  the member in the generic template, so every use groups under its single
  source declaration.
- Some kinds of name are not bound by the linker yet: activity labels
  (`L.a`), `bind` operands, and names inside covergroup bodies. They are
  reported as `unresolved` even in legal code. Treat `unresolved` in a model
  that linked cleanly as "unknown", not as an error.
- Names inside the inactive branch of a `compile if` are not in the AST and are
  not reported. `p.inactive_regions()` gives those branches
  (`source-tools.md`).
