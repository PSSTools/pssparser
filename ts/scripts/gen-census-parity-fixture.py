#!/usr/bin/env python3
"""Record every node and every field of the native AST, as a fixture for the TS tests.

    packages/python/bin/astbuilder gen-census -astdir ast \\
        -py ts/scripts/generated -ts ts/test/generated
    packages/python/bin/python ts/scripts/gen-census-parity-fixture.py \\
        -o ts/test/fixtures/census-parity.json

Fourth in the series after gen-parity-fixture.py (markers),
gen-ast-parity-fixture.py (per-unit declaration spine) and
gen-link-parity-fixture.py (the linked root's spine), and there because the
first three stop at the spine.

The spine is `ASTUtils.walkScope`: `Scope` and `SymbolChildrenScope` children,
and on each node its class, name and location. It never enters an expression, a
constraint body or an exec block, and it reads three fields of the twenty-odd
most classes have. A serialisation defect confined to `ExprBin.op` passes all
three fixtures. This one walks the whole ownership graph and records every
field, so it can fail on one.

The walk itself is **generated** rather than written here -- `census_gen.py`
from `astbuilder gen-census`, whose TypeScript twin the test uses. Writing it by
hand would mean transliterating 200-odd classes twice and keeping both
transliterations current, which is exactly the drift the generated
serializer/deserializer pair exists to avoid. See `astbuilder/gen_census.py` for
what the pair covers, and for the two things it does not: map fields, which the
pyext backend exposes only as `<field>Has`/`<field>At` with no way to enumerate
keys, and values above 2^53, which the TypeScript reader cannot represent
whatever the census does.

What is recorded per case:

1. **Each parsed unit**, pre-link, by fileid: the node count, the count by class
   name, and a sha256 of the record stream. Full records for the inline cases'
   *user* units only -- unit 0 is the standard library, ~50k nodes, and its
   records would be a hundred megabytes of fixture that every case repeats.
2. **The linked root**, count/classes/digest only, for the same reason: the
   merged tree contains the whole standard library and cannot be elided the way
   a per-unit walk elides unit 0.

The class histogram is what makes a corpus digest mismatch diagnosable. A digest
alone says the streams differ; the histogram usually says which class gained or
lost nodes, and the inline cases then reproduce it with full records.
"""

import argparse
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "generated"))

# Deep expression trees and the standard library's nesting both exceed the
# default 1000. The census recurses once per level of ownership, not once per
# node, so this is generous rather than close.
sys.setrecursionlimit(50000)


def digest(records):
    """sha256 of the record stream as JSON.

    `separators` and `ensure_ascii` are both load-bearing: Python defaults to
    `", "` / `": "` and to `\\uXXXX` escapes, JavaScript's `JSON.stringify` does
    neither, and a digest that can never match would read as a parity defect
    rather than as a formatting one.
    """
    h = hashlib.sha256()
    h.update(json.dumps(records, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    return h.hexdigest()


def summarise(result, full):
    out = {
        "count": result["count"],
        "classes": result["classes"],
        "digest": digest(result["records"]),
    }
    if full:
        out["records"] = result["records"]
    return out


def run_case(case, census, full):
    """Parse one case, census every unit, then link and census the root."""
    from pssparser.parser import Parser

    parser = Parser()
    parse_raised = None
    try:
        parser.parses(list(case["files"]))
    except Exception as e:
        parse_raised = type(e).__name__

    out = {
        "id": case["id"],
        "why": case.get("why", ""),
        "files": [{"name": n, "content": c} for n, c in case["files"]],
        "parseRaised": parse_raised,
        "linkRaised": None,
        "units": [],
        "root": None,
    }

    if parse_raised is not None:
        return out

    # parser._files is the unit list, standard library at index 0, reached
    # directly for gen-ast-parity-fixture.py's reason: the public API exposes
    # units only after link(), and linking produces a different tree.
    for i, unit in enumerate(parser._files):
        entry = summarise(census(unit), full and i >= 1)
        entry["fileid"] = i
        out["units"].append(entry)

    root = None
    try:
        root = parser.link()
    except Exception as e:
        out["linkRaised"] = type(e).__name__
        root = parser._root

    if root is not None:
        out["root"] = summarise(census(root), False)

    return out


#: Inline cases, recorded with full records for their user units. Chosen for the
#: parts of the schema the spine fixtures never reach -- expressions, constraint
#: bodies, exec blocks, coverage -- rather than for coverage of PSS.
INLINE_CASES = [
    {
        "id": "minimal",
        "why": "a component and an action: the smallest tree with a body at all",
        "files": [("top.pss", "component pss_top {\n    action A { }\n}\n")],
    },
    {
        "id": "expressions",
        "why": (
            "binary, unary, conditional and cast expressions nested several "
            "deep. ExprBin.op is the field the spine fixtures cannot see."
        ),
        "files": [("top.pss",
                   "component pss_top {\n"
                   "    action A {\n"
                   "        rand int a, b;\n"
                   "        constraint c {\n"
                   "            a + 1 < 4 * (b - 2);\n"
                   "            (a > 0) ? b == 1 : b == 2;\n"
                   "            -a != ~b;\n"
                   "            a in [1..4, 8];\n"
                   "        }\n"
                   "    }\n"
                   "}\n")],
    },
    {
        "id": "literals",
        "why": (
            "the scalar leaves: signed, unsigned, based, float, bool and string "
            "literals. Float and 64-bit values are compared as IEEE-754 bits."
        ),
        # `const` is a package-level declaration; inside a component it does not
        # parse, which is how this case spent its first run contributing nothing.
        "files": [("top.pss",
                   "package p {\n"
                   "    const int     i = -42;\n"
                   "    const int     h = 0xff;\n"
                   "    const bit[8]  b = 8'b1010_0101;\n"
                   "    const float64 f = 1.0e-9;\n"
                   "    const float32 g = 1.5;\n"
                   "    const bool    t = true;\n"
                   "    const string  s = \"a \\\" b\";\n"
                   "}\n"
                   "component pss_top {\n"
                   "    action A { }\n"
                   "}\n")],
    },
    {
        "id": "exec-and-functions",
        "why": "exec bodies and function definitions: statement classes the spine never enters",
        "files": [("top.pss",
                   "component pss_top {\n"
                   "    function int f(int a, int b) {\n"
                   "        int t = a;\n"
                   "        if (a > b) { t = b; } else { t = a + 1; }\n"
                   "        repeat (3) { t = t + 1; }\n"
                   "        return t;\n"
                   "    }\n"
                   "    action A {\n"
                   "        rand int x;\n"
                   "        exec post_solve { x = 1; }\n"
                   "    }\n"
                   "}\n")],
    },
    {
        "id": "activity",
        "why": "an activity body: schedule/parallel/select statements hang off the action",
        "files": [("top.pss",
                   "component pss_top {\n"
                   "    action A { }\n"
                   "    action B { }\n"
                   "    action Top {\n"
                   "        A a1, a2;\n"
                   "        B b1;\n"
                   "        activity {\n"
                   "            parallel { a1; b1; }\n"
                   "            select { a2; b1; }\n"
                   "            repeat (2) { a1; }\n"
                   "        }\n"
                   "    }\n"
                   "}\n")],
    },
    {
        "id": "coverage",
        "why": "covergroups: coverpoints, bins and crosses, none of which the spine descends into",
        "files": [("top.pss",
                   "component pss_top {\n"
                   "    action A {\n"
                   "        rand bit[4] x;\n"
                   "        rand bit[4] y;\n"
                   "        covergroup {\n"
                   "            cp_x : coverpoint x { bins lo = [0..3]; bins hi = [4..15]; }\n"
                   "            cp_y : coverpoint y;\n"
                   "            cr   : cross cp_x, cp_y;\n"
                   "        } cg;\n"
                   "    }\n"
                   "}\n")],
    },
    {
        "id": "two-units",
        "why": "two user units, each censused separately before the link",
        "files": [("p.pss", "package p {\n    const int W = 8;\n}\n"),
                  ("top.pss",
                   "import p::*;\n"
                   "component pss_top {\n"
                   "    action A { rand bit[p::W] f; }\n"
                   "}\n")],
    },
    {
        "id": "unresolved-reference",
        "why": (
            "a link that fails. The units parsed cleanly, so their censuses are "
            "expectations even though the root's is taken after an error."
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
                "why": "corpus census parity",
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
        import pssparser.parser  # noqa: F401
    except ImportError as e:
        raise SystemExit(
            "cannot import pssparser (%s).\n"
            "Build the native extension first:\n"
            "    packages/python/bin/python setup.py build_ext --inplace\n"
            "and run this with PYTHONPATH=python." % e)

    try:
        from census_gen import census
    except ImportError as e:
        raise SystemExit(
            "cannot import the generated census walker (%s).\n"
            "Generate it first:\n"
            "    packages/python/bin/astbuilder gen-census -astdir ast "
            "-py ts/scripts/generated -ts ts/test/generated" % e)

    results = [run_case(c, census, full=True) for c in INLINE_CASES]

    corpus = None
    if not args.no_corpus:
        corpus = args.corpus or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "packages", "pss-corpus", "curated")
        corpus = os.path.abspath(corpus)
        if os.path.isdir(corpus):
            for c in corpus_cases(corpus):
                results.append(run_case(c, census, full=False))
        else:
            print("no corpus at %s -- inline cases only" % corpus, file=sys.stderr)
            corpus = None

    out = {
        "generator": "ts/scripts/gen-census-parity-fixture.py",
        "note": (
            "Generated from the native pssparser Python bindings through the "
            "generated census walker. Do not edit by hand -- regenerate. A "
            "record is [class, ...fields] in the schema's flattened field "
            "order; `digest` is the sha256 of the record stream as compact "
            "JSON. Full records are carried only for the inline cases' user "
            "units, because unit 0 is the standard library."),
        "cases": results,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as fp:
        json.dump(out, fp, indent=1, sort_keys=True)
        fp.write("\n")

    units = sum(len(c["units"]) for c in results)
    nodes = sum(u["count"] for c in results for u in c["units"])
    print("%d cases, %d units, %d nodes -> %s" % (
        len(results), units, nodes, args.output), file=sys.stderr)


if __name__ == "__main__":
    main()
