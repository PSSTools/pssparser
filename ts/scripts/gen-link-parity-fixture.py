#!/usr/bin/env python3
"""Record what the native parser's `link()` produces, as a fixture for the TS tests.

    packages/python/bin/python ts/scripts/gen-link-parity-fixture.py \\
        -o ts/test/fixtures/link-parity.json

Third in the series after gen-parity-fixture.py (markers) and
gen-ast-parity-fixture.py (per-unit AST), and there for the same reason: an
expectation written by hand only shows that the WASM core agrees with what the
author believed while reading the same source twice.

`link()` needs its own fixture rather than an extension of the AST one because
it produces a *different tree*.  The per-unit fixture walks each `GlobalScope`
as parsed; the linked root is a `RootSymbolScope` holding a merged symbol tree
built by `TaskBuildSymbolTree`, with the units hanging off it as owned children.
Nothing about the first tree constrains the second.

Three things are recorded, and the third is the one that motivated this file:

1. **The units** the root ended up owning, by fileid and in order.  This is what
   `Parser.userUnits()` filters, and a unit lost or reordered during linking
   would show up nowhere else.
2. **The declaration spine** of the linked root -- the same `ASTUtils.walkScope`
   transliteration the per-unit fixture uses.  Full for the inline cases; for
   the corpus, a length and a digest, because the merged tree includes the whole
   standard library and cannot be elided the way the per-unit fixture elides
   unit 0.  A corpus mismatch says only *that* the spine differs; the inline
   cases are what make a difference diagnosable.
3. **Reference resolution.**  The schema has exactly two non-owning *list*
   fields -- `SymbolImportSpec.imports` (`list<P<PackageImportStmt>>`) and
   `SymbolFunctionScope.prototypes` (`list<P<FunctionPrototype>>`) -- and the
   serialiser drops an entry whose target is not in the buffer, because the
   generated TypeScript element type is non-nullable and a hole is not a state
   the C++ AST can represent.  Serialising one unit at a time, that loss was
   real and unavoidable.  Serialising the linked root, the targets are in the
   same buffer, and these counts are how that claim is checked rather than
   asserted.
"""

import argparse
import hashlib
import json
import os
import sys


def spine(root, ast):
    """The pre-order walk of `ASTUtils.walkScope`, flattened.

    Deliberately identical to gen-ast-parity-fixture.py's, including the
    two-container-classes branch that a schema-generic emitter cannot infer.
    """
    out = []

    def children_of(node):
        if isinstance(node, (ast.Scope, ast.SymbolChildrenScope)):
            return list(node.children())
        return []

    def name_of(node):
        if isinstance(node, (ast.NamedScope, ast.NamedScopeChild)):
            n = node.getName()
            return n.getId() if n is not None else None
        return None

    def visit(node, depth):
        loc = node.getLocation()
        out.append([
            type(node).__name__,
            name_of(node),
            depth,
            loc.fileid, loc.lineno, loc.linepos, loc.extent,
        ])
        for c in children_of(node):
            visit(c, depth + 1)

    for child in children_of(root):
        visit(child, 0)

    return out


def refs(root, ast):
    """Count the resolved entries of every non-owning list field in the tree.

    `imports` hangs off `SymbolScope` as an owned `SymbolImportSpec` rather than
    appearing among its children, so the walk has to follow it explicitly --
    a children-only walk finds no `SymbolImportSpec` at all and would report
    zero of everything without failing.
    """
    counts = {
        "importSpecs": 0, "imports": 0,
        "functionScopes": 0, "prototypes": 0,
    }
    seen = set()

    def visit(node):
        if node is None or id(node) in seen:
            return
        seen.add(id(node))

        if isinstance(node, ast.SymbolScope):
            spec = node.getImports()
            if spec is not None:
                counts["importSpecs"] += 1
                counts["imports"] += spec.numImports()
        if isinstance(node, ast.SymbolFunctionScope):
            counts["functionScopes"] += 1
            counts["prototypes"] += node.numPrototypes()

        if isinstance(node, (ast.Scope, ast.SymbolChildrenScope)):
            for c in node.children():
                visit(c)

    visit(root)
    return counts


def digest(entries):
    """sha256 of the spine, over a serialisation `JSON.stringify` reproduces.

    The separators matter: Python's default `", "` / `": "` would give a digest
    the TypeScript side could never compute, and the failure would look like a
    parity defect rather than a formatting one.
    """
    h = hashlib.sha256()
    h.update(json.dumps(entries, separators=(",", ":")).encode("utf-8"))
    return h.hexdigest()


def run_case(case, ast, full_spine):
    """Parse a case's sources and link them, recording what came out.

    A case whose *parse* fails never reaches link() and is recorded as such. A
    case whose *link* fails is recorded with its root anyway -- that is the
    behaviour under test (`parser.py:186-217`), not an edge case to skip.
    """
    from pssparser.parser import Parser

    parser = Parser()
    parse_raised = None
    link_raised = None
    try:
        parser.parses(list(case["files"]))
    except Exception as e:
        parse_raised = type(e).__name__

    root = None
    if parse_raised is None:
        try:
            root = parser.link()
        except Exception as e:
            link_raised = type(e).__name__
            root = parser._root

    out = {
        "id": case["id"],
        "why": case.get("why", ""),
        "files": [{"name": n, "content": c} for n, c in case["files"]],
        "parseRaised": parse_raised,
        "linkRaised": link_raised,
    }

    if root is None:
        return out

    out["units"] = [root.getUnit(i).getFileid() for i in range(root.numUnits())]
    out["fileMap"] = {str(k): v for k, v in parser.file_map.items()}
    out["userUnits"] = [u.getFileid() for u in parser.user_units()]
    out["refs"] = refs(root, ast)

    s = spine(root, ast)
    out["spineLength"] = len(s)
    out["spineDigest"] = digest(s)
    if full_spine:
        out["spine"] = s

    # The units hang off `units`, not off `children`, so the walk above never
    # reaches them -- it covers the merged symbol tree and nothing else. Their
    # spines are recorded separately, and only for the user files: unit 0 is
    # the standard library and unit -1 the builtins, identical in every case
    # and already covered by the per-unit fixture.
    out["userUnitSpines"] = []
    for u in parser.user_units():
        us = spine(u, ast)
        entry = {"fileid": u.getFileid(), "length": len(us), "digest": digest(us)}
        if full_spine:
            entry["spine"] = us
        out["userUnitSpines"].append(entry)

    return out


#: Inline cases, recorded with their full spine. Each is here for a linking
#: question rather than a parsing one.
INLINE_CASES = [
    {
        "id": "minimal",
        "why": "one unit: the smallest linked root there is",
        "files": [("top.pss", "component pss_top {\n    action A { }\n}\n")],
    },
    {
        "id": "two-units",
        "why": "two user units under one root, in parse order",
        "files": [("p.pss", "package p {\n    const int W = 8;\n}\n"),
                  ("top.pss", "component pss_top {\n    action A { }\n}\n")],
    },
    {
        "id": "cross-unit-const",
        "why": (
            "the second unit reads a constant declared in the first. Before "
            "linking, a reference across that boundary has no id to write and "
            "is dropped; after it, both units are in one buffer."
        ),
        "files": [("p.pss", "package p {\n    const int W = 8;\n}\n"),
                  ("top.pss",
                   "import p::*;\n"
                   "component pss_top {\n"
                   "    action A { rand bit[p::W] f; }\n"
                   "}\n")],
    },
    {
        "id": "cross-unit-type",
        "why": "a type declared in one unit and instanced in another, plus an import spec",
        "files": [("p.pss", "package p {\n    struct S { int a; }\n}\n"),
                  ("top.pss",
                   "import p::*;\n"
                   "component pss_top {\n"
                   "    action A { p::S s; }\n"
                   "}\n")],
    },
    {
        "id": "extension",
        "why": "an extend in a second unit merges into the first unit's type during linking",
        "files": [("base.pss", "component pss_top {\n    action A { }\n}\n"),
                  ("ext.pss", "extend action pss_top::A {\n    rand int x;\n}\n")],
    },
    {
        "id": "function-prototypes",
        "why": "SymbolFunctionScope.prototypes is the schema's other non-owning list",
        "files": [("fn.pss",
                   "package p {\n"
                   "    function int f(int a);\n"
                   "}\n"
                   "component pss_top {\n"
                   "    action A { }\n"
                   "}\n")],
    },
    {
        "id": "unresolved-reference",
        "why": (
            "a link that fails. The root must still be recorded and its units "
            "still reachable -- ownership moved into it before the error was "
            "reported (parser.py:186-217)."
        ),
        "files": [("bad.pss",
                   "component pss_top {\n"
                   "    action A { no_such_type_t f; }\n"
                   "}\n")],
    },
]


def corpus_cases(corpus_dir):
    cases = []
    for dirpath, _, filenames in os.walk(corpus_dir):
        for fn in sorted(filenames):
            if not fn.endswith(".pss"):
                continue
            path = os.path.join(dirpath, fn)
            rel = os.path.relpath(path, corpus_dir).replace(os.sep, "/")
            with open(path, "r", encoding="utf-8", errors="replace") as fp:
                content = fp.read()
            cases.append({
                "id": "corpus:" + rel,
                "why": "corpus link parity",
                "files": [(rel, content)],
            })
    return sorted(cases, key=lambda c: c["id"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--corpus", help="directory of .pss files to include")
    ap.add_argument("--no-corpus", action="store_true")
    args = ap.parse_args(argv)

    try:
        import pssparser.ast as ast
        import pssparser.parser  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "cannot import pssparser (%s).\n"
            "Build the native extension first:\n"
            "    packages/python/bin/python setup.py build_ext --inplace\n"
            "and run this with PYTHONPATH=python." % e)

    results = [run_case(c, ast, full_spine=True) for c in INLINE_CASES]

    corpus = None
    if not args.no_corpus:
        corpus = args.corpus or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "packages", "pss-corpus", "curated")
        corpus = os.path.abspath(corpus)
        if os.path.isdir(corpus):
            for c in corpus_cases(corpus):
                results.append(run_case(c, ast, full_spine=False))
        else:
            print("no corpus at %s -- inline cases only" % corpus, file=sys.stderr)
            corpus = None

    out = {
        "generator": "ts/scripts/gen-link-parity-fixture.py",
        "note": (
            "Generated from the native pssparser Python bindings. Do not edit by "
            "hand -- regenerate. `spine` is the pre-order walk of "
            "ASTUtils.walkScope over the linked root: [class, name, depth, "
            "fileid, lineno, linepos, extent]. Corpus cases carry only its "
            "length and sha256, because the merged tree contains the whole "
            "standard library and cannot be elided."),
        "cases": results,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as fp:
        json.dump(out, fp, indent=1, sort_keys=True)
        fp.write("\n")

    linked = [r for r in results if "units" in r]
    print("wrote %s: %d cases, %d linked, %d spine nodes%s" % (
        args.output, len(results), len(linked),
        sum(r["spineLength"] for r in linked),
        (" (corpus: %s)" % corpus) if corpus else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
