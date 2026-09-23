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

    #: Declared configuration options, as ``{name: spec}``.  Each *spec* is a
    #: dict with:
    #:
    #: ``type``
    #:     one of ``"string"``, ``"int"``, ``"bool"``, ``"string-list"``
    #: ``default``
    #:     the value :meth:`configure` receives when the user sets nothing
    #: ``help``
    #:     one line, shown by ``--describe-checker``
    #: ``choices``
    #:     optional; for ``"string"``, the permitted values
    #:
    #: Declaring the schema is what makes an unknown or mistyped option a
    #: startup error naming the checker rather than a silently ignored
    #: table.  A checker that declares nothing accepts nothing, and any
    #: ``[checker.<name>]`` table aimed at it is an error.
    options_schema: dict = {}

    def configure(self, options: dict) -> None:
        """Receive validated options before :meth:`check` is called.

        *options* always carries every key in :attr:`options_schema`, with
        declared defaults filled in for anything the user did not set, so an
        implementation never needs ``.get()`` with a second default.

        Optional: the base implementation stores them on ``self.options``,
        which is enough for a checker that only needs to read them.
        """
        self.options = dict(options)

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
