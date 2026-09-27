# The Parser lifecycle

`pssparser.Parser` turns PSS sources into one linked model. There are three
steps: parse every file, link once, then read the result.

## Constructing

```python no-check
Parser(collect_docstrings=False, collect_comments=False)
```

Both flags default off, because collection costs time. Turn on
`collect_docstrings` for documentation tools, and `collect_comments` for tools
that must carry every comment across (it implies `collect_docstrings`). See
`source-tools.md`.

## Parsing

| Call | Input | Returns |
|---|---|---|
| `p.parse(paths)` | a list of file paths | `True`, or raises `ParseException` |
| `p.parses(pairs)` | a list of `(name, text)` pairs | `True`, or raises `ParseException` |

Call either one as many times as you like before `link()`. Each file becomes
one compilation unit (a `GlobalScope`), numbered from fileid 1 in the order
given. The order does not matter for name resolution: a file may use a package
that a later file declares.

```python
import os, tempfile
from pssparser import Parser

d = tempfile.mkdtemp()
with open(os.path.join(d, "types.pss"), "w") as f:
    f.write("package types_pkg { struct cfg_s { int depth; } }\n")
with open(os.path.join(d, "top.pss"), "w") as f:
    f.write("import types_pkg::*;\n"
            "component pss_top { action run { cfg_s cfg; } }\n")

p = Parser()
p.parse([os.path.join(d, "top.pss")])     # uses types_pkg ...
p.parse([os.path.join(d, "types.pss")])   # ... declared here, later
root = p.link()
print(sorted(os.path.basename(v) for v in p.file_map.values()))
```

A syntax error stops at the file that contains it: `parse()` raises before it
adds that file, so do not call `link()` after a parse error.

## Linking

`root = p.link()` resolves every name across all the files and returns the
`RootSymbolScope`. It raises `ParseException` if any error was reported. Call
it once per `Parser`. For a new model, make a new `Parser`.

`root.numUnits()` counts every unit, including two you did not write: fileid
`-1` holds built-ins and fileid `0` holds the standard library. Use
`p.user_units()` to get only your files, in parse order.

## Markers

`p.markers` (a property) is a list of dicts, sorted by `(file, line, col)`:

| Key | Meaning |
|---|---|
| `severity` | `"error"`, `"warning"`, `"info"` or `"hint"` |
| `message` | the text |
| `file`, `line`, `col` | 1-based position |
| `extent` | length of the primary span in characters (0 if unknown) |
| `related` | list of `{file, line, col, label}` secondary locations |
| `code` | stable ID such as `"PSS020"`; absent when none is assigned yet |
| `fix` | `{file, line, col, extent, replacement}`: a machine-applicable repair; absent when there is none |

`ParseException.markers` carries the same list. Its `str()` is a formatted
summary of the errors.

```python
from pssparser import Parser, ParseException

p = Parser()
try:
    p.parses([("bad.pss", "component pss_top { action a { rand bit[8] x } }")])
except ParseException as e:
    m = e.markers[0]
    print(m.get("code"), m["line"], m["col"], m["message"])
    assert e.markers == p.markers
```

To explain a marker ID, run `pssparser --describe PSS020`.

## Recovering from a failed link

A caught `ParseException` from `link()` still leaves the model in place:
`p.root`, `p.user_units()` and `p.file_map` are all set. You get the
*per-file* view, meaning every declaration, its location, and its doc comment.
The *cross-file* view is not reliable: a type reference may be unresolved, and
`extend` bodies may not be merged. Use this to document or index a model that
has one bad reference. Do not use it to generate code.

```python
from pssparser import Parser, ParseException

p = Parser()
p.parses([("u.pss", "component pss_top { action a { undefined_t f; } }")])
try:
    p.link()
except ParseException:
    for m in p.markers:
        print(m["file"], m["line"], m["message"])
    unit = p.user_units()[0]
    print("still walkable:", unit.numChildren(), "top-level declarations")
```

`pssparser.refs.occurrences(p)` also works after a failed link. The names that
the error left unbound are reported as `unresolved`.

## Ownership

- `link()` moves ownership of every `GlobalScope` into the root. Never hold a
  unit object from before `link()` and use it afterwards: it becomes a second
  owner and crashes the interpreter. Get the units again through
  `p.user_units()` or `root.getUnit(i)`.
- The root returned by `link()` keeps the tree alive, and so do the objects
  that `refs.occurrences()` returns. Keep one of them referenced for as long
  as you use nodes from the tree.

## Limits and timings

- `p.set_max_errors(n)` stops collecting after `n` errors. `0` means
  unlimited, which is the default for library use. The CLI defaults to 20.
- `p.timings_ns` (a property) maps phase names (`"stdlib"`,
  `"parse (incl. read)"`, ...) to nanoseconds.
- `p.enable_profiling(True)` before parsing enables ANTLR profiling, and
  `p.get_profile_info()` returns the result. This is for grammar work only.

## Reading the linked tree without Python

`pssparser --dump-ast OUT file.pss` writes the linked AST as JSON. Use it to
look at a model's shape while you design a Python walker.
