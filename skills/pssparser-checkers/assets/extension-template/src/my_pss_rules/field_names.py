"""MPR001: field names shorter than a configurable minimum."""
from __future__ import annotations

import pssparser.ast as pss_ast
from pssparser.checkers import CheckContext, CheckerBase, MarkerDef


class FieldNameLengthChecker(CheckerBase):
    """Warn on field names shorter than ``min_length`` characters.

    Bad (with the default ``min_length = 2``)::

        struct packet_s { rand bit[8] a; }      // MPR001

    Good::

        struct packet_s { rand bit[8] addr; }
    """

    name = "field-name-length"
    description = "Warn when a field name is shorter than min_length"

    marker_defs = [
        MarkerDef(
            id="MPR001",
            severity="warning",
            summary="Field name is shorter than the configured minimum",
            detail=(
                "Very short field names make constraints and coverage hard "
                "to read.  Rename the field, or lower ``min_length`` under "
                "``[checker.field-name-length]``.  Names listed in "
                "``allow`` are exempt."
            ),
        ),
    ]

    options_schema = {
        "min_length": {
            "type": "int",
            "default": 2,
            "help": "Shortest field name accepted.",
        },
        "allow": {
            "type": "string-list",
            "default": ["i", "j", "k"],
            "help": "Names exempt from the rule.",
        },
    }

    #: The defaults, for when the class is used without configure().
    options = {"min_length": 2, "allow": ["i", "j", "k"]}

    def check(self, context: CheckContext) -> None:
        # global_scopes holds the user's files only, not the core library.
        for unit in context.global_scopes:
            path = context.file_map.get(unit.getFileid(), "")
            unit.accept(_FieldVisitor(self, context, path))

    def check_field(self, context: CheckContext, path: str, field) -> None:
        name_expr = field.getName()
        name = name_expr.getId()
        if name in self.options["allow"]:
            return
        if len(name) >= self.options["min_length"]:
            return
        loc = name_expr.getLocation()
        context.add_marker(
            code="MPR001",
            file=path,
            line=loc.lineno,
            col=loc.linepos,
            extent=len(name),
            message=(f"field '{name}' is shorter than "
                     f"{self.options['min_length']} characters"),
        )


class _FieldVisitor(pss_ast.VisitorBase):
    def __init__(self, checker, context, path):
        super().__init__()
        self._checker = checker
        self._context = context
        self._path = path

    def visitField(self, field):
        self._checker.check_field(self._context, self._path, field)
        super().visitField(field)
