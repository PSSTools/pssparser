"""Structured metadata for one diagnostic code."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Tuple


@dataclass(frozen=True)
class MarkerDef:
    """Describes one diagnostic that a checker (or the core) may emit.

    Attributes
    ----------
    id:
        Globally unique identifier string, e.g. ``"PSS001"`` or ``"PSC042"``.
        IDs must be unique across *all* registered checkers and the core; the
        ``CheckerManager`` enforces this at discovery time.
    severity:
        Default severity: ``"error"``, ``"warning"``, ``"info"``, or
        ``"hint"``.  Some IDs cover a family of related messages that are not
        all emitted at the same severity; this is the representative one.
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
    """

    id: str
    severity: str
    summary: str
    detail: str = ""
    patterns: Tuple[str, ...] = field(default_factory=tuple)
