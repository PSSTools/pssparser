"""Built-in CoreChecker: metadata for parser and linker diagnostics."""
from __future__ import annotations

from .base import CheckerBase
from .markerdef import MarkerDef


class CoreChecker(CheckerBase):
    """Metadata-only checker that documents built-in parse/link markers.

    The actual checking is performed by C++ code; this class exists purely
    to make the built-in marker catalogue discoverable via ``--list-markers``
    and ``--describe``.
    """

    name = "core"
    description = "Built-in parser and linker diagnostics"

    #: Marks this as a built-in checker that cannot be disabled via
    #: ``--no-checker`` and is never passed to the checker invocation loop.
    is_builtin = True

    marker_defs = [
        MarkerDef(
            id="PSS001",
            severity="error",
            summary="Syntax error: unexpected token",
            detail=(
                "The parser encountered a token it did not expect at this "
                "position.  Check that the surrounding PSS syntax is "
                "well-formed."
            ),
        ),
        MarkerDef(
            id="PSS002",
            severity="error",
            summary="Undefined symbol reference",
            detail=(
                "The linker could not resolve a reference to a named type "
                "or identifier.  Ensure the symbol is declared in one of "
                "the source files passed to pssparser, or that the correct "
                "package is imported."
            ),
        ),
        MarkerDef(
            id="PSS003",
            severity="error",
            summary="Duplicate symbol declaration",
            detail=(
                "A symbol with this name is already declared in the same "
                "scope.  Rename one of the declarations to resolve the "
                "conflict."
            ),
        ),
        MarkerDef(
            id="PSS004",
            severity="error",
            summary="Type resolution error",
            detail=(
                "The type referenced in this expression or declaration could "
                "not be resolved.  Ensure the type is declared or imported "
                "before use."
            ),
        ),
        MarkerDef(
            id="PSS005",
            severity="error",
            summary="Import resolution error",
            detail=(
                "An imported package or symbol could not be found.  Check "
                "that the package name is correct and that the providing "
                "file is included in the pssparser invocation."
            ),
        ),
        MarkerDef(
            id="PSS006",
            severity="warning",
            summary="Ambiguous symbol reference",
            detail=(
                "More than one symbol matches this reference.  Use a "
                "fully-qualified name to disambiguate."
            ),
        ),
    ]

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
