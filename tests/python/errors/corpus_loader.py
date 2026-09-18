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

``at`` is ``line:col``, ``line:col-col`` (same-line span) or
``line:col-line:col``.  ``match`` is a plain substring unless wrapped in
``/regex/``.  ``also`` is repeatable.  Header parsing is strict: an unknown
directive is an error, not a silently ignored line -- a typo'd directive that
silently disables an assertion is exactly the failure mode this layer exists to
catch.

**Two vocabularies, one file.**  The directives above assert things about
*pssparser* -- our marker ID, our exact wording, our error cap.  The
tool-neutral suite (``error-suite/``) describes the same cases in terms any PSS
tool can be measured against: ``case``, ``class``, ``expect``, ``detect``,
``at``, ``lrm``, ``fix``, ``cause``...  Both vocabularies are accepted here, so
a case file has one home rather than two::

    //! case:    SYN-PUNCT-SEMI-01     neutral: stable id, taxonomy, expectation
    //! class:   syntax.punct
    //! expect:  error
    //! at:      16:14
    //! fix:     16:         int a;
    //! pssparser.id:    PSS020        ours: namespaced
    //! pssparser.match: expected ';'
    //! xfail.pssparser: D1 -- ...

``<tool>.<key>`` for any other tool is parsed and ignored, which is what makes
the file portable.  ``expect: accept`` cases assert *silence* and therefore need
neither ``at:`` nor ``match:``.  See ``docs/design/error-suite-design.md`` §3.4
for why this is one corpus and not two.

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

#: Directives this loader has always understood.  Every one of them asserts
#: something about *pssparser's* output specifically -- an exact message, our
#: marker ID, our error cap -- which is why the tool-neutral suite namespaces
#: them as ``pssparser.<key>`` instead (see below).
_NATIVE_DIRECTIVES = {
    "id", "at", "match", "also", "count", "severity", "hint",
    "max-errors", "xfail", "files", "at-file",
}

#: Directives from the tool-neutral suite
#: (``error-suite/pss_errsuite/case.py``).  They are accepted here so that one
#: case file can be read by both loaders, which is what lets the two corpora be
#: a single corpus rather than a fork that diverges within a month (design
#: §3.4).  Most carry no meaning for pytest assertions; `expect` and `class` do.
_NEUTRAL_DIRECTIVES = {
    "case", "class", "title", "expect", "detect", "lrm", "pss", "tags",
    "requires", "fix", "cause", "not_cause", "names", "about",
}

_KNOWN_DIRECTIVES = _NATIVE_DIRECTIVES | _NEUTRAL_DIRECTIVES

#: ``pssparser.<key>`` sets the native directive ``<key>``; any other namespace
#: belongs to another tool and is ignored.  ``xfail.<tool>`` is spelled the
#: other way round (the suite's convention) and only ``xfail.pssparser``
#: applies here.
_OUR_NAMESPACE = "pssparser"

_HEADER_LINE_RE = re.compile(r"^//!\s*([A-Za-z_][A-Za-z0-9_.-]*):\s*(.*)$")
#: ``line:col``, ``line:col-col`` (same-line span, end column) or
#: ``line:col-line:col`` (the suite's spelling).  All three mean the same thing
#: and both loaders accept all three -- see error-suite-plan.md §0.4.
_AT_RE = re.compile(r"^(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")
_ALSO_RE = re.compile(r'^(\d+):(\d+)\s+"([^"]*)"$')
_FIX_RE = re.compile(r"^(\d+):\s?(.*)$")


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

    # -- neutral directives (error-suite) ---------------------------------
    # Carried so a case file has one home rather than two.  `expect` and
    # `class` are the only ones with behaviour here: `expect: accept` means the
    # case asserts *silence*, so the "at: or match:" requirement does not
    # apply to it.
    case_id: Optional[str] = None
    cls: Optional[str] = None
    title: Optional[str] = None
    expect: Optional[str] = None
    detect: Optional[str] = None
    lrm: Optional[str] = None
    pss: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    fix: List[Tuple[int, str]] = field(default_factory=list)
    cause: List[str] = field(default_factory=list)
    not_cause: List[str] = field(default_factory=list)
    names: List[str] = field(default_factory=list)
    #: ``program`` (the default) or ``tool`` -- see the suite's
    #: ``case.ABOUT_KINDS``.  Carried only so the two loaders agree.
    about: str = "program"
    #: The full ``at:`` span ``(end_line, end_col)``, kept even when it crosses
    #: a line and ``at``'s third element therefore cannot hold it.
    at_end: Optional[Tuple[int, int]] = None
    #: Set only when ``pssparser.at:`` overrode the neutral ``at:``: the
    #: location a *good* diagnostic would carry, as opposed to ours.
    neutral_at: Optional[Tuple[int, int, Optional[int]]] = None
    neutral_at_end: Optional[Tuple[int, int]] = None
    #: ``{tool: {key: value}}`` for namespaces other than ours.
    other_tools: dict = field(default_factory=dict)

    @property
    def name(self) -> str:
        try:
            return str(self.path.relative_to(DATA_DIR))
        except ValueError:
            return str(self.path)


def _parse_at(raw: str, path: Path) -> Tuple[int, int, Optional[int], Optional[int]]:
    """Returns the full span ``(line, col, end_line, end_col)``.

    Callers that can only express a same-line extent -- which is all of them
    today, since ``IMarker::extent()`` is a length and ``--json`` has no
    ``end_line`` at all (known-issues ES-S1) -- read ``CorpusCase.at``, whose
    end column is dropped when the span crosses a line.  ``CorpusCase.at_end``
    keeps what was written either way, so nothing is lost in the round trip.
    """
    m = _AT_RE.match(raw.strip())
    if not m:
        raise CorpusFormatError(
            f"{path}: malformed 'at:' directive {raw!r}; expected 'line:col', "
            f"'line:col-col' or 'line:col-line:col'"
        )
    line, col, end_line, end_col = m.groups()
    line, col = int(line), int(col)
    if end_col is None:
        return line, col, None, None
    return line, col, (int(end_line) if end_line is not None else line), int(end_col)


_LIST_SEP = re.compile(r"(?<!\\),")


def _split_list(raw: str) -> List[str]:
    r"""Comma-separated, always.  Not ``;`` -- that is a plausible ``cause:``
    term for a punctuation case (error-suite-plan.md §0.9).

    ``\,`` is a literal comma, because a `cause:` term may *be* one: a missing
    separator in an argument list is a defect whose accurate diagnostic says
    `','`.  Must stay identical to ``pss_errsuite.case._split_list`` --
    ``test_both_loaders_extract_the_same_facts_from_every_suite_case`` is what
    holds the two readers together, and it caught this one.
    """
    return [v.strip().replace("\\,", ",")
            for v in _LIST_SEP.split(raw) if v.strip()]


def _parse_fix(raw: str, path: Path) -> Tuple[int, str]:
    m = _FIX_RE.match(raw)
    if not m:
        raise CorpusFormatError(
            f"{path}: malformed 'fix:' directive {raw!r}; expected "
            f"'LINE: replacement'"
        )
    return int(m.group(1)), m.group(2)


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
    other: dict = {}
    override_at: Optional[str] = None
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
        if "." in key:
            head, _, tail = key.partition(".")
            if head == "xfail":
                # xfail.<tool>: only ours applies; another tool's known-bad is
                # not our problem and must not silently become one.
                if tail == _OUR_NAMESPACE:
                    directives.append(("xfail", value))
                else:
                    other.setdefault(tail, {})["xfail"] = value
            elif head == _OUR_NAMESPACE:
                native_key = tail.replace("_", "-")
                if native_key not in _NATIVE_DIRECTIVES:
                    raise CorpusFormatError(
                        f"{path}: unknown directive '{key}:'; "
                        f"'{_OUR_NAMESPACE}.<key>' takes one of "
                        f"{', '.join(sorted(_NATIVE_DIRECTIVES))}"
                    )
                if native_key == "at":
                    # Deferred: `pssparser.at:` is where *we* point, which
                    # overrides the neutral `at:` (where a good diagnostic
                    # would) for our assertions only.  Both are kept.
                    override_at = value
                else:
                    directives.append((native_key, value))
            else:
                other.setdefault(head, {})[tail] = value
        elif key not in _KNOWN_DIRECTIVES:
            raise CorpusFormatError(
                f"{path}: unknown directive '{key}:' (known: "
                f"{', '.join(sorted(_KNOWN_DIRECTIVES))})"
            )
        else:
            directives.append((key, value))
        header_end += len(line)

    case = CorpusCase(path=path, code=text, other_tools=other)

    for key, value in directives:
        value = value.strip()
        if key == "id":
            case.id = value
        elif key == "at":
            line_, col_, end_line_, end_col_ = _parse_at(value, path)
            case.at = (line_, col_,
                       end_col_ if end_line_ == line_ else None)
            case.at_end = (end_line_, end_col_) if end_col_ is not None else None
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
            case.files = _split_list(value)
        elif key == "at-file":
            case.at_file = value
        # -- neutral directives -------------------------------------------
        elif key == "case":
            case.case_id = value
        elif key == "class":
            case.cls = value
        elif key == "title":
            case.title = value
        elif key == "expect":
            case.expect = value
        elif key == "detect":
            case.detect = value
        elif key == "lrm":
            case.lrm = value
        elif key == "pss":
            case.pss = value
        elif key == "tags":
            case.tags = _split_list(value)
        elif key == "requires":
            case.requires = _split_list(value)
        elif key == "fix":
            case.fix.append(_parse_fix(value, path))
        elif key == "cause":
            case.cause = _split_list(value)
        elif key == "not_cause":
            case.not_cause = _split_list(value)
        elif key == "names":
            case.names = _split_list(value)
        elif key == "about":
            case.about = value

    if override_at is not None:
        # Keep the neutral expectation visible -- the pair of them is the
        # per-case record of how far our location is off -- and point our own
        # assertions at where we actually are.
        case.neutral_at, case.neutral_at_end = case.at, case.at_end
        line_, col_, end_line_, end_col_ = _parse_at(override_at, path)
        case.at = (line_, col_, end_col_ if end_line_ == line_ else None)
        case.at_end = (end_line_, end_col_) if end_col_ is not None else None

    # `severity:` (ours) and `expect:` (neutral) say the same thing from two
    # vocabularies, so each supplies the other when only one is written.  The
    # remaining neutral defaults are the suite's, so that both loaders read the
    # same facts out of a header that omits them -- pinned by
    # test_corpus_loader.py's convergence test.
    written = {k for k, _ in directives}
    if case.expect in ("error", "warning") and "severity" not in written:
        case.severity = case.expect
    elif case.expect is None:
        case.expect = case.severity
    if case.detect is None:
        case.detect = "recommended"
    if case.pss is None:
        case.pss = "3.0"

    if case.files is not None and path.name not in case.files:
        raise CorpusFormatError(
            f"{path}: 'files:' directive {case.files!r} does not include "
            f"the case file's own name {path.name!r}"
        )

    if case.expect == "accept":
        # The assertion is silence; there is no marker to pin an id or a
        # message on.
        return case

    if case.id is None and case.case_id is None:
        raise CorpusFormatError(
            f"{path}: missing required 'id:' directive "
            f"(or 'case:', for a tool-neutral case)")
    if case.match is None and case.at is None:
        raise CorpusFormatError(
            f"{path}: header must assert at least one of 'at:' or 'match:'"
        )

    return case


def _neutral_at(case: "CorpusCase"):
    at = case.neutral_at if case.neutral_at is not None else case.at
    end = case.neutral_at_end if case.neutral_at is not None else case.at_end
    if at is None:
        return None
    return (at[0], at[1], end[0] if end else None, end[1] if end else None)


def asserts_pssparser(case: "CorpusCase") -> bool:
    """True if this case says anything about *our* output.

    A tool-neutral case declares where a *good* diagnostic points; that is an
    expectation, not an assertion about pssparser, and pytest must not treat a
    gap in our behaviour as a red test -- the error suite records those as
    data (`missed`, `detected_mislocated`).  A case opts into pytest by
    carrying a `pssparser.id:`, `pssparser.match:` or `pssparser.at:`.

    The useful consequence: once a ported case's neutral `at:` is corrected
    from "where we point" to "where a good diagnostic points", the case needs
    an explicit `pssparser.at:` to keep passing -- and the pair of them is a
    greppable, per-case record of exactly how far our locations are off.
    """
    return (case.id is not None or case.match is not None
            or case.neutral_at is not None)


def neutral_view(case: "CorpusCase") -> dict:
    """The tool-neutral facts about a case, as a plain dict.

    Exists so the two loaders can be compared field-for-field
    (``test_corpus_loader.py``): if they ever disagree about what a header
    says, one of the two corpora is quietly running different cases than its
    author thinks.
    """
    return {
        "case": case.case_id,
        "class": case.cls,
        "title": case.title,
        "expect": case.expect,
        "detect": case.detect,
        "at": _neutral_at(case),
        "also": [(a.line, a.col, a.label) for a in case.also],
        "count": case.count,
        "lrm": case.lrm,
        "pss": case.pss,
        "tags": list(case.tags),
        "requires": list(case.requires),
        "fix": list(case.fix),
        "cause": list(case.cause),
        "not_cause": list(case.not_cause),
        "names": list(case.names),
        "files": None if case.files is None else list(case.files),
        "at_file": case.at_file,
        "about": case.about,
    }


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
        # `<name>.ok.pss` is a control -- the repaired twin of a case, whose
        # job is to parse clean.  It is an input to the error suite, not a case
        # in its own right (error-suite design §3.1).
        and not p.name.endswith(".ok.pss")
    ]
