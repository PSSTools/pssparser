#!/usr/bin/env python3
"""List Annex B productions that end in ';' whose PSSParser.g4 rule does not.

`int x = 1` / `int y = 2;` linked clean for years because
`procedural_data_declaration` had no TOK_SEMICOLON: the `;` was eaten by the
empty-statement alternative of `procedural_stmt`, so the bad model was a legal
parse and no recovery (and no marker) was involved.  This census finds rules of
the same shape.  A hit is not necessarily a bug -- some rules leave the `;` to
their caller on purpose -- so each is reviewed by hand.

Usage: grammar_semicolon_census.py LRM.pdf|LRM.txt [PSSParser.g4]
The LRM text comes from `pdftotext -layout` (the supplied .md mangles Annex B).
"""
import os
import re
import subprocess
import sys


def lrm_text(path):
    if path.endswith(".pdf"):
        return subprocess.check_output(
            ["pdftotext", "-layout", path, "-"]).decode("utf-8", "replace")
    with open(path, encoding="utf-8", errors="replace") as fp:
        return fp.read()


def annex_b(text):
    """{name: body} for each `name ::= body` production in Annex B."""
    start = text.rfind("Annex B")
    # The last 'Annex B' heading is the annex itself; the TOC precedes it.
    lines = text[start:].splitlines()
    prods, name, body = {}, None, []
    for raw in lines:
        if raw.strip().startswith("Annex C"):
            break
        # Page line numbers sit at the left margin, or after the text when
        # the text is indented past them.
        line = re.sub(r"^\s*\d+\s", " ", raw)
        line = re.sub(r"\s\d+\s*$", "", line)
        if re.fullmatch(r"\s*\d*\s*", line):
            line = ""
        m = re.match(r"\s*([a-z_][a-z0-9_]*)\s*::=(.*)$", line)
        if m:
            if name:
                prods[name] = " ".join(body)
            name, body = m.group(1), [m.group(2)]
        elif name and line.strip() and "Copyright" not in line \
                and "Portable Test" not in line:
            body.append(line.strip())
        elif not line.strip() and name:
            prods[name] = " ".join(body)
            name, body = None, []
    if name:
        prods[name] = " ".join(body)
    return prods


def g4_rules(path):
    with open(path) as fp:
        text = fp.read()
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//[^\n]*", " ", text)
    rules = {}
    for m in re.finditer(r"^([a-z_][a-z0-9_]*)\s*:(.*?)^\s*;", text, re.S | re.M):
        rules[m.group(1)] = m.group(2)
    return rules


def ends_in_semicolon(body):
    toks = body.split()
    while toks and toks[-1] in ("]", "}", "|"):
        toks.pop()
    return bool(toks) and toks[-1] == ";"


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    g4 = argv[2] if len(argv) > 2 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "src", "PSSParser.g4")
    prods = annex_b(lrm_text(argv[1]))
    rules = g4_rules(g4)
    hits = []
    for name, body in sorted(prods.items()):
        if not ends_in_semicolon(body):
            continue
        rule = rules.get(name)
        if rule is None:
            print(f"absent   {name}")
        elif "TOK_SEMICOLON" not in rule:
            hits.append(name)
            print(f"NO-SEMI  {name}")
    print(f"{len(prods)} productions, {len(hits)} hits", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
