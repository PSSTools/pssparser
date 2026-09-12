#!/usr/bin/env python3
"""Check that ``ast/*.yaml`` and ``src/PSSParser.g4`` stay a truthful map of
what this parser actually produces.

This is item 6.3-6.5 of docs/ast-coverage-plan.md, and it is the mechanism that
keeps that document from being needed a second time. The coverage effort found
three defect classes that no existing test could see, because each one is a
*silence* rather than a wrong answer. Each check below catches one of them.

``producers``
    A class declared in ``ast/*.yaml`` that the builder never constructs.
    Thirteen such classes had accumulated, every one of them superseded by a
    differently-named node that *is* built. Nothing announced that: a
    downstream consumer writing ``visitExprStructLiteral`` gets a visitor that
    compiles, links, and never fires.

    A class is exempt when another class names it as ``super`` -- an abstract
    base is not expected to be constructed. Copy code (``TaskCopyAst.h``) does
    not count as a producer: it only ever copies a node the builder made, so a
    class reachable *only* from there is still dead.

``symtree``
    A class whose children are silently duplicated into the enclosing scope.
    The generated ``VisitorBase::visitC`` calls the base-class visitor -- which
    in TaskBuildSymbolTree adds the node and stops -- and then walks C's own
    declared fields, with the *enclosing* symbol scope still current. Anything
    in those fields that registers a name or a scope therefore registers it in
    the wrong place. Six defects in the coverage effort were this one defect,
    and a seventh (``ExtendEnum``) was found by writing this check.

``grammar``
    A parser rule no input can reach. LRM B.11's monitor traversal had been
    mistranscribed into a rule that accepted meaningless source; removing it
    left the rule itself unreferenced, and nothing said so.

Every exemption lives in ``scripts/ast_inventory_allowlist.txt`` with a reason.
A stale entry -- one that no longer names a violation -- is itself an error, so
the file cannot quietly grow into a list of things nobody has looked at since.

Usage::

    python3 scripts/check_ast_inventory.py [--list]

Exits non-zero on any violation. ``--list`` prints the current findings without
consulting the allowlist, which is how you write a new entry.
"""

import argparse
import glob
import os
import re
import sys

try:
    import yaml
except ImportError:
    sys.stderr.write("check_ast_inventory: PyYAML is required\n")
    sys.exit(2)


PROJ_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWLIST = os.path.join(PROJ_DIR, "scripts", "ast_inventory_allowlist.txt")

#: Copies are not producers. A class only this file constructs is still dead.
COPY_FILE = os.path.join("src", "include", "pssp", "impl", "TaskCopyAst.h")

#: Where the symbol tree is built. A class needing custom handling needs it here.
SYMTREE_FILE = os.path.join("src", "TaskBuildSymbolTree.h")

GRAMMAR_FILE = os.path.join("src", "PSSParser.g4")
GRAMMAR_ROOT = "compilation_unit"

#: A field of one of these kinds is what makes the symtree walk damaging: a
#: Scope brings a child list, a NamedScopeChild brings a name to register.
SYMTREE_RISK_BASES = ("Scope", "NamedScopeChild")


# ---------------------------------------------------------------------------
# ast/*.yaml
# ---------------------------------------------------------------------------

def _norm(v):
    """Normalize a yaml class or field body to a dict.

    Both spellings appear in ``ast/*.yaml`` -- a mapping, and a list of
    single-key mappings (``- type: ...`` / ``- visit: false``) -- and they mean
    the same thing.
    """
    if isinstance(v, dict):
        return v
    if isinstance(v, list):
        d = {}
        for e in v:
            if isinstance(e, dict):
                d.update(e)
        return d
    return {}


def load_classes():
    """Return {name: (yaml_file, body)} for every class in ``ast/*.yaml``."""
    classes = {}
    for f in sorted(glob.glob(os.path.join(PROJ_DIR, "ast", "*.yaml"))):
        doc = yaml.safe_load(open(f))
        for c in (doc.get("classes") or []):
            for name, body in c.items():
                classes[name] = (os.path.relpath(f, PROJ_DIR), _norm(body))
    return classes


def ancestors(name, classes):
    out = []
    seen = set()
    while name in classes and name not in seen:
        out.append(name)
        seen.add(name)
        name = classes[name][1].get("super")
    if name:
        out.append(name)
    return out


def fields(body):
    """Yield (field_name, type_string, visited) for a class body."""
    for fld in (body.get("data") or []):
        if not isinstance(fld, dict):
            continue
        for fname, fbody in fld.items():
            if isinstance(fbody, str):
                yield fname, fbody, True
            else:
                d = _norm(fbody)
                t = d.get("type")
                if isinstance(t, str):
                    yield fname, t, d.get("visit") is not False


def source_files():
    out = []
    for root, _dirs, names in os.walk(os.path.join(PROJ_DIR, "src")):
        for n in names:
            if n.endswith((".cpp", ".h")):
                out.append(os.path.join(root, n))
    return out


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_producers(classes):
    """Concrete classes the builder never constructs."""
    bases = set()
    for _f, body in classes.values():
        if body.get("super"):
            bases.add(body["super"])

    blob = {}
    for p in source_files():
        blob[os.path.relpath(p, PROJ_DIR)] = open(p, errors="replace").read()

    out = []
    for name in sorted(classes):
        if name in bases:
            continue  # abstract base; its subclasses are what get built
        pat = re.compile(r"\bmk%s\b" % re.escape(name))
        producers = [p for p, t in blob.items()
                     if p != COPY_FILE and pat.search(t)]
        if not producers:
            copied = COPY_FILE in blob and pat.search(blob[COPY_FILE])
            out.append((name, "%s, never constructed%s" % (
                classes[name][0],
                " (copy visitor only)" if copied else "")))
    return out


def check_symtree(classes):
    """Classes whose walked fields would land in the enclosing symbol scope."""
    subclasses = {}
    for name in classes:
        for a in ancestors(name, classes):
            subclasses.setdefault(a, set()).add(name)

    risky_types = set()
    for base in SYMTREE_RISK_BASES:
        risky_types |= subclasses.get(base, set())

    header = open(os.path.join(PROJ_DIR, SYMTREE_FILE), errors="replace").read()

    out = []
    for name in sorted(classes):
        body = classes[name][1]
        hits = []
        for fname, ftype, visited in fields(body):
            if not visited:
                continue
            for word in re.findall(r"\w+", ftype):
                # A field declared as a base type can hold any subclass of it,
                # so `UP<ScopeChild>` is as risky as the riskiest thing under
                # ScopeChild.
                if word in risky_types or (subclasses.get(word, set()) & risky_types):
                    hits.append("%s: %s" % (fname, ftype))
                    break
        if not hits:
            continue
        # An abstract base is never dispatched to directly: the generated
        # visitor for a subclass calls the base-class *visitor*, then walks the
        # subclass's own fields. So a base whose every concrete descendant has
        # a visitor is covered -- that visitor decides what happens to the
        # inherited field too.
        descendants = subclasses.get(name, set()) - {name}
        if descendants and all(("visit%s(" % d) in header for d in descendants):
            continue
        if ("visit%s(" % name) not in header:
            out.append((name, "no TaskBuildSymbolTree visitor; walks %s"
                        % ", ".join(sorted(set(hits)))))
    return out


def check_grammar():
    """Parser rules unreachable from the start rule."""
    text = open(os.path.join(PROJ_DIR, GRAMMAR_FILE), errors="replace").read()
    text = re.sub(r"//[^\n]*", "", text)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"'(\\.|[^'\\])*'", "", text)  # literals, not rule refs

    rules = {}
    for m in re.finditer(r"^([a-z][A-Za-z0-9_]*)\s*:(.*?)^\s*;",
                         text, flags=re.S | re.M):
        rules[m.group(1)] = m.group(2)

    if GRAMMAR_ROOT not in rules:
        return [(GRAMMAR_ROOT, "%s: start rule not found" % GRAMMAR_FILE)]

    seen = set()
    stack = [GRAMMAR_ROOT]
    while stack:
        r = stack.pop()
        if r in seen:
            continue
        seen.add(r)
        for n in re.findall(r"\b([a-z][A-Za-z0-9_]*)\b", rules[r]):
            if n in rules and n not in seen:
                stack.append(n)

    return [(r, "%s: unreachable from %s" % (GRAMMAR_FILE, GRAMMAR_ROOT))
            for r in sorted(rules) if r not in seen]


CHECKS = ("producers", "symtree", "grammar")


# ---------------------------------------------------------------------------
# Allowlist
# ---------------------------------------------------------------------------

def load_allowlist():
    """Return {(check, name): reason}."""
    entries = {}
    if not os.path.exists(ALLOWLIST):
        return entries
    for lineno, line in enumerate(open(ALLOWLIST), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        if len(parts) != 2 or ":" not in parts[0]:
            raise SystemExit(
                "%s:%d: expected '<check>:<name> <reason>'" % (ALLOWLIST, lineno))
        key, reason = parts[0], parts[1].strip()
        check, _, name = key.partition(":")
        if check not in CHECKS:
            raise SystemExit("%s:%d: unknown check '%s' (expected one of %s)"
                             % (ALLOWLIST, lineno, check, ", ".join(CHECKS)))
        if not reason:
            raise SystemExit("%s:%d: entry needs a reason" % (ALLOWLIST, lineno))
        entries[(check, name)] = reason
    return entries


def run():
    """Return (violations, stale) -- both lists of (check, name, detail)."""
    classes = load_classes()
    found = []
    for name, detail in check_producers(classes):
        found.append(("producers", name, detail))
    for name, detail in check_symtree(classes):
        found.append(("symtree", name, detail))
    for name, detail in check_grammar():
        found.append(("grammar", name, detail))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--list", action="store_true",
                    help="print all findings, ignoring the allowlist")
    args = ap.parse_args()

    found = run()

    if args.list:
        for check, name, detail in found:
            print("%s:%s\t%s" % (check, name, detail))
        return 0

    allow = load_allowlist()
    keys = set((c, n) for c, n, _d in found)

    violations = [(c, n, d) for c, n, d in found if (c, n) not in allow]
    stale = sorted(k for k in allow if k not in keys)

    for check, name, detail in violations:
        print("ERROR: %s:%s -- %s" % (check, name, detail))
    for check, name in stale:
        print("ERROR: %s:%s is allowlisted but is no longer a finding; "
              "remove the entry from %s"
              % (check, name, os.path.relpath(ALLOWLIST, PROJ_DIR)))

    if violations or stale:
        print("\n%d new finding(s), %d stale allowlist entr(ies). "
              "Run with --list to see every finding."
              % (len(violations), len(stale)))
        return 1

    print("ast inventory: %d allowlisted exemption(s), no new findings"
          % len(allow))
    return 0


if __name__ == "__main__":
    sys.exit(main())
