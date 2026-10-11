"""The AST reference's "Lint rule" column gives the types the rule checker gives.

docs/_ext/pss_rule_projection.py derives each field's CEL type from
ast/*.yaml, so the documentation builds without a compiled pssparser. This
compares it, for every field of every class, with what the built checker
reports for ``type(d) == Class`` ... ``d.field``. (It replaces the staleness
test of the generated docs/lint-nodes.rst, removed with
scripts/gen_lint_nodes.py; see docs/design/astbuilder-sphinx-plan.md S4.3.)
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pytest

pytest.importorskip("astbuilder.projection")

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "docs" / "_ext"))

from astbuilder.ast import Ast  # noqa: E402
from astbuilder.linker import Linker  # noqa: E402
from astbuilder.parser import Parser  # noqa: E402
from pss_rule_projection import RuleProjection  # noqa: E402


def _checker_types():
    from pssparser.core import Factory
    from pssparser.parser import Parser as PssParser
    hooks = Factory.inst()._lintTestHooks()
    schema = hooks.reflect_schema()
    p = PssParser()
    p.parses([("probe.pss", "component pss_top { }\n")])
    root = p.link()
    (unit,) = p.user_units()
    out = {}
    for c in schema["classes"][1:]:
        for f in c["fields"]:
            expr = "descendants(node).filter(d, type(d) == %s).map(d, d.%s)" % (
                c["name"], f["name"])
            r = hooks.cel_check_node({"expr": expr}, unit, model=root)
            t = None
            if not r["errors"]:
                t = r["types"]["expr"]
                assert t.startswith("list(") and t.endswith(")"), t
                t = t[len("list("):-1]
            out[(c["name"], f["name"])] = t
    return out


def test_rule_projection_matches_checker():
    ast = Ast()
    for f in sorted(glob.glob(str(ROOT / "ast" / "*.yaml"))):
        with open(f) as fp:
            Parser(ast).parse(fp)
    Linker().link(ast)
    proj = RuleProjection(ast)
    want = _checker_types()
    got = {(c.name, d.name): proj.field_type(c, d) for c in ast.classes for d in c.data}
    assert set(got) == set(want)
    diff = {k: (got[k], want[k]) for k in got if got[k] != want[k]}
    assert diff == {}, diff
