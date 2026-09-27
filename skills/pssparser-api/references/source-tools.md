# Source-level tools: tokens, CST, comments, annotations

The AST describes what the source *means*. It folds `((x))` to `x`, evaluates
`compile if` and drops the branch that lost, and gives most expressions only a
start position. A tool that must reproduce the source exactly (a formatter, a
highlighter, a comment extractor, a layout linter) should use `tokens` or
`cst` instead.

## Tokens: `pssparser.tokens`

`tokens.tokenize(src)` lexes without parsing and keeps every character:
`ts.text == src` holds for **any** input, including input that does not lex.
Whitespace and comments are tokens on their own channels.

```python
from pssparser import tokens

src = "component c { } // done\n"
ts = tokens.tokenize(src)
assert ts.text == src
for t in ts:
    if t.channel == tokens.CHANNEL_DEFAULT:
        print(t.line, t.col, t.type_name, repr(t.text))
    assert src[t.start:t.stop + 1] == t.text      # inclusive, code points
```

- Token fields: `text`, `type`, `type_name`, `channel`, `start`, `stop`
  (inclusive offsets), `line`, `col`, `index`, `is_comment`, `is_trivia`,
  `is_error`.
- Channels: `CHANNEL_DEFAULT` (what the parser sees), `CHANNEL_WS`,
  `CHANNEL_SL_COMMENT`, `CHANNEL_ML_COMMENT`, `CHANNEL_ERROR` (text no rule
  matched), and `CHANNEL_BOM`.
- Stream fields: `tokens`, `text`, `num_errors`, `valid_utf8`.
- Read files in **binary** mode (`open(path, "rb").read()`). Text mode
  translates newlines. Invalid UTF-8 raises `UnicodeDecodeError`.

Lexer facts that a source tool must allow for:

- A `//` comment token includes its trailing newline.
- Block comments do not nest.
- An unterminated `/*` is lexed as ordinary tokens, and `num_errors` stays 0.
- A triple-quoted string is one token, byte for byte.
- Line numbers count LF only. Under CR-only line endings every token is on
  line 1, so work in offsets.

## Concrete syntax tree: `pssparser.cst`

`cst.parse(src)` runs the grammar and stops. It builds no AST, does not
evaluate `compile if`, and resolves nothing.

```python
from pssparser import cst

tree = cst.parse("component c { action a { } }  // tail\n")
print(tree.root.rule_name, tree.num_syntax_errors)      # compilation_unit 0
for node in tree.root.walk():
    if node.rule_name == "action_declaration":
        print(node.text)
```

- Rule nodes have `rule_name`, `children`, `start_token` and `stop_token`
  (indices into `tree.tokens`), and `text`. Terminal nodes have `token_index`.
- Syntax errors are counted in `num_syntax_errors` and not raised. A tree and
  a full token stream come back either way, so a tool can return a file it
  could not parse unchanged.
- To find rule names, parse a sample and print
  `{n.rule_name for n in tree.root.walk()}`.

## Doc comments

Pass `Parser(collect_docstrings=True)`. Every declaration then returns its doc
comment from `getDocstring()` (an empty string when there is none), on both
the per-file AST and the linked symbol scopes.

```python
from pssparser import Parser

p = Parser(collect_docstrings=True)
p.parses([("m.pss", """
/** Transfer configuration.
 *  Used by every DMA action. */
struct cfg_s {
    /// Queue depth.
    rand bit[8] depth;
}
""")])
root = p.link()
cfg = p.user_units()[0].getChild(0)
print(repr(cfg.getDocstring()))
print(repr(cfg.getChild(0).getDocstring()))
print(repr(root.getChild(root.symtabAt("cfg_s")).getDocstring()))  # same text
```

- Every comment form counts by default: `//`, `///`, `/* */`, `/** */`. A doc
  comment attaches to the declaration immediately below it. A blank line
  breaks the association. Consecutive `//` lines merge into one block.
- `getDocRaw()` returns the untouched comment. `getDocForm()` says which form
  it was (compare against `pssparser.ast.DocCommentForm`).
- A doc comment above `rand`, `static const` and similar qualifiers documents
  the field.

## All comments

Pass `Parser(collect_comments=True)`, which implies `collect_docstrings`.
Every `ScopeChild` then has `getComments()`: `Comment` nodes with `getText()`
(markers stripped, indentation normalized), `getRaw()`, `getIs_block()`,
`getLocation()` and `getPlacement()`.

```python
from pssparser import Parser
import pssparser.ast as A

p = Parser(collect_comments=True)
p.parses([("m.pss", """
component pss_top {
    // Leading: documents the action.
    action run {
        rand bit[8] len;   // Trailing: on the same line.
    }
}
""")])
p.link()
run = p.user_units()[0].getChild(0).getChild(0)
for c in run.getComments():
    print(A.CommentPlacement(c.getPlacement()).name, c.getText())
for field in run.children():
    for c in field.getComments():
        print(A.CommentPlacement(c.getPlacement()).name, c.getText())
```

Placement is `CommentPlacement_Leading` (the lines directly above),
`CommentPlacement_Trailing` (the same line, after the node), or
`CommentPlacement_Orphan` (separated by a blank line). Comments at the end of a
block, after the last statement, go on the enclosing scope's
`getTrailing_comments()`.

## Annotations

Every `ScopeChild` has `getAnnotations()`. An `Annotation` has `getType()` (a
`TypeIdentifier`), `getParameters()`, and `getIs_standalone()`. Each
`AnnotationParam` has `getName()` (an `ExprRefName`, or `None` for a positional
parameter in pssparser's paren form) and `getValue()` (an `Expr`).

```python
from pssparser import Parser
import pssparser.ast as A

p = Parser()
p.parses([("m.pss", """
annotation desc_s { string desc; int weight; }
@desc_s {.desc = "Configures the IP", .weight = 3}
component pss_top { }
""")])
p.link()
comp = p.user_units()[0].getChild(1)
for a in comp.getAnnotations():
    print("@" + a.getType().getElem(0).getId().getId())
    for prm in a.getParameters():
        v = prm.getValue()
        value = v.getValue() if isinstance(v, (A.ExprString, A.ExprNumber)) else v
        print("  ", prm.getName().getId().getId(), "=", value)
```

## Inactive `compile if` branches

`p.inactive_regions()`, called after `link()`, returns the branches that
`compile if` left out. Each is an
`InactiveRegion(fileid, start_line, start_col, end_line, end_col)`, and both
ends are inclusive. A highlighter can grey these out. Names inside a region are
not in the AST and not in `refs.occurrences()`.

```python
from pssparser import Parser

p = Parser()
p.parses([("m.pss", """
component pss_top {
    compile if (1) { action a { } } else { action b { } }
}
""")])
p.link()
for r in p.inactive_regions():
    print(p.file_map[r.fileid], r.start_line, r.start_col, r.end_line, r.end_col)
```
