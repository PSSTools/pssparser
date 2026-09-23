"""Example pssparser *extension*: a collection of checkers in one package.

The whole contract with pssparser is the ``register()`` function below, wired
up by a single ``pssparser.extensions`` entry point in ``setup.cfg``::

    [options.entry_points]
    pssparser.extensions =
        example-rules = pss_rules

Once this package is pip-installed, both checkers are available with no
command-line flags at all -- that is the point of shipping a collection rather
than individual ``pssparser.checkers`` entry points.
"""
from __future__ import annotations

#: Minimum checker-API version this extension needs.
#:
#: Declared at module level so pssparser can refuse an incompatible build
#: *before* importing the rule modules -- the only point at which refusing has
#: no side effects.  Refusing produces one clear PSS032 message; loading
#: anyway would produce an AttributeError from inside a checker halfway
#: through somebody's run.
REQUIRES_API = 1

__version__ = "0.1.0"


def register(reg) -> None:
    """Contribute this package's checkers to *reg*.

    ``reg`` is a :class:`pssparser.checkers.ExtensionRegistry`.  Inbound it
    carries ``api_version`` (what the running pssparser provides) and ``name``
    (the entry-point key); outbound it takes ``add_checker()`` plus the
    ``version``/``description`` shown by ``pssparser --list-extensions``.
    """
    reg.version = __version__
    reg.description = "Example rule collection: component and package naming"

    # Imported inside register() rather than at module scope so that a syntax
    # error or bad dependency in one rule module is reported as a PSS030
    # against this extension, instead of breaking the import of the package
    # that declares the entry point.
    from .component_naming import ComponentNamingChecker
    from .package_naming import PackageNamingChecker

    reg.add_checker(ComponentNamingChecker)
    reg.add_checker(PackageNamingChecker)

    # Feature-probing is how one release of an extension supports several
    # releases of pssparser.  API_VERSION is bumped only for *incompatible*
    # changes, so a guard like this is the safe way to use anything newer than
    # REQUIRES_API promises.
    if reg.api_version >= 2:  # pragma: no cover - no API 2 exists yet
        pass
