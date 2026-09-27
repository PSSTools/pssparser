# The AST

`pssparser.ast` is a generated Cython binding with about 250 node classes.
This file is a map of them. The `ast.pyi` stub installed next to the package
has the exact getters for each class, and its docstrings show the PSS each
node comes from. Search the stub before you guess a method name:

```python
import os, pssparser
stub = os.path.join(os.path.dirname(pssparser.__file__), "ast.pyi")
with open(stub) as f:
    text = f.read()
start = text.index("class Field(")
print(text[start:start + 200])
```

## Two trees

After `link()`, one root holds two views of the model:

| View | Entry point | Nodes | Use it for |
|---|---|---|---|
| Per-file AST | `p.user_units()` gives one `GlobalScope` per file | declarations as written: `PackageScope`, `Component`, `Action`, `Field`, ... | anything tied to source: generators, docs, analyzers |
| Linked symbol tree | `root` (`RootSymbolScope`) | `SymbolScope`, `SymbolTypeScope`, ... with name tables | "what is `pss_top::run`?"; the merged view of a type across files and `extend`s |

A `SymbolTypeScope` wraps a type declaration. Its `getTarget()` returns the
declaration (`Component`, `Action`, `Struct`, ...).

```python
from pssparser import Parser

p = Parser(collect_docstrings=True)
p.parses([("m.pss", """
package cfg_pkg {
    /** Transfer configuration. */
    struct cfg_s { rand bit[8] depth; }
}
import cfg_pkg::*;
component pss_top { action run { rand cfg_s cfg; } }
""")])
root = p.link()

top = root.getChild(root.symtabAt("pss_top"))        # SymbolTypeScope
run = top.getChild(top.symtabAt("run"))
print(type(run.getTarget()).__name__)                # Action

pkg = root.getChild(root.symtabAt("cfg_pkg"))
if pkg.symtabHas("cfg_s"):          # always check: symtabAt on a miss crashes
    cfg = pkg.getChild(pkg.symtabAt("cfg_s"))
    print(cfg.getName(), "-", cfg.getDocstring())
```

Symbol-scope names are plain strings (`cfg.getName()`). Declaration names are
`ExprId` nodes (`decl.getName().getId()`).

## Walking

- Visitor: subclass `pssparser.ast.VisitorBase`, override
  `visit<ClassName>(self, i)`, and call `super().visit<ClassName>(i)` to keep
  descending. Start it with `node.accept(visitor)`. Every concrete class has a
  `visit` method.
- Direct iteration: anything with children (`Scope`, and the symbol scopes
  such as `ActivityDecl` and `ExecBlock`) has `children()`, `numChildren()`
  and `getChild(i)`. Other list fields follow the same pattern:
  `items()`/`getItems()`/`getItem(i)`/`numItems()`.
- `node.getParent()` goes up.

```python
from pssparser import Parser
import pssparser.ast as A

p = Parser()
p.parses([("m.pss", """
package p1 {
    enum mode_e { A, B }
    struct s { int x; }
}
import p1::*;
component pss_top {
    function int f(int a) { return a + 1; }
    action run { rand mode_e m; activity { do run2; } exec body { int y = 1; } }
    action run2 { }
}
""")])
p.link()

def label(n):
    if isinstance(n, A.PackageScope):
        return "::".join(n.getId(i).getId() for i in range(n.numId()))
    if isinstance(n, A.FunctionDefinition):
        return n.getProto().getName().getId()
    name = getattr(n, "getName", None)
    return name().getId() if name and isinstance(name(), A.ExprId) else ""

def dump(n, depth=0):
    loc = n.getLocation()
    print(f"{'  ' * depth}{type(n).__name__} {label(n)} @{loc.lineno}:{loc.linepos}")
    if hasattr(n, "children"):
        for c in n.children():
            dump(c, depth + 1)

for unit in p.user_units():
    dump(unit)
```

Note the `FieldCompRef comp` child at `-1:-1` in every action. That is the
implicit `comp` handle. It has no source location. Skip nodes whose
`getLocation().lineno` is not positive when you report positions.

## Taxonomy

Base classes first, then the main families. `isinstance` works on every level.

| Base | Subclasses you will meet |
|---|---|
| `ScopeChild` | everything in a scope; carries location, doc comment, comments, annotations |
| `Scope` | `GlobalScope` (a file), `PackageScope`, `ExtendType`, `NamedScope` |
| `TypeScope` (a `NamedScope`) | `Component`, `Action`, `Struct` (also buffer/stream/state/resource: see `getKind()` against `A.StructKind`), `Monitor`, `CovergroupType`, `AnnotationDecl` |
| `NamedScopeChild` | `Field`, `FieldCompRef`, `FieldRef`, `FieldPool`, `FieldClaim`, `ActionHandleField`, `EnumDecl`, `EnumItem`, `FunctionPrototype`, `Covergroup*` |
| functions | `FunctionDefinition` (`getProto()`, `getBody()`), `FunctionPrototype`, `FunctionImport*` |
| `DataType` | `DataTypeInt`, `DataTypeBool`, `DataTypeString`, `DataTypeEnum`, `DataTypeChandle`, `DataTypeFloat`, `DataTypeRef`, `DataTypeUserDefined` (`getType_id()` gives a `TypeIdentifier`) |
| `ConstraintStmt` | `ConstraintBlock`, `ConstraintStmtExpr`, `ConstraintStmtIf`, `ConstraintStmtForeach`, `ConstraintStmtForall`, `ConstraintStmtImplication`, `ConstraintStmtDist`, `ConstraintStmtUnique`, `ConstraintStmtSoft`, `ConstraintStmtDefault*` |
| activities | `ActivityDecl`, then `ActivitySequence`, `ActivityParallel`, `ActivitySchedule`, `ActivitySelect`, `ActivityIfElse`, `ActivityMatch`, `ActivityRepeatCount`, `ActivityRepeatWhile`, `ActivityForeach`, `ActivityReplicate`, `ActivityActionTypeTraversal` (`do T`), `ActivityActionHandleTraversal` (`a;`), `ActivityBindStmt`, `ActivityConstraint` |
| exec / procedural | `ExecBlock` (`getKind()` against `A.ExecKind`), `ProceduralStmtAssignment`, `ProceduralStmtDataDeclaration`, `ProceduralStmtIfElse`, `ProceduralStmtRepeat`, `ProceduralStmtForeach`, `ProceduralStmtWhile`, `ProceduralStmtMatch`, `ProceduralStmtReturn`, `ProceduralStmtExpr` |
| `Expr` | `ExprBin` (`getOp()` against `A.ExprBinOp`), `ExprUnary`, `ExprCond`, `ExprIn`, `ExprCast`, `ExprBitSlice`, `ExprId`, `ExprNumber` (`ExprSignedNumber`/`ExprUnsignedNumber`; `getValue()`, `getImage()`), `ExprBool`, `ExprString`, `ExprTemplateString`, `ExprNull`, `ExprAggr*`, `ExprRefPath*` (member and static paths), `ExprMemberCall`, `TypeIdentifier` |
| monitors | `Monitor`, `MonitorActivity*` |
| templates | `TemplateParamDecl` subclasses on generic types (`getParams()`), `TemplateParamValue` subclasses on uses |
| other | `PackageImportStmt`, `Annotation`, `AnnotationParam`, `Comment`, `ComponentBind`, `OverrideStmt`, `CompileCond` |
| linked tree | `RootSymbolScope`, `SymbolScope`, `SymbolTypeScope`, `SymbolFunctionScope`, `SymbolEnumScope`, `SymbolExtendScope` |

To find the class for a construct, parse a tiny example and print
`type(node).__name__`, or search `ast.pyi` for the PSS keyword: the docstrings
contain "PSS Example" snippets.

## Locations

`node.getLocation()` returns a `Location` with `fileid`, `lineno`, and
`linepos` (1-based column), plus `extent`. Map `fileid` to a path with
`p.file_map[loc.fileid]`. Fileid `0` is the standard library and `-1` is
built-in. Declarations also have `getEndLocation()`.

Many expressions carry only a start position, and the AST keeps no text. For
exact source spans, use `pssparser.tokens` / `pssparser.cst`
(`source-tools.md`).

## Enums and flags

- Compare against runtime members: `A.FieldAttr.Rand`, `A.ExprBinOp.BinOp_Gt`,
  `A.ExecKind.ExecKind_Body`. Several getters return a plain `int`, so wrap
  the value to print it (`A.ExprBinOp(i.getOp()).name`).
- `FieldAttr` is a bit set: test with `field.getAttr() & A.FieldAttr.Rand`.
- Do not copy numeric values from `ast.pyi`. The stub writes each enum with
  `auto()`, which does not match the runtime values (for example,
  `CommentPlacement_Leading` is 0 at run time, and `FieldAttr` values are
  powers of two).

## Identity

Every getter returns a new wrapper object. Compare nodes with `==` and use them
as dict keys, since they hash by the underlying node. `is` and `id()` do not
work for this.

## Resolving a reference

`TypeIdentifier.getTarget()` and `ExprRefPath.getTarget()` return a
`SymbolRefPath`, which is an index path into the linked tree and is awkward to
follow by hand. Use `pssparser.refs.occurrences()` instead. It maps each name
(`ExprId`) to its declaration (`refs.md`).
