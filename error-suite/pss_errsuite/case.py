"""Case files and their ``//!`` headers.

A case is a ``.pss`` file whose leading lines are ``//!`` directives.  The
header is a PSS comment, so the file is *also* a valid input you can hand
straight to any tool while debugging -- the single property that has made
pssparser's internal corpus pleasant to work with, and the reason the format is
shared rather than reinvented (design §3.2).

Header grammar: one directive per line, any order, header ends at the first
line that is not ``//!``.  Values are plain text; there are **no inline
comments** and list-valued directives are comma-separated::

    //! case:    SEM-TYPE-ASSIGN-WIDTH-01
    //! class:   semantic.type.assign-incompatible
    //! title:   string literal assigned to a bit field
    //! expect:  error
    //! detect:  required
    //! at:      14:9-14:26
    //! also:    9:5 "declared here"
    //! count:   1
    //! lrm:     8.4.2
    //! pss:     3.1
    //! cause:   assign, string, bit
    //! fix:     14: b = 8'h20;
    //! pssparser.id: PSS0xx

Three ``at:`` spellings are accepted, because the internal corpus and this
suite grew different ones (plan §0.4): ``line:col``, ``line:col-col`` (a
same-line span, end column) and ``line:col-line:col``.

Parsing is **strict**: an unknown directive is an error, never a silently
ignored line.  A typo'd directive that quietly disables an assertion is exactly
the failure mode a corpus cannot afford.

Line and column numbers count the header lines, since the header is part of the
file the tool is given.  Adding a header line shifts every ``at:`` by one;
there is no way around that without giving up the hand-runnable property.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

#: Directives with meaning to every tool.  Anything else must be namespaced.
NEUTRAL_DIRECTIVES = frozenset({
    "case", "class", "title", "expect", "detect", "at", "also", "count",
    "lrm", "pss", "tags", "requires", "fix", "cause", "not_cause", "names",
    "files", "at-file", "about",
})

#: What the expected diagnostic is *about*.  Almost always the user's program.
#:
#: `tool` marks the handful of cases whose subject is the tool's own reporting
#: behaviour -- an error cap firing, say.  Such a diagnostic has no declaration
#: to name and no repair to offer, so asking "does it name an entity from the
#: program" has no answer, and the rubric records `null` rather than 0.  Before
#: this existed the four `syntax.volume` cap cases were charged D3 = 0 for
#: correctly reporting that they had stopped reporting.
ABOUT_KINDS = frozenset({"program", "tool"})

#: Directives that may appear more than once.
REPEATABLE = frozenset({"also", "fix"})

#: Keys a ``<tool>.<key>`` directive is known to mean something by.  The suite
#: consumes `max_errors`; the rest are read by a tool's own test harness
#: (pssparser's `corpus_loader.py` reads `id`, `match`, `at` and `hint`).
#:
#: Unknown keys are *not* rejected at parse time -- see `load_case` -- but they
#: are worth saying out loud, because a silently ignored directive is how
#: `pssparser.max-errors` went un-consumed across the whole corpus: every
#: volume case ran at the default cap of 20 and the tool was scored on it.
TOOL_KEYS = frozenset({"max_errors", "id", "match", "at", "hint"})

EXPECT_KINDS = frozenset({"error", "warning", "accept"})
DETECT_LEVELS = frozenset({"required", "recommended", "optional"})

_HEADER_RE = re.compile(r"^//!\s*([A-Za-z_][A-Za-z0-9_.-]*):\s*(.*?)\s*$")
_AT_RE = re.compile(r"^(\d+):(\d+)(?:-(?:(\d+):)?(\d+))?$")
_ALSO_RE = re.compile(r'^(\d+):(\d+)\s+"([^"]*)"$')
_FIX_RE = re.compile(r"^(\d+):\s?(.*)$")
_CLASS_RE = re.compile(r"^[a-z0-9]+(?:\.[a-z0-9-]+)+$")
_PSS_RE = re.compile(r"^\d+\.\d+$")


class CaseFormatError(Exception):
    """Raised for a malformed ``//!`` header or an unreadable case file."""


@dataclass(frozen=True)
class Span:
    line: int
    col: int
    end_line: int | None = None
    end_col: int | None = None

    def as_dict(self) -> dict:
        d = {"line": self.line, "col": self.col}
        if self.end_line is not None:
            d["end_line"] = self.end_line
        if self.end_col is not None:
            d["end_col"] = self.end_col
        return d


@dataclass(frozen=True)
class RelatedExpectation:
    line: int
    col: int
    label: str


@dataclass
class Case:
    path: Path
    root: Path
    source: str

    case_id: str = ""
    cls: str = ""
    title: str = ""
    expect: str = "error"
    detect: str = "recommended"
    at: Span | None = None
    also: list[RelatedExpectation] = field(default_factory=list)
    count: int = 1
    lrm: str | None = None
    pss: str = "3.0"
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    fix: list[tuple[int, str]] = field(default_factory=list)
    cause: list[str] = field(default_factory=list)
    not_cause: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    files: list[str] | None = None
    at_file: str | None = None
    about: str = "program"

    #: ``{tool: {key: value}}`` from ``<tool>.<key>`` directives.
    tool_opts: dict[str, dict[str, str]] = field(default_factory=dict)
    #: ``{tool: reason}`` from ``xfail.<tool>``.
    xfail: dict[str, str] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return str(self.path.relative_to(self.root))

    @property
    def body(self) -> str:
        """The source with the ``//!`` header stripped.

        Anything that asks "does the case mention X" has to ask this rather
        than `source`: the header is part of the file, so a `names: foo` check
        against `source` would happily match the directive that declares it.
        """
        lines = self.source.splitlines(keepends=True)
        i = 0
        while i < len(lines) and lines[i].startswith("//!"):
            i += 1
        return "".join(lines[i:])

    @property
    def source_sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    def input_files(self) -> list[Path]:
        """The ordered file list to hand the tool (usually just this file)."""
        if self.files is None:
            return [self.path]
        return [self.path.parent / f for f in self.files]

    # -- controls ---------------------------------------------------------
    #
    # Every `expect: error` case has a control: the same file with the defect
    # repaired, which must parse clean.  Without it, a tool that chokes on our
    # preamble scores 100% detection (design §3.1).

    @property
    def control_path(self) -> Path:
        return self.path.with_suffix(".ok.pss")

    def control_source(self) -> str | None:
        """This file's repaired source, from a ``.ok.pss`` sibling or ``fix:``.

        Returns ``None`` when *this file* declares no repair.  That is not the
        same as "no control": see :meth:`control_overrides`.
        """
        if self.control_path.is_file():
            return self.control_path.read_text(encoding="utf-8")
        if not self.fix:
            return None
        lines = self.source.splitlines(keepends=True)
        for lineno, text in self.fix:
            if not 1 <= lineno <= len(lines):
                raise CaseFormatError(
                    f"{self.path}: fix: line {lineno} is outside the file "
                    f"(1..{len(lines)})"
                )
            nl = "\n" if lines[lineno - 1].endswith("\n") else ""
            lines[lineno - 1] = text + nl
        return "".join(lines)

    def control_overrides(self) -> dict[str, str] | None:
        """The repaired *file set*, as ``{file name: repaired source}``.

        For the usual single-file case this is just this file.  A multifile
        case whose defect lives in a companion -- the point of that class is
        that a tool must attribute a diagnostic to the right file, which needs
        cases where the defect is *not* in the file the case is named after --
        repairs the companion instead: ``_lib.pss`` is repaired by
        ``_lib.ok.pss``.  The control has to be the file set with the defect
        removed, not merely this file with the defect removed.

        ``None`` means nothing at all is repaired, which ``validate`` treats
        as a corpus error for any non-``accept`` case.
        """
        out: dict[str, str] = {}
        own = self.control_source()
        if own is not None and own != self.source:
            out[self.path.name] = own
        for path in self.input_files():
            if path.name == self.path.name:
                continue
            repaired = path.with_suffix(".ok.pss")
            if repaired.is_file():
                out[path.name] = repaired.read_text(encoding="utf-8")
        return out or None


def _parse_at(raw: str, path: Path) -> Span:
    m = _AT_RE.match(raw)
    if not m:
        raise CaseFormatError(
            f"{path}: malformed 'at:' {raw!r}; expected 'line:col', "
            f"'line:col-col' or 'line:col-line:col'"
        )
    line, col, end_line, end_col = m.groups()
    if end_col is None:
        return Span(int(line), int(col))
    return Span(
        int(line), int(col),
        int(end_line) if end_line is not None else int(line),
        int(end_col),
    )


def _parse_also(raw: str, path: Path) -> RelatedExpectation:
    m = _ALSO_RE.match(raw)
    if not m:
        raise CaseFormatError(
            f"{path}: malformed 'also:' {raw!r}; expected 'line:col \"label\"'"
        )
    line, col, label = m.groups()
    return RelatedExpectation(int(line), int(col), label)


def _parse_fix(raw: str, path: Path) -> tuple[int, str]:
    m = _FIX_RE.match(raw)
    if not m:
        raise CaseFormatError(
            f"{path}: malformed 'fix:' {raw!r}; expected 'LINE: replacement'"
        )
    return int(m.group(1)), m.group(2)


_LIST_SEP = re.compile(r"(?<!\\),")


def _split_list(raw: str) -> list[str]:
    r"""Comma-separated, with ``\,`` for a literal comma.

    The escape exists for exactly one reason: a `cause:` term may *be* a
    comma. The suite has cases whose whole defect is a missing separator in an
    argument list or an enum item list, and an accurate diagnostic for one of
    those says `','`. Without the escape the only ways to express that are a
    term the message will not contain ("comma") or no term at all, and both
    make the accuracy proxy report a good message as a bad one.

    Design §5.4 chose `,` as the separator over `;` because `;` is itself a
    plausible cause term; this is the same argument arriving one step later.
    """
    return [p.strip().replace("\\,", ",")
            for p in _LIST_SEP.split(raw) if p.strip()]


def parse_header(source: str, path: Path) -> dict[str, list[str]]:
    """Split *source*'s leading ``//!`` block into ``{directive: [values]}``."""
    out: dict[str, list[str]] = {}
    for raw_line in source.splitlines():
        if not raw_line.startswith("//!"):
            break
        m = _HEADER_RE.match(raw_line)
        if not m:
            raise CaseFormatError(
                f"{path}: malformed header line {raw_line!r}; expected "
                f"'//! directive: value'"
            )
        key, value = m.group(1), m.group(2)
        if key in out and key not in REPEATABLE and "." not in key:
            raise CaseFormatError(f"{path}: duplicate directive {key!r}")
        out.setdefault(key, []).append(value)
    return out


def load_case(path: Path, root: Path | None = None) -> Case:
    """Read and validate one case file."""
    path = Path(path)
    root = Path(root) if root is not None else path.parent
    try:
        source = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as e:
        raise CaseFormatError(f"{path}: not valid UTF-8: {e}") from None

    directives = parse_header(source, path)
    case = Case(path=path, root=root, source=source)

    for key, values in directives.items():
        if "." in key:
            head, _, tail = key.partition(".")
            if head == "xfail":
                case.xfail[tail] = values[-1]
            else:
                # `-` and `_` are the same key.  Both spellings are in the
                # corpus and pssparser's loader already folds them this way;
                # not folding them here is what made `pssparser.max-errors`
                # miss the runner's `max_errors` lookup.
                #
                # The key is *not* validated here.  A namespace belongs to a
                # tool this suite may never have heard of, and rejecting
                # `vendorx.foo` at parse time would mean a corpus that cannot
                # be read until every tool in it is onboarded.  `validate`
                # warns and the runner errors for the tool it is running --
                # both places know enough to be right.
                case.tool_opts.setdefault(head, {})[tail.replace("-", "_")] = \
                    values[-1]
            continue
        if key not in NEUTRAL_DIRECTIVES:
            raise CaseFormatError(
                f"{path}: unknown directive {key!r}. Neutral directives are "
                f"{sorted(NEUTRAL_DIRECTIVES)}; tool-specific ones must be "
                f"namespaced as '<tool>.{key}'."
            )
        value = values[-1]
        if key == "case":
            case.case_id = value
        elif key == "class":
            case.cls = value
        elif key == "title":
            case.title = value
        elif key == "expect":
            case.expect = value
        elif key == "detect":
            case.detect = value
        elif key == "at":
            case.at = _parse_at(value, path)
        elif key == "also":
            case.also = [_parse_also(v, path) for v in values]
        elif key == "count":
            try:
                case.count = int(value)
            except ValueError:
                raise CaseFormatError(
                    f"{path}: 'count:' must be an integer, got {value!r}"
                ) from None
        elif key == "lrm":
            case.lrm = value
        elif key == "pss":
            case.pss = value
        elif key == "about":
            if value not in ABOUT_KINDS:
                raise CaseFormatError(
                    f"{path}: about: {value!r} is not one of "
                    f"{sorted(ABOUT_KINDS)}")
            case.about = value
        elif key == "tags":
            case.tags = _split_list(value)
        elif key == "requires":
            case.requires = _split_list(value)
        elif key == "fix":
            case.fix = [_parse_fix(v, path) for v in values]
        elif key == "cause":
            case.cause = _split_list(value)
        elif key == "not_cause":
            case.not_cause = _split_list(value)
        elif key == "names":
            case.names = _split_list(value)
        elif key == "files":
            case.files = _split_list(value)
        elif key == "at-file":
            case.at_file = value

    _check_case(case)
    return case


def _check_case(case: Case) -> None:
    """Structural checks every reader applies; ``validate`` adds corpus ones."""
    path = case.path
    if not case.case_id:
        raise CaseFormatError(f"{path}: missing 'case:' directive")
    if not case.cls:
        raise CaseFormatError(f"{path}: missing 'class:' directive")
    if not _CLASS_RE.match(case.cls):
        raise CaseFormatError(
            f"{path}: 'class:' {case.cls!r} is not a dotted lower-case path"
        )
    if case.expect not in EXPECT_KINDS:
        raise CaseFormatError(
            f"{path}: 'expect:' must be one of {sorted(EXPECT_KINDS)}, "
            f"got {case.expect!r}"
        )
    if case.detect not in DETECT_LEVELS:
        raise CaseFormatError(
            f"{path}: 'detect:' must be one of {sorted(DETECT_LEVELS)}, "
            f"got {case.detect!r}"
        )
    if not _PSS_RE.match(case.pss):
        raise CaseFormatError(
            f"{path}: 'pss:' must look like '3.0', got {case.pss!r}"
        )
    if case.expect == "accept":
        if case.at is not None:
            raise CaseFormatError(
                f"{path}: an 'expect: accept' case must not carry 'at:'"
            )
    elif case.at is None:
        raise CaseFormatError(
            f"{path}: 'expect: {case.expect}' requires an 'at:' directive"
        )
    if case.at is not None and case.at_file in (None, case.path.name):
        # One past the last line is legal and means end-of-input, which is
        # exactly where a truncated-file case expects a diagnostic.
        n_lines = len(case.source.splitlines())
        if not 1 <= case.at.line <= n_lines + 1:
            raise CaseFormatError(
                f"{path}: 'at:' line {case.at.line} is outside the file "
                f"(1..{n_lines}, or {n_lines + 1} for end-of-input); "
                f"remember the header counts"
            )
    if case.files is not None and case.path.name not in case.files:
        raise CaseFormatError(
            f"{path}: 'files:' must list this file ({case.path.name!r}); "
            f"got {case.files}"
        )


def neutral_view(case: Case) -> dict:
    """The tool-neutral facts about a case, as a plain dict.

    Mirrors ``corpus_loader.neutral_view`` on pssparser's side so the two
    readers can be compared field-for-field.  Both corpora are read by both
    loaders; if the two ever disagree about what a header says, one of them is
    quietly running different cases than its author thinks.
    """
    return {
        "case": case.case_id or None,
        "class": case.cls or None,
        "title": case.title or None,
        "expect": case.expect,
        "detect": case.detect,
        "at": None if case.at is None else (
            case.at.line, case.at.col, case.at.end_line, case.at.end_col),
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


def collect_cases(root: Path) -> list[Case]:
    """Load every case under *root*, sorted by path.

    Skipped: ``*.ok.pss`` controls and leading-underscore companion files,
    which are fragments referenced by a ``files:`` directive rather than
    independent cases.
    """
    root = Path(root)
    cases = []
    for path in sorted(root.rglob("*.pss")):
        if path.name.startswith("_") or path.name.endswith(".ok.pss"):
            continue
        cases.append(load_case(path, root))
    return cases
