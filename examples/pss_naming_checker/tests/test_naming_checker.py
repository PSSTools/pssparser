"""Tests for the pss_naming_checker example plug-in."""
from __future__ import annotations

import sys
import os

# Make pssparser importable without installation (same PYTHONPATH=python trick)
_repo = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "python")
if _repo not in sys.path:
    sys.path.insert(0, os.path.abspath(_repo))

# Make pss_naming importable from src/
_src = os.path.join(os.path.dirname(__file__), "..", "src")
if _src not in sys.path:
    sys.path.insert(0, os.path.abspath(_src))

import pytest
from pss_naming.checker import NamingConventionChecker
from pssparser.checkers import CheckerManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_and_check(pss_code: str, tmp_path, options: dict | None = None) -> list:
    """Parse *pss_code*, run NamingConventionChecker, return marker dicts.

    *options* goes through the same ``resolve_options`` path the CLI uses,
    so a test here exercises the real schema -- defaults, types, choices --
    rather than poking attributes onto the instance.
    """
    from pssparser import Parser
    from pssparser.parser import ParseException
    from pssparser.checkers import CheckContext

    f = tmp_path / "test.pss"
    f.write_text(pss_code)

    p = Parser()
    try:
        p.parse([str(f)])
    except ParseException:
        pass  # we still get global_scopes for syntax-only style tests

    # Filter to only user GlobalScopes using fileid→path mapping.
    # Built-in PSS library has fileid=0 and is absent from p._filenames.
    user_files = {str(f)}
    filenames = getattr(p, "_filenames", {})  # {fileid: path}
    global_scopes = [
        gs for gs in getattr(p, "_files", [])
        if filenames.get(gs.getFileid(), "") in user_files
    ]

    marker_index = {md.id: md for md in NamingConventionChecker.marker_defs}
    ctx = CheckContext(
        root=None,
        files=[str(f)],
        global_scopes=global_scopes,
        file_map=dict(filenames),
        _marker_index=marker_index,
    )

    from pssparser.checkers.manager import resolve_options

    checker = NamingConventionChecker()
    checker.configure(resolve_options(checker, options))
    checker.check(ctx)
    return ctx._markers


# ---------------------------------------------------------------------------
# PSC001 — action names
# ---------------------------------------------------------------------------

def test_action_lowercase_name_triggers_psc001(tmp_path):
    markers = _parse_and_check(
        "component pss_top { action write_data {} }", tmp_path
    )
    codes = [m["code"] for m in markers]
    assert "PSC001" in codes


def test_action_lowercase_message_contains_name(tmp_path):
    markers = _parse_and_check(
        "component pss_top { action write_data {} }", tmp_path
    )
    psc001 = [m for m in markers if m["code"] == "PSC001"]
    assert any("write_data" in m["message"] for m in psc001)


def test_action_uppercase_name_no_psc001(tmp_path):
    markers = _parse_and_check(
        "component pss_top { action WriteData {} }", tmp_path
    )
    assert all(m["code"] != "PSC001" for m in markers)


def test_multiple_actions_each_checked(tmp_path):
    markers = _parse_and_check(
        "component pss_top { action good {} action also_bad {} }", tmp_path
    )
    # 'good' is lowercase → PSC001; 'also_bad' is lowercase → PSC001
    psc001 = [m for m in markers if m["code"] == "PSC001"]
    assert len(psc001) == 2


# ---------------------------------------------------------------------------
# PSC002 — struct names
# ---------------------------------------------------------------------------

def test_struct_lowercase_name_triggers_psc002(tmp_path):
    markers = _parse_and_check("struct my_packet { int x; }", tmp_path)
    codes = [m["code"] for m in markers]
    assert "PSC002" in codes


def test_struct_uppercase_name_no_psc002(tmp_path):
    markers = _parse_and_check("struct MyPacket { int x; }", tmp_path)
    assert all(m["code"] != "PSC002" for m in markers)


def test_struct_message_contains_name(tmp_path):
    markers = _parse_and_check("struct my_packet { int x; }", tmp_path)
    psc002 = [m for m in markers if m["code"] == "PSC002"]
    assert any("my_packet" in m["message"] for m in psc002)


# ---------------------------------------------------------------------------
# runs_without_link
# ---------------------------------------------------------------------------

def test_runs_without_link_is_true():
    assert NamingConventionChecker.runs_without_link is True


# ---------------------------------------------------------------------------
# Marker location
# ---------------------------------------------------------------------------

def test_marker_has_line_and_col(tmp_path):
    markers = _parse_and_check(
        "component pss_top { action write_data {} }", tmp_path
    )
    psc001 = [m for m in markers if m["code"] == "PSC001"]
    assert psc001, "expected at least one PSC001 marker"
    m = psc001[0]
    assert isinstance(m["line"], int) and m["line"] > 0
    assert isinstance(m["col"], int) and m["col"] > 0


# ---------------------------------------------------------------------------
# Integration: marker_defs registered correctly in CheckerManager
# ---------------------------------------------------------------------------

def test_marker_defs_unique_ids():
    m = CheckerManager()
    m.discover()
    m._registered["naming-convention"] = NamingConventionChecker
    # Should not raise
    m._check_unique_ids()


def test_list_markers_includes_psc001_psc002():
    m = CheckerManager()
    m._registered["naming-convention"] = NamingConventionChecker
    ids = [x["id"] for x in m.list_all_markers()]
    assert "PSC001" in ids
    assert "PSC002" in ids


# ---------------------------------------------------------------------------
# Configuration — the `style` and `exempt` options
# ---------------------------------------------------------------------------

def test_default_style_is_pascal_case(tmp_path):
    """No configuration means the rule this checker has always enforced."""
    markers = _parse_and_check(
        "component pss_top { action write_data {} }", tmp_path, options={}
    )
    assert [m["code"] for m in markers] == ["PSC001"]


def test_snake_case_style_inverts_the_rule(tmp_path):
    """The Phase 3 gate: the house style is switchable from configuration.

    The same source that is clean under PascalCase is a violation under
    snake_case and vice versa -- which is only true if the option actually
    reaches the comparison rather than being stored and ignored.
    """
    opts = {"style": "snake_case"}
    clean = _parse_and_check(
        "component pss_top { action write_data {} }", tmp_path, options=opts
    )
    assert clean == []

    dirty = _parse_and_check(
        "component pss_top { action WriteData {} }", tmp_path, options=opts
    )
    assert [m["code"] for m in dirty] == ["PSC001"]
    assert "lower_snake_case" in dirty[0]["message"]


def test_exempt_patterns_skip_matching_names(tmp_path):
    """Globs, so an in-progress migration can exclude a prefix wholesale."""
    markers = _parse_and_check(
        "struct legacy_pkt {} struct other_pkt {}",
        tmp_path,
        options={"exempt": ["legacy_*"]},
    )
    messages = [m["message"] for m in markers]
    assert len(messages) == 1
    assert "other_pkt" in messages[0]


def test_exempt_matching_is_case_sensitive(tmp_path):
    """fnmatchcase, not fnmatch: on a case-insensitive filesystem the
    default fnmatch would make 'LEGACY_*' match 'legacy_pkt'."""
    markers = _parse_and_check(
        "struct legacy_pkt {}", tmp_path, options={"exempt": ["LEGACY_*"]}
    )
    assert [m["code"] for m in markers] == ["PSC002"]


def test_a_bad_style_value_is_rejected_by_the_schema(tmp_path):
    """`choices` is what turns a typo into an error instead of a silent
    fall-through to the default branch."""
    from pssparser.checkers.manager import resolve_options

    with pytest.raises(ValueError, match="must be one of"):
        resolve_options(NamingConventionChecker(), {"style": "camelCase"})


def test_the_declared_defaults_match_the_class_level_fallback(tmp_path):
    """The instance attribute exists so the checker works when constructed
    directly; it must not drift from the schema it shadows."""
    from pssparser.checkers.manager import resolve_options

    resolved = resolve_options(NamingConventionChecker(), None)
    assert resolved == NamingConventionChecker.options
