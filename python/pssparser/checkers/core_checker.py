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
            summary="Syntax error",
            detail=(
                "The parser encountered a token it did not expect.  "
                "Messages include patterns such as:\n\n"
                "* ``expected ';' before '}'``\n"
                "* ``unexpected end of input; possible missing closing '}'``\n"
                "* ``unexpected '<token>' in this context``\n"
                "* ``expected identifier before '<token>'``\n\n"
                "Check that the surrounding PSS syntax is well-formed."
            ),
        ),
        MarkerDef(
            id="PSS002",
            severity="error",
            summary="Unknown symbol reference",
            detail=(
                "The linker could not resolve a named type, identifier, or "
                "method.  Messages include patterns such as:\n\n"
                "* ``unknown type 'Foo'``\n"
                "* ``unknown identifier 'bar'``\n"
                "* ``unknown method 'baz' on built-in type``\n\n"
                "Ensure the symbol is declared in one of the source files "
                "passed to pssparser, or that the correct package is imported."
                "  When a close match exists, a ``did you mean '...'?`` "
                "suggestion is appended."
            ),
        ),
        MarkerDef(
            id="PSS003",
            severity="error",
            summary="Duplicate symbol declaration",
            detail=(
                "A symbol with this name is already declared in the same "
                "scope.  Messages include patterns such as:\n\n"
                "* ``duplicate declaration of 'Foo'``\n"
                "* ``duplicate variable declaration bar``\n"
                "* ``duplicate parameter name 'p'``\n"
                "* ``duplicate symbol declaration``\n\n"
                "Rename one of the declarations to resolve the conflict."
            ),
        ),
        MarkerDef(
            id="PSS004",
            severity="error",
            summary="Symbol or ref-path resolution failure",
            detail=(
                "A symbol or reference path could not be resolved during "
                "linking.  Messages include patterns such as:\n\n"
                "* ``failed to resolve ref-path <path>``\n"
                "* ``failed to resolve symbol <name>``\n"
                "* ``root ref-path element <x> is not a composite scope``\n\n"
                "Check that all referenced symbols are declared and that "
                "composite-type fields are used correctly."
            ),
        ),
        MarkerDef(
            id="PSS005",
            severity="error",
            summary="Cannot extend unknown type or enum",
            detail=(
                "An ``extend`` declaration targets a type or enum that does "
                "not exist.  Messages include patterns such as:\n\n"
                "* ``cannot extend unknown type 'Foo'``\n"
                "* ``cannot extend unknown enum 'MyEnum'``\n\n"
                "Ensure the base type is declared before or alongside the "
                "extend block."
            ),
        ),
    ]

    def check(self, context) -> None:  # noqa: D102
        pass  # core checking is performed in C++
