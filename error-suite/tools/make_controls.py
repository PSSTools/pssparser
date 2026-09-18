#!/usr/bin/env python3
"""Propose a control for every case that lacks one, and verify each proposal.

A control is the same file with the defect repaired, which must parse clean
(design §3.1).  Authoring 140 of them by hand is a day of work; guessing 140 of
them is worthless.  So this does both: it *searches* a small space of minimal
repairs and accepts a candidate only when a real parse of the repaired file
comes back clean.  A proposal that does not parse is never written.

The search is deliberately dumb and local -- append a `;`, close a brace, name
an unnamed field, drop the offending token -- because a clever repair that
changes what the case is about would defeat the point.  Candidates are tried
smallest-edit-first, and anything the search cannot fix is listed for manual
authoring rather than papered over.

Requires an importable pssparser (PYTHONPATH=python).  Usage:

    python3 error-suite/tools/make_controls.py            # dry run
    python3 error-suite/tools/make_controls.py --apply
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))

from pss_errsuite.case import Case, collect_cases, load_case  # noqa: E402

CASES = SUITE_ROOT / "cases"

#: Directives whose value begins with a line number and must be rebased when
#: the header grows.  (Same rule as port_corpus.py; getting it wrong turns
#: every case in the file into a mislocation.)
_LINE_NUMBERED = {"at", "also", "fix"}
_HEADER_RE = re.compile(r"^//!\s*([A-Za-z_][A-Za-z0-9_.-]*):(\s*)(.*)$")


def parses_clean(files: list[tuple[str, str]]) -> bool:
    """True if pssparser reports no error on *files*."""
    from pssparser import Parser
    from pssparser.parser import ParseException
    parser = Parser()
    try:
        parser.parse_files = None       # (no-op; keeps linters quiet)
    except Exception:
        pass
    try:
        parser.parses(files)
        parser.link()
    except ParseException:
        return False
    except Exception:
        return False
    return not any(m.get("severity") == "error" for m in parser.markers)


def header_length(source: str) -> int:
    n = 0
    for line in source.splitlines():
        if not line.startswith("//!"):
            break
        n += 1
    return n


def candidates(source: str, at_line: int | None) -> list[list[str]]:
    """Minimal repairs, smallest edit first.  Header lines are never touched."""
    lines = source.splitlines()
    head = header_length(source)
    out: list[list[str]] = []

    def variant(mutate):
        copy = list(lines)
        if mutate(copy) is not False:
            out.append(copy)

    body = range(head, len(lines))
    near = []
    if at_line is not None:
        # The line *above* the reported one comes first: the classic defect
        # is a terminator missing at the end of the previous line, which the
        # parser only notices at the head of this one.
        for i in (at_line - 2, at_line - 1, at_line, at_line - 3):
            if head <= i < len(lines):
                near.append(i)
    near += [i for i in body if i not in near]

    # 1. a missing terminator or closer, inserted at a plausible point on a
    #    nearby line.  Position matters: `struct S { int x }` is repaired by
    #    `int x;`, not by `… }` + `;`, and only the first is the same case with
    #    the defect removed.
    for i in near:
        line = lines[i]
        stripped = line.rstrip()
        if re.fullmatch(r"[\s)\]}]*", stripped):
            # Nothing but closers: inserting here *moves* the terminator to
            # the next line rather than supplying the missing one, which
            # parses but is not the case with its defect removed.
            continue
        points = {len(stripped)}
        m = re.search(r"[)\]}]+\s*$", stripped)
        if m:
            points.add(m.start())          # before the trailing closer(s)
        for p in sorted(points):
            for token in (";", ")", "}", "]", ">", ");"):
                variant(lambda c, i=i, p=p, t=token: c.__setitem__(
                    i, (c[i][:p].rstrip() + t + " " + c[i][p:].strip()).rstrip()
                    if p < len(c[i].rstrip()) else c[i].rstrip() + t))

    # 2. an unnamed declaration: `int ;` -> `int x;`  (one line, then all)
    for i in near:
        if re.search(r"\b(int|bit|bool|string)\s*;", lines[i]):
            variant(lambda c, i=i: c.__setitem__(
                i, re.sub(r"\b(int|bit|bool|string)\s*;", r"\1 x;", c[i])))
    if any(re.search(r"\b(int|bit|bool|string)\s*;", l) for l in lines[head:]):
        out.append(lines[:head] + [
            re.sub(r"\b(int|bit|bool|string)\s*;", r"\1 x;", l)
            for l in lines[head:]])

    # 3. drop the offending line entirely
    for i in near:
        variant(lambda c, i=i: c.__delitem__(i))

    # 4. an unclosed construct: close it at end of file
    for k in (1, 2, 3, 4):
        out.append(lines + ["}" * 1] * k)

    # 5. the token at the reported column is spurious: cut it
    if at_line is not None and head <= at_line - 1 < len(lines):
        i = at_line - 1
        for m in re.finditer(r"\S+", lines[i]):
            variant(lambda c, i=i, m=m: c.__setitem__(
                i, (c[i][:m.start()] + c[i][m.end():]).rstrip()))

    return out


def companions(case: Case) -> list[tuple[str, str]]:
    return [(p.name, p.read_text())
            for p in case.input_files() if p.name != case.path.name]


def find_control(case: Case) -> list[str] | None:
    at_line = case.at.line if case.at else None
    others = companions(case)
    for cand in candidates(case.source, at_line):
        text = "\n".join(cand) + "\n"
        files = []
        for name, content in [(case.path.name, text)] + others:
            files.append((name, content))
        if case.files:                       # preserve the declared order
            by_name = dict(files)
            files = [(n, by_name[n]) for n in case.files]
        if parses_clean(files):
            return cand
    return None


def single_line_change(source: str, repaired: list[str]) -> tuple[int, str] | None:
    original = source.splitlines()
    if len(original) != len(repaired):
        return None
    diff = [i for i, (a, b) in enumerate(zip(original, repaired)) if a != b]
    if len(diff) != 1:
        return None
    return diff[0] + 1, repaired[diff[0]]


def with_fix_directive(source: str, lineno: int, text: str) -> str:
    """Insert `//! fix: N: text`, rebasing every line-numbered directive."""
    lines = source.splitlines()
    head = header_length(source)
    rebased = []
    for line in lines[:head]:
        m = _HEADER_RE.match(line)
        key, gap, value = m.group(1), m.group(2), m.group(3)
        if key in _LINE_NUMBERED:
            value = re.sub(r"^(\d+)", lambda mm: str(int(mm.group(1)) + 1),
                           value)
        rebased.append(f"//! {key}:{gap}{value}")
    width = max((len(k) for k in ("fix",)), default=3)
    fix_line = f"//! fix:{' ' * max(1, len('pssparser.match:') - len('fix:'))}" \
               f"{lineno + 1}:{text}"
    return "\n".join(rebased + [fix_line] + lines[head:]) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--filter", default=None,
                    help="only cases whose class starts with this")
    args = ap.parse_args()

    fixed = sibling = failed = 0
    for case in collect_cases(CASES):
        if case.expect == "accept" or case.control_source() is not None:
            continue
        if args.filter and not case.cls.startswith(args.filter):
            continue
        repaired = find_control(case)
        if repaired is None:
            print(f"MANUAL  {case.name}")
            failed += 1
            continue
        change = single_line_change(case.source, repaired)
        if change is not None:
            lineno, text = change
            print(f"fix     {case.name}: {lineno}:{text.strip()[:50]}")
            if args.apply:
                case.path.write_text(
                    with_fix_directive(case.source, lineno, text))
            fixed += 1
        else:
            print(f"ok.pss  {case.name}")
            if args.apply:
                case.control_path.write_text("\n".join(repaired) + "\n")
            sibling += 1
    print(f"\n{fixed} fix: directive(s), {sibling} .ok.pss sibling(s), "
          f"{failed} need manual authoring")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
