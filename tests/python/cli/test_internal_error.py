"""PSS000: an internal error is reported, never suppressed, and exits 3.

The C++ side reports its own failures as PSS000 markers (the catch-all in
AstLinker::link and AstBuilderInt::build); the Python side turns anything
that escapes even that into the same marker (`except +` in decl.pxd, then
Parser.link/parse). Every known internal error has been fixed, so these tests
inject one at the Parser boundary. See symbol-resolution-plan.md INV-1.
"""
import io
import json

import pytest

from pssparser.checkers.extension import NO_FILE
from pssparser.cli.commands import EXIT_INTERNAL_ERROR, cmd_parse
from pssparser.parser import INTERNAL_ERROR_CODE, Parser, ParseException, \
    _internal_error_marker


@pytest.fixture
def failing_link(monkeypatch):
    """Make Parser.link fail the way an escaped C++ exception does."""
    def link(self):
        m = _internal_error_marker("while linking", RuntimeError("boom"))
        self._markers.append(m)
        raise ParseException(m["message"], self._markers)
    monkeypatch.setattr(Parser, "link", link)


def _src(tmp_path):
    p = tmp_path / "t.pss"
    p.write_text("component pss_top { }\n")
    return str(p)


def test_internal_error_exits_3(tmp_path, failing_link):
    out = io.StringIO()
    rc = cmd_parse([_src(tmp_path)], use_json=True, stdout=out,
                   stderr=io.StringIO())
    assert rc == EXIT_INTERNAL_ERROR == 3
    diags = json.loads(out.getvalue())["diagnostics"]
    assert [d["code"] for d in diags] == [INTERNAL_ERROR_CODE]
    assert diags[0]["file"] == NO_FILE
    assert diags[0]["message"].startswith("internal error while linking: boom")


def test_internal_error_is_not_configurable_away(tmp_path, failing_link):
    class Cfg:
        severity = {INTERNAL_ERROR_CODE: "off"}
        checker_options = {}

    out = io.StringIO()
    rc = cmd_parse([_src(tmp_path)], use_json=True, stdout=out,
                   stderr=io.StringIO(), config=Cfg())
    assert rc == 3
    assert [d["code"] for d in json.loads(out.getvalue())["diagnostics"]] \
        == [INTERNAL_ERROR_CODE]


def test_internal_error_renders_as_a_tool_diagnostic(tmp_path, failing_link):
    err = io.StringIO()
    rc = cmd_parse([_src(tmp_path)], stderr=err, color=False)
    assert rc == 3
    assert err.getvalue().startswith("pssparser: error: internal error while linking")
