"""PRC002 — package names should be snake_case."""
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pssparser.ast as pss_ast
from pssparser.checkers import CheckerBase, MarkerDef

if TYPE_CHECKING:
    from pssparser.checkers import CheckContext

_SNAKE = re.compile(r"^[a-z][a-z0-9_]*$")


class PackageNamingChecker(CheckerBase):
    """Warn when a ``package`` name segment is not lower_snake_case.

    Bad::

        package MyPkg { ... }           // PRC002

    Good::

        package my_pkg { ... }

    ``PackageScope`` models the name as a *list* of identifier segments
    (``numId()`` / ``getId(i)``), so this walks the list rather than assuming
    a single name.  In practice the grammar accepts only one segment today --
    ``package a.b { }`` is a syntax error -- but reading the node the way the
    AST presents it costs nothing and does not have to be revisited if that
    changes.
    """

    name = "package-naming"
    description = "Warn when package names are not lower_snake_case"

    marker_defs = [
        MarkerDef(
            id="PRC002",
            severity="warning",
            summary="Package name is not lower_snake_case",
            detail=(
                "Packages are namespaces rather than types, and PSS "
                "convention spells them in lowercase with underscores, "
                "reserving PascalCase for named types.  Rename the package "
                "segment, e.g. ``MyPkg`` to ``my_pkg``.\n\n"
                "Each segment of a dotted path is checked separately; the "
                "diagnostic points at the offending segment."
            ),
        ),
    ]

    runs_without_link = True

    def check(self, context: "CheckContext") -> None:
        for global_scope in context.global_scopes:
            filename = context.file_map.get(global_scope.getFileid(), "")
            self._walk(context, global_scope, filename)

    def _walk(self, context: "CheckContext", scope, filename: str) -> None:
        for child in scope.children():
            if isinstance(child, pss_ast.PackageScope):
                self._check(context, child, filename)
            if isinstance(child, pss_ast.Scope):
                self._walk(context, child, filename)

    @staticmethod
    def _check(context: "CheckContext", node, filename: str) -> None:
        for i in range(node.numId()):
            segment = node.getId(i)
            name = segment.getId()
            if not name or _SNAKE.match(name):
                continue
            loc = segment.getLocation()
            context.add_marker(
                code="PRC002",
                file=filename,
                line=loc.lineno,
                col=loc.linepos,
                message=f"Package name '{name}' should be lower_snake_case",
                extent=len(name),
            )
