"""Declarative rule files (``pss-rules``): finding them, loading them into
the core engine, and checking them against the Python marker registry.

Where rules come from (pss-rules-format §6.2, lint-core-plan C4.3): the
built-in files embedded in the core, then ``[lint] rules`` entries in order,
then ``--rules`` in order.  A named file must be a rule file; a named
directory contributes every ``*.yaml``, ``*.yml`` and ``*.json`` directly in
it that has a top-level ``pss-rules`` key, and the others are skipped (and
listed at ``--verbose``).

The C++ loader checks rule IDs and names across every rule file it loads
(``PSSP217``, pss-rules-format §5), but cannot see the ``MarkerDef``s that
Python extensions declare.  :func:`conflicts` finds those clashes after load;
the rules that clash are left out, so a Python checker keeps its ID.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

CONFLICT_CODE = "PSSP217"


def conflicts(
    rules: Iterable[dict],
    mdefs: Iterable,
    owner_of: Optional[Callable[[str], str]] = None,
) -> List[dict]:
    """Return a ``PSSP217`` diagnostic for each declarative rule whose ID,
    alias or name a ``MarkerDef`` already uses.

    *rules* are as :meth:`pssparser.core.LintEngine.rules` returns them;
    *owner_of* maps a marker ID to a description of who declared it
    (``"checker 'prc' from extension 'acme'"``).  The diagnostics have the
    shape of :meth:`~pssparser.core.LintEngine.rule_diagnostics`, located at
    the rule, with ``rule`` set to the rule's ID: the caller drops those
    rules.
    """
    ids: Dict[str, str] = {}
    names: Dict[str, str] = {}
    for md in mdefs:
        ids.setdefault(md.id, md.id)
        for alias in getattr(md, "aliases", ()) or ():
            ids.setdefault(alias, md.id)
        if getattr(md, "name", ""):
            names.setdefault(md.name, md.id)

    def owner(mid: str) -> str:
        who = owner_of(mid) if owner_of is not None else ""
        return f"{mid}, declared by {who}" if who else mid

    out: List[dict] = []
    for r in rules:
        claims = [("ID", r["id"], ids)]
        if r.get("name"):
            claims.append(("name", r["name"], names))
        claims += [("alias", a, ids) for a in r.get("aliases", ())]
        for what, key, table in claims:
            if key not in table:
                continue
            mid = table[key]
            taken = ("the ID of marker" if what != "name" and key == mid
                     else "an alias of marker" if what != "name"
                     else "the name of marker")
            out.append({
                "code": CONFLICT_CODE,
                "severity": "error",
                "message": f"rule {what} '{key}' is already {taken} {owner(mid)}",
                "file": r.get("file", ""),
                "line": r.get("line", 0),
                "col": r.get("col", 0),
                "rule": r["id"],
            })
    return out


# -- Finding and loading rule files -----------------------------------------

#: The extensions a directory entry is examined for (format §6.2).
RULE_FILE_EXTENSIONS = (".yaml", ".yml", ".json")

#: Why a file in a named directory is not a rule file, by probe result.
SKIP_REASONS = {
    "empty": "the file is empty",
    "not-yaml": "not valid YAML, and no line starts 'pss-rules:'",
    "not-mapping": "the top level is not a mapping",
    "no-key": "no top-level 'pss-rules' key",
}


class RulePathError(Exception):
    """A rule path that does not exist or cannot be read: a usage error."""


@dataclass
class RulePath:
    """One ``[lint] rules`` entry or ``--rules`` argument.

    *path* is already resolved (a config entry against its file's
    directory); *origin* names where it came from, for error messages.
    """

    path: str
    origin: str = "command line"


@dataclass
class RuleLoad:
    """What loading the rule files gave."""

    #: The engine, holding every rule that loaded (the runner's input, C5).
    engine: object = None
    #: Rule files loaded, in order, as display paths (built-ins excluded).
    files: List[str] = field(default_factory=list)
    #: Files in a named directory that were not rule files: (path, reason).
    skipped: List[Tuple[str, str]] = field(default_factory=list)
    #: Every rule-file diagnostic, as marker dicts (``Diagnostic.from_marker``).
    diagnostics: List[dict] = field(default_factory=list)
    #: IDs of rules left out because a Python ``MarkerDef`` holds their ID,
    #: an alias or name.  The engine still holds them; the runner skips them.
    refused: Set[str] = field(default_factory=set)
    #: Where each loaded file came from, by display path: the origin of the
    #: rule path that reached it (``"<file>: lint.rules"``, ``"--rules"``).
    origins: Dict[str, str] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        return any(d["severity"] == "error" for d in self.diagnostics)


def display_path(path: str) -> str:
    """*path* relative to the working directory when that is shorter."""
    try:
        rel = os.path.relpath(path)
    except ValueError:
        return path
    return path if rel.startswith(".." + os.sep + "..") else rel


def _read(path: str, origin: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except UnicodeDecodeError as exc:
        raise RulePathError(
            f"{origin}: rule file {display_path(path)} is not UTF-8 ({exc.reason} "
            f"at byte {exc.start})") from None
    except OSError as exc:
        raise RulePathError(
            f"{origin}: cannot read rule file {display_path(path)}: "
            f"{exc.strerror or exc}") from None


def expand(entries: Sequence[RulePath], probe: Callable[[str], str]
           ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """Turn rule paths into ``(files, skipped)``.

    *files* is ``[(path, text)]`` in load order: each named file, and each
    rule file in a named directory, sorted by name.  *skipped* is
    ``[(path, reason)]`` for the other files in a named directory.  *probe*
    is :meth:`pssparser.core.LintEngine.probe_rules`.  A named file is never
    probed: if it is not a rule file, loading it says so.  A file reached
    twice (named, and in a named directory) is loaded once, at its first
    place, rather than clashing with itself.

    Raises :class:`RulePathError` for a path that does not exist or a file
    that cannot be read.
    """
    files: List[Tuple[str, str]] = []
    skipped: List[Tuple[str, str]] = []
    seen: Set[str] = set()

    def first(path: str) -> bool:
        real = os.path.realpath(path)
        if real in seen:
            return False
        seen.add(real)
        return True

    for entry in entries:
        if os.path.isdir(entry.path):
            try:
                names = sorted(os.listdir(entry.path))
            except OSError as exc:
                raise RulePathError(
                    f"{entry.origin}: cannot list rule directory "
                    f"{display_path(entry.path)}: {exc.strerror or exc}") from None
            for name in names:
                path = os.path.join(entry.path, name)
                if (os.path.splitext(name)[1] not in RULE_FILE_EXTENSIONS
                        or not os.path.isfile(path) or not first(path)):
                    continue
                text = _read(path, entry.origin)
                kind = probe(text)
                if kind == "rule-file":
                    files.append((path, text))
                else:
                    skipped.append((path, SKIP_REASONS[kind]))
        elif os.path.isfile(entry.path):
            if first(entry.path):
                files.append((entry.path, _read(entry.path, entry.origin)))
        else:
            raise RulePathError(
                f"{entry.origin}: rule path {display_path(entry.path)} does not exist")
    return files, skipped


def to_marker(d: dict) -> dict:
    """A rule-file diagnostic from the engine as a marker dict."""
    related = []
    if d.get("related"):
        r = d["related"]
        related.append({"file": r["file"], "line": r["line"], "col": r["col"],
                        "label": "first claimed here"})
    return {
        "severity": d["severity"],
        "message": f"[{d['code']}] {d['message']}",
        "file": d["file"],
        "line": d["line"],
        "col": d["col"],
        "code": d["code"],
        "extent": 0,
        "related": related,
    }


def _origin_of(path: str, entries: Sequence[RulePath]) -> str:
    """The origin of the first entry that names *path*, or its directory."""
    real = os.path.realpath(path)
    for entry in entries:
        named = os.path.realpath(entry.path)
        if named == real or named == os.path.dirname(real):
            return entry.origin
    return ""


def load(entries: Sequence[RulePath], mdefs: Iterable = (),
         owner_of: Optional[Callable[[str], str]] = None,
         engine=None) -> RuleLoad:
    """Load the built-in rules, then *entries* in order, into a new engine
    (or *engine*), and check them against *mdefs*, the Python registry.

    Raises :class:`RulePathError` for a missing or unreadable path; every
    problem inside a rule file is a diagnostic.
    """
    if engine is None:
        from pssparser.core import Factory
        engine = Factory.inst().mkLintEngine()
    engine.load_builtin_rules()
    files, skipped = expand(entries, engine.probe_rules)
    out = RuleLoad(engine=engine, skipped=[(display_path(p), r) for p, r in skipped])
    for path, text in files:
        shown = display_path(path)
        engine.load_rules(shown, text)
        out.files.append(shown)
        out.origins[shown] = _origin_of(path, entries)
    out.diagnostics = [to_marker(d) for d in engine.rule_diagnostics()]
    clashes = conflicts(engine.rules(), mdefs, owner_of)
    out.diagnostics += [to_marker(d) for d in clashes]
    out.refused = {d["rule"] for d in clashes}
    return out
