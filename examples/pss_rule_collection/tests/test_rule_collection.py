"""Tests for the pss_rule_collection example extension."""
from __future__ import annotations

import os
import sys

# Make pssparser importable without installation (same PYTHONPATH=python trick
# the pss_naming_checker example uses).
_repo = os.path.join(os.path.dirname(__file__), "..", "..", "..", "python")
if _repo not in sys.path:
    sys.path.insert(0, os.path.abspath(_repo))

# Make pss_rules importable from src/.
_src = os.path.join(os.path.dirname(__file__), "..", "src")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

import pytest

import pss_rules
from pssparser.checkers import API_VERSION, CheckContext, ExtensionRegistry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_and_check(checker_cls, pss_code: str, tmp_path) -> list:
    """Parse *pss_code*, run *checker_cls*, return the marker dicts."""
    from pssparser import Parser
    from pssparser.parser import ParseException

    f = tmp_path / "test.pss"
    f.write_text(pss_code)

    p = Parser()
    try:
        p.parse([str(f)])
    except ParseException:
        pass

    filenames = getattr(p, "_filenames", {})
    global_scopes = [
        gs for gs in getattr(p, "_files", [])
        if filenames.get(gs.getFileid(), "") == str(f)
    ]

    ctx = CheckContext(
        root=None,
        files=[str(f)],
        global_scopes=global_scopes,
        file_map=dict(filenames),
        _marker_index={md.id: md for md in checker_cls.marker_defs},
    )
    checker_cls().check(ctx)
    return ctx._markers


def _registry() -> ExtensionRegistry:
    reg = ExtensionRegistry("example-rules", api_version=API_VERSION)
    pss_rules.register(reg)
    return reg


# ---------------------------------------------------------------------------
# register() — the extension contract
# ---------------------------------------------------------------------------

def test_register_contributes_both_checkers():
    names = {cls.name for cls in _registry().checkers}
    assert names == {"component-naming", "package-naming"}


def test_register_sets_version_and_description():
    reg = _registry()
    assert reg.version == pss_rules.__version__
    assert reg.description


def test_requires_api_is_satisfied_by_this_build():
    assert pss_rules.REQUIRES_API <= API_VERSION


def test_marker_ids_do_not_collide_with_each_other():
    ids = [md.id for cls in _registry().checkers for md in cls.marker_defs]
    assert len(ids) == len(set(ids))


def test_marker_ids_avoid_the_reserved_pss_prefix():
    for cls in _registry().checkers:
        for md in cls.marker_defs:
            assert not md.id.startswith("PSS")


def test_the_extension_loads_through_the_manager(monkeypatch):
    """End-to-end through CheckerManager, with a faked entry point."""
    from pssparser.checkers import CheckerManager, EXTENSION_GROUP
    from pssparser.checkers import manager as manager_mod

    class _EP:
        name = "example-rules"
        dist = None

        def load(self):
            return pss_rules

    monkeypatch.setattr(
        manager_mod, "_entry_points",
        lambda group: [_EP()] if group == EXTENSION_GROUP else [],
    )
    monkeypatch.delenv("PSSPARSER_NO_EXTENSIONS", raising=False)

    m = CheckerManager()
    m.discover()

    assert m.load_diagnostics == []
    assert m.extension_of("component-naming") == "example-rules"
    assert m.list_extensions()[0]["checkers"] == [
        "component-naming", "package-naming",
    ]


# ---------------------------------------------------------------------------
# PRC001 — component naming
# ---------------------------------------------------------------------------

def test_lowercase_component_triggers_prc001(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    markers = _parse_and_check(ComponentNamingChecker, "component widget_c {}", tmp_path)
    assert [m["code"] for m in markers] == ["PRC001"]
    assert "widget_c" in markers[0]["message"]


def test_pascalcase_component_is_clean(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    markers = _parse_and_check(ComponentNamingChecker, "component Widget {}", tmp_path)
    assert markers == []


def test_pss_top_is_exempt(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    markers = _parse_and_check(ComponentNamingChecker, "component pss_top {}", tmp_path)
    assert markers == []


def test_nested_component_is_checked(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    markers = _parse_and_check(
        ComponentNamingChecker,
        "package p { component inner_c {} }",
        tmp_path,
    )
    assert [m["code"] for m in markers] == ["PRC001"]


def test_prc001_marker_has_a_usable_location(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    markers = _parse_and_check(
        ComponentNamingChecker, "\n\ncomponent widget_c {}", tmp_path
    )
    m = markers[0]
    assert m["line"] == 3
    assert m["col"] > 0
    assert m["extent"] == len("widget_c")


# ---------------------------------------------------------------------------
# PRC002 — package naming
# ---------------------------------------------------------------------------

def test_pascalcase_package_triggers_prc002(tmp_path):
    from pss_rules.package_naming import PackageNamingChecker
    markers = _parse_and_check(PackageNamingChecker, "package MyPkg {}", tmp_path)
    assert [m["code"] for m in markers] == ["PRC002"]
    assert "MyPkg" in markers[0]["message"]


def test_snake_case_package_is_clean(tmp_path):
    from pss_rules.package_naming import PackageNamingChecker
    markers = _parse_and_check(PackageNamingChecker, "package my_pkg {}", tmp_path)
    assert markers == []


def test_snake_case_with_digits_and_underscores_is_clean(tmp_path):
    from pss_rules.package_naming import PackageNamingChecker
    markers = _parse_and_check(PackageNamingChecker, "package my_pkg_v2 {}", tmp_path)
    assert markers == []


def test_leading_underscore_package_triggers_prc002(tmp_path):
    from pss_rules.package_naming import PackageNamingChecker
    markers = _parse_and_check(PackageNamingChecker, "package _hidden {}", tmp_path)
    assert [m["code"] for m in markers] == ["PRC002"]


def test_a_dotted_package_name_is_a_parse_error_not_our_concern(tmp_path):
    """Pins the premise behind PackageNamingChecker's segment loop.

    ``package a.b { }`` does not parse today, so the loop over ``numId()``
    only ever sees one segment. If this test starts failing because the
    grammar grew multi-segment package names, the checker already handles
    them -- delete this test rather than the loop.
    """
    from pssparser import Parser
    from pssparser.parser import ParseException

    f = tmp_path / "dotted.pss"
    f.write_text("package good.BadSeg {}\n")
    with pytest.raises(ParseException):
        Parser().parse([str(f)])


# ---------------------------------------------------------------------------
# Both checkers together
# ---------------------------------------------------------------------------

def test_both_checkers_report_on_one_file(tmp_path):
    from pss_rules.component_naming import ComponentNamingChecker
    from pss_rules.package_naming import PackageNamingChecker

    src = "package MyPkg {\n    component widget_c {}\n}\n"
    codes = set()
    for cls in (ComponentNamingChecker, PackageNamingChecker):
        codes.update(m["code"] for m in _parse_and_check(cls, src, tmp_path))
    assert codes == {"PRC001", "PRC002"}
