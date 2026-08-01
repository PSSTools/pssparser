"""Structured metadata for one diagnostic code."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarkerDef:
    """Describes one diagnostic that a checker (or the core) may emit.

    Attributes
    ----------
    id:
        Globally unique identifier string, e.g. ``"PSC042"``.
        IDs must be unique across *all* registered checkers and the core; the
        ``CheckerManager`` enforces this at discovery time.

        **The ``PSS`` prefix is reserved for the built-in ``CoreChecker``.**
        Choose a distinct prefix for a plug-in -- three letters plus a
        three-digit number is the convention (``PSC042``, ``PSL001``).  This
        is stated in the plug-in guide too, but this docstring is where an
        implementer actually looks when filling the field in.
    severity:
        Default severity: ``"error"``, ``"warning"``, ``"info"``, or
        ``"hint"``.
    summary:
        One-line description displayed in ``--list-markers`` output.
    detail:
        Multi-line explanation shown by ``--describe ID``.  May include
        reStructuredText markup.
    """

    id: str
    severity: str
    summary: str
    detail: str = ""
