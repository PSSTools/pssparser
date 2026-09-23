"""The ``pssparser.extensions`` contract: registries, records, and load issues.

An *extension* is one installable distribution that contributes a collection of
checkers.  It declares a single entry point in the ``pssparser.extensions``
group whose value is a module exposing ``register(registry)``::

    [options.entry_points]
    pssparser.extensions =
        acme-rules = acme_pss_rules

    # acme_pss_rules/__init__.py
    def register(reg):
        reg.version = "2.3.0"
        reg.description = "Acme house rules for PSS"
        reg.add_checker(NamingChecker)
        reg.add_checker(CoverageChecker)

The older ``pssparser.checkers`` group -- one entry point per checker class --
keeps working.  Each such entry point is adapted into a synthetic
single-checker extension so that the registry, the CLI, and the configuration
layer see exactly one model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Type

from .base import CheckerBase

#: Version of the checker-facing API this build provides.
#:
#: Bump this when the surface a checker is written against changes
#: *incompatibly* -- a ``CheckContext`` field removed, a ``MarkerDef`` field
#: renamed, ``check()``'s signature altered.  Adding a field or an optional
#: hook is not a break and must not bump it; extensions probe for those with
#: ``reg.api_version >= N`` inside ``register()``.
API_VERSION = 1

#: Pseudo-path carried by diagnostics that belong to the *tool* rather than to
#: any source file -- extension load failures and the like.  The human renderer
#: prints these without a ``file:line:col`` prefix and the file counter skips
#: them, so a failed extension does not report itself as a processed file.
NO_FILE = "<pssparser>"


class ExtensionError(Exception):
    """Raised by ``ExtensionRegistry`` when an extension misuses the API.

    Caught by the manager and reported as ``PSS030``; it never escapes
    discovery.
    """


class ExtensionRegistry:
    """The object handed to an extension's ``register()`` function.

    Inbound attributes (set by pssparser, read by the extension):

    ``api_version``
        The checker-API version of the *running* pssparser.  Lets one
        extension support several pssparser releases by feature-probing.
    ``name``
        The entry-point key this extension was registered under.

    Outbound attributes (set by the extension, read by pssparser):

    ``version``, ``description``
        Shown by ``--list-extensions``.  ``version`` defaults to the
        distribution version when the extension does not set one.
    ``requires_api``
        Minimum ``API_VERSION`` this extension needs.  Declaring it is how an
        extension refuses to load against a pssparser too old for it, instead
        of failing with an ``AttributeError`` halfway through a check.
    """

    def __init__(
        self,
        name: str,
        *,
        api_version: int = API_VERSION,
        dist: Optional[str] = None,
        version: str = "",
    ) -> None:
        self.name = name
        self.api_version = api_version
        self.dist = dist
        self.version = version
        self.description = ""
        self.requires_api = 1
        self._checkers: List[Type[CheckerBase]] = []

    def add_checker(self, cls: Type[CheckerBase]) -> None:
        """Register one ``CheckerBase`` subclass.  Repeatable.

        Raises
        ------
        ExtensionError
            If *cls* is not a ``CheckerBase`` subclass, declares an empty
            ``name``, or is added twice by this extension.
        """
        if not isinstance(cls, type) or not issubclass(cls, CheckerBase):
            raise ExtensionError(
                f"add_checker() expects a CheckerBase subclass, got {cls!r}"
            )
        # The class is the authority on its own name (see CK-X1); an empty one
        # leaves the checker unselectable and unnameable in any diagnostic.
        checker_name = getattr(cls, "name", "")
        if not checker_name:
            raise ExtensionError(
                f"checker {cls.__name__!r} declares an empty 'name' attribute"
            )
        if cls in self._checkers:
            raise ExtensionError(
                f"checker {checker_name!r} was added twice by this extension"
            )
        self._checkers.append(cls)

    @property
    def checkers(self) -> List[Type[CheckerBase]]:
        """The classes registered so far, in registration order."""
        return list(self._checkers)


@dataclass
class ExtensionInfo:
    """What the manager retains about one successfully-loaded extension."""

    name: str
    version: str = ""
    description: str = ""
    dist: Optional[str] = None
    #: Checker names this extension contributed *and that were accepted*.
    #: A checker rejected for a duplicate marker ID is not listed here.
    checkers: List[str] = field(default_factory=list)
    #: True for a ``pssparser.checkers`` entry point adapted into an
    #: extension, so ``--list-extensions`` can say where it came from.
    legacy: bool = False


@dataclass
class ExtensionIssue:
    """One problem found while loading extensions.

    Converted to a diagnostic by ``CheckerManager.load_diagnostics``; carries
    no source location because none of these originate in a source file.
    """

    code: str
    severity: str
    message: str


def make_registry(
    name: str,
    *,
    dist: Optional[str] = None,
    version: str = "",
) -> ExtensionRegistry:
    """Build a registry bound to this build's ``API_VERSION``."""
    return ExtensionRegistry(name, api_version=API_VERSION, dist=dist, version=version)
