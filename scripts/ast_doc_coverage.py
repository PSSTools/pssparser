#!/usr/bin/env python3
"""Report what in ast/*.yaml has no documentation.

Lists, per ast/<group>.yaml: classes with no ``doc:``, fields with neither a
``doc:`` of their own nor an ``Attributes:`` entry in their class's doc,
``Attributes:`` entries that name no field of the class, enums, flags and
structs with no ``doc:``, and enum/flags values with no doc. ``--thin`` also
lists class docs whose description is a single line.

Exit status 1 when anything is missing (``--check``), so it can gate CI.
Needs pyastbuilder (``pip install pyastbuilder``).
"""
import argparse
import glob
import os
import sys

from astbuilder.ast import Ast
from astbuilder.docstring import split
from astbuilder.linker import Linker
from astbuilder.parser import Parser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load():
    ast = Ast()
    for f in sorted(glob.glob(os.path.join(ROOT, "ast", "*.yaml"))):
        with open(f) as fp:
            Parser(ast, f).parse(fp)
    Linker().link(ast)
    return ast


def group(ent):
    return os.path.splitext(os.path.basename(ent.srcfile))[0]


def ancestors(c):
    out = []
    while c.super is not None:
        c = c.super.target
        out.append(c)
    return out


def report(ast, thin=False):
    out = {}

    def add(ent, msg):
        out.setdefault(group(ent), []).append(msg)

    for c in ast.classes:
        parts = split(c.doc or "")
        if not c.doc:
            add(c, "class %s: no doc" % c.name)
        elif thin and len([l for l in parts.body.strip().splitlines() if l.strip()]) <= 1:
            add(c, "class %s: one-line doc" % c.name)
        # An Attributes: entry may describe an inherited field for this class.
        names = {d.name for k in [c] + ancestors(c) for d in k.data}
        for d in c.data:
            if not d.doc and not parts.attributes.get(d.name):
                add(c, "field %s.%s: no doc" % (c.name, d.name))
        for a in parts.attributes:
            if a not in names:
                add(c, "class %s: Attributes names %r, which is no field of it or its bases" % (c.name, a))
    for kind, ents in (("struct", ast.structs), ("enum", ast.enums), ("flags", ast.flags)):
        for e in ents:
            if not getattr(e, "doc", None):
                add(e, "%s %s: no doc" % (kind, e.name))
            vdocs = getattr(e, "value_docs", None) or {}
            for v in getattr(e, "values", None) or []:
                v = v if isinstance(v, str) else v[0]
                if not vdocs.get(v):
                    add(e, "%s value %s.%s: no doc" % (kind, e.name, v))
            if kind == "struct":
                for d in e.data:
                    if not d.doc and not split(e.doc or "").attributes.get(d.name):
                        add(e, "field %s.%s: no doc" % (e.name, d.name))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--thin", action="store_true", help="also list one-line class docs")
    ap.add_argument("--check", action="store_true", help="exit 1 if anything is missing")
    args = ap.parse_args()
    out = report(load(), args.thin)
    n = 0
    for g in sorted(out):
        print("ast/%s.yaml" % g)
        for m in out[g]:
            print("  " + m)
            n += 1
    print("%d gaps" % n)
    return 1 if args.check and n else 0


if __name__ == "__main__":
    sys.exit(main())
