"""PRC001 — component type names should be PascalCase."""
from __future__ import annotations

from typing import TYPE_CHECKING

import pssparser.ast as pss_ast
from pssparser.checkers import CheckerBase, MarkerDef

if TYPE_CHECKING:
    from pssparser.checkers import CheckContext

#: The conventional entry-point component; exempt by name, as every PSS model
#: has one and renaming it would break the convention it belongs to.
_EXEMPT = {"pss_top"}


class ComponentNamingChecker(CheckerBase):
    """Warn when a ``component`` type name does not start with an uppercase letter.

    Bad::

        component widget_c { ... }      // PRC001

    Good::

        component Widget { ... }
        component pss_top { ... }       // exempt: the conventional entry point
    """

    name = "component-naming"
    description = "Warn when component type names are not PascalCase"

    marker_defs = [
        MarkerDef(
            id="PRC001",
            severity="warning",
            summary="Component type name does not start with an uppercase letter",
            detail=(
                "PSS convention uses PascalCase for named types, components "
                "included.  Rename the component so that its first letter is "
                "uppercase, e.g. ``widget_c`` to ``Widget``.\n\n"
                "``pss_top`` is exempt: it is the conventional name for the "
                "root component and is expected to be spelled exactly that "
                "way."
            ),
        ),
    ]

    #: Name checking needs only the parse tree, so this checker still runs
    #: under ``--syntax-only``.
    runs_without_link = True

    def check(self, context: "CheckContext") -> None:
        for global_scope in context.global_scopes:
            filename = context.file_map.get(global_scope.getFileid(), "")
            self._walk(context, global_scope, filename)

    def _walk(self, context: "CheckContext", scope, filename: str) -> None:
        for child in scope.children():
            if isinstance(child, pss_ast.Component):
                self._check(context, child, filename)
            # Components nest inside packages and inside other components.
            if isinstance(child, pss_ast.Scope):
                self._walk(context, child, filename)

    @staticmethod
    def _check(context: "CheckContext", node, filename: str) -> None:
        name_expr = node.getName()
        name = name_expr.getId()
        if not name or name in _EXEMPT or name[0].isupper():
            return
        loc = name_expr.getLocation()
        context.add_marker(
            code="PRC001",
            file=filename,
            line=loc.lineno,
            col=loc.linepos,
            message=f"Component '{name}' should start with an uppercase letter",
            extent=len(name),
        )
