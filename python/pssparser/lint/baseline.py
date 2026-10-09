"""Baselines: record today's findings, report only new ones.

A baseline lets a team switch lint on over an existing model and gate CI on
*new* findings only.  ``pssparser --write-baseline lint-baseline.json`` records
every finding the run reports; a later run with ``--baseline`` (or
``[lint] baseline``) drops the findings it recorded and reports the rest.

The file::

    {
      "schema": "pssparser-baseline/1",
      "rules-version": "2026.1",
      "entries": [
        {"code": "LINT402", "file": "src/m.pss", "fingerprint": "...", "count": 2},
        ...
      ]
    }

* A finding is matched by ``(code, file, fingerprint)``
  (:mod:`pssparser.lint.fingerprint`), so it survives edits elsewhere in the
  file and reformatting.
* ``count`` is how many identical findings (same fingerprint) were recorded.
  With three recorded and four found, three are baselined and one is new --
  the last one in source order, since nothing tells the four apart.
* ``file`` is relative to the directory holding the baseline, with ``/``
  separators, so a baseline checked into a repository works from any
  checkout.
* Entries are sorted and written one per line, so a diff of the file reads as
  a list of findings added and removed.
* ``rules-version`` records the run's ``lint.rules-version`` pin (``null``
  when unpinned).  It is informational.

An LRM error, and any of pssparser's own diagnostics (``PSSP``, tier
``tool``), is never recorded and never matched: a baseline exists to defer
lint findings, not to accept a model that does not compile.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

SCHEMA = "pssparser-baseline/1"


class BaselineError(ValueError):
    """A baseline file that cannot be read; the message names the file."""


@dataclass
class Entry:
    code: str
    file: str
    fingerprint: str
    count: int = 1
    #: 1-based line of the entry in the file it was read from (0 if built).
    line: int = 0

    @property
    def key(self) -> Tuple[str, str, str]:
        return (self.code, self.file, self.fingerprint)

    def to_json(self) -> dict:
        return {"code": self.code, "file": self.file,
                "fingerprint": self.fingerprint, "count": self.count}


@dataclass
class Baseline:
    """A baseline: its file and its entries."""

    path: str
    entries: List[Entry] = field(default_factory=list)
    rules_version: Optional[str] = None

    @property
    def directory(self) -> str:
        return os.path.dirname(os.path.realpath(self.path))

    def relative(self, file: str) -> str:
        """*file* as the baseline records it: relative to its directory."""
        return relative_to(file, self.directory)

    def total(self) -> int:
        return sum(e.count for e in self.entries)


def relative_to(file: str, directory: str) -> str:
    real = os.path.realpath(file)
    try:
        rel = os.path.relpath(real, directory)
    except ValueError:  # another drive on Windows
        return Path(real).as_posix()
    return PurePosixPath(*Path(rel).parts).as_posix()


# -- reading and writing ------------------------------------------------------

def load(path: str, *, aliases: Optional[Dict[str, str]] = None) -> Baseline:
    """Read *path*.  Raises :class:`BaselineError` naming the file.

    *aliases* maps a retired marker ID to its successor, so a baseline that
    records an ID which has since moved (``PSS104`` -> ``LINT601``) still
    matches.
    """
    try:
        with open(path, "r", encoding="utf-8") as fp:
            text = fp.read()
    except FileNotFoundError:
        raise BaselineError(
            f"baseline file not found: {path} (create it with "
            f"--write-baseline)") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise BaselineError(f"{path}: cannot read baseline: {exc}") from None
    try:
        doc = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BaselineError(
            f"{path}:{exc.lineno}:{exc.colno}: not a baseline file: "
            f"invalid JSON: {exc.msg}") from None

    def bad(why: str) -> BaselineError:
        return BaselineError(f"{path}: not a baseline file: {why}")

    if not isinstance(doc, dict):
        raise bad("expected a JSON object")
    if doc.get("schema") != SCHEMA:
        raise bad(f"'schema' is {doc.get('schema')!r}, expected {SCHEMA!r}")
    entries = doc.get("entries")
    if not isinstance(entries, list):
        raise bad("'entries' must be an array")
    rules_version = doc.get("rules-version")
    if rules_version is not None and not isinstance(rules_version, str):
        raise bad("'rules-version' must be a string or null")

    lines = text.splitlines()
    out: List[Entry] = []
    for n, raw in enumerate(entries):
        if not isinstance(raw, dict):
            raise bad(f"entry {n + 1} is not an object")
        for key in ("code", "file", "fingerprint"):
            if not isinstance(raw.get(key), str) or not raw[key]:
                raise bad(f"entry {n + 1} has no '{key}' string")
        count = raw.get("count", 1)
        if not isinstance(count, int) or isinstance(count, bool) or count < 1:
            raise bad(f"entry {n + 1}: 'count' must be a positive integer")
        code = raw["code"]
        if aliases:
            code = aliases.get(code, code)
        out.append(Entry(code=code, file=raw["file"],
                         fingerprint=raw["fingerprint"], count=count,
                         line=_line_of(lines, raw["fingerprint"])))
    return Baseline(path=path, entries=out, rules_version=rules_version)


def _line_of(lines: List[str], fingerprint: str) -> int:
    needle = '"%s"' % fingerprint
    for i, text in enumerate(lines):
        if needle in text:
            return i + 1
    return 0


def dumps(baseline: Baseline) -> str:
    """The file text: sorted entries, one per line."""
    entries = sorted(baseline.entries, key=lambda e: (e.file, e.code, e.fingerprint))
    # One key per line at the top, one entry per line below: diffable.
    head = json.dumps({"schema": SCHEMA,
                       "rules-version": baseline.rules_version}, indent=2)[:-2]
    if not entries:
        return head + ',\n  "entries": []\n}\n'
    body = ",\n".join("    " + json.dumps(e.to_json()) for e in entries)
    return head + ',\n  "entries": [\n' + body + "\n  ]\n}\n"


def write(baseline: Baseline) -> None:
    """Write *baseline* to its path, replacing the file atomically."""
    text = dumps(baseline)
    directory = os.path.dirname(os.path.abspath(baseline.path))
    os.makedirs(directory, exist_ok=True)
    tmp = baseline.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as fp:
        fp.write(text)
    os.replace(tmp, baseline.path)


# -- building and matching ------------------------------------------------------

def build(path: str, diags: Iterable[Any], *,
          rules_version: Optional[str] = None) -> Baseline:
    """A baseline recording *diags*, which must already carry fingerprints
    and be eligible (see :func:`eligible`)."""
    baseline = Baseline(path=path, rules_version=rules_version or None)
    counts: Dict[Tuple[str, str, str], int] = {}
    for d in diags:
        key = (d.code, baseline.relative(d.file), d.fingerprint)
        counts[key] = counts.get(key, 0) + 1
    baseline.entries = [Entry(code=c, file=f, fingerprint=fp, count=n)
                        for (c, f, fp), n in counts.items()]
    return baseline


def eligible(diag, is_core_error: Callable[[str], bool]) -> bool:
    """Whether a baseline may record or match *diag*: it has a code and a
    fingerprint, and is neither an LRM error nor a tool diagnostic."""
    from pssparser.checkers import taxonomy

    code = getattr(diag, "code", None)
    if not code or not getattr(diag, "fingerprint", None):
        return False
    if taxonomy.namespace_of(code) == "PSSP":
        return False
    return not is_core_error(code)


@dataclass
class MatchResult:
    #: Findings the baseline does not cover, in input order.
    new: List[Any] = field(default_factory=list)
    #: Findings it covers.
    baselined: List[Any] = field(default_factory=list)
    #: ``(entry, missing)``: an entry with fewer findings than recorded.
    stale: List[Tuple[Entry, int]] = field(default_factory=list)


def match(diags: Iterable[Any], baseline: Baseline, *,
          is_eligible: Callable[[Any], bool],
          checked: Optional[Callable[[Entry], bool]] = None) -> MatchResult:
    """Split *diags* into new and baselined findings, and find stale entries.

    *is_eligible* says whether a diagnostic may be matched at all.  *checked*
    says whether an entry's finding could have been reported by this run (its
    file was checked and its rule ran); only those can be stale.  ``None``
    means no entry is checked for staleness.
    """
    remaining = {e.key: e.count for e in baseline.entries}
    found: Dict[Tuple[str, str, str], int] = {}
    diags = list(diags)
    covered = [False] * len(diags)
    # Source order, so with more findings than recorded it is the last ones
    # that are reported as new.
    order = sorted(range(len(diags)),
                   key=lambda i: (diags[i].file, diags[i].line, diags[i].col, i))
    for i in order:
        d = diags[i]
        if not is_eligible(d):
            continue
        key = (d.code, baseline.relative(d.file), d.fingerprint)
        found[key] = found.get(key, 0) + 1
        if remaining.get(key, 0) > 0:
            remaining[key] -= 1
            covered[i] = True
    result = MatchResult()
    for d, hit in zip(diags, covered):
        (result.baselined if hit else result.new).append(d)
    if checked is not None:
        for e in baseline.entries:
            missing = e.count - found.get(e.key, 0)
            if missing > 0 and checked(e):
                result.stale.append((e, missing))
    return result
