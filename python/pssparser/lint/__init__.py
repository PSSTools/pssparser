"""pssparser's bundled lint rules.

``catalog`` holds the core-emitted ``LINT`` rule definitions
(``catalog.CORE_EMITTED``), which the C++ linker raises.  Every other lint
rule is declarative: a ``pss-rules`` file run by the core engine, built-in
or site (lint-core-plan C5.4).  The engine's rules are registered as the
``pss-rules`` checker (:mod:`pssparser.lint.ruleview`), which runs them in
one walk.

The manager still loads this package as the bundled extension ``lint`` (it
is part of pssparser, so it needs no entry point), the only extension
allowed to use the reserved ``LINT`` namespace; it registers no Python
checker.  ``PSSPARSER_NO_LINT=1`` skips it and the declarative rules' run;
``--no-extensions`` does neither, because neither is a third-party
extension.
"""

#: Environment escape hatch: run no lint rules -- neither the bundled
#: extension nor the declarative rules.  The core-emitted LINT warnings are
#: unaffected (they come from the linker and are governed by the lint
#: profile).
NO_LINT_ENV = "PSSPARSER_NO_LINT"


def register(reg) -> None:
    """Register the bundled lint extension.  It has no Python checkers: the
    lint rules are declarative and run in the core."""
    from pssparser.__version__ import get_version

    reg.version = get_version()
    reg.description = "pssparser's bundled lint rules"
