"""The marker catalogue in the core (lint-core-plan.md C7.3).

``src/lint/catalog/catalog.json`` is generated from the Python ``MarkerDef``s
(``scripts/gen_catalog.py``) and embedded in the core: the taxonomy, every
core marker with its documentation, and the message patterns that give a core
marker its code.  The Python side stays the source of truth, so these tests
check that the two agree, that the core-emitted lint carries its ID from C++,
and what ``LintEngine.catalog()`` serves an editor.
"""
import importlib.util
from pathlib import Path

import pytest

from pssparser.checkers import MarkerDef, taxonomy
from pssparser.checkers.core_checker import CoreChecker
from pssparser.lint.catalog import CORE_EMITTED, MINIMAL_IDS
from pssparser.lint.selection import host_marker
from pssparser.parser import Parser

ROOT = Path(__file__).resolve().parents[3]


def _gen_catalog():
    spec = importlib.util.spec_from_file_location(
        "gen_catalog", ROOT / "scripts" / "gen_catalog.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_catalogue_is_current():
    gen = _gen_catalog()
    assert gen.OUT.read_text(encoding="utf-8") == gen.render(), (
        "src/lint/catalog/catalog.json is stale: run "
        "PYTHONPATH=python python3 scripts/gen_catalog.py and rebuild")


@pytest.fixture
def engine(factory):
    return factory.mkLintEngine()


def test_the_taxonomy_is_taxonomy_py(engine):
    t = engine.catalog()["taxonomy"]
    assert t == {
        "tiers": [[k, v] for k, v in taxonomy.TIER_SEVERITY.items()],
        "families": list(taxonomy.FAMILIES),
        "profiles": list(taxonomy.PROFILES),
        "default_profile": taxonomy.DEFAULT_PROFILE,
        "profile_tiers": {p: list(v) for p, v in taxonomy.PROFILE_TIERS.items()},
        "doc_url": taxonomy.RULE_DOC_URL,
    }


def test_without_a_host_the_engine_knows_the_core(engine):
    cat = engine.catalog()
    assert cat["schema"] == "pssparser-catalog/1"
    got = cat["markers"]
    assert [m["id"] for m in got] == [md.id for md in CoreChecker.marker_defs]
    mins = set(MINIMAL_IDS)
    for m, md in zip(got, CoreChecker.marker_defs):
        assert m == {
            "id": md.id, "name": md.name, "tier": md.tier, "family": md.family,
            "since": md.since, "status": md.status,
            "severity": md.severity or taxonomy.TIER_SEVERITY.get(md.tier, ""),
            "aliases": list(md.aliases), "replaced_by": list(md.replaced_by),
            "default_enabled": md.default_enabled, "minimal": md.id in mins,
            "summary": md.summary, "detail": md.detail, "lrm": list(md.lrm),
            "doc_url": taxonomy.doc_url(md.id), "source": "core",
        }


def test_the_host_replaces_core_entries_in_place(engine):
    first = CoreChecker.marker_defs[0]
    mine = MarkerDef(id=first.id, severity="warning", summary="host's own", name="renamed")
    extra = MarkerDef(id="ACME001", severity="", summary="team", tier="style",
                      name="acme-rule", family="naming")
    assert engine.set_host_markers([host_marker(extra), host_marker(mine)]) == []
    got = engine.catalog()["markers"]
    assert [m["id"] for m in got] == [md.id for md in CoreChecker.marker_defs] + ["ACME001"]
    # A host entry decides selection; the documentation stays the core's.
    assert (got[0]["name"], got[0]["severity"], got[0]["summary"], got[0]["source"]) == \
        ("renamed", "warning", first.summary, "core")
    assert (got[-1]["severity"], got[-1]["summary"], got[-1]["source"]) == \
        ("hint", "", "host")


def test_the_registry_keeps_its_order(engine):
    from pssparser.checkers.manager import CheckerManager
    manager = CheckerManager()
    manager.discover()
    mdefs = manager.all_marker_defs()
    assert mdefs
    assert engine.set_host_markers([host_marker(md) for md in mdefs]) == []
    assert [m["id"] for m in engine.catalog()["markers"]] == [md.id for md in mdefs]


_RULES = """\
pss-rules:
  rules:
    - id: ACME001
      name: comp
      tier: suspicious
      summary: Components named oddly
      doc: Why it matters.
      lrm: ["10.1"]
      message: "component ${node.name.id}"
      match: { kind: Component }
"""


def test_loaded_rules_come_last_with_their_docs(engine):
    assert engine.load_rules("r.yaml", _RULES)
    got = engine.catalog()["markers"][-1]
    assert {k: got[k] for k in ("id", "name", "severity", "summary", "detail", "lrm",
                                "source")} == {
        "id": "ACME001", "name": "comp", "severity": "warning",
        "summary": "Components named oddly", "detail": "Why it matters.",
        "lrm": ["10.1"], "source": "rules"}
    # A host entry with the rule's ID: the rule's docs, the host's metadata.
    assert engine.set_host_markers([{"id": "ACME001", "name": "comp", "tier": "style"}]) == []
    got = engine.catalog()["markers"]
    assert [m["id"] for m in got].count("ACME001") == 1
    assert (got[-1]["severity"], got[-1]["detail"], got[-1]["source"]) == \
        ("hint", "Why it matters.", "rules")


def test_refused_rules_are_left_out(engine):
    assert engine.load_rules("r.yaml", _RULES)
    assert engine.set_host_markers([], ["ACME001"]) == []
    assert "ACME001" not in [m["id"] for m in engine.catalog()["markers"]]


def test_selection_without_a_host_knows_core_codes(engine):
    r = engine.resolve_selection({"lint": {"profile": "none", "select": ["LINT403"]},
                                  "severity": {"PSS002": "warning"}})
    assert r["ok"] and r["errors"] == []
    assert r["groups"][0]["enabled"] == ["LINT403"]
    # The default profile is the core's minimal set.
    r = engine.resolve_selection({})
    assert set(r["groups"][0]["enabled"]) == set(MINIMAL_IDS)


def test_waivers_without_a_host_know_core_codes(engine):
    w = {"form": "pragma", "file": "m.pss", "line": 1, "col": 1, "selectors": ["PSS046"],
         "reason": "r", "start": [1, 1], "end": [2, 1]}
    r = engine.apply_waivers([w], [{"code": "LINT101", "file": "m.pss", "line": 1, "col": 5}])
    assert r["waived"] == [[0, 0]]
    # PSS046 is LINT101's old ID.
    assert [m["code"] for m in r["markers"]] == ["PSSP004"]


# -- the core-emitted lint gets its ID where C++ emits it -------------------

def _markers(path):
    p = Parser()
    p.parse([str(path)])
    p.link()
    return p.markers


@pytest.mark.parametrize("md", CORE_EMITTED, ids=[md.id for md in CORE_EMITTED])
def test_core_lint_carries_its_id_from_cxx(md):
    fixtures = ROOT / "tests" / "lint" / md.name
    got = [m for m in _markers(fixtures / "l01.pss") if m.get("code") == md.id]
    assert got, f"{md.id} not reported on tests/lint/{md.name}/l01.pss"
    assert md.id not in [m.get("code") for m in _markers(fixtures / "ok_01.pss")]


def test_every_core_marker_has_a_code_from_the_core():
    # Parser markers' "code" is the C++ marker's ID, unprocessed.
    for d in sorted((ROOT / "tests" / "lint").iterdir()):
        for f in sorted(d.glob("*.pss")):
            for m in _markers(f):
                assert m.get("code"), (f, m)
