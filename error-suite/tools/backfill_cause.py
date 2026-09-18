#!/usr/bin/env python3
"""Insert authored `cause:` / `not_cause:` / `names:` into case headers.

Not a generator. The terms live in `cause_terms.py`, authored per case from the
*defect* — never from what any tool says about it, which is the failure design
§5.6 warns about: a rubric written to agree with the tool it grades finds
nothing.

The mechanical part this script does own is the hazard: the `//!` header is part
of the file the tool is handed, so adding header lines shifts every body line,
and `at:`, `also:` and `fix:` all count from line 1. Each is renumbered by the
number of lines inserted. A `.ok.pss` sibling gets the same insertion so the
two files stay line-aligned.

    python3 tools/backfill_cause.py --dry-run
    python3 tools/backfill_cause.py

Verification is not this script's job and must not be: run the corpus before
and after and diff the per-case statuses. If renumbering broke a case, its
status changes.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cause_terms import TERMS  # noqa: E402

SUITE = Path(__file__).resolve().parent.parent
ORDER = ("cause", "not_cause", "names")

# `-` belongs in a key: `at-file` and `max-errors` are both real.  Without
# it `existing_keys` under-reports and, worse, the `at-file:` lookup in
# `insert` never matches -- so a case whose `at:` counts from a companion
# file would have been renumbered as if it counted from this one.
_DIRECTIVE = re.compile(r"^//!\s*(?P<key>[A-Za-z_][\w.-]*)\s*:\s*(?P<val>.*)$")
# `(?s)` and an explicit trailing group: these run over lines kept with their
# line endings, and `.*$` silently drops the `\n`, which glues the next
# directive onto this one.  That is not a hypothetical -- it happened.
_AT = re.compile(r"(?s)^(//!\s*at\s*:\s*)(\d+)(:.*)$")
_ALSO = re.compile(r"(?s)^(//!\s*also\s*:\s*)(\d+)(:.*)$")
_FIX = re.compile(r"(?s)^(//!\s*fix\s*:\s*)(\d+)(:.*)$")
# `pssparser.at:` and friends: a per-tool override of `at:`, counted from the
# same line 1.  Missed on the first pass, which is why the before/after status
# diff is not the only check -- this one only showed up in the *other* reader's
# tests, because a namespaced directive is invisible to the neutral one.
_TOOL_AT = re.compile(r"(?s)^(//!\s*[\w.]+\.at\s*:\s*)(\d+)(:.*)$")


def header_len(lines: list[str]) -> int:
    i = 0
    while i < len(lines) and lines[i].startswith("//!"):
        i += 1
    return i


def key_width(lines: list[str]) -> int:
    """Match the file's own alignment rather than imposing one."""
    widths = []
    for line in lines[:header_len(lines)]:
        m = _DIRECTIVE.match(line)
        if m:
            widths.append(line.index(":") - 3)
    return max(widths) if widths else 10


def existing_keys(lines: list[str]) -> set[str]:
    return {m.group("key") for line in lines[:header_len(lines)]
            if (m := _DIRECTIVE.match(line))}


def renumber(line: str, shift: int, own_file: bool) -> str:
    """Bump a header line number by *shift*.

    `own_file` is false for a case whose `at:` names a companion: that line
    number counts from the companion's line 1, which this edit does not touch.
    """
    for pattern in (_AT, _TOOL_AT, _ALSO, _FIX):
        m = pattern.match(line)
        if m:
            if pattern in (_AT, _TOOL_AT) and not own_file:
                return line
            return f"{m.group(1)}{int(m.group(2)) + shift}{m.group(3)}"
    return line


def insert(text: str, entries: dict[str, str], *, shift_lines: bool,
           own_name: str = "") -> str:
    lines = text.splitlines(keepends=True)
    n = header_len(lines)
    have = existing_keys(lines)
    new = [(k, v) for k, v in ((k, entries.get(k)) for k in ORDER)
           if v and k not in have]
    if not new:
        return text

    width = key_width(lines)
    eol = "\n"
    block = [f"//! {k + ':':<{width + 1}} {v}{eol}" for k, v in new]

    # `at-file:` naming a *companion* means `at:` counts from that file's
    # line 1, which this edit does not touch. Naming this file is redundant
    # but legal, and does shift.
    own_file = True
    for line in lines[:n]:
        m = _DIRECTIVE.match(line)
        if m and m.group("key") == "at-file":
            own_file = m.group("val").strip() == own_name
            break
    head = lines[:n]
    if shift_lines:
        head = [renumber(line, len(block), own_file) for line in head]
    return "".join(head + block + lines[n:])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cases = {}
    for path in (SUITE / "cases").rglob("*.pss"):
        if path.name.startswith("_") or path.name.endswith(".ok.pss"):
            continue
        text = path.read_text(encoding="utf-8")
        m = re.search(r"^//!\s*case\s*:\s*(\S+)", text, re.M)
        if m:
            cases[m.group(1)] = path

    missing = sorted(set(TERMS) - set(cases))
    if missing:
        print(f"error: no such case: {', '.join(missing)}", file=sys.stderr)
        return 2

    touched = 0
    for case_id, entries in sorted(TERMS.items()):
        path = cases[case_id]
        text = path.read_text(encoding="utf-8")
        out = insert(text, entries, shift_lines=True,
                     own_name=path.name)
        if out == text:
            continue
        touched += 1
        control = path.with_suffix(".ok.pss")
        if args.dry_run:
            print(f"would edit {path.relative_to(SUITE)}"
                  + (" (+ control)" if control.is_file() else ""))
            continue
        path.write_text(out, encoding="utf-8")
        if control.is_file():
            # The control is never loaded as a case; the insertion is purely
            # so the two files still line up when you diff them.
            ctext = control.read_text(encoding="utf-8")
            control.write_text(
                insert(ctext, entries, shift_lines=True, own_name=path.name),
                encoding="utf-8")
    print(f"{touched} case(s) {'would be ' if args.dry_run else ''}updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
