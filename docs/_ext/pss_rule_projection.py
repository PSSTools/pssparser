"""The "Lint rule" column of the AST reference: how a pss-rules expression
reads each field.

A rule reads a field by name through the lint engine's reflection tables
(``node.lhs``), so this extends pyastbuilder's reflection projection with the
types the rule checker gives: a class name, ``list(T)``, ``int`` for an enum or
flags field, ``bool``, ``string``, ``double``. A map, or a list of lists, is not
readable by a rule.

Docs-only: the wheel does not depend on pyastbuilder.
``tests/python/lintcore/test_rule_projection.py`` checks every field's type
against the built checker, so this table cannot drift from what a rule sees.
"""
from astbuilder.ast_enum import AstEnum
from astbuilder.ast_flags import AstFlags
from astbuilder.projection import Access, ReflectProjection
from astbuilder.type_list import TypeList
from astbuilder.type_map import TypeMap
from astbuilder.type_pointer import TypePointer
from astbuilder.type_userdef import TypeUserDef


class RuleProjection(ReflectProjection):
    name = "rule"
    label = "Lint rule"

    def hidden(self, cls, field):
        t = field.t
        if isinstance(t, TypeMap):
            return "maps are not readable by a rule"
        if isinstance(t, TypeList) and isinstance(t.t, TypeList):
            return "lists of lists are not readable by a rule"
        return None

    def _target(self, t):
        if isinstance(t, TypePointer):
            t = t.t
        return t.target if isinstance(t, TypeUserDef) else None

    def cel_type(self, t):
        """The CEL type the rule checker gives a value of YAML type `t`."""
        if isinstance(t, TypeList):
            return "list(%s)" % self.cel_type(t.t)
        tgt = self._target(t)
        if isinstance(tgt, (AstEnum, AstFlags)):
            return "int"
        if tgt is not None:
            return tgt.name
        return self.type_name(t)      # bool, string, int, double

    def field_type(self, cls, field):
        return None if self.hidden(cls, field) else self.cel_type(field.t)

    def _accessors(self, cls, field):
        t = self.cel_type(field.t)
        tgt = self._target(field.t)
        if isinstance(tgt, AstFlags):
            t = "int (%s flags; test with has_flag)" % tgt.name
        elif isinstance(tgt, AstEnum):
            t = "int (%s)" % tgt.name
        return [Access("view", "node.%s" % field.name, t)]
