#!/usr/bin/env python3
"""Reference coverage: which name references the linker binds, and which
undefined names it reports.

Three measurements (docs/design/symbol-resolution-plan.md §3, WS0.6):

schema
    Every AST field that can hold a reference: a field whose type is one of
    the reference classes (``TypeIdentifier``, the ``ExprRefPath*`` family)
    or a subclass. This is the universe INV-4 is measured against.

bind
    Over the legal corpus -- files that link with no errors -- every
    reference node found by walking each unit's *owning* fields (including
    ``visit: false`` ones, which the linker never walks), counted per
    (field, class) as bound or unbound. On legal input every reference should
    be bound, so every unbound one is a *silent* failure. Name-bearing nodes
    that have no target slot at all are counted as ``noslot``. A reference
    whose target path resolves to nothing is ``dead``: it looks bound, and
    reads as unbound to everything downstream (report C, S3 -- the paths
    recorded inside unaddressable activity scopes). A path that runs through
    an inline scope (``with {...}``) cannot be followed without that scope,
    so it counts as ``bound`` unless an element of it is negative.

tmiss
    The slot harness (scripts/refcov_slots.py). For each slot, an undefined
    name is substituted into an otherwise legal model and the result
    classified: ``reported`` (an error on the slot's line), ``wrong_line``,
    ``silent`` (no error at all), ``internal`` (PSS000), ``crash`` or
    ``raw`` (unparseable --json).

Usage::

    PYTHONPATH=python python3 scripts/refcov.py report     # human summary
    PYTHONPATH=python python3 scripts/refcov.py baseline   # rewrite the baseline
    PYTHONPATH=python python3 scripts/refcov.py check      # compare; exit 1 on drift

The baseline is tests/python/baselines/references.json. ``check`` (and
tests/python/test_reference_coverage.py) fails on *any* difference, in either
direction: a regression is a bug, and an improvement is progress that should
be recorded by regenerating the baseline in the same change.
"""
import argparse
import collections
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "python" / "baselines" / "references.json"
SCHEMA_VERSION = 1

#: The node classes that carry a resolved target.
REF_ROOTS = {"TypeIdentifier", "ExprRefPath", "ExprRefName"}

#: The role of every name-bearing field (WS3.1), kept by
#: tests/python/test_ast_reference_roles.py.
ROLES = ROOT / "tests" / "python" / "baselines" / "reference-roles.yaml"


def _decl_id_contexts():
    """Fields whose ExprId *declares* a name, or is part of a reference node
    counted on its own, or names nothing: every field whose role is not
    `ref`. Anything else holding a bare ExprId/ExprHierarchicalId is a
    reference with nowhere to record its target, and is counted as
    ``noslot``."""
    import yaml
    roles = (yaml.safe_load(ROLES.read_text()) or {}).get("roles", {})
    return {f for f, r in roles.items() if r != "ref"}


DECL_ID_CONTEXTS = _decl_id_contexts()


# -- schema ------------------------------------------------------------------

def load_schema():
    """{class: (yaml file, super, [(field, type, visit)])} from ast/*.yaml."""
    import yaml
    classes = {}
    for f in sorted(glob.glob(str(ROOT / "ast" / "*.yaml"))):
        doc = yaml.safe_load(open(f)) or {}
        for c in doc.get("classes", []) or []:
            (name, body), = c.items()
            body = body or {}
            if isinstance(body, list):
                merged = {}
                for a in body:
                    merged.update(a)
                body = merged
            fields = []
            for fe in body.get("data", []) or []:
                (fn, spec), = fe.items()
                if isinstance(spec, str):
                    t, attrs = spec, {}
                elif isinstance(spec, list):
                    attrs = {}
                    for a in spec:
                        attrs.update(a)
                    t = attrs.get("type")
                else:
                    attrs, t = spec, spec.get("type")
                fields.append((fn, t, attrs.get("visit", True)))
            classes[name] = (os.path.basename(f), body.get("super"), fields)
    return classes


def _ref_classes(classes):
    """REF_ROOTS and everything that derives from them."""
    out = set(REF_ROOTS)
    changed = True
    while changed:
        changed = False
        for name, (_, sup, _) in classes.items():
            if sup in out and name not in out:
                out.add(name)
                changed = True
    return out


def _elem_type(t):
    m = re.match(r"^(?:list<)?\s*(?:UP|P|SP)<\s*(\w+)\s*>\s*>?$", (t or "").strip())
    return m.group(1) if m else None


def ref_fields(classes):
    """{"Class.field": {"type": X, "visit": bool}} for every reference field."""
    refs = _ref_classes(classes)
    out = {}
    for name, (_, _, fields) in classes.items():
        for fn, t, vis in fields:
            et = _elem_type(t)
            if et in refs:
                out["%s.%s" % (name, fn)] = {"type": et, "visit": bool(vis)}
    return dict(sorted(out.items()))


# -- bind: the ownership walk (runs in a child process) ----------------------

def _fields_of(classes, cls):
    out = []
    while cls in classes:
        _, sup, fl = classes[cls]
        out = [(cls,) + tuple(x) for x in fl] + out
        cls = sup
    return out


def _walk_file(fn):
    """Link *fn* and classify every reference node under its units."""
    sys.path.insert(0, str(ROOT / "python"))
    from pssparser.parser import Parser, ParseException

    classes = load_schema()
    refcls = _ref_classes(classes)
    import pssparser.core as zspp

    p = Parser()
    p.parse([fn])
    clean = True
    root = None
    try:
        root = p.link()
    except ParseException:
        clean = False
        root = p._root

    def state_of(t):
        if t is None:
            return "unbound"
        path = [(int(e.kind), e.idx) for e in t.path()]
        # ElemKind_ChildIdx is 0, ElemKind_Inline is 2 (ast/linking.yaml).
        if any(k == 0 and i < 0 for k, i in path):
            return "dead"
        if root is None or any(k == 2 for k, _ in path):
            return "bound"
        return "bound" if zspp.resolveSymbolPathRef(root, t) is not None else "dead"

    res = []

    def getter_values(n, fname):
        cap = fname[0].upper() + fname[1:]
        g = getattr(n, "get" + cap, None)
        if g is None:
            return None
        try:
            v = g()
        except TypeError:
            nm = getattr(n, "num" + cap, None) or getattr(n, "size" + cap, None)
            if nm is None:
                return None
            v = [g(i) for i in range(nm())]
        except Exception:
            return None
        if isinstance(v, (list, tuple)):
            return list(v)
        if hasattr(v, "__iter__") and not hasattr(v, "accept"):
            return list(v)
        return [v]

    def walk(n, ctx, unwalked):
        if n is None:
            return
        cn = type(n).__name__
        tag = ctx + ("{UNWALKED}" if unwalked else "")
        if cn in refcls:
            try:
                t = n.getTarget()
            except Exception:
                t = None
            res.append((tag, cn, state_of(t)))
        elif cn == "ExprId" and _field_of_ctx(ctx) not in DECL_ID_CONTEXTS:
            res.append((tag, cn, "noslot"))
        elif cn == "ExprHierarchicalId" and "ExprRefPath" not in ctx:
            res.append((tag, cn, "noslot"))
        for (dc, fname, ftype, vis) in _fields_of(classes, cn):
            if not ftype or not any(ftype.startswith(pfx) for pfx in ("UP<", "list<UP<")):
                continue
            vals = getter_values(n, fname)
            if not vals:
                continue
            sub = "%s.%s%s" % (dc, fname, "" if vis else "[NOVISIT]")
            for c in vals:
                walk(c, sub, unwalked or not vis)

    for u in p.user_units():
        for c in u.getChildren():
            walk(c, "GlobalScope.children", False)
    return {"clean": clean, "refs": res}


def _run_child(fn):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "python") + os.pathsep + env.get("PYTHONPATH", "")
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    r = subprocess.run([sys.executable, __file__, "_walk", fn],
                       capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        return {"clean": False, "refs": [], "crashed": True}
    return json.loads(r.stdout)


def corpus_files():
    """The legal inputs: every parses=true pss-corpus bucket, plus the
    error suite's accept cases. Tracked inputs only, so the baseline is
    reproducible from a checkout."""
    files = []
    corpus = ROOT / "packages" / "pss-corpus" / "curated"
    manifest = ROOT / "packages" / "pss-corpus" / "manifest.toml"
    if corpus.is_dir() and manifest.is_file():
        try:
            import tomllib
        except ImportError:  # Python < 3.11
            import tomli as tomllib
        buckets = tomllib.loads(manifest.read_text()).get("bucket", {})
        for name, pol in sorted(buckets.items()):
            if pol.get("parses", True):
                files += sorted(glob.glob(str(corpus / name / "**" / "*.pss"), recursive=True))
    files += sorted(glob.glob(str(ROOT / "error-suite" / "cases" / "accept" / "**" / "*.pss"),
                              recursive=True))
    return files


def bind(files):
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        results = list(ex.map(_run_child, files))
    agg = collections.defaultdict(collections.Counter)
    examples = collections.defaultdict(list)
    n_clean = 0
    for fn, r in zip(files, results):
        if not r["clean"]:
            continue
        n_clean += 1
        for ctx, cn, st in r["refs"]:
            key = "%s | %s" % (ctx, cn)
            agg[key][st] += 1
            if st in ("unbound", "dead") and len(examples[key]) < 3:
                examples[key].append(os.path.relpath(fn, ROOT))
    table = {k: dict(sorted(v.items())) for k, v in sorted(agg.items())}
    return {"files": len(files), "clean_files": n_clean, "fields": table}, examples


# -- tmiss -------------------------------------------------------------------

def _slot_lines(base):
    lines = {}
    for i, line in enumerate(base.split("\n"), 1):
        for m in re.finditer(r"@@(\w+)@@", line):
            lines[m.group(1)] = i
    return lines


def _classify(path, slot_line):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "python") + os.pathsep + env.get("PYTHONPATH", "")
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    r = subprocess.run([sys.executable, "-m", "pssparser", "--json", "--max-errors", "0", path],
                       capture_output=True, text=True, env=env, timeout=300)
    if r.returncode not in (0, 1, 3):
        return "crash"
    try:
        diags = json.loads(r.stdout)["diagnostics"]
    except ValueError:
        return "raw"
    if r.stderr.strip():
        return "raw"
    if any(d.get("code") == "PSS000" for d in diags):
        return "internal"
    errs = [d for d in diags if d.get("severity") == "error"]
    if slot_line is None:            # the legal model
        return "clean" if not errs else "errors"
    if not errs:
        return "silent"
    if any(d.get("line") == slot_line for d in errs):
        return "reported"
    return "wrong_line"


def tmiss():
    sys.path.insert(0, str(ROOT / "scripts"))
    import refcov_slots as S

    def render(over):
        d = dict(S.DEF)
        d.update(over)
        return re.sub(r"@@(\w+)@@", lambda m: d[m.group(1)], S.BASE)

    lines = _slot_lines(S.BASE)
    jobs = [("00_legal", render({}), None)]
    for k, v in S.BAD.items():
        jobs.append((k.lower(), render({k: v}), lines[k]))
    for k, v in S.EXTRA.items():
        key, tag = k.split(":")
        jobs.append(("%s__%s" % (key.lower(), tag), render({key: v}), lines[key]))

    with tempfile.TemporaryDirectory() as d:
        paths = []
        for name, text, _ in jobs:
            p = os.path.join(d, name + ".pss")
            with open(p, "w") as fp:
                fp.write(text)
            paths.append(p)
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            states = list(ex.map(lambda a: _classify(*a),
                                 [(p, j[2]) for p, j in zip(paths, jobs)]))
        # Which reference fields the legal model exercises -- the slots'
        # coverage of the schema (INV-4's gap list).
        legal = _run_child(paths[0])
    exercised = sorted({ctx for ctx, cn, st in legal["refs"]
                        if cn != "ExprId" and cn != "ExprHierarchicalId"})
    return {name: st for (name, _, _), st in zip(jobs, states)}, exercised


# -- baseline ----------------------------------------------------------------

def _field_of_ctx(ctx):
    return ctx.split("[")[0].split("{")[0]


def compute():
    classes = load_schema()
    schema = ref_fields(classes)
    bind_tbl, examples = bind(corpus_files())
    slots, template_ctx = tmiss()

    corpus_fields = {_field_of_ctx(k.split(" | ")[0]) for k in bind_tbl["fields"]
                     if not k.endswith("| ExprId") and not k.endswith("| ExprHierarchicalId")}
    template_fields = {_field_of_ctx(c) for c in template_ctx}
    for f, info in schema.items():
        info["in_corpus"] = f in corpus_fields
        info["in_slots"] = f in template_fields

    counts = collections.Counter(slots[k] for k in slots if k != "00_legal")
    tot = collections.Counter()
    for v in bind_tbl["fields"].values():
        tot.update(v)
    summary = {
        "slots": sum(counts.values()),
        "slots_by_state": dict(sorted(counts.items())),
        "legal_model": slots["00_legal"],
        "corpus_refs": dict(sorted(tot.items())),
        "schema_ref_fields": len(schema),
        "schema_ref_fields_in_corpus": sum(1 for i in schema.values() if i["in_corpus"]),
        "schema_ref_fields_in_slots": sum(1 for i in schema.values() if i["in_slots"]),
    }
    data = {
        "schema": SCHEMA_VERSION,
        "summary": summary,
        "schema_ref_fields": schema,
        "tmiss": dict(sorted(slots.items())),
        "bind": bind_tbl,
    }
    return data, examples


def diff(old, new):
    """Human-readable differences between two baselines ([] when equal)."""
    out = []
    for k in sorted(set(old.get("tmiss", {})) | set(new.get("tmiss", {}))):
        a, b = old.get("tmiss", {}).get(k), new.get("tmiss", {}).get(k)
        if a != b:
            out.append("slot %-28s %s -> %s" % (k, a, b))
    of, nf = old.get("bind", {}).get("fields", {}), new.get("bind", {}).get("fields", {})
    for k in sorted(set(of) | set(nf)):
        if of.get(k) != nf.get(k):
            out.append("bind %s: %s -> %s" % (k, of.get(k), nf.get(k)))
    for key in ("files", "clean_files"):
        a, b = old.get("bind", {}).get(key), new.get("bind", {}).get(key)
        if a != b:
            out.append("bind %s: %s -> %s" % (key, a, b))
    os_, ns = old.get("schema_ref_fields", {}), new.get("schema_ref_fields", {})
    for k in sorted(set(os_) | set(ns)):
        if os_.get(k) != ns.get(k):
            out.append("schema %s: %s -> %s" % (k, os_.get(k), ns.get(k)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["report", "baseline", "check", "_walk"])
    ap.add_argument("file", nargs="?")
    args = ap.parse_args(argv)

    if args.cmd == "_walk":
        print(json.dumps(_walk_file(args.file)))
        return 0

    data, examples = compute()
    if args.cmd == "baseline":
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(data, indent=1, sort_keys=False) + "\n")
        print("wrote %s" % BASELINE.relative_to(ROOT))
        print(json.dumps(data["summary"], indent=1))
        return 0
    if args.cmd == "check":
        old = json.loads(BASELINE.read_text())
        d = diff(old, data)
        for line in d:
            print(line)
        if d:
            print("\nreference coverage differs from %s -- if the change is deliberate, "
                  "run `scripts/refcov.py baseline`" % BASELINE.relative_to(ROOT))
        return 1 if d else 0

    # report
    print(json.dumps(data["summary"], indent=1))
    print("\nslots not reported:")
    for k, v in data["tmiss"].items():
        if v not in ("reported", "clean"):
            print("  %-30s %s" % (k, v))
    print("\nsilently unbound on legal corpus files:")
    for k, v in data["bind"]["fields"].items():
        if v.get("unbound") or v.get("dead"):
            print("  %-70s %s  e.g. %s" % (k, v, " ".join(examples.get(k, []))))
    print("\nschema reference fields exercised by neither corpus nor slots:")
    for k, v in data["schema_ref_fields"].items():
        if not v["in_corpus"] and not v["in_slots"]:
            print("  %s" % k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
