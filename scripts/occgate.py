#!/usr/bin/env python3
"""Occurrence completeness: does pssparser.refs.occurrences() report every
identifier in the legal corpus? (pss-scrambler FR-001, plan S3.2.)

For each legal corpus file (refcov.corpus_files(); files that link with
errors are skipped), every ``ID`` token from ``pssparser.tokens`` must be an
occurrence, apart from the contextual keywords below and the tokens inside a
`compile if` branch that was not elaborated (Parser.inactive_regions(): that
text is not in the AST at all). Every occurrence must be
an ``ID`` token, or sit inside a string token (a ``{{name}}`` in a
triple-quoted template).

What falls short is recorded per file in a baseline, as refcov.py does for
references: ``missing`` (tokens with no occurrence) and ``unresolved``
(occurrences the linker did not bind, on input that links cleanly -- each one
a resolver gap). ``check`` fails on *any* difference, in either direction: a
regression is a bug, and an improvement is progress that should be recorded
by regenerating the baseline in the same change.

Usage::

    PYTHONPATH=python python3 scripts/occgate.py report
    PYTHONPATH=python python3 scripts/occgate.py baseline
    PYTHONPATH=python python3 scripts/occgate.py check
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "tests" / "python" / "baselines" / "occurrences.json"

#: `exec <kind>`: the kind is lexed as an ID but names nothing.
EXEC_KINDS = {"body", "header", "declaration", "run_start", "run_end",
              "init_down", "init_up", "init", "pre_solve", "post_solve",
              "pre_body"}


def _exempt(code):
    """Indexes of ID tokens that are contextual keywords, not names:
    `exec <kind>`, the language in `exec <kind> <lang> = ...`, and the
    language in `import [target|solve] <lang> [static] function ...`."""
    out = set()
    for i, t in enumerate(code):
        if t.type_name != "ID":
            continue
        prev = code[i - 1].text if i else ""
        nxt = code[i + 1].text if i + 1 < len(code) else ""
        if prev == "exec" and t.text in EXEC_KINDS:
            out.add(i)
        elif i - 1 in out and nxt == "=":
            out.add(i)
        elif nxt in ("function", "static") and prev in ("import", "target", "solve"):
            out.add(i)
    return out


def check_file(fn):
    # The path is pinned by _run_child (see _pssparser_root).
    import pssparser
    from pssparser import refs, tokens

    p = pssparser.Parser()
    try:
        p.parse([fn])
        p.link()
    except pssparser.ParseException:
        return None

    src = Path(fn).read_text(encoding="utf-8")
    code = tokens.tokenize(src).code()
    exempt = _exempt(code)
    inactive = p.inactive_regions()

    def in_inactive(line, col):
        return any((r.start_line, r.start_col) <= (line, col) <= (r.end_line, r.end_col)
                   for r in inactive)

    ids = {(t.line, t.col + 1): t.text for i, t in enumerate(code)
           if t.type_name == "ID" and i not in exempt
           and not in_inactive(t.line, t.col + 1)}
    strings = [(t.line, t.col + 1, t.stop - t.start + 1, t.text) for t in code
               if "STRING" in t.type_name]

    def in_string(line, col):
        for (sl, sc, n, text) in strings:
            # Walk the token's text to find where it ends.
            el, ec = sl, sc
            for ch in text:
                if ch == "\n":
                    el, ec = el + 1, 1
                else:
                    ec += 1
            if (sl, sc) <= (line, col) <= (el, ec):
                return True
        return False

    occs = refs.occurrences(p)
    have = {(o.line, o.col): o for o in occs}
    return {
        "missing": sorted("%s@%d:%d" % (v, l, c) for (l, c), v in ids.items()
                          if (l, c) not in have),
        "stray": sorted("%s@%d:%d" % (o.text, o.line, o.col) for o in occs
                        if (o.line, o.col) not in ids and not in_string(o.line, o.col)),
        "unresolved": sorted("%s@%d:%d" % (o.text, o.line, o.col) for o in occs
                             if o.resolution == "unresolved"),
        "count": len(occs),
    }



def _pssparser_root():
    """The directory a child process must import ``pssparser`` from.

    The child has to test the same parser as this run. That is the working
    tree when the compiled extension is built in it (``build_ext --inplace``,
    a developer machine), and otherwise the copy this process imports -- in CI,
    the installed wheel: there the tree holds only the Python sources, and
    putting it first made every child fail with ``No module named
    'pssparser.core'``. Same rule as tests/python/isolation.py's
    ``_parent_package_root``, with the tree preferred so that a plain
    ``python scripts/...`` run never picks up another checkout (P7-X1).
    """
    tree = ROOT / "python"
    if any((tree / "pssparser").glob("core*.so")) \
            or any((tree / "pssparser").glob("core*.pyd")):
        return str(tree)
    try:
        import pssparser
        if getattr(pssparser, "__file__", None):
            return str(Path(pssparser.__file__).resolve().parents[1])
    except ImportError:
        pass
    return str(tree)


def _run_child(fn):
    env = dict(os.environ)
    env["PYTHONPATH"] = _pssparser_root() + os.pathsep + env.get("PYTHONPATH", "")
    env["PSSPARSER_NO_EXTENSIONS"] = "1"
    r = subprocess.run([sys.executable, __file__, "_file", fn],
                       capture_output=True, text=True, env=env, timeout=300)
    if r.returncode != 0:
        return {"crashed": r.stderr[-400:]}
    return json.loads(r.stdout)


def measure():
    sys.path.insert(0, str(ROOT / "scripts"))
    from refcov import corpus_files
    files = corpus_files()
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        results = list(ex.map(_run_child, files))
    out = {}
    for fn, r in zip(files, results):
        if r is None:
            continue
        rel = os.path.relpath(fn, ROOT)
        if "crashed" in r:
            out[rel] = {"crashed": True}
            continue
        entry = {k: r[k] for k in ("missing", "stray", "unresolved") if r[k]}
        if entry:
            out[rel] = entry
    return {"files": len(files), "gaps": out}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["report", "baseline", "check", "_file"])
    ap.add_argument("file", nargs="?")
    a = ap.parse_args()

    if a.cmd == "_file":
        print(json.dumps(check_file(a.file)))
        return 0

    m = measure()
    if a.cmd == "report":
        print(json.dumps(m, indent=1))
        return 0
    if a.cmd == "baseline":
        BASELINE.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        print("wrote", os.path.relpath(BASELINE, ROOT))
        return 0

    base = json.loads(BASELINE.read_text())
    if base == json.loads(json.dumps(m, sort_keys=True)):
        return 0
    for fn in sorted(set(base["gaps"]) | set(m["gaps"])):
        b, n = base["gaps"].get(fn, {}), m["gaps"].get(fn, {})
        if b != n:
            print("%s\n  baseline: %s\n  now:      %s" % (fn, b, n))
    if base["files"] != m["files"]:
        print("corpus size: baseline %d, now %d" % (base["files"], m["files"]))
    return 1


if __name__ == "__main__":
    sys.exit(main())
