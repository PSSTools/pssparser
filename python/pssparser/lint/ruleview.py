"""Declarative rules as registry entries (lint-core-plan C4.4).

The core engine holds the rules loaded from ``pss-rules`` files.  This module
shows them to the Python side as ``MarkerDef``s, so that everything that
reads the registry -- ``--describe``, ``--explain``, ``--list-markers``,
selectors and profiles, ``[severity]``, SARIF's rule table and
``docs/lint-rules.rst`` -- sees them exactly as it sees a Python checker's
rules.  The engine stays the owner: the view is rebuilt from
:meth:`pssparser.core.LintEngine.rules`, never edited.

The view is registered with the :class:`~pssparser.checkers.CheckerManager`
as one metadata-only checker, :data:`CHECKER_NAME`, like the core's: it is
never run as a Python checker (the runner, C5, runs the rules in the core).
"""
from __future__ import annotations

import re
from typing import Iterable, List, Type

from pssparser.checkers.base import CheckerBase
from pssparser.checkers.markerdef import Example, MarkerDef

#: The checker the declarative rules are listed under.
CHECKER_NAME = "pss-rules"

#: Rule files compiled into the core are named ``pssparser:rules/<file>``.
BUILTIN_PREFIX = "pssparser:"


#: An example's ``// expect: ...`` and ``/* expect: ... */`` comments
#: (format §4), which are for the harness, not the reader.
_EXPECT = re.compile(r"[ \t]*//[ \t]*expect:.*|/\*[ \t]*expect:.*?\*/[ \t]?")


def _shown(text: str) -> str:
    """Example text as documentation shows it: without expect comments."""
    return "\n".join(_EXPECT.sub("", line).rstrip() for line in text.splitlines())


def _example(ex: dict) -> Example:
    files = ex.get("files", [])
    expect = tuple((e["line"], e["col"]) for f in files for e in f.get("expect", ()))
    if len(files) == 1:
        code = _shown(files[0]["text"])
    else:
        # Several files: shown one after another, each under its name.
        code = "\n".join(f"// {f['name']}\n{_shown(f['text']).rstrip()}" for f in files)
    return Example(code=code.strip("\n"), expect=expect, note=ex.get("name", ""))


def _options(rule: dict) -> dict:
    out = {}
    for o in rule.get("options", ()):
        spec = {"type": o["type"], "default": o["default"]}
        if o.get("help"):
            spec["help"] = o["help"]
        if o.get("choices"):
            spec["choices"] = list(o["choices"])
        out[o["name"]] = spec
    return out


def source_of(rule: dict) -> str:
    """Where a rule is defined, as ``file:line:col``."""
    return f"{rule.get('file', '')}:{rule.get('line', 0)}:{rule.get('col', 0)}"


def marker_def(rule: dict) -> MarkerDef:
    """One rule, as :meth:`~pssparser.core.LintEngine.rules` gives it, as a
    ``MarkerDef``.  ``severity`` left empty takes the tier's default."""
    return MarkerDef(
        id=rule["id"],
        severity=rule.get("severity", ""),
        summary=rule.get("summary", ""),
        detail=rule.get("doc", "").strip(),
        status=rule.get("status", "active"),
        replaced_by=tuple(rule.get("replaced_by", ())),
        aliases=tuple(rule.get("aliases", ())),
        since=rule.get("since", ""),
        name=rule.get("name", ""),
        tier=rule.get("tier", ""),
        family=rule.get("family", ""),
        level=rule.get("level", ""),
        default_enabled=rule.get("default_enabled", True),
        lrm=tuple(rule.get("lrm", ())),
        examples=tuple(_example(e) for e in rule.get("examples", ())),
        options_schema=_options(rule),
        scope=rule.get("scope", ""),
        source=source_of(rule),
        match=tuple(rule.get("match", {}).get("kind", ())),
    )


def marker_defs(rules: Iterable[dict], refused: Iterable[str] = ()) -> List[MarkerDef]:
    """The rules that take part in a run, in load order: every loaded rule
    except those *refused* because a Python ``MarkerDef`` holds their ID,
    alias or name (:func:`pssparser.lint.rulefiles.conflicts`)."""
    skip = set(refused)
    return [marker_def(r) for r in rules if r["id"] not in skip]


def is_builtin(md: MarkerDef) -> bool:
    """True for a rule from a rule file compiled into pssparser."""
    return md.source.startswith(BUILTIN_PREFIX)


def checker_class(mdefs: List[MarkerDef]) -> Type[CheckerBase]:
    """A metadata-only checker class whose ``marker_defs`` are *mdefs*."""

    class DeclarativeRules(CheckerBase):
        name = CHECKER_NAME
        description = "Declarative rules from pss-rules files"
        #: Metadata only: never instantiated for a run (as the core's).
        is_builtin = True
        is_declarative = True
        marker_defs = list(mdefs)

        def check(self, context) -> None:  # pragma: no cover - never run
            pass

    return DeclarativeRules
