"""Marker-ID grammar, reserved namespaces and lint-metadata validation.

Plan items F1.0 (namespace grammar and reservation) and F1.2 (``MarkerDef``
lint fields).  Discovery is faked with the same entry-point fixture as
``test_extensions.py``.
"""
from __future__ import annotations

import pytest

from pssparser.checkers import EXTENSION_GROUP, CheckerBase, CheckerManager, MarkerDef
from pssparser.checkers.manager import metadata_problem
from pssparser.checkers.markerdef import Example
from pssparser.checkers.taxonomy import (
    RESERVED_NAMESPACES,
    TIER_SEVERITY,
    parse_rules_version,
    split_code,
)

from .test_extensions import FakeEP, codes, eps, make_module, messages  # noqa: F401


def _checker(name, *mdefs):
    return type(
        f"Checker_{name.replace('-', '_')}",
        (CheckerBase,),
        {
            "name": name,
            "description": name,
            "marker_defs": list(mdefs),
            "check": lambda self, context: None,
        },
    )


def _discover(eps, *checker_classes):
    def register(reg):
        for cls in checker_classes:
            reg.add_checker(cls)

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]
    m = CheckerManager()
    m.discover()
    return m


# -- the ID grammar -----------------------------------------------------------

@pytest.mark.parametrize("code,expected", [
    ("PRC001", ("PRC", 1)),
    ("LINT104", ("LINT", 104)),
    ("PSSP101", ("PSSP", 101)),
    ("AC999", ("AC", 999)),
])
def test_split_code_accepts(code, expected):
    assert split_code(code) == expected


@pytest.mark.parametrize("code", [
    "A001", "ABCDEF001", "PRC01", "PRC0001", "prc001", "PR1C001", "", "PRC-001",
])
def test_split_code_rejects(code):
    assert split_code(code) is None


@pytest.mark.parametrize("ns", RESERVED_NAMESPACES)
def test_reserved_namespace_is_refused(eps, ns):
    m = _discover(eps, _checker("squatter", MarkerDef(
        id=f"{ns}500", severity="warning", summary="s")))
    assert codes(m) == ["PSSP005"]
    assert "squatter" not in m.registered
    assert f"{ns}500" in messages(m)


def test_reserved_refusal_costs_only_that_checker(eps):
    m = _discover(
        eps,
        _checker("squatter", MarkerDef(id="LINT001", severity="warning", summary="s")),
        _checker("fine", MarkerDef(id="ACM001", severity="warning", summary="s")),
    )
    assert "fine" in m.registered
    assert "squatter" not in m.registered


def test_malformed_id_still_loads_with_a_warning(eps):
    m = _discover(eps, _checker("old-style", MarkerDef(
        id="X1", severity="warning", summary="s")))
    assert codes(m) == ["PSSP006"]
    assert "old-style" in m.registered


def test_load_checker_refuses_a_reserved_namespace(tmp_path, monkeypatch):
    mod = tmp_path / "squat_mod.py"
    mod.write_text(
        "from pssparser.checkers import CheckerBase, MarkerDef\n"
        "class Squat(CheckerBase):\n"
        "    name = 'squat'\n"
        "    marker_defs = [MarkerDef(id='LINT900', severity='warning', summary='s')]\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    m = CheckerManager()
    m.discover()
    with pytest.raises(ValueError, match="reserved namespace"):
        m.load("squat_mod:Squat")


# -- lint metadata (F1.2) ------------------------------------------------------

def _md(**kw):
    base = dict(id="ACM001", severity="", summary="s", tier="suspicious")
    base.update(kw)
    return MarkerDef(**base)


def test_tier_gives_the_default_severity():
    for tier, sev in TIER_SEVERITY.items():
        assert MarkerDef(id="ACM001", severity="", summary="s", tier=tier).severity == sev


def test_explicit_severity_is_kept():
    assert MarkerDef(id="ACM001", severity="error", summary="s").severity == "error"


@pytest.mark.parametrize("kwargs,fragment", [
    (dict(name="Not_Kebab"), "kebab-case"),
    (dict(tier="bogus"), "tier 'bogus'"),
    (dict(family="bogus"), "family 'bogus'"),
    (dict(level="L9"), "level 'L9'"),
    (dict(fix="maybe"), "fix 'maybe'"),
    (dict(status="gone"), "status 'gone'"),
    (dict(since="1.2.3"), "YYYY.N"),
    (dict(id="ACM001", tier="nursery"), "must declare 'since'"),
    (dict(fix="safe"), "no example shows"),
    (dict(severity="error"), "'Severity:' paragraph"),
])
def test_metadata_problem_is_reported(kwargs, fragment):
    problem = metadata_problem(_md(**kwargs))
    assert problem is not None and fragment in problem


@pytest.mark.parametrize("kwargs", [
    dict(),
    dict(name="good-name", family="constraint", level="L2"),
    dict(tier="nursery", since="2026.1"),
    dict(fix="safe", examples=(Example(code="a", expect=((1, 1),), fixed="b"),)),
    dict(severity="error", detail="Severity: error, because it always is."),
])
def test_valid_metadata_passes(kwargs):
    assert metadata_problem(_md(**kwargs)) is None


def test_a_lint_id_needs_a_tier():
    md = MarkerDef(id="LINT900", severity="warning", summary="s")
    assert "must declare a tier" in metadata_problem(md)


def test_legacy_marker_without_lint_fields_passes():
    assert metadata_problem(MarkerDef(id="ACM001", severity="warning", summary="s")) is None


def test_invalid_metadata_refuses_the_checker(eps):
    m = _discover(eps, _checker("bad", _md(tier="bogus")))
    assert codes(m) == ["PSSP201"]
    assert "bad" not in m.registered
    assert "tier 'bogus'" in messages(m)


def test_rule_names_are_unique_across_checkers(eps):
    m = _discover(
        eps,
        _checker("one", _md(id="ACM001", name="same-name")),
        _checker("two", _md(id="ACM002", name="same-name")),
    )
    assert "one" in m.registered
    assert "two" not in m.registered
    assert codes(m) == ["PSSP201"]


def test_a_rule_name_may_not_shadow_a_core_rule(eps):
    m = _discover(eps, _checker("dup", _md(name="import-after-declaration")))
    assert "dup" not in m.registered


def test_rules_version_format():
    assert parse_rules_version("2026.1") == (2026, 1)
    assert parse_rules_version("2026.12") == (2026, 12)
    assert parse_rules_version("2026") is None
    assert parse_rules_version("v2026.1") is None
