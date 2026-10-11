#!/usr/bin/env python3
"""Run every pyastbuilder backend over ast/*.yaml into one directory.

Used as a gate when pyastbuilder itself changes (astbuilder-sphinx-plan.md
S0/S1): snapshot before the change, snapshot after, and compare.

    scripts/astbuilder_snapshot.py OUT_DIR
    scripts/astbuilder_snapshot.py --compare BEFORE_DIR AFTER_DIR

The backends and arguments match the build (scripts/gen_ast.py,
wasm/CMakeLists.txt, src/lint/lint.cmake, ts/package.json), so the snapshot is
what a build would compile.  It never writes into the source tree.
"""
from __future__ import annotations

import argparse
import filecmp
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_AST = str(_ROOT / "ast")
_LICENSE = str(_ROOT / "etc" / "copyright.cpp")


def _run(args, cwd):
    os.makedirs(cwd, exist_ok=True)
    r = subprocess.run([sys.executable, "-m", "astbuilder"] + args, cwd=cwd,
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if r.returncode != 0:
        sys.exit("astbuilder %s failed:\n%s" % (args[0], r.stdout))


def snapshot(out: Path):
    out = out.resolve()
    _run(["gen-cpp", "-name", "ast", "-namespace", "pssp::ast", "-astdir", _AST,
          "-license", _LICENSE], out / "cpp")
    # gen-pyext writes its extension sources to -o, relative to the cwd.
    _run(["gen-pyext", "-name", "ast", "-namespace", "pssp::ast", "-astdir", _AST,
          "-package", "pssparser.ast", "-o", "../pyext"], out / "pyext-cwd")
    _run(["gen-ts", "-astdir", _AST, "-o", str(out / "ts")], out)
    _run(["gen-wasm", "-astdir", _AST, "-cpp", str(out / "wasm-cpp"),
          "-ts", str(out / "wasm-ts"), "-license", _LICENSE], out)
    _run(["gen-census", "-astdir", _AST, "-py", str(out / "census-py"),
          "-ts", str(out / "census-ts")], out)
    _run(["gen-reflect", "-astdir", _AST, "-o", str(out / "reflect"),
          "-namespace", "pssp::ast", "-license", _LICENSE], out)


def _files(d: Path):
    return {str(p.relative_to(d)) for p in d.rglob("*") if p.is_file()}


def compare(a: Path, b: Path) -> int:
    fa, fb = _files(a), _files(b)
    bad = 0
    for f in sorted(fa - fb):
        print("only in %s: %s" % (a, f)); bad += 1
    for f in sorted(fb - fa):
        print("only in %s: %s" % (b, f)); bad += 1
    for f in sorted(fa & fb):
        if not filecmp.cmp(a / f, b / f, shallow=False):
            print("differs: %s" % f); bad += 1
    print("%d files compared, %d differences" % (len(fa | fb), bad))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--compare", nargs=2, metavar=("BEFORE", "AFTER"))
    ap.add_argument("out", nargs="?")
    args = ap.parse_args()
    if args.compare:
        sys.exit(compare(Path(args.compare[0]), Path(args.compare[1])))
    if not args.out:
        ap.error("OUT_DIR is required")
    snapshot(Path(args.out))


if __name__ == "__main__":
    main()
