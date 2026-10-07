"""Closed vocabularies for marker metadata: namespaces, tiers, families, profiles.

Everything here is data.  Validation (``manager._accept_checker``), the
selector engine, profile expansion, ``--explain`` and the generated rule
reference all read from these tables, so a tier or family added here is
accepted, selectable and documented in one edit.

Namespaces (lint-framework D-1, D-6):

``PSS``
    Normative PSS: a violation of the language reference manual.
``LINT``
    A lint rule: legal PSS that is probably not what the author meant.
``PSSP``
    pssparser itself: an extension failed to load, a construct is accepted but
    not represented, a configuration key used an old ID.
"""
from __future__ import annotations

import re
from typing import Dict, Optional, Tuple

#: ``namespace ::= [A-Z]{2,5}``, ``number ::= [0-9]{3}``.  Letters only in the
#: namespace, so a code splits without a lookup table.
CODE_RE = re.compile(r"^([A-Z]{2,5})([0-9]{3})$")

#: Namespaces no third-party checker may declare.  ``PSSX`` is held for a
#: future core split.
RESERVED_NAMESPACES = ("PSS", "PSSP", "PSSX", "LINT")

#: Lifecycle states (marker-id-namespaces §2.5).
STATUSES = ("active", "deprecated", "retired", "reserved")

#: Tier -> default severity (lint-framework L2).  ``tool`` is not a lint tier:
#: it marks pssparser's own diagnostics, which no profile selects or hides.
TIER_SEVERITY: Dict[str, str] = {
    "correctness": "warning",
    "suspicious": "warning",
    "portability": "warning",
    "simplify": "info",
    "style": "hint",
    "pedantic": "warning",
    "restriction": "warning",
    "nursery": "warning",
    "tool": "warning",
}

#: The lint tiers, in documentation order.
TIERS: Tuple[str, ...] = tuple(TIER_SEVERITY)

#: Lint tiers proper -- everything but ``tool``.
LINT_TIERS: Tuple[str, ...] = tuple(t for t in TIERS if t != "tool")

FAMILIES: Tuple[str, ...] = (
    "constraint", "activity", "exec", "decl", "import", "register",
    "evolution", "naming", "metric",
)

#: Analysis levels (lint-criteria §3.3).
LEVELS: Tuple[str, ...] = ("L0", "L1", "L2", "L3", "L4", "L5")

FIX_KINDS: Tuple[str, ...] = ("none", "safe", "unsafe")

#: Profile names.  Expansion lives in :mod:`pssparser.checkers.selectors`.
PROFILES: Tuple[str, ...] = (
    "minimal", "recommended", "library", "strict", "all", "none",
)

#: The profile in effect when nothing selects one.  ``minimal`` is exactly the
#: core warnings that moved from ``PSS`` to ``LINT``, so the default output is
#: what it was before lint existed (plan F1.3); F3.9 moves this to
#: ``recommended``.
DEFAULT_PROFILE = "minimal"

#: Tiers each profile enables (``minimal`` is an explicit list, not a tier
#: set; every profile but ``none`` includes it on top of these).
PROFILE_TIERS: Dict[str, Tuple[str, ...]] = {
    "minimal": (),
    "recommended": ("correctness", "suspicious", "portability", "simplify"),
    "library": ("correctness", "suspicious", "portability", "simplify"),
    "strict": ("correctness", "suspicious", "portability", "simplify",
               "pedantic"),
    "all": ("correctness", "suspicious", "portability", "simplify",
            "style", "pedantic", "restriction"),
    "none": (),
}

#: ``"YYYY.N"``: the version a rule entered the rule set (lint-framework D-7).
RULES_VERSION_RE = re.compile(r"^(\d{4})\.(\d+)$")

#: The project home, for SARIF ``informationUri``.
PROJECT_URL = "https://github.com/psstools/pssparser"

#: Where a rule's documentation lives; ``{id}`` is the lower-cased ID.  One
#: template, read by the text "see:" link, ``--explain`` and SARIF
#: ``helpUri``, so moving the docs is one edit.
RULE_DOC_URL = "https://psstools.github.io/pssparser/lint-rules.html#{id}"

_KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def split_code(code: str) -> Optional[Tuple[str, int]]:
    """Return ``(namespace, number)`` for a well-formed code, else ``None``.

    >>> split_code("LINT104")
    ('LINT', 104)
    """
    m = CODE_RE.match(code or "")
    if m is None:
        return None
    return m.group(1), int(m.group(2))


def namespace_of(code: str) -> str:
    """The namespace of *code*, or ``""`` when it does not parse."""
    parts = split_code(code)
    return parts[0] if parts else ""


def is_kebab(name: str) -> bool:
    return bool(_KEBAB_RE.match(name or ""))


def parse_rules_version(text: str) -> Optional[Tuple[int, int]]:
    """``"2026.1"`` -> ``(2026, 1)``; anything else -> ``None``."""
    m = RULES_VERSION_RE.match(text or "")
    if m is None:
        return None
    return int(m.group(1)), int(m.group(2))


def doc_url(code: str) -> str:
    return RULE_DOC_URL.format(id=code.lower())
