"""Rule selectors and profile expansion (plan F1.4, F1.5)."""
from __future__ import annotations

import pytest

from pssparser.checkers import MarkerDef
from pssparser.checkers.selectors import RuleSet, SelectorError
from pssparser.lint.catalog import MINIMAL_IDS


def _rule(id, tier, *, name="", family="", since="", default_enabled=True):
    return MarkerDef(id=id, severity="", summary=id, tier=tier, name=name,
                     family=family, since=since,
                     default_enabled=default_enabled,
                     detail="Severity: tier default.")


#: One rule per tier, plus a core error and a minimal-profile rule.
RULES = [
    MarkerDef(id="PSS001", severity="error", summary="syntax"),
    _rule("LINT101", "correctness", name="corr-rule", family="constraint"),
    _rule("LINT102", "suspicious", name="susp-rule", family="constraint"),
    _rule("LINT203", "portability", name="port-rule", family="activity"),
    _rule("LINT204", "simplify", name="simp-rule", family="activity"),
    _rule("LINT301", "style", name="style-rule", family="exec"),
    _rule("LINT302", "pedantic", name="ped-rule", family="exec"),
    _rule("LINT401", "restriction", name="restr-rule", family="decl"),
    _rule("LINT402", "nursery", name="nurs-rule", family="decl", since="2026.1"),
    _rule("LINT501", "suspicious", name="new-rule", family="register",
          since="2027.1"),
    _rule("LINT502", "suspicious", name="opt-in-rule", family="register",
          default_enabled=False),
    _rule("LINT601", "style", name="minimal-style", family="evolution"),
]

MINIMAL = ("LINT601",)


def ruleset(**kw):
    return RuleSet(RULES, minimal=MINIMAL, **kw)


@pytest.mark.parametrize("text,kind", [
    ("LINT101", "id"),
    ("corr-rule", "name"),
    ("LINT1", "prefix"),
    ("LINT", "namespace"),
    ("family:activity", "family"),
    ("correctness", "tier"),
    ("recommended", "profile"),
])
def test_each_form_parses(text, kind):
    assert ruleset().parse(text).kind == kind


def test_unknown_selector_suggests():
    with pytest.raises(SelectorError, match="did you mean 'corr-rule'"):
        ruleset().parse("cor-rule")


def test_unknown_family_suggests():
    with pytest.raises(SelectorError, match="family:constraint"):
        ruleset().parse("family:constrain")


def test_alias_parses_as_its_current_id():
    rs = ruleset()
    rs.aliases = {"PSS053": "LINT601"}
    sel = rs.parse("PSS053")
    assert (sel.kind, sel.value) == ("id", "LINT601")


@pytest.mark.parametrize("profile,expected", [
    ("none", set()),
    ("minimal", {"LINT601"}),
    ("recommended", {"LINT101", "LINT102", "LINT203", "LINT204", "LINT501", "LINT601"}),
    ("library", {"LINT101", "LINT102", "LINT203", "LINT204", "LINT501", "LINT601"}),
    ("strict", {"LINT101", "LINT102", "LINT203", "LINT204", "LINT302", "LINT501",
                "LINT601"}),
    ("all", {"LINT101", "LINT102", "LINT203", "LINT204", "LINT301", "LINT302",
             "LINT401", "LINT501", "LINT601"}),
])
def test_profile_expansion(profile, expected):
    assert ruleset().profile_members(profile) == expected


def test_every_profile_but_none_includes_minimal():
    rs = ruleset()
    for profile in ("minimal", "recommended", "library", "strict", "all"):
        assert set(MINIMAL) <= rs.profile_members(profile)


def test_nursery_is_in_no_profile():
    rs = ruleset()
    assert all("LINT402" not in rs.profile_members(p)
               for p in ("recommended", "strict", "all"))


def test_pin_holds_back_a_newer_rule():
    rs = ruleset(rules_version="2026.1")
    assert "LINT501" not in rs.profile_members("recommended")
    assert rs.held_back("recommended") == ["LINT501"]


def test_explicit_select_overrides_the_pin():
    rs = ruleset(rules_version="2026.1")
    assert "LINT501" in rs.resolve("recommended", select=["new-rule"])


def test_precedence_id_beats_tier():
    enabled = ruleset().resolve("recommended", ignore=["suspicious"],
                                select=["LINT102"])
    assert "LINT102" in enabled
    assert "LINT501" not in enabled


def test_precedence_prefix_beats_family_beats_tier():
    rs = ruleset()
    # family:constraint off, but the LINT10 band back on: the band wins
    assert "LINT101" in rs.resolve("recommended", ignore=["family:constraint"],
                                   select=["LINT10"])
    # tier off, family on: family wins
    assert "LINT203" in rs.resolve("none", select=["family:activity"],
                                   ignore=["portability"])


def test_longer_prefix_is_more_specific():
    rs = ruleset()
    enabled = rs.resolve("none", select=["LINT1"], ignore=["LINT"])
    assert {"LINT101", "LINT102"} <= enabled
    enabled = rs.resolve("none", select=["LINT"], ignore=["LINT10"])
    assert "LINT101" not in enabled and "LINT203" in enabled


def test_tie_goes_to_ignore():
    assert "LINT101" not in ruleset().resolve("none", select=["LINT101"],
                                              ignore=["corr-rule"])


def test_design_example_profiles_plus_tier_minus_one_rule():
    enabled = ruleset().resolve("none", select=["recommended", "pedantic"],
                                ignore=["LINT203"])
    assert "LINT302" in enabled
    assert "LINT203" not in enabled
    assert "LINT101" in enabled


def test_default_enabled_false_needs_an_explicit_select():
    rs = ruleset()
    assert "LINT502" not in rs.resolve("all")
    assert "LINT502" in rs.resolve("all", select=["opt-in-rule"])


def test_expand_never_widens_to_a_core_error():
    expanded = ruleset().expand(["PSS"])
    assert "PSS001" not in expanded


def test_expand_keeps_the_most_specific_key():
    expanded = ruleset().expand(["suspicious", "LINT102"])
    assert expanded["LINT102"][0] == "LINT102"
    assert expanded["LINT501"][0] == "suspicious"


def test_real_minimal_profile_is_the_nine_migrated_rules():
    from pssparser.checkers.core_checker import CoreChecker

    rs = RuleSet(CoreChecker.marker_defs)
    assert rs.profile_members("minimal") == set(MINIMAL_IDS)
    assert len(MINIMAL_IDS) == 9
