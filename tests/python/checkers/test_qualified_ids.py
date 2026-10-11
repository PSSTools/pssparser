"""Organisation-qualified marker IDs (``ACME-NET001``; lint-core-plan C4.2,
pss-rules-format §5.1, Q-F1a).

The grammar gains one letters-only team segment, and namespace selection
becomes hierarchical: ``ACME`` covers ``ACME-*``, ``ACME-NET`` only itself.
Every reserved namespace stays reserved with any qualifier, so ``PSS`` and
``LINT`` can never select a site rule.
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.checkers import MarkerDef, taxonomy
from pssparser.checkers.selectors import RuleSet, SelectorError
from pssparser.checkers.testing import FixtureError, parse_expectations
from pssparser.cli.app import main
from pssparser.cli.sarif import strip_code
from pssparser.lint.rulefiles import conflicts


# ------------------------------------------------------------- grammar ---

@pytest.mark.parametrize("code,parts", [
    ("ACME001", ("ACME", 1)),
    ("ACME-NET001", ("ACME-NET", 1)),
    ("ACME-DMA104", ("ACME-DMA", 104)),
    ("AB-CD999", ("AB-CD", 999)),
    ("ACME-TEAM1001", None),        # a digit in a segment
    ("ACME-NET-RX001", None),       # one qualifier at most
    ("ACMEINC001", None),           # six letters
    ("ACME-N001", None),            # one-letter team
    ("ACME-NET01", None),
    ("acme-net001", None),
])
def test_split_code(code, parts):
    assert taxonomy.split_code(code) == parts


@pytest.mark.parametrize("ns,reserved", [
    ("PSS", True), ("LINT", True), ("PSSP", True), ("PSSX", True),
    ("PSS-ACME", True), ("LINT-NET", True), ("PSSP-X", True),
    ("ACME", False), ("ACME-NET", False), ("PSSAC", False), ("LINTX", False),
])
def test_reserved_with_any_qualifier(ns, reserved):
    assert taxonomy.is_reserved(ns) is reserved


# ----------------------------------------------------------- selectors ---

def _md(id, name=""):
    return MarkerDef(id=id, severity="", summary=id, tier="style", name=name,
                     family="naming", detail="Severity: tier default.")


RULES = [
    MarkerDef(id="PSS001", severity="error", summary="syntax"),
    MarkerDef(id="PSSP005", severity="error", summary="tool"),
    _md("LINT301", "lint-rule"),
    _md("ACME001", "org-rule"),
    _md("ACME100", "org-band-rule"),
    _md("ACME-NET001", "net-rule"),
    _md("ACME-NET100", "net-band-rule"),
    _md("ACME-DMA001", "dma-rule"),
    _md("ACMEX001", "other-org-rule"),
]


def _selects(text):
    rs = RuleSet(RULES, minimal=())
    sel = rs.parse(text)
    return sorted(md.id for md in rs.mdefs if sel.matches(md))


def test_an_organisation_selects_its_teams():
    assert _selects("ACME") == ["ACME-DMA001", "ACME-NET001", "ACME-NET100",
                                "ACME001", "ACME100"]


def test_a_team_selects_only_itself():
    assert _selects("ACME-NET") == ["ACME-NET001", "ACME-NET100"]


def test_a_band_of_a_team():
    assert _selects("ACME-NET1") == ["ACME-NET100"]
    assert _selects("ACME1") == ["ACME100"]


def test_reserved_selectors_never_select_a_site_rule():
    assert _selects("PSS") == ["PSS001"]
    assert _selects("LINT") == ["LINT301"]


def test_selectors_parse_by_kind():
    rs = RuleSet(RULES, minimal=())
    assert rs.parse("ACME-NET").kind == "namespace"
    assert rs.parse("ACME-NET1").kind == "prefix"
    assert rs.parse("ACME-NET001").kind == "id"
    with pytest.raises(SelectorError):
        rs.parse("ACME-TEAM1")
    with pytest.raises(SelectorError):
        rs.parse("ACME-OPS")            # well-formed, but nothing declares it


def test_a_team_is_more_specific_than_its_organisation():
    rs = RuleSet(RULES, minimal=())
    spec = [rs.parse(t).specificity for t in ("ACME", "ACME-NET", "ACME-NET1",
                                               "ACME-NET001")]
    assert spec == sorted(spec) and len(set(spec)) == 4


def test_the_namespace_list_offers_teams():
    assert {"ACME", "ACME-NET", "ACME-DMA"} <= set(RuleSet(RULES, minimal=()).candidates())


# ------------------------------------------------- harness, SARIF text ---

def test_fixture_expectations_accept_qualified_ids():
    exp = parse_expectations("x;  // expect: ACME-NET001 @ 1:1, ACME001 @ 1:3\n")
    assert exp.findings == [("ACME-NET001", 1, 1), ("ACME001", 1, 3)]
    with pytest.raises(FixtureError):
        parse_expectations("x;  // expect: ACME-TEAM1001 @ 1:1\n")


def test_sarif_strips_a_qualified_code():
    assert strip_code("[ACME-NET001] too wide") == "too wide"


# ------------------------------------------- rule files vs. extensions ---

def _rule(id, name, aliases=(), line=3):
    return {"id": id, "name": name, "aliases": list(aliases), "file": "site.yaml",
            "line": line, "col": 7}


def test_a_rule_file_cannot_take_an_extension_id_or_name():
    mdefs = [_md("ACME001", "org-rule"),
             MarkerDef(id="ACME-NET001", severity="warning", summary="s",
                       aliases=("ACME-NET900",))]
    got = conflicts(
        [_rule("ACME001", "fresh"), _rule("ACME002", "org-rule", line=9),
         _rule("ACME003", "fine", aliases=["ACME-NET900"], line=15),
         _rule("ACME-DMA001", "dma")],
        mdefs, owner_of=lambda mid: "checker 'acme' from extension 'acme-rules'")
    assert [(d["code"], d["rule"], d["line"]) for d in got] == [
        ("PSSP217", "ACME001", 3), ("PSSP217", "ACME002", 9), ("PSSP217", "ACME003", 15)]
    assert got[0]["message"] == ("rule ID 'ACME001' is already the ID of marker ACME001, "
                                 "declared by checker 'acme' from extension 'acme-rules'")
    assert "the name of marker ACME001" in got[1]["message"]
    assert "an alias of marker ACME-NET001" in got[2]["message"]


def test_team_namespaces_do_not_clash():
    assert conflicts([_rule("ACME-DMA001", "dma")], [_md("ACME-NET001", "net")]) == []


# ----------------------------------------------------------- end to end ---

CHECKER = (
    "from pssparser.checkers import CheckerBase, MarkerDef\n"
    "class TeamChecker(CheckerBase):\n"
    "    name = 'team-checker'\n"
    "    marker_defs = [\n"
    "        MarkerDef(id='ACME001', severity='', summary='org', name='org-rule',\n"
    "                  tier='suspicious', family='naming', detail='Severity: tier default.'),\n"
    "        MarkerDef(id='ACME-NET001', severity='', summary='net', name='net-rule',\n"
    "                  tier='suspicious', family='naming', detail='Severity: tier default.'),\n"
    "    ]\n"
    "    def check(self, context):\n"
    "        for f in context.files:\n"
    "            for code in ('ACME001', 'ACME-NET001'):\n"
    "                context.add_marker(code=code, file=f, line=1, col=1,\n"
    "                                   message='found')\n"
)


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


@pytest.fixture
def ws(tmp_path, monkeypatch):
    """``m.pss`` and a checker reporting ACME001 and ACME-NET001 on line 1."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "teamchk.py").write_text(CHECKER)
    monkeypatch.syspath_prepend(str(tmp_path))

    def run(*flags, src="component pss_top { }\n", config=None):
        (tmp_path / "m.pss").write_text(src)
        cfg = ["--no-config"]
        if config is not None:
            (tmp_path / ".pssparser.toml").write_text(config)
            cfg = []
        rc, out, err = _run([*cfg, "--load-checker", "teamchk:TeamChecker",
                             "--lint-profile", "recommended", "--format", "json",
                             *flags, "m.pss"])
        doc = json.loads(out)
        return rc, {d["code"]: d["severity"] for d in doc["diagnostics"]}, doc
    return run


def test_end_to_end_both_are_reported(ws):
    _, got, _ = ws()
    assert got == {"ACME001": "warning", "ACME-NET001": "warning"}


@pytest.mark.parametrize("sel,errors", [
    ("ACME", {"ACME001", "ACME-NET001"}),
    ("ACME-NET", {"ACME-NET001"}),
    ("ACME-NET001", {"ACME-NET001"}),
])
def test_werror_selects_hierarchically(ws, sel, errors):
    _, got, _ = ws(f"-Werror={sel}")
    assert {c for c, s in got.items() if s == "error"} == errors


def test_ignore_a_team(ws):
    _, got, _ = ws(config='[lint]\nignore = ["ACME-NET"]\n')
    assert set(got) == {"ACME001"}


def test_a_team_selection_beats_its_organisation(ws):
    _, got, _ = ws(config='[lint]\nignore = ["ACME"]\nselect = ["ACME-NET"]\n')
    assert set(got) == {"ACME-NET001"}


def test_waive_a_qualified_id(ws):
    src = "component pss_top { }  // pssparser waive ACME-NET001: vendored\n"
    _, got, doc = ws(src=src)
    assert set(got) == {"ACME001"}


def test_waive_a_whole_organisation(ws):
    src = "component pss_top { }  // pssparser waive ACME: vendored\n"
    _, got, _ = ws(src=src)
    assert got == {}


def test_baseline_records_qualified_ids(ws, tmp_path):
    rc, _, _ = ws("--write-baseline", "base.json")
    assert rc == 0
    recorded = json.loads((tmp_path / "base.json").read_text())
    assert "ACME-NET001" in json.dumps(recorded)
    _, got, doc = ws("--baseline", "base.json")
    assert got == {}
    assert sorted(d["code"] for d in doc["baselined"]) == ["ACME-NET001", "ACME001"]
