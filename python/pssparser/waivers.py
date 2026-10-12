"""Source waivers: waive a diagnostic in the PSS text next to the code.

Two forms (``docs/waivers.rst``; design ``docs/design/source-waivers.md``):

* The annotation ``@lint_pkg::waive {.id = "...", .reason = "..."}``.  As an
  *element* annotation it covers the element that follows, from its location
  to its end location.  As a *standalone* annotation (terminated by ``;``) it
  covers from the annotation to the end of the enclosing scope -- at file
  scope, the rest of the file.  It is recognised by its spelled name, so write
  it fully qualified: ``lint_pkg`` needs no import.
* The comment ``// pssparser waive <id>[, <id>...]: <reason>``.  Trailing code
  on a line, it covers that line; alone on its line, the next line that holds
  code.

A waiver's ``id`` is a marker ID, a rule name, or any rule selector
(``pssparser.checkers.selectors``).  A diagnostic is waived when its
**primary** location lies in a waiver's span and its code is one the waiver
names.  Errors from the core (an LRM violation, or a failure of pssparser
itself) are never waived: the model was not built.

This module is the library entry point, so that the CLI, pssc and an editor
apply the same waivers::

    waivers = collect(parser, files)
    result = apply(diagnostics, waivers, rules=..., ran=...)

``result.kept`` are the diagnostics to report, ``result.waived`` pairs each
waived diagnostic with its waiver, and ``result.markers`` are the hygiene
diagnostics (PSSP202-PSSP205 and PSSP004) as marker dicts.

The core lint engine collects and applies waivers too (lint-core-plan.md
C7.2), so the WASM build and an editor apply the same ones:
:func:`collect_in` and :func:`apply_in` take a
:class:`pssparser.core.LintEngine` that knows the host's markers
(:func:`pssparser.lint.selection.tell_engine`).  :func:`collect` and
:func:`apply` stay, as the test oracle and for a host without an engine.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: The waiver annotation's spelled name.
WAIVE_ANNOTATION = ("lint_pkg", "waive")

UNUSED = "PSSP202"
UNKNOWN_RULE = "PSSP203"
ON_ERROR = "PSSP204"
NO_REASON = "PSSP205"
ALIAS = "PSSP004"

#: Codes a source waiver cannot waive: it could hide the warning that it is
#: itself unused.
HYGIENE = frozenset([UNUSED, UNKNOWN_RULE, ON_ERROR, NO_REASON, ALIAS])

#: A position past any real column, for a span that runs to a line's end.
_EOL = 1 << 30

_PRAGMA_RE = re.compile(r"^//\s*pssparser\s+waive\b(.*)$", re.DOTALL)


@dataclass
class Waiver:
    """One waiver, of either form.

    ``file``/``line``/``col`` are where the waiver is written (1-based).
    ``start``/``end`` are the covered span as ``(line, col)``, ``end``
    exclusive.  ``selectors`` are as written; ``ids`` is filled in by
    :func:`apply`.
    """

    form: str
    file: str
    line: int
    col: int
    selectors: List[str]
    reason: str
    start: Tuple[int, int]
    end: Tuple[int, int]
    ids: Set[str] = field(default_factory=set)
    used: int = 0

    def covers(self, file: str, line: int, col: int) -> bool:
        if _real(file) != _real(self.file):
            return False
        return self.start <= (line, col) < self.end

    def to_engine(self) -> dict:
        """The waiver as :meth:`LintEngine.apply_waivers` reads it."""
        return {
            "form": self.form, "file": self.file, "line": self.line, "col": self.col,
            "selectors": list(self.selectors), "reason": self.reason,
            "start": list(self.start), "end": list(self.end),
        }

    @classmethod
    def from_engine(cls, d: dict) -> "Waiver":
        return cls(form=d["form"], file=d["file"], line=d["line"], col=d["col"],
                   selectors=list(d["selectors"]), reason=d["reason"],
                   start=tuple(d["start"]), end=tuple(d["end"]))

    def to_json(self) -> dict:
        return {
            "form": self.form,
            "id": ", ".join(self.selectors),
            "file": self.file,
            "line": self.line,
            "col": self.col,
            "reason": self.reason,
        }


@dataclass
class WaiverResult:
    kept: List[Any]
    waived: List[Tuple[Any, Waiver]]
    markers: List[dict]


def _real(path: str) -> str:
    return os.path.realpath(path) if path else path


# ---------------------------------------------------------------------------
# Collection: comment pragmas
# ---------------------------------------------------------------------------

def collect_pragmas(path: str, text: str) -> List[Waiver]:
    """The ``// pssparser waive`` comments in *text*.

    Read from the lexer's comment tokens (``pssparser.tokens``), so a pragma
    inside a block comment or a string is not one.
    """
    if "pssparser" not in text:
        return []
    from pssparser.tokens import CHANNEL_SL_COMMENT, tokenize

    tokens = list(tokenize(text))
    out: List[Waiver] = []
    for i, tok in enumerate(tokens):
        if tok.channel != CHANNEL_SL_COMMENT:
            continue
        m = _PRAGMA_RE.match(tok.text.rstrip("\r\n"))
        if m is None:
            continue
        body = m.group(1)
        ids_text, sep, reason = body.partition(":")
        selectors = [s.strip() for s in ids_text.split(",") if s.strip()]
        # Trailing code on the line covers that line; alone, the next line
        # that holds code.
        trails = any(t.line == tok.line and not t.is_trivia
                     for t in tokens[:i])
        target = tok.line
        if not trails:
            target = next((t.line for t in tokens[i + 1:]
                           if not t.is_trivia and t.line > tok.line), None)
            if target is None:
                target = tok.line
        out.append(Waiver(
            form="pragma",
            file=path,
            line=tok.line,
            col=tok.col + 1,
            selectors=selectors,
            reason=reason.strip() if sep else "",
            start=(target, 1),
            end=(target, _EOL),
        ))
    return out


# ---------------------------------------------------------------------------
# Collection: annotations
# ---------------------------------------------------------------------------

def _string_value(expr) -> Optional[str]:
    get = getattr(expr, "getValue", None)
    if get is None:
        return None
    try:
        value = get()
    except Exception:
        return None
    return value if isinstance(value, str) else None


def _spelled(type_id) -> Tuple[str, ...]:
    try:
        return tuple(e.getId().getId() for e in type_id.getElems())
    except Exception:
        return ()


def _span_of(node) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    b, e = node.getLocation(), node.getEndLocation()
    if b.lineno < 1:
        return None
    if e.lineno < 1:
        return (b.lineno, b.linepos), (b.lineno, _EOL)
    return (b.lineno, b.linepos), (e.lineno, e.linepos)


def _waiver_from(ann, path: str, span) -> Waiver:
    selectors: List[str] = []
    reason = ""
    for p in ann.getParameters():
        try:
            name = p.getName().getId().getId()
        except Exception:
            continue
        value = _string_value(p.getValue())
        if value is None:
            continue
        if name == "id":
            selectors = [s.strip() for s in value.split(",") if s.strip()]
        elif name == "reason":
            reason = value.strip()
    loc = ann.getLocation()
    return Waiver(
        form="annotation",
        file=path,
        line=loc.lineno,
        col=loc.linepos,
        selectors=selectors,
        reason=reason,
        start=span[0],
        end=span[1],
    )


def collect_annotations(units: Iterable, file_map: Dict[int, str],
                        texts: Optional[Dict[str, str]] = None) -> List[Waiver]:
    """The ``@lint_pkg::waive`` annotations in *units* (global scopes).

    *texts* maps a path to its source; a unit whose text does not mention
    ``lint_pkg`` is skipped without a walk.
    """
    import pssparser.ast as A

    out: List[Waiver] = []
    seen: Set[Tuple[int, int, int]] = set()

    for unit in units:
        path = file_map.get(unit.getFileid(), "")
        if texts is not None and "lint_pkg" not in texts.get(path, "lint_pkg"):
            continue

        def record(node):
            for ann in node.getAnnotations():
                if _spelled(ann.getType()) != WAIVE_ANNOTATION:
                    continue
                loc = ann.getLocation()
                key = (unit.getFileid(), loc.lineno, loc.linepos)
                if key in seen:
                    continue
                seen.add(key)
                span = _span_of(node)
                if span is not None:
                    # From the annotation itself, which precedes the element:
                    # a field's location is its name, and a finding on its
                    # type is still within the declaration.
                    start = min(span[0], (loc.lineno, loc.linepos))
                    out.append(_waiver_from(ann, path, (start, span[1])))

        class _V(A.VisitorBase):
            pass

        # Every visitX is overridden: dispatch calls the most-derived method
        # first, and not every generated visit reaches a node's annotations
        # through the base classes.
        def make(name):
            def f(self, i):
                anns = getattr(i, "getAnnotations", None)
                if anns is not None and anns():
                    record(i)
                if name == "visitAnnotation" and i.getIs_standalone():
                    standalone(i)
                return getattr(A.VisitorBase, name)(self, i)
            return f

        def standalone(ann):
            if _spelled(ann.getType()) != WAIVE_ANNOTATION:
                return
            loc = ann.getLocation()
            key = (unit.getFileid(), loc.lineno, loc.linepos)
            if key in seen:
                return
            seen.add(key)
            parent = ann.getParent()
            end = (_EOL, _EOL)
            if parent is not None:
                e = parent.getEndLocation()
                if e.lineno >= 1 and type(parent).__name__ != "GlobalScope":
                    end = (e.lineno, e.linepos)
            out.append(_waiver_from(ann, path, ((loc.lineno, loc.linepos), end)))

        for name in dir(A.VisitorBase):
            if name.startswith("visit"):
                setattr(_V, name, make(name))
        unit.accept(_V())
    return out


def collect(parser, files: Sequence[str], *, annotations: bool = True,
            read: Optional[Callable[[str], str]] = None) -> List[Waiver]:
    """Every waiver in *files*: pragmas always, annotations if the parser has
    units (after ``link()``, or ``parse()`` for ``--syntax-only``).

    *read* returns a file's text; it defaults to reading the file.
    """
    def _read(path):
        if read is not None:
            return read(path)
        try:
            with open(path, encoding="utf-8", errors="replace") as fp:
                return fp.read()
        except OSError:
            return ""

    texts = {f: _read(f) for f in files}
    out: List[Waiver] = []
    for f in files:
        out.extend(collect_pragmas(f, texts[f]))
    if annotations and parser is not None:
        units, file_map = _user_units(parser, files)
        out.extend(collect_annotations(units, file_map, texts))
    out.sort(key=lambda w: (w.file, w.line, w.col))
    return out


def _user_units(parser, files: Sequence[str]):
    file_map = dict(getattr(parser, "file_map", {}) or {})
    wanted = set(files)
    units = []
    if hasattr(parser, "user_units"):
        units = [u for u in parser.user_units()
                 if file_map.get(u.getFileid(), "") in wanted]
    if not units and hasattr(parser, "_files"):
        names = getattr(parser, "_filenames", {}) or {}
        if not file_map:
            file_map = dict(names)
        units = [u for u in parser._files
                 if names.get(u.getFileid(), "") in wanted]
    return units, file_map


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

def _attr(diag, name, default=None):
    if isinstance(diag, dict):
        return diag.get(name, default)
    return getattr(diag, name, default)


def _marker(code, w: Waiver, message, severity="warning") -> dict:
    return {
        "severity": severity,
        "message": message,
        "file": w.file,
        "line": w.line,
        "col": w.col,
        "code": code,
        "extent": -1,
        "related": [],
    }


def _where(w: Waiver) -> str:
    return "waiver" if w.form == "annotation" else "waiver comment"


def apply(
    diagnostics: Sequence[Any],
    waivers: Sequence[Waiver],
    *,
    rules,
    is_core_error: Callable[[str], bool],
    ran: Optional[Set[str]] = None,
    aliases: Optional[Dict[str, str]] = None,
) -> WaiverResult:
    """Split *diagnostics* into kept and waived, and report on the waivers.

    *rules* is a :class:`~pssparser.checkers.selectors.RuleSet` over every
    known marker.  *is_core_error* says whether a code is a core error (never
    waived).  *ran* is the set of codes whose rule ran on this run; ``None``
    means unknown, and no waiver is then reported unused.  *aliases* maps an
    old ID (a rule's alias, or a retired code) to the current one.

    Diagnostics may be marker dicts or objects with ``file``, ``line``,
    ``col`` and ``code`` attributes.
    """
    from pssparser.checkers.selectors import SelectorError

    aliases = aliases or {}
    markers: List[dict] = []
    active: List[Waiver] = []

    for w in waivers:
        if not w.reason:
            markers.append(_marker(
                NO_REASON, w,
                f"{_where(w)} gives no reason; say why the finding is "
                + ("intended in '.reason'" if w.form == "annotation"
                   else "intended after ':'")))
        if not w.selectors:
            markers.append(_marker(
                UNKNOWN_RULE, w,
                f"{_where(w)} names no rule; "
                + ("set '.id' to a marker ID or rule name" if w.form == "annotation"
                   else "write the ID before ':'")))
            continue
        core: List[str] = []
        for sel in w.selectors:
            text = sel
            if sel in aliases:
                markers.append(_marker(
                    ALIAS, w,
                    f"'{sel}' is the old ID of {aliases[sel]}; write "
                    f"'{aliases[sel]}' in the waiver", severity="info"))
                text = aliases[sel]
            try:
                expanded = rules.expand([text], include_core_errors=True)
            except SelectorError as exc:
                markers.append(_marker(UNKNOWN_RULE, w, f"{_where(w)}: {exc}"))
                continue
            ids = set(expanded) - HYGIENE
            errors = {i for i in ids if is_core_error(i)}
            if errors and errors == ids:
                core.append(sel)
            w.ids |= ids - errors
        for sel in core:
            markers.append(_marker(
                ON_ERROR, w,
                f"'{sel}' is an error, which cannot be waived; fix it and "
                "delete the waiver"))
        if w.ids:
            active.append(w)

    kept: List[Any] = []
    waived: List[Tuple[Any, Waiver]] = []
    for d in diagnostics:
        code = _attr(d, "code")
        hit = None
        if code and code not in HYGIENE and not is_core_error(code):
            file, line, col = _attr(d, "file"), _attr(d, "line", 0), _attr(d, "col", 0)
            for w in active:
                if code in w.ids and w.covers(file, line, col):
                    hit = w
                    break
        if hit is None:
            kept.append(d)
        else:
            hit.used += 1
            waived.append((d, hit))

    if ran is not None:
        for w in active:
            if w.used == 0 and w.ids & ran:
                markers.append(_marker(
                    UNUSED, w,
                    f"{_where(w)} for '{', '.join(w.selectors)}' matched no "
                    "diagnostic; delete it if the finding was fixed"))

    markers.sort(key=lambda m: (m["file"], m["line"], m["col"], m["code"]))
    return WaiverResult(kept=kept, waived=waived, markers=markers)


# ---------------------------------------------------------------------------
# In the core engine (lint-core-plan.md C7.2)
# ---------------------------------------------------------------------------

def collect_in(engine, parser, files: Sequence[str], *, annotations: bool = True,
               read: Optional[Callable[[str], str]] = None) -> List[Waiver]:
    """:func:`collect`, by the core *engine*."""
    texts: Dict[str, str] = {}
    for f in files:
        if read is not None:
            texts[f] = read(f)
            continue
        try:
            with open(f, encoding="utf-8", errors="replace") as fp:
                texts[f] = fp.read()
        except OSError:
            texts[f] = ""
    roots: list = []
    file_map: Dict[int, str] = {}
    if annotations and parser is not None:
        roots, file_map = _user_units(parser, files)
    r = engine.collect_waivers(roots, texts, file_map)
    if not r.get("ok"):  # pragma: no cover - the request is built here
        raise ValueError(r.get("error", "collect_waivers failed"))
    return [Waiver.from_engine(w) for w in r["waivers"]]


def apply_in(engine, diagnostics: Sequence[Any], waivers: Sequence[Waiver], *,
             ran: Optional[Set[str]] = None) -> WaiverResult:
    """:func:`apply`, by the core *engine*: its catalogue (the host markers
    and loaded rules) resolves the selectors and says which codes are core
    errors.  Fills in each waiver's ``ids`` and ``used``."""
    # The engine compares paths as given: spell each diagnostic's file as
    # the waiver for the same real file does.
    spelling = {_real(w.file): w.file for w in waivers}
    diags = []
    for d in diagnostics:
        file = _attr(d, "file") or ""
        diags.append({"code": _attr(d, "code") or "",
                      "file": spelling.get(_real(file), file),
                      "line": _attr(d, "line", 0) or 0, "col": _attr(d, "col", 0) or 0})
    r = engine.apply_waivers([w.to_engine() for w in waivers], diags, ran)
    if not r.get("ok"):  # pragma: no cover - the request is built here
        raise ValueError(r.get("error", "apply_waivers failed"))
    for w, out in zip(waivers, r["waivers"]):
        w.ids = set(out["ids"])
        w.used = out["used"]
    return WaiverResult(
        kept=[diagnostics[i] for i in r["kept"]],
        waived=[(diagnostics[i], waivers[w]) for i, w in r["waived"]],
        markers=list(r["markers"]))
