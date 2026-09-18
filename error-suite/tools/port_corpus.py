#!/usr/bin/env python3
"""One-shot, re-runnable port of pssparser's L1 corpus into the error suite.

`tests/python/errors/data/**.pss` → `error-suite/cases/<class>/…`, rewriting
the header from pssparser's vocabulary into the tool-neutral one and
namespacing everything that is an assertion about *our* output
(``id`` → ``pssparser.id``, and so on -- error-suite-plan.md §0.4).

Two things here are easy to get wrong and are therefore done mechanically:

*Line numbers shift.*  The header is part of the file, so `at:`, `also:` and
`fix:` count header lines.  The neutral header is longer than the native one,
so every line-numbered directive is rebased by the difference.  Get this wrong
and 137 cases silently become `detected_mislocated`, which reads as a pssparser
regression rather than a porting bug.

*Values are copied verbatim.*  The transformation is line-by-line rather than
parse-and-re-serialize, so an `at:` span or a `match:` regex arrives byte-exact
on the other side.

Run from anywhere:  python3 error-suite/tools/port_corpus.py [--apply]
Without --apply it prints what it would write and touches nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SUITE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SUITE_ROOT.parent
LEGACY_DATA = REPO_ROOT / "tests" / "python" / "errors" / "data"
DEST = SUITE_ROOT / "cases"

#: Legacy directory → suite class.  `None` means "decided per file", below.
DIR_CLASS = {
    "braces": "syntax.braces",
    "expr": "syntax.expr",
    "keywords": "syntax.keyword",
    "lex": "syntax.lex",
    "multifile": "syntax.multifile",
    "names": "syntax.names",
    "punct": "syntax.punct",
    "recover": "syntax.recover",
    "reserved": "syntax.reserved",
    "scope": "syntax.scope",
    "stmts": "syntax.stmt",
    "types": "syntax.type",
    "volume": "syntax.volume",
    "deprecated": "semantic.compile",
    "smoke": None,
    "syntax": None,
}

#: Per-file overrides.  The `syntax/` and `smoke/` directories were named after
#: pssparser's *marker* classification rather than after the defect, so their
#: cases belong wherever the defect does.
FILE_CLASS = {
    "syntax/expected_identifier.pss": "syntax.names",
    "syntax/expected_punctuation.pss": "syntax.punct",
    "syntax/unclassified_syntax_error.pss": "syntax.names",
    "syntax/unexpected_eof.pss": "syntax.braces",
    "syntax/unexpected_keyword.pss": "syntax.reserved",
    "syntax/unexpected_punctuation.pss": "syntax.punct",
    "syntax/unexpected_token.pss": "syntax.names",
    "smoke/keyword_jargon.pss": "syntax.lex",
    "smoke/missing_semicolon.pss": "syntax.punct",
    # Template strings and template-directive lexing are their own class.
    "lex/mustache_literal_braces_hint.pss": "syntax.template",
    "lex/mustache_malformed_expression.pss": "syntax.template",
    "lex/mustache_unterminated_expression.pss": "syntax.template",
    "lex/template_comment_unterminated.pss": "syntax.template",
    "lex/template_directive_malformed.pss": "syntax.template",
    "lex/template_directive_unterminated.pss": "syntax.template",
    # These two are link-time, not syntax: arity and defaults of template
    # parameters.
    "types/array_template_arity_extra_arg.pss": "semantic.template",
    "types/missing_template_arg_default.pss": "semantic.template",
}

#: `validate` requires an `lrm:` citation on every `semantic.*` case, and on
#: anything marked `detect: required`.
#:
#: Syntax cases cite **Annex B** (normative, "Formal syntax"): the input is not
#: derivable from the grammar, so a conforming tool must reject it.  That is a
#: real citation rather than a rubber stamp -- but it is deliberately the whole
#: annex, not a sub-clause, because deciding that a particular input violates
#: B.11 rather than B.3 is a judgement no script should make.  Sub-clauses get
#: filled in by hand as classes are reviewed.
#:
#: The semantic classes cite the clause that governs them.  Neither is promoted
#: to `required` here: a semantic "shall" has to be read before it is claimed.
CLASS_LRM = {
    "semantic.template": "10",
    "semantic.compile": "19.2",
}

SYNTAX_LRM = "B"

#: Syntax cases are `detect: required` -- a tool that accepts a file the
#: grammar cannot generate is wrong, full stop -- *except* these, which are
#: about pssparser's error **cap** rather than about the language.  A tool with
#: no cap, or a different one, is not wrong; `requires: max_errors` keeps it out
#: of the run, and `recommended` keeps it out of the headline either way.
CAP_CASES = {
    "volume/cap_default_twenty.pss",
    "volume/cap_fires_at_five.pss",
    "volume/cap_fires_at_one.pss",
    "volume/max_errors_cap_fires.pss",
}

#: Two legacy cases assert only `match:`.  The suite requires a location -- that
#: is most of what it measures -- so the missing `at:` is supplied here, in the
#: *legacy* line numbering, and rebased with everything else.
AT_OVERRIDE = {
    "punct/cascade_garbage_tokens.pss": "7:13",
    "volume/max_errors_cap_fires.pss": "8:17",
}

#: Where *we* actually point, when that differs from where a good diagnostic
#: would.  Written as `pssparser.at:` so the neutral `at:` can state the ideal
#: without turning pytest red -- and so the gap is greppable, per case.
PSSPARSER_AT_OVERRIDE = {
    # We point at the second '@' of "@@@", one column past the run's start.
    "punct/cascade_garbage_tokens.pss": "7:14",
}

#: Cases whose legality is a PSS 3.1 question.
PSS_31 = {"semantic.compile"}

_ID_PREFIX = {"syntax": "SYN", "semantic": "SEM", "accept": "ACC"}

_HEADER_RE = re.compile(r"^//!\s*([A-Za-z_][A-Za-z0-9_.-]*):\s*(.*)$")
_LINE_REF_RE = re.compile(r"^(\d+)(.*)$", re.DOTALL)

#: Directives whose value starts with a line number that must be rebased.
_LINE_NUMBERED = {"at", "also", "fix"}

#: Directives that become `pssparser.<key>`.
_OURS = {"id", "match", "hint", "max-errors"}

#: Not cases: the L3 golden fixtures, and companion files.
_SKIP_DIRS = {"golden"}


def case_id(rel: Path, cls: str) -> str:
    prefix = _ID_PREFIX[cls.split(".", 1)[0]]
    family = cls.split(".", 1)[1].upper().replace("-", "")
    stem = rel.name[:-len(".pss")].replace(".", "-").replace("_", "-").upper()
    return f"{prefix}-{family}-{stem}"


def title_of(rel: Path) -> str:
    stem = rel.name[:-len(".pss")].replace(".", " ").replace("_", " ")
    return stem.strip()


def class_of(rel: Path) -> str | None:
    key = f"{rel.parts[0]}/{rel.name}"
    if key in FILE_CLASS:
        return FILE_CLASS[key]
    return DIR_CLASS.get(rel.parts[0])


def rebase(value: str, delta: int) -> str:
    m = _LINE_REF_RE.match(value)
    if not m:
        return value
    return f"{int(m.group(1)) + delta}{m.group(2)}"


def port_one(path: Path, rel: Path) -> tuple[Path, str] | None:
    cls = class_of(rel)
    if cls is None:
        print(f"  ?? no class for {rel}", file=sys.stderr)
        return None

    text = path.read_text()
    lines = text.splitlines()
    native: list[tuple[str, str]] = []
    body_start = 0
    for line in lines:
        if not line.startswith("//!"):
            break
        m = _HEADER_RE.match(line)
        if not m:
            raise SystemExit(f"{path}: malformed header line {line!r}")
        native.append((m.group(1), m.group(2).strip()))
        body_start += 1

    by_key = dict(native)
    severity = by_key.get("severity", "error")

    file_key = f"{rel.parts[0]}/{rel.name}"
    required = cls.startswith("syntax.") and file_key not in CAP_CASES
    head: list[tuple[str, str]] = [
        ("case", case_id(rel, cls)),
        ("class", cls),
        ("title", title_of(rel)),
        ("expect", severity),
        ("detect", "required" if required else "recommended"),
    ]
    if required:
        head.append(("lrm", SYNTAX_LRM))
    elif cls in CLASS_LRM:
        head.append(("lrm", CLASS_LRM[cls]))
    if cls in PSS_31:
        head.append(("pss", "3.1"))
    if "max-errors" in by_key:
        head.append(("requires", "max_errors"))

    tail: list[tuple[str, str]] = []
    if file_key in AT_OVERRIDE and "at" not in by_key:
        tail.append(("at", AT_OVERRIDE[file_key]))
    if file_key in PSSPARSER_AT_OVERRIDE:
        tail.append(("pssparser.at", PSSPARSER_AT_OVERRIDE[file_key]))
    for key, value in native:
        if key == "severity":
            continue                      # expressed as `expect:` above
        if key in _OURS:
            tail.append((f"pssparser.{key}", value))
        elif key == "xfail":
            tail.append(("xfail.pssparser", value))
        else:
            tail.append((key, value))

    delta = len(head) + len(tail) - len(native)
    tail = [(k, rebase(v, delta) if k in _LINE_NUMBERED else v)
            for k, v in tail]

    width = max(len(k) for k, _ in head + tail) + 2
    header = "".join(f"//! {(k + ':').ljust(width)}{v}\n".rstrip() + "\n"
                     for k, v in head + tail)
    return DEST / cls.replace(".", "/") / rel.name, header + "\n".join(
        lines[body_start:]) + ("\n" if text.endswith("\n") else "")


def companions(path: Path) -> list[Path]:
    return [p for p in sorted(path.parent.glob("_*.pss"))]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="write the files (default: dry run)")
    args = ap.parse_args()

    written = 0
    for path in sorted(LEGACY_DATA.rglob("*.pss")):
        rel = path.relative_to(LEGACY_DATA)
        if rel.parts[0] in _SKIP_DIRS or path.name.startswith("_"):
            continue
        ported = port_one(path, rel)
        if ported is None:
            continue
        dest, text = ported
        print(f"{rel}  ->  {dest.relative_to(SUITE_ROOT)}")
        if args.apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text)
            for comp in companions(path):
                (dest.parent / comp.name).write_text(comp.read_text())
            written += 1
    if args.apply:
        print(f"\nwrote {written} case(s) under {DEST}")
    else:
        print("\n(dry run; pass --apply to write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
