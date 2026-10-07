"""``off`` means the rule does not run (plan F1.7, lint-framework L1)."""
from __future__ import annotations

import io
import textwrap

import pytest

from pssparser.checkers import CheckerManager
from pssparser.cli.commands import cmd_parse

SPY = textwrap.dedent('''
    from pssparser.checkers import CheckerBase, MarkerDef

    CALLS = []

    class OneRule(CheckerBase):
        name = "one-rule"
        marker_defs = [MarkerDef(id="SPY001", severity="warning", summary="s")]

        def check(self, context):
            CALLS.append(self.name)
            for f in context.files:
                context.add_marker(code="SPY001", file=f, line=1, col=1,
                                   message="spy one")

    class TwoRules(CheckerBase):
        name = "two-rules"
        marker_defs = [
            MarkerDef(id="SPY002", severity="warning", summary="s"),
            MarkerDef(id="SPY003", severity="warning", summary="s"),
        ]

        def check(self, context):
            CALLS.append(self.name)
            for f in context.files:
                # deliberately ignores is_enabled(): add_marker is the backstop
                context.add_marker(code="SPY002", file=f, line=1, col=1,
                                   message="spy two")
                if context.is_enabled("SPY003"):
                    context.add_marker(code="SPY003", file=f, line=1, col=1,
                                       message="spy three")
''')


@pytest.fixture
def spy(tmp_path, monkeypatch):
    (tmp_path / "spy_rules.py").write_text(SPY)
    monkeypatch.syspath_prepend(str(tmp_path))
    import importlib
    import spy_rules
    importlib.reload(spy_rules)
    manager = CheckerManager()
    manager.discover()
    manager.load("spy_rules:OneRule")
    manager.load("spy_rules:TwoRules")
    src = tmp_path / "m.pss"
    src.write_text("component pss_top { }\n")
    return spy_rules, manager, str(src)


class _Cfg:
    def __init__(self, severity):
        self.severity = severity
        self.checker_options = {}


def _run(manager, src, severity):
    out = io.StringIO()
    cmd_parse([src], use_json=True, stdout=out, stderr=io.StringIO(),
              manager=manager, config=_Cfg(severity))
    import json
    return [d["code"] for d in json.loads(out.getvalue())["diagnostics"]]


def test_a_checker_whose_ids_are_all_off_is_not_called(spy):
    mod, manager, src = spy
    codes = _run(manager, src, {"SPY001": "off"})
    assert "one-rule" not in mod.CALLS
    assert "SPY001" not in codes


def test_a_partly_off_checker_runs_and_the_off_id_never_reaches_output(spy):
    mod, manager, src = spy
    codes = _run(manager, src, {"SPY002": "off"})
    assert "two-rules" in mod.CALLS
    assert "SPY002" not in codes
    assert "SPY003" in codes


def test_is_enabled_reports_the_off_id(spy):
    mod, manager, src = spy
    codes = _run(manager, src, {"SPY003": "off"})
    assert codes.count("SPY002") == 1
    assert "SPY003" not in codes


def test_internal_error_cannot_be_turned_off():
    from pssparser.cli.diagnostics import Diagnostic, DiagnosticCollection

    coll = DiagnosticCollection()
    coll.add(Diagnostic(file="f", line=1, col=1, severity="error",
                        message="internal error", code="PSS000"))
    coll.apply_severity_map({"PSS000": "off"})
    assert [d.code for d in coll.diagnostics] == ["PSS000"]
