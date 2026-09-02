"""Loader for the L1 curated error corpus.

Each corpus case is a ``.pss`` file under ``tests/python/errors/data/`` whose
leading lines are a ``//!`` directive header — still a valid PSS comment, so
the file is also a valid input you can hand to the CLI while debugging.  See
``docs/design/error-testing-strategy.md`` §4 (L1) for the format rationale.

Header grammar, one directive per line, in any order, header ends at the
first non-``//!`` line::

    //! id:     PSS020
    //! at:     1:13
    //! match:  expected ';'
    //! also:   4:1 "input ends here"
    //! count:  1
    //! severity: error
    //! hint:   did you mean
    //! max-errors: 5
    //! xfail:  D1 -- token-set jargon leaks into the message

``at`` is ``line:col`` or ``line:col-col`` for a span.  ``match`` is a plain
substring unless wrapped in ``/regex/``.  ``also`` is repeatable.  Header
parsing is strict: an unknown directive is an error, not a silently ignored
line -- a typo'd directive that silently disables an assertion is exactly the
failure mode this layer exists to catch.

Two more directives exist solely for S12 (``data/multifile/``), the one
category where a single ``.pss`` file is not the whole input:

* ``files`` -- a comma-separated, ordered list of filenames to feed to
  ``Parser.parses()`` together, e.g. ``files: _a.pss, case.pss, _c.pss``.
  Exactly one entry must equal the case file's own name; the others are
  *companion* files living beside it in the same directory, with **no**
  ``//!`` header of their own (their raw text is fed to the parser as-is).
  Companion files are named with a leading underscore (``_a.pss``) so
  ``collect_cases()`` does not also try to load them as standalone cases --
  see the leading-underscore skip below. When ``files`` is absent (the
  common case), the case behaves exactly as it always has: a single file,
  fed to the parser alone.
* ``at-file`` -- the filename the primary marker's ``file`` field is
  expected to equal. Defaults to the case file's own name. Only meaningful
  alongside ``files``, where the error may legitimately be attributed to a
  companion file rather than the header-bearing one.

Companion files (leading-underscore ``.pss`` names) are skipped by
``collect_cases()``'s directory walk -- they are fragments referenced by a
``files:`` directive, not independent corpus cases, and have no header to
parse.

The full file, header included, is fed to the parser (that is what makes it a
valid CLI input too) -- so ``at:`` line numbers count the header lines. This
means every line added to or removed from the header shifts ``at:`` by one;
there is no way around this without breaking the "hand it to the CLI" property,
so just recount after editing a header.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

DATA_DIR = Path(__file__).parent / "data"

_KNOWN_DIRECTIVES = {
    "id", "at", "match", "also", "count", "severity", "hint",
    "max-errors", "xfail", "files", "at-file",
}

_HEADER_LINE_RE = re.compile(r"^//!\s*([a-zA-Z-]+):\s*(.*)$")
_AT_RE = re.compile(r"^(\d+):(\d+)(?:-(\d+))?$")
_ALSO_RE = re.compile(r'^(\d+):(\d+)\s+"([^"]*)"$')


class CorpusFormatError(Exception):
    """Raised for a malformed ``//!`` header."""


@dataclass
class RelatedExpectation:
    line: int
    col: int
    label: str


@dataclass
class CorpusCase:
    path: Path
    code: str
    id: Optional[str] = None
    at: Optional[Tuple[int, int, Optional[int]]] = None
    match: Optional[str] = None
    match_is_regex: bool = False
    also: List[RelatedExpectation] = field(default_factory=list)
    count: int = 1
    severity: str = "error"
    hint: Optional[str] = None
    max_errors: Optional[int] = None
    xfail: Optional[str] = None
    files: Optional[List[str]] = None
    at_file: Optional[str] = None

    @property
    def name(self) -> str:
        return str(self.path.relative_to(DATA_DIR))


def _parse_at(raw: str, path: Path) -> Tuple[int, int, Optional[int]]:
    m = _AT_RE.match(raw.strip())
    if not m:
        raise CorpusFormatError(
            f"{path}: malformed 'at:' directive {raw!r}; expected 'line:col' "
            f"or 'line:col-col'"
        )
    line, col, col_end = m.groups()
    return int(line), int(col), int(col_end) if col_end else None


def _parse_also(raw: str, path: Path) -> RelatedExpectation:
    m = _ALSO_RE.match(raw.strip())
    if not m:
        raise CorpusFormatError(
            f"{path}: malformed 'also:' directive {raw!r}; expected "
            f"'line:col \"label\"'"
        )
    line, col, label = m.groups()
    return RelatedExpectation(int(line), int(col), label)


def parse_case(path: Path) -> CorpusCase:
    text = path.read_text()
    lines = text.splitlines(keepends=True)

    header_end = 0
    directives: List[Tuple[str, str]] = []
    for line in lines:
        stripped = line.rstrip("\n")
        if not stripped.startswith("//!"):
            break
        m = _HEADER_LINE_RE.match(stripped)
        if not m:
            raise CorpusFormatError(
                f"{path}: malformed header line {stripped!r}"
            )
        key, value = m.group(1), m.group(2)
        if key not in _KNOWN_DIRECTIVES:
            raise CorpusFormatError(
                f"{path}: unknown directive '{key}:' (known: "
                f"{', '.join(sorted(_KNOWN_DIRECTIVES))})"
            )
        directives.append((key, value))
        header_end += len(line)

    case = CorpusCase(path=path, code=text)

    for key, value in directives:
        value = value.strip()
        if key == "id":
            case.id = value
        elif key == "at":
            case.at = _parse_at(value, path)
        elif key == "match":
            if value.startswith("/") and value.endswith("/") and len(value) > 1:
                case.match = value[1:-1]
                case.match_is_regex = True
            else:
                case.match = value
        elif key == "also":
            case.also.append(_parse_also(value, path))
        elif key == "count":
            case.count = int(value)
        elif key == "severity":
            case.severity = value
        elif key == "hint":
            case.hint = value
        elif key == "max-errors":
            case.max_errors = int(value)
        elif key == "xfail":
            case.xfail = value or "(no reason given)"
        elif key == "files":
            case.files = [v.strip() for v in value.split(",") if v.strip()]
        elif key == "at-file":
            case.at_file = value

    if case.files is not None and path.name not in case.files:
        raise CorpusFormatError(
            f"{path}: 'files:' directive {case.files!r} does not include "
            f"the case file's own name {path.name!r}"
        )

    if case.id is None:
        raise CorpusFormatError(f"{path}: missing required 'id:' directive")
    if case.match is None and case.at is None:
        raise CorpusFormatError(
            f"{path}: header must assert at least one of 'at:' or 'match:'"
        )

    return case


#: Directories under DATA_DIR that hold ``.pss`` fixtures for a *different*
#: harness and are not L1 corpus cases -- ``golden/`` backs the L3 rendered-
#: output goldens (``test_golden.py``), whose sources are plain PSS files
#: with no ``//!`` header (the assertion is the full captured CLI output,
#: not a marker-dict directive).
_EXCLUDED_DIRS = {"golden"}


def collect_cases(root: Path = DATA_DIR) -> List[CorpusCase]:
    """Discover and parse every ``.pss`` file under *root*, sorted by path."""
    return [
        parse_case(p)
        for p in sorted(root.rglob("*.pss"))
        if p.relative_to(root).parts[0] not in _EXCLUDED_DIRS
        and not p.name.startswith("_")
    ]
