"""Rule selectors and profile expansion (lint-framework L3).

Everywhere an ID is accepted -- ``[severity]`` keys, ``-Werror=``,
``[lint] select``/``ignore`` -- these forms are accepted too:

==============  ====================  ======================================
Form            Example               Matches
==============  ====================  ======================================
ID              ``LINT104``           one rule
name            ``unknown-annotation``  one rule
prefix          ``LINT1``             an ID band
namespace       ``PRC``               every code in the namespace
family          ``family:constraint`` every rule in the family
tier            ``correctness``       every rule in the tier
profile         ``recommended``       every rule the profile enables
==============  ====================  ======================================

When several selectors match one rule, the most specific wins: ID or name,
then prefix (a longer prefix is more specific), then namespace, family, tier,
and profile last.  A tie between ``select`` and ``ignore`` goes to
``ignore``.  This is Ruff's model; it lets ``select = ["recommended",
"pedantic"]`` with ``ignore = ["LINT203"]`` mean what it says.

Selectors are resolved **once**, at configuration time, to concrete IDs, so
everything downstream stays an ID lookup.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

from . import taxonomy

_PREFIX_RE = re.compile(r"^([A-Z]{2,5})([0-9]{0,2})$")

#: Specificity by selector kind; a prefix adds its digit count.
_SPECIFICITY = {
    "id": 100,
    "name": 100,
    "prefix": 50,
    "namespace": 50,
    "family": 30,
    "tier": 20,
    "profile": 10,
}


class SelectorError(ValueError):
    """An unknown or malformed selector; the message carries a did-you-mean."""


@dataclass(frozen=True)
class Selector:
    text: str
    kind: str
    value: str

    @property
    def specificity(self) -> int:
        base = _SPECIFICITY[self.kind]
        if self.kind == "prefix":
            m = _PREFIX_RE.match(self.value)
            base += len(m.group(2)) if m else 0
        return base

    def matches(self, md, profile_members: Optional[Set[str]] = None) -> bool:
        if self.kind == "id":
            return md.id == self.value
        if self.kind == "name":
            return md.name == self.value
        if self.kind == "prefix":
            return md.id.startswith(self.value)
        if self.kind == "namespace":
            return taxonomy.namespace_of(md.id) == self.value
        if self.kind == "family":
            return md.family == self.value
        if self.kind == "tier":
            return md.tier == self.value
        if self.kind == "profile":
            return profile_members is not None and md.id in profile_members
        return False


class RuleSet:
    """Every known ``MarkerDef``, with selector parsing and profile expansion.

    Parameters
    ----------
    mdefs:
        Every registered marker definition (``CheckerManager.all_marker_defs``).
    rules_version:
        The ``rules-version`` pin, ``"YYYY.N"``, or empty for no pin.
    minimal:
        IDs of the ``minimal`` profile.  Defaults to the core-emitted lint
        from :mod:`pssparser.lint.catalog`.
    """

    def __init__(
        self,
        mdefs: Iterable,
        *,
        rules_version: str = "",
        minimal: Optional[Sequence[str]] = None,
    ) -> None:
        self.mdefs = [md for md in mdefs if md.emittable]
        self.by_id = {md.id: md for md in self.mdefs}
        self.by_name = {md.name: md for md in self.mdefs if md.name}
        self.lint = [md for md in self.mdefs if md.is_lint]
        self.rules_version = rules_version
        self._pin = taxonomy.parse_rules_version(rules_version) if rules_version else None
        if minimal is None:
            from pssparser.lint.catalog import MINIMAL_IDS
            minimal = MINIMAL_IDS
        self.minimal = tuple(m for m in minimal if m in self.by_id)
        self._profiles: Dict[str, Set[str]] = {}
        self.aliases: Dict[str, str] = {}

    # -- parsing ----------------------------------------------------------

    def candidates(self) -> List[str]:
        """Every spelling a selector may take, for did-you-mean."""
        namespaces = {taxonomy.namespace_of(md.id) for md in self.mdefs}
        return sorted(
            set(self.by_id) | set(self.by_name) | set(taxonomy.TIERS)
            | {f"family:{f}" for f in taxonomy.FAMILIES}
            | set(taxonomy.PROFILES) | (namespaces - {""})
        )

    def parse(self, text: str) -> Selector:
        """Parse *text* into a :class:`Selector`, or raise :class:`SelectorError`."""
        text = (text or "").strip()
        canonical = self.aliases.get(text, text)
        if canonical in self.by_id:
            return Selector(text, "id", canonical)
        if canonical in self.by_name:
            return Selector(text, "name", canonical)
        if text in taxonomy.PROFILES:
            return Selector(text, "profile", text)
        if text in taxonomy.TIERS:
            return Selector(text, "tier", text)
        if text.startswith("family:"):
            fam = text[len("family:"):]
            if fam in taxonomy.FAMILIES:
                return Selector(text, "family", fam)
            raise SelectorError(self._unknown(text, "family"))
        m = _PREFIX_RE.match(text)
        if m is not None:
            ns, digits = m.groups()
            if any(md.id.startswith(text) for md in self.mdefs):
                return Selector(text, "prefix" if digits else "namespace", text)
        raise SelectorError(self._unknown(text))

    def _unknown(self, text: str, what: str = "") -> str:
        from pssparser.cli.suggestion import suggest

        hint = suggest(text, self.candidates())
        kind = f"{what} selector" if what else "marker or selector"
        detail = (f"did you mean '{hint}'?" if hint
                  else "run --list-markers to see the declared IDs and names")
        return f"unknown {kind} '{text}'; {detail}"

    # -- profiles ---------------------------------------------------------

    def _pinned_out(self, md) -> bool:
        if self._pin is None or not md.since:
            return False
        since = taxonomy.parse_rules_version(md.since)
        return since is not None and since > self._pin

    def profile_members(self, profile: str) -> Set[str]:
        """IDs *profile* enables, after the ``rules-version`` pin.

        Every profile but ``none`` includes ``minimal`` -- the warnings users
        saw before lint existed -- whatever its tiers say, so moving to a
        larger profile never drops one (LINT402 is ``style``).
        """
        if profile in self._profiles:
            return self._profiles[profile]
        if profile == "none":
            members: Set[str] = set()
        else:
            members = set(self.minimal)
            tiers = taxonomy.PROFILE_TIERS.get(profile, ())
            for md in self.lint:
                if (md.tier in tiers and md.default_enabled
                        and not self._pinned_out(md)):
                    members.add(md.id)
        self._profiles[profile] = members
        return members

    def held_back(self, profile: str) -> List[str]:
        """Rules the ``rules-version`` pin keeps out of *profile*."""
        if self._pin is None or profile == "none":
            return []
        tiers = taxonomy.PROFILE_TIERS.get(profile, ())
        return sorted(
            md.id for md in self.lint
            if md.tier in tiers and md.default_enabled and self._pinned_out(md)
        )

    # -- resolution -------------------------------------------------------

    def _best(self, selectors: Sequence[Selector], md) -> int:
        best = -1
        for sel in selectors:
            members = (self.profile_members(sel.value)
                       if sel.kind == "profile" else None)
            if sel.matches(md, members) and sel.specificity > best:
                best = sel.specificity
        return best

    def resolve(
        self,
        profile: str,
        select: Sequence[str] = (),
        ignore: Sequence[str] = (),
    ) -> Set[str]:
        """The set of enabled lint rule IDs.

        *profile* is the base, at profile specificity; *select* adds and
        *ignore* removes, most specific selector winning, ties to *ignore*.
        """
        on = [Selector(profile, "profile", profile)] + [self.parse(t) for t in select]
        off = [self.parse(t) for t in ignore]
        enabled = set()
        for md in self.lint:
            best_on = self._best(on, md)
            best_off = self._best(off, md)
            if best_on >= 0 and best_on > best_off:
                enabled.add(md.id)
        return enabled

    def expand(self, texts: Iterable[str], *, include_core_errors: bool = False
               ) -> Dict[str, Tuple[str, int]]:
        """Map each matching ID to ``(selector text, specificity)``, most
        specific selector per ID.

        Used for ``[severity]`` keys and ``-W`` groups.  A broad selector
        (anything but an ID or name) never expands to a core error unless
        *include_core_errors*: core errors cannot be configured, and a
        namespace-wide ``PSS = "warning"`` must not try.
        """
        result: Dict[str, Tuple[str, int]] = {}
        for text in texts:
            sel = self.parse(text)
            members = (self.profile_members(sel.value)
                       if sel.kind == "profile" else None)
            for md in self.mdefs:
                if not sel.matches(md, members):
                    continue
                if (sel.kind not in ("id", "name") and not include_core_errors
                        and _is_core_error(md)):
                    continue
                prev = result.get(md.id)
                if prev is None or sel.specificity > prev[1]:
                    result[md.id] = (text, sel.specificity)
        return result


def _is_core_error(md) -> bool:
    # Tool errors (PSSP000, PSSP008 ...) carry tier "tool"; a `tool = "warning"`
    # key must not reach them any more than `PSS = "warning"` reaches PSS002.
    return (md.severity == "error" and md.tier in ("", "tool")
            and taxonomy.namespace_of(md.id) in ("PSS", "PSSP"))
