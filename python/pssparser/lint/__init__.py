"""pssparser's bundled lint rules.

``catalog`` holds every ``LINT`` rule definition as data.  Rules that the lint
runner executes live in ``rules/`` and register through :func:`register`,
exactly as a third-party extension's checkers do -- which keeps the extension
API honest: if pssparser's own rules need something, every extension gets it.
The core-emitted rules in ``catalog.CORE_EMITTED`` are raised by the C++
linker and need no registration.

The manager loads this extension directly (it is part of pssparser, so it
needs no entry point), as extension ``lint``, and it is the only extension
allowed to use the reserved ``LINT`` namespace.  ``PSSPARSER_NO_LINT=1`` skips
it; ``--no-extensions`` does not, because it is not a third-party extension.
"""

#: Environment escape hatch: skip the bundled lint runner rules.  The
#: core-emitted LINT warnings are unaffected (they come from the linker and
#: are governed by the lint profile).
NO_LINT_ENV = "PSSPARSER_NO_LINT"


def register(reg) -> None:
    """Register the bundled lint checkers."""
    from pssparser.__version__ import get_version

    from .rules import CHECKERS

    reg.version = get_version()
    reg.description = "pssparser's bundled lint rules"
    for cls in CHECKERS:
        reg.add_checker(cls)
