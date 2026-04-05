"""Abstract base class for all pssparser plug-in checkers."""
from __future__ import annotations

from typing import TYPE_CHECKING, List

from .markerdef import MarkerDef

if TYPE_CHECKING:
    from .context import CheckContext


class CheckerBase:
    """Abstract base for all pssparser plug-in checkers.

    Subclasses must override :attr:`name`, :attr:`description`,
    :attr:`marker_defs`, and :meth:`check`.
    """

    #: Short unique identifier, e.g. ``"naming-convention"``.
    name: str = ""

    #: One-line description shown in ``--list-checkers``.
    description: str = ""

    #: Structured definitions of every marker this checker may emit.
    #: Each subclass must declare its own list — do *not* mutate the
    #: inherited one.
    marker_defs: List[MarkerDef] = []

    #: If ``True`` the checker runs even when ``--syntax-only`` was
    #: requested (i.e. the linked AST is not available).
    runs_without_link: bool = False

    def check(self, context: "CheckContext") -> None:
        """Perform checks and emit diagnostics via *context*.

        Parameters
        ----------
        context:
            Provides access to the AST and the marker-emission API.
        """
        raise NotImplementedError(
            f"{type(self).__name__} must implement check()"
        )
