"""PSS naming-convention checker — pssparser plug-in example."""
from __future__ import annotations

import re
from fnmatch import fnmatchcase
from typing import TYPE_CHECKING

import pssparser.ast as pss_ast
from pssparser.checkers import CheckerBase, MarkerDef

if TYPE_CHECKING:
    from pssparser.checkers import CheckContext


class NamingConventionChecker(CheckerBase):
    """Warn when action or struct type names do not start with an uppercase letter.

    PSS coding convention (and industry practice) uses PascalCase for named
    types: actions, structs, and user-defined types should all start with an
    uppercase letter.  The built-in entry-point ``pss_top`` is the conventional
    component name and is intentionally excluded from this rule.

    Markers
    -------
    PSC001
        An action type name does not start with an uppercase letter.
    PSC002
        A struct type name does not start with an uppercase letter.

    Example
    -------
    Bad::

        action write_data { ... }   // PSC001: should be WriteData
        struct packet { ... }       // PSC002: should be Packet

    Good::

        action WriteData { ... }
        struct Packet { ... }
    """

    name = "naming-convention"
    description = "Warn when action or struct type names do not start with uppercase"

    marker_defs = [
        MarkerDef(
            id="PSC001",
            severity="warning",
            summary="Action type name does not follow the configured style",
            detail=(
                "PSS convention uses PascalCase for action type names.  "
                "Rename the action so that its first letter is uppercase, "
                "e.g. rename ``write_data`` to ``WriteData``.\n\n"
                "The required style is the ``style`` option; set it to "
                "``snake_case`` under ``[checker.naming-convention]`` to "
                "invert the rule, and list glob patterns under ``exempt`` "
                "to skip names you are not ready to rename."
            ),
        ),
        MarkerDef(
            id="PSC002",
            severity="warning",
            summary="Struct type name does not follow the configured style",
            detail=(
                "PSS convention uses PascalCase for struct type names.  "
                "Rename the struct so that its first letter is uppercase, "
                "e.g. rename ``my_packet`` to ``MyPacket``.\n\n"
                "See PSC001 for the ``style`` and ``exempt`` options, which "
                "apply to both markers."
            ),
        ),
    ]

    #: Name-checking only needs the parse tree; no linked AST required.
    runs_without_link = True

    #: A house style is exactly the kind of thing that differs per project,
    #: which is why it is configuration rather than a second checker.
    options_schema = {
        "style": {
            "type": "string",
            "default": "PascalCase",
            "choices": ["PascalCase", "snake_case"],
            "help": "Naming style required for action and struct types.",
        },
        "exempt": {
            "type": "string-list",
            "default": [],
            "help": (
                "Glob patterns for type names to skip, e.g. 'legacy_*'. "
                "Useful while migrating an existing codebase."
            ),
        },
    }

    #: Filled in by ``configure()``; the class-level value is what applies
    #: when this checker is constructed directly, as the tests do.
    options = {"style": "PascalCase", "exempt": []}

    def check(self, context: "CheckContext") -> None:
        for global_scope in context.global_scopes:
            filename = context.file_map.get(global_scope.getFileid(), "")
            self._walk(context, global_scope, filename)

    # ------------------------------------------------------------------
    # Style rules
    # ------------------------------------------------------------------

    _SNAKE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")

    def _conforms(self, name: str) -> bool:
        if self.options.get("style") == "snake_case":
            return bool(self._SNAKE_RE.match(name))
        return name[0].isupper()

    def _expectation(self) -> str:
        if self.options.get("style") == "snake_case":
            return "should be lower_snake_case"
        return "should start with an uppercase letter"

    def _exempt(self, name: str) -> bool:
        return any(
            fnmatchcase(name, pat) for pat in self.options.get("exempt", [])
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _walk(self, context: "CheckContext", scope, filename: str) -> None:
        """Recursively walk *scope* and emit markers for naming violations."""
        for child in scope.children():
            if isinstance(child, pss_ast.Action):
                self._check_name(context, child, filename, "PSC001", "Action")
            elif isinstance(child, pss_ast.Struct):
                self._check_name(context, child, filename, "PSC002", "Struct")

            # Recurse into any child scope (components, packages, …)
            if isinstance(child, pss_ast.Scope):
                self._walk(context, child, filename)

    def _check_name(
        self,
        context: "CheckContext",
        node,
        filename: str,
        code: str,
        kind: str,
    ) -> None:
        name_expr = node.getName()
        name = name_expr.getId()
        if not name or self._exempt(name) or self._conforms(name):
            return
        loc = name_expr.getLocation()
        context.add_marker(
            code=code,
            file=filename,
            line=loc.lineno,
            col=loc.linepos,
            message=f"{kind} '{name}' {self._expectation()}",
        )
