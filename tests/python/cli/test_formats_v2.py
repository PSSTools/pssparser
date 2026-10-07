"""--format sarif|github|json (schema v2) and --statistics (plan F1.9).

The SARIF tests check the parts of the 2.1.0 schema a consumer relies on
(GitHub code scanning, VS Code's SARIF viewer).  Full schema validation runs
when ``jsonschema`` is installed (a dev dependency) against the OASIS schema
vendored at ``tests/python/cli/data/sarif-2.1.0.json`` (from
https://github.com/oasis-tcs/sarif-spec, ``sarif-2.1/schema/sarif-schema-2.1.0.json``,
fetched 2026-10-07).
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

from pssparser.cli.app import main
from pssparser.cli.github import escape_data, escape_property


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


WARN_SRC = (
    "package lib { struct s {} }\n"
    "package p {\n"
    "  struct t {}\n"
    "  import lib::*;\n"
    "}\n"
)
ERR_SRC = "component pss_top { action a { int x } }\n"


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "w.pss").write_text(WARN_SRC)
    (tmp_path / "e.pss").write_text(ERR_SRC)
    return tmp_path


# -- JSON v2 ----------------------------------------------------------------------

def test_json_v2_has_a_schema_key_and_rule_metadata(workdir):
    _, out, _ = _run(["--no-config", "--format", "json", "w.pss"])
    doc = json.loads(out)
    assert doc["schema"] == "pssparser-diagnostics/2"
    d = doc["diagnostics"][0]
    assert (d["code"], d["rule"], d["tier"], d["family"]) == (
        "LINT402", "import-after-declaration", "style", "import")


def test_json_v2_keeps_every_v1_key(workdir):
    _, out, _ = _run(["--no-config", "--json", "w.pss"])
    doc = json.loads(out)
    assert {"diagnostics", "summary"} <= set(doc)
    assert {"errors", "warnings", "files"} <= set(doc["summary"])
    assert {"file", "line", "col", "severity", "message", "code"} <= set(
        doc["diagnostics"][0])


def test_json_and_format_conflict_is_a_usage_error(workdir):
    rc, _, err = _run(["--json", "--format", "sarif", "w.pss"])
    assert rc == 2
    assert "conflicts" in err


def test_json_and_format_json_agree(workdir):
    rc, _, _ = _run(["--no-config", "--json", "--format", "json", "w.pss"])
    assert rc == 0


def test_statistics_in_json(workdir):
    _, out, _ = _run(["--no-config", "--json", "--statistics", "w.pss"])
    assert json.loads(out)["statistics"] == [
        {"code": "LINT402", "count": 1, "name": "import-after-declaration",
         "tier": "style"}]


def test_statistics_in_text(workdir):
    _, _, err = _run(["--no-config", "--statistics", "w.pss"])
    assert "     1  LINT402  import-after-declaration [style]" in err


# -- SARIF -------------------------------------------------------------------------

def _sarif(*files):
    rc, out, _ = _run(["--no-config", "--format", "sarif", *files])
    return rc, json.loads(out)


def test_sarif_top_level_shape(workdir):
    rc, doc = _sarif("w.pss")
    assert rc == 0
    assert doc["version"] == "2.1.0"
    assert doc["$schema"].endswith("sarif-2.1.0.json")
    driver = doc["runs"][0]["tool"]["driver"]
    assert driver["name"] == "pssparser"
    assert driver["version"]
    assert driver["informationUri"].startswith("https://")


def test_sarif_result_points_at_its_rule(workdir):
    _, doc = _sarif("w.pss")
    run = doc["runs"][0]
    result = run["results"][0]
    rule = run["tool"]["driver"]["rules"][result["ruleIndex"]]
    assert rule["id"] == result["ruleId"] == "LINT402"
    assert rule["name"] == "import-after-declaration"
    assert rule["helpUri"].endswith("#lint402")
    assert rule["properties"]["tier"] == "style"
    assert result["level"] == "warning"
    loc = result["locations"][0]["physicalLocation"]
    assert loc["artifactLocation"]["uri"] == "w.pss"
    assert loc["region"]["startLine"] == 4
    assert loc["region"]["startColumn"] == 3
    assert result["relatedLocations"][0]["message"]["text"]


def test_sarif_lists_rules_that_ran_without_findings(workdir):
    _, doc = _sarif("e.pss")
    ids = [r["id"] for r in doc["runs"][0]["tool"]["driver"]["rules"]]
    assert "LINT402" in ids          # enabled by the default profile
    assert any(i.startswith("PSS") for i in ids)


def test_sarif_message_drops_the_code_prefix(workdir):
    _, doc = _sarif("e.pss")
    for result in doc["runs"][0]["results"]:
        assert not result["message"]["text"].startswith("[")


@pytest.mark.parametrize("severity,level", [
    ("error", "error"), ("warning", "warning"), ("info", "note"), ("hint", "none"),
])
def test_sarif_level_mapping(workdir, severity, level):
    (workdir / ".pssparser.toml").write_text(f'[severity]\nLINT402 = "{severity}"\n')
    _, out, _ = _run(["--format", "sarif", "w.pss"])
    assert json.loads(out)["runs"][0]["results"][0]["level"] == level


def test_sarif_validates_against_the_schema(workdir):
    jsonschema = pytest.importorskip("jsonschema")
    schema_path = Path(__file__).parent / "data" / "sarif-2.1.0.json"
    if not schema_path.is_file():
        pytest.skip("SARIF 2.1.0 schema not vendored")
    _, doc = _sarif("w.pss", "e.pss")
    jsonschema.validate(doc, json.loads(schema_path.read_text()))


# -- GitHub ----------------------------------------------------------------------

def test_github_annotation_line(workdir):
    rc, out, _ = _run(["--no-config", "--format", "github", "w.pss"])
    assert rc == 0
    line = out.splitlines()[0]
    assert line.startswith("::warning file=w.pss,line=4,col=3,")
    assert ",title=LINT402::'import lib::*;' follows a declaration" in line


def test_github_error_and_exit_code(workdir):
    rc, out, _ = _run(["--no-config", "--format", "github", "e.pss"])
    assert rc == 1
    assert out.startswith("::error ")


def test_github_hints_are_not_emitted(workdir):
    (workdir / ".pssparser.toml").write_text('[severity]\nLINT402 = "hint"\n')
    _, out, _ = _run(["--format", "github", "w.pss"])
    assert out == ""


def test_github_info_is_a_notice(workdir):
    (workdir / ".pssparser.toml").write_text('[severity]\nLINT402 = "info"\n')
    _, out, _ = _run(["--format", "github", "w.pss"])
    assert out.startswith("::notice ")


def test_github_escaping():
    assert escape_data("50%\r\nnext") == "50%25%0D%0Anext"
    assert escape_property("a:b,c") == "a%3Ab%2Cc"
