"""The core warnings that moved from PSS to LINT (nine; LINT101 has since
become the error PSS130, ruling R22), and the four tool
warnings and three tool errors that moved to PSSP (plan F1.3, F1.3a, F1.3b).

Each moved warning is still raised by the C++ linker with the same message and
location; only its ID changed, and it is now governed by lint selection.  The
old IDs keep working wherever an ID is typed, with one PSSP004 note.
"""
from __future__ import annotations

import io
import json
import sys

import pytest

from pssparser.cli.app import main

#: (new ID, old ID, source, (line, col)) -- one probe per moved warning.
PROBES = [
    ("LINT301", "PSS120",
     "component pss_top {\n"
     "  function void bump();\n"
     "  export target function bump;\n"
     "}\n", (3, 26)),
    ("LINT401", "PSS044",
     "enum mode_e { A, B }\n"
     "component pss_top {\n"
     "  action a {\n"
     "    rand mode_e m;\n"
     "    rand int A;\n"
     "    constraint { m == A; }\n"
     "  }\n"
     "}\n", (6, 23)),
    ("LINT402", "PSS053",
     "package lib { struct s {} }\n"
     "package p {\n"
     "  struct t {}\n"
     "  import lib::*;\n"
     "}\n", (4, 3)),
    ("LINT403", "PSS101",
     "component pss_top {\n"
     "  @desc_s\n"
     "  action a { }\n"
     "}\n", (2, 3)),
    ("LINT404", "PSS119",
     "component pss_top {\n"
     "  struct s { bit[W] f; }\n"
     "  static const int W = 8;\n"
     "}\n", (2, 18)),
    ("LINT501", "PSS016",
     "import addr_reg_pkg::*;\n"
     "struct r96_s : packed_s<> { bit[96] v; }\n"
     "component regs_c : reg_group_c {\n"
     "  reg_c<r96_s> r;\n"
     "}\n", (4, 3)),
    ("LINT601", "PSS104",
     "compile if (1) struct q {}\n", (1, 16)),
    ("LINT602", "PSS117",
     "component pss_top {\n"
     "  action a {\n"
     "    rand int x;\n"
     "    dynamic constraint dc { x > 0; }\n"
     "    activity { dc; }\n"
     "  }\n"
     "}\n", (5, 16)),
]

_IDS = [p[0] for p in PROBES]


def _run(argv, cwd=None, monkeypatch=None):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def _json(argv):
    rc, out, err = _run(["--json", "--no-config", *argv])
    return rc, json.loads(out), err


@pytest.fixture
def probe(tmp_path):
    def write(src, name="m.pss"):
        path = tmp_path / name
        path.write_text(src)
        return str(path)
    return write


@pytest.mark.parametrize("new,old,src,loc", PROBES, ids=_IDS)
def test_reported_under_the_new_id(probe, new, old, src, loc):
    rc, doc, _ = _json([probe(src)])
    found = [(d["code"], d["line"], d["col"]) for d in doc["diagnostics"]]
    assert found == [(new, *loc)]
    assert rc == 0


@pytest.mark.parametrize("new,old,src,loc", PROBES, ids=_IDS)
def test_no_lint_hides_it(probe, new, old, src, loc):
    _, doc, _ = _json(["--no-lint", probe(src)])
    assert doc["diagnostics"] == []


@pytest.mark.parametrize("profile", ["minimal", "recommended", "strict", "all"])
def test_every_profile_shows_all_nine(probe, profile):
    for new, _, src, _ in PROBES:
        _, doc, _ = _json(["--lint-profile", profile, probe(src)])
        assert [d["code"] for d in doc["diagnostics"]] == [new]


def test_old_id_in_severity_config_still_works(probe, tmp_path, monkeypatch):
    (tmp_path / ".pssparser.toml").write_text('[severity]\nPSS044 = "off"\n')
    monkeypatch.chdir(tmp_path)
    src = dict((p[0], p[2]) for p in PROBES)["LINT401"]
    rc, out, _ = _run(["--json", probe(src)])
    doc = json.loads(out)
    codes = [d["code"] for d in doc["diagnostics"]]
    assert codes == ["PSSP004"]
    note = doc["diagnostics"][0]
    assert note["severity"] == "info"
    assert "severity.PSS044" in note["message"]
    assert "LINT401" in note["message"]


def test_old_id_in_werror_still_promotes_and_notes_once(probe):
    src = dict((p[0], p[2]) for p in PROBES)["LINT601"]
    rc, doc, _ = _json(["-Werror=PSS104", "-Werror=PSS104", probe(src)])
    by_code = {d["code"]: d for d in doc["diagnostics"]}
    assert by_code["LINT601"]["severity"] == "error"
    assert [d["code"] for d in doc["diagnostics"]].count("PSSP004") == 1
    assert rc == 1


def test_describe_old_id_explains_the_move():
    rc, out, _ = _run(["--describe", "PSS053"])
    assert rc == 0
    assert "retired -> LINT402" in out
    assert "import-after-declaration" in out


def test_describe_by_rule_name():
    rc, out, _ = _run(["--describe", "import-after-declaration"])
    assert rc == 0
    assert out.startswith("LINT402")
    assert "formerly: PSS053" in out


def test_tool_diagnostics_survive_no_lint(probe):
    """PSSP is the tool's own voice: no lint profile hides it."""
    src = dict((p[0], p[2]) for p in PROBES)["LINT601"]
    _, doc, _ = _json(["--no-lint", "-Werror=PSS104", probe(src)])
    assert [d["code"] for d in doc["diagnostics"]] == ["PSSP004"]


def test_tool_warning_old_id_is_accepted(probe):
    """-Werror=PSS030 still names the extension-load warning."""
    _, doc, _ = _json(["-Werror=PSS030", probe("component pss_top { }\n")])
    notes = [d for d in doc["diagnostics"] if d["code"] == "PSSP004"]
    assert len(notes) == 1 and "PSSP001" in notes[0]["message"]


def test_the_error_cap_is_pssp007(probe):
    src = "".join("struct S%d { int ; }\n" % i for i in range(3))
    rc, doc, _ = _json(["--max-errors", "1", probe(src)])
    assert [d["code"] for d in doc["diagnostics"]] == ["PSS022", "PSSP007"]
    assert rc == 1


def test_tool_error_old_id_is_still_a_core_error(probe, tmp_path, monkeypatch):
    """PSS033 rewrites to PSSP008, which -- like a PSS error -- cannot be
    downgraded."""
    (tmp_path / ".pssparser.toml").write_text('[severity]\nPSS033 = "warning"\n')
    monkeypatch.chdir(tmp_path)
    rc, _, err = _run([probe("component pss_top { }\n")])
    assert rc == 2
    assert "'PSSP008' is a core error" in err


def test_a_tool_group_selector_skips_tool_errors():
    """`tool = "warning"` reaches the tool warnings, never the tool errors."""
    from pssparser.checkers import CheckerManager
    from pssparser.checkers.selectors import RuleSet

    manager = CheckerManager()
    manager.discover()
    rules = RuleSet(manager.all_marker_defs())
    for group in ("tool", "PSSP", "PSSP00"):
        ids = set(rules.expand([group]))
        assert "PSSP001" in ids, group
        assert not ids & {"PSSP000", "PSSP005", "PSSP007", "PSSP008"}, group


def test_a_lint_finding_outside_the_users_files_is_dropped(probe):
    """Ownership: lint is reported only in files named on the command line.

    The C++ linker raises lint in the built-in standard library too; that is
    never the user's to fix.  Simulated by asking for a file that is not the
    one the finding is in."""
    from pssparser.cli.diagnostics import Diagnostic, DiagnosticCollection

    coll = DiagnosticCollection()
    coll.add(Diagnostic(file="/elsewhere/std.pss", line=1, col=1,
                        severity="warning", message="m", code="LINT402"))
    coll.add(Diagnostic(file="/elsewhere/std.pss", line=1, col=1,
                        severity="error", message="m", code="PSS001"))
    dropped = coll.apply_lint_selection({"LINT402"}, {"LINT402"},
                                        owned={"/mine/m.pss"})
    assert dropped == 1
    assert [d.code for d in coll.diagnostics] == ["PSS001"]
