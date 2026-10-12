"""Finishing diagnostics in the core (lint-core-plan.md C7.4).

``ILintEngine::finish`` does what the CLI did in Python between the run and
the output: lint selection per file and ownership, ``[severity]``, source
waivers and the ``-W`` policy. The CLI now calls it; the Python steps stay
as the oracle (``commands._CORE_FINISH = False``), and a run must print the
same either way.
"""
from __future__ import annotations

import io
import json
import random
import sys

import pytest

from pssparser.cli import commands
from pssparser.cli.app import main

ACME = """\
pss-rules:
  defaults:
    family: naming
  rules:
    - id: ACME001
      name: comp-suffix
      tier: style
      summary: Component names end in _c
      message: "'${node.name.id}' should end in '_c'"
      match: { kind: Component }
      where: "!node.name.id.endsWith('_c')"
    - id: ACME002
      name: action-upper
      tier: suspicious
      summary: Action names are lower case
      message: "action '${node.name.id}' is not lower case"
      match: { kind: Action }
      where: "!node.name.id.matches('^[a-z_0-9]+$')"
    - id: ACME003
      name: action-info
      tier: pedantic
      severity: info
      summary: Every action
      message: "action '${node.name.id}'"
      match: { kind: Action }
"""

FILES = ("ip/a.pss", "ip/legacy/b.pss", "tests/t.pss", "lib/l.pss")

#: Selectors a waiver, `[severity]` key or `-W` group may name.
SELECTORS = ["LINT403", "unknown-annotation", "ACME001", "ACME002", "ACME003", "ACME",
             "action-upper", "family:naming", "style", "suspicious", "pedantic", "LINT4",
             "LINT402", "PSSP202", "PSSP205"]
WAIVE = SELECTORS + ["PSS002", "nosuch", "LINT", "PSS053"]


def _run(*argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(list(argv))
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def _model(rng, n):
    lines = [f"component dma{n} {{", "  @desc_s", f"  action Xfer{n} {{ }}",
             f"  action ok{n} {{ }}", "}"]
    out = []
    for line in lines:
        if rng.random() < 0.25:
            sels = ", ".join(rng.sample(WAIVE, rng.choice((1, 1, 2))))
            out.append(f"// pssparser waive {sels}" + rng.choice((": why", "")))
        if rng.random() < 0.3:
            sels = ", ".join(rng.sample(WAIVE, 1))
            line += f"  // pssparser waive {sels}" + rng.choice((": why", ": ok", ""))
        out.append(line)
    return "\n".join(out) + "\n"


def _list(rng, pool, most=3):
    return json.dumps(rng.sample(pool, rng.randint(0, most)))


def _config(rng):
    toml = ['[lint]', 'rules = ["acme.yaml"]']
    toml.append(f'profile = "{rng.choice(["minimal", "recommended", "strict", "all"])}"')
    toml.append(f"select = {_list(rng, SELECTORS)}")
    toml.append(f"ignore = {_list(rng, SELECTORS, 2)}")
    for _ in range(rng.randint(0, 2)):
        toml.append("[[lint.overrides]]")
        toml.append(f'files = {json.dumps(rng.sample(["ip/**", "ip/legacy", "tests", "*.pss", "lib/l.pss"], rng.randint(1, 2)))}')
        if rng.random() < 0.5:
            toml.append(f"select = {_list(rng, SELECTORS)}")
        if rng.random() < 0.5:
            toml.append(f"ignore = {_list(rng, SELECTORS)}")
    keys = rng.sample(SELECTORS, rng.randint(0, 3))
    if keys:
        toml.append("[severity]")
        for k in keys:
            sev = rng.choice(["error", "warning", "info", "hint", "off"])
            toml.append(f'"{k}" = "{sev}"')
    warnings = []
    r = rng.random()
    if r < 0.25:
        warnings.append("error = true")
    elif r < 0.6:
        warnings.append(f"error = {_list(rng, SELECTORS + ['info'], 2)}")
    if rng.random() < 0.4:
        warnings.append(f'"no-error" = {_list(rng, SELECTORS, 2)}')
    if rng.random() < 0.2:
        warnings.append("none = true")
    if warnings:
        toml += ["[warnings]"] + warnings
    return "\n".join(toml) + "\n"


def _flags(rng):
    out = []
    for f in ("-Werror", "-Werror=info", "-Wno-error=ACME002", "-Werror=style", "--no-warnings"):
        if rng.random() < 0.12:
            out.append(f)
    return out


def _both(monkeypatch, *argv):
    monkeypatch.setattr(commands, "_CORE_FINISH", False)
    want = _run(*argv)
    monkeypatch.setattr(commands, "_CORE_FINISH", True)
    got = _run(*argv)
    return got, want


@pytest.fixture
def ws(lint_enabled, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "acme.yaml").write_text(ACME)
    for f in FILES:
        (tmp_path / f).parent.mkdir(parents=True, exist_ok=True)
    return tmp_path


@pytest.mark.parametrize("seed", range(40))
def test_the_core_finishes_as_the_oracle_does(ws, monkeypatch, seed):
    rng = random.Random(seed)
    for n, f in enumerate(FILES):
        (ws / f).write_text(_model(rng, n))
    (ws / ".pssparser.toml").write_text(_config(rng))
    argv = ["--format", "json", "--show-hints", *_flags(rng), *FILES]
    got, want = _both(monkeypatch, *argv)
    assert got == want
    assert got[0] in (0, 1, 2), got[2]


def test_the_runs_report_something(ws, monkeypatch):
    # The differential above is not vacuous: findings, waived ones, hygiene
    # markers and promotions all occur across its seeds.
    seen = set()
    for seed in range(40):
        rng = random.Random(seed)
        for n, f in enumerate(FILES):
            (ws / f).write_text(_model(rng, n))
        (ws / ".pssparser.toml").write_text(_config(rng))
        rc, out, _ = _run("--format", "json", "--show-hints", *_flags(rng), *FILES)
        if rc == 2:
            continue
        doc = json.loads(out)
        for d in doc["diagnostics"]:
            seen.add(d["code"][:4] if d["code"].startswith("ACME") else d["code"])
            if d.get("original_severity"):
                seen.add("promoted")
        if doc.get("waived"):
            seen.add("waived")
    assert {"ACME", "LINT403", "PSSP202", "PSSP203", "PSSP204", "PSSP205", "promoted",
            "waived"} <= seen, seen


# -- the call itself -------------------------------------------------------

@pytest.fixture
def engine(factory):
    return factory.mkLintEngine()


def _d(code, severity="warning", file="a.pss", line=1, col=1):
    return {"code": code, "severity": severity, "file": file, "line": line, "col": col}


def test_the_stages_in_order(engine):
    diags = [_d("LINT403"), _d("PSS001", "error", line=2), _d("LINT101", "hint", line=3),
             _d("LINT402", line=4), _d("", "warning", line=5)]
    r = engine.finish({
        "diagnostics": diags,
        "selection": {"lint": {"profile": "none", "select": ["LINT403", "LINT402"]},
                      "severity": {"LINT402": "info", "PSS001": "warning"},
                      "warnings": {"error": True}},
    })
    assert r["ok"] and r["waived"] == [] and r["dropped"] == {"outside": 0}
    assert r["diagnostics"] == [
        {"index": 0, "severity": "error", "original_severity": "warning", "werror": "-Werror"},
        {"index": 1, "severity": "error"},
        {"index": 3, "severity": "info"},
        {"index": 4, "severity": "error", "original_severity": "warning", "werror": "-Werror"},
    ]
    assert r["problems"] == ["severity: 'PSS001' is a core error; its severity stays 'error'"]


def test_ownership_and_stages(engine):
    diags = [_d("LINT403", file="a.pss"), _d("LINT403", file="std.pss")]
    r = engine.finish({"diagnostics": diags, "owned": ["a.pss"], "stages": ["select"]})
    assert [d["index"] for d in r["diagnostics"]] == [0]
    assert r["dropped"] == {"outside": 1}
    r = engine.finish({"diagnostics": diags, "stages": ["policy"],
                       "policy": {"none": True}})
    assert r["diagnostics"] == []


def test_a_waiver_and_its_hygiene(engine):
    w = {"form": "pragma", "file": "a.pss", "line": 1, "col": 1, "selectors": ["LINT403"],
         "reason": "", "start": [1, 1], "end": [2, 1]}
    r = engine.finish({"diagnostics": [_d("LINT403")], "waivers": [w], "ran": "auto",
                       "selection": {"severity": {"PSSP205": "info"},
                                     "warnings": {"error": ["info"]}}})
    assert r["waived"] == [{"index": 0, "severity": "warning", "waiver": 0}]
    [m] = r["diagnostics"]
    assert (m["index"], m["code"], m["severity"], m["werror"]) == (
        -1, "PSSP205", "error", "-Werror=info")
    assert r["waivers"][0]["used"] == 1


def test_ran_auto_reports_an_unused_waiver_only_for_a_rule_that_ran(engine):
    def unused(sel, profile, severity=None):
        w = {"form": "pragma", "file": "a.pss", "line": 1, "col": 1, "selectors": [sel],
             "reason": "r", "start": [1, 1], "end": [2, 1]}
        r = engine.finish({"diagnostics": [], "waivers": [w], "ran": "auto",
                           "selection": {"lint": {"profile": profile},
                                         "severity": severity or {}}})
        return [m["code"] for m in r["diagnostics"]]
    assert unused("LINT403", "minimal") == ["PSSP202"]
    assert unused("LINT403", "none") == []
    assert unused("LINT403", "minimal", {"LINT403": "off"}) == []
    assert unused("PSS002", "none") == ["PSSP204"]


def test_bad_requests(engine):
    assert not engine.finish([])["ok"]
    r = engine.finish({"stages": ["nope"], "selection": 3, "ran": 1})
    assert r["ok"] and r["problems"] == [
        "stages: no stage 'nope'", "selection: not an object",
        "ran: not a list of IDs or \"auto\""]
