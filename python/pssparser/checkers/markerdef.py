"""Structured metadata for one diagnostic code."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

from .taxonomy import TIER_SEVERITY


@dataclass(frozen=True)
class Example:
    """One documented example for a rule.

    ``expect`` lists the ``(line, col)`` positions the rule must report in
    ``code``; an empty ``expect`` is a "good" example on which the rule must
    stay silent.  ``fixed`` is the source after the rule's fix is applied,
    for rules that offer one.
    """

    code: str
    expect: Tuple[Tuple[int, int], ...] = ()
    fixed: str = ""
    note: str = ""


@dataclass(frozen=True)
class MarkerDef:
    """Describes one diagnostic that a checker (or the core) may emit.

    Attributes
    ----------
    id:
        Globally unique identifier string, e.g. ``"PRC042"``: a namespace of
        two to five capital letters, then three digits.  IDs must be unique
        across *all* registered checkers and the core; the
        ``CheckerManager`` enforces this at discovery time.

        **The ``PSS``, ``LINT``, ``PSSP`` and ``PSSX`` namespaces are
        reserved for pssparser** -- ``PSS`` for LRM violations, ``LINT`` for
        lint rules, ``PSSP`` for the tool's own diagnostics.  Choose a
        distinct namespace for a plug-in (``PSC042``, ``PRC001``).  This is
        stated in the plug-in guide too, but this docstring is where an
        implementer actually looks when filling the field in.
    severity:
        Default severity: ``"error"``, ``"warning"``, ``"info"``, or
        ``"hint"``.  Some IDs cover a family of related messages that are not
        all emitted at the same severity; this is the representative one.
        Leave it ``""`` on a tiered rule to take the tier's default.
    summary:
        One-line description displayed in ``--list-markers`` output.
    detail:
        Multi-line explanation shown by ``--describe ID``.  May include
        reStructuredText markup.
    patterns:
        Regular expressions matched (case-insensitively) against a marker's
        message text to assign this ID.  Only meaningful for core markers,
        which originate in C++ and therefore carry no ID of their own -- see
        ``pssparser.cli.commands._assign_core_code``.  Checker-produced markers
        set their ``code`` directly and leave this empty.

    Lifecycle (marker-id-namespaces §2.5)
    -------------------------------------
    status:
        ``"active"``, ``"deprecated"`` (still emitted, has a successor),
        ``"retired"`` (never emitted, never reused; kept so ``--describe``
        can explain it) or ``"reserved"`` (allocated, not yet emitted).
    replaced_by:
        Successor code(s) of a deprecated or retired code.
    aliases:
        Old codes that now mean this one.  A configuration key, ``-W`` flag
        or ``--describe`` naming an alias is rewritten to this ID.
    since:
        The rules version (``"YYYY.N"``) the code entered the rule set.

    Lint metadata (lint-framework L2)
    ---------------------------------
    name:
        Kebab-case rule name, unique, accepted wherever an ID is.
    tier:
        ``""`` for core LRM errors; otherwise one of
        :data:`~pssparser.checkers.taxonomy.TIERS`.  Gives the default
        severity and the profiles the rule belongs to.
    family, level:
        Rule family and analysis level, from the closed sets in
        :mod:`~pssparser.checkers.taxonomy`.
    default_enabled:
        Whether the tier's profile turns the rule on.
    fix:
        ``"none"``, ``"safe"`` or ``"unsafe"``.
    lrm:
        LRM clause references, e.g. ``("11.4.6",)``.
    examples:
        :class:`Example` records; drive the docs and the rule harness.
    options_schema:
        Per-rule options, in the ``CheckerBase.options_schema`` format.
    """

    id: str
    severity: str
    summary: str
    detail: str = ""
    patterns: Tuple[str, ...] = field(default_factory=tuple)
    # -- lifecycle --
    status: str = "active"
    replaced_by: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()
    since: str = ""
    # -- lint --
    name: str = ""
    tier: str = ""
    family: str = ""
    level: str = ""
    default_enabled: bool = True
    fix: str = "none"
    lrm: Tuple[str, ...] = ()
    examples: Tuple[Example, ...] = ()
    options_schema: Dict[str, Any] = field(
        default_factory=dict, hash=False, compare=False
    )

    def __post_init__(self) -> None:
        # A tiered rule may leave severity empty and take the tier's default
        # (L2); filled in here so every reader sees a concrete severity.
        if not self.severity and self.tier in TIER_SEVERITY:
            object.__setattr__(self, "severity", TIER_SEVERITY[self.tier])

    @property
    def is_lint(self) -> bool:
        """True for a tiered rule other than a ``tool`` diagnostic."""
        return bool(self.tier) and self.tier != "tool"

    @property
    def emittable(self) -> bool:
        """False for retired and reserved codes, which never appear in output."""
        return self.status in ("active", "deprecated")
