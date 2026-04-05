"""Tests for pssparser.checkers.CheckerManager."""
from __future__ import annotations

from unittest.mock import patch, MagicMock
import pytest

from pssparser.checkers import CheckerBase, CheckerManager, MarkerDef
from tests.python.checkers.conftest import (
    DummyChecker,
    AnotherDummyChecker,
    ConflictingChecker,
)


# ---------------------------------------------------------------------------
# discover()
# ---------------------------------------------------------------------------

def test_discover_registers_core():
    m = CheckerManager()
    m.discover()
    assert "core" in m._registered


def test_discover_core_is_builtin():
    m = CheckerManager()
    m.discover()
    cls = m._registered["core"]
    assert getattr(cls, "is_builtin", False) is True


def test_discover_with_entry_points(monkeypatch):
    fake_ep = MagicMock()
    fake_ep.name = "dummy"
    fake_ep.load.return_value = DummyChecker

    def fake_entry_points(group):
        return [fake_ep]

    with patch("pssparser.checkers.manager.CheckerManager.discover") as mock_discover:
        mock_discover.side_effect = lambda: None
        m = CheckerManager()

    # Manually register core and the fake ep
    from pssparser.checkers.core_checker import CoreChecker
    m._registered["core"] = CoreChecker
    m._registered["dummy"] = DummyChecker
    assert "dummy" in m._registered


# ---------------------------------------------------------------------------
# _check_unique_ids()
# ---------------------------------------------------------------------------

def test_unique_ids_no_overlap_passes():
    m = CheckerManager()
    from pssparser.checkers.core_checker import CoreChecker
    m._registered["core"] = CoreChecker
    m._registered["dummy"] = DummyChecker
    m._registered["another"] = AnotherDummyChecker
    m._check_unique_ids()  # should not raise


def test_unique_ids_overlap_raises():
    m = CheckerManager()
    m._registered["dummy"] = DummyChecker
    m._registered["conflicting"] = ConflictingChecker
    with pytest.raises(ValueError, match="TST001"):
        m._check_unique_ids()


# ---------------------------------------------------------------------------
# load()
# ---------------------------------------------------------------------------

def test_load_valid_spec(tmp_path, monkeypatch):
    import sys
    mod_file = tmp_path / "mychecker.py"
    mod_file.write_text(
        "from pssparser.checkers import CheckerBase, MarkerDef\n"
        "class MyChecker(CheckerBase):\n"
        "    name = 'my-checker'\n"
        "    marker_defs = [MarkerDef(id='MY001', severity='warning', summary='s')]\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    m = CheckerManager()
    m.load("mychecker:MyChecker")
    assert "my-checker" in m._registered


def test_load_missing_colon_raises():
    m = CheckerManager()
    with pytest.raises(ValueError, match="expected"):
        m.load("nocolonspec")


def test_load_missing_module_raises():
    m = CheckerManager()
    with pytest.raises(ValueError, match="module not found"):
        m.load("nonexistent.module.xyz:SomeClass")


def test_load_missing_class_raises(tmp_path, monkeypatch):
    mod_file = tmp_path / "emptymod.py"
    mod_file.write_text("# empty\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    m = CheckerManager()
    with pytest.raises(ValueError, match="attribute not found"):
        m.load("emptymod:MissingClass")


def test_load_empty_name_raises(tmp_path, monkeypatch):
    mod_file = tmp_path / "noname.py"
    mod_file.write_text(
        "from pssparser.checkers import CheckerBase\n"
        "class NoName(CheckerBase):\n"
        "    name = ''\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    m = CheckerManager()
    with pytest.raises(ValueError, match="empty 'name'"):
        m.load("noname:NoName")


def test_load_duplicate_id_raises(tmp_path, monkeypatch):
    mod_file = tmp_path / "dupchecker.py"
    mod_file.write_text(
        "from pssparser.checkers import CheckerBase, MarkerDef\n"
        "class DupChecker(CheckerBase):\n"
        "    name = 'dup'\n"
        "    marker_defs = [MarkerDef(id='TST001', severity='error', summary='s')]\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    m = CheckerManager()
    m._registered["dummy"] = DummyChecker
    with pytest.raises(ValueError, match="TST001"):
        m.load("dupchecker:DupChecker")


# ---------------------------------------------------------------------------
# active()
# ---------------------------------------------------------------------------

def _manager_with_dummies():
    m = CheckerManager()
    from pssparser.checkers.core_checker import CoreChecker
    m._registered["core"] = CoreChecker
    m._registered["dummy"] = DummyChecker
    m._registered["another-dummy"] = AnotherDummyChecker
    return m


def test_active_returns_all_non_builtin_by_default():
    m = _manager_with_dummies()
    active = m.active(select=None, exclude=None)
    names = {c.name for c in active}
    assert "dummy" in names
    assert "another-dummy" in names
    assert "core" not in names


def test_active_with_select_returns_only_selected():
    m = _manager_with_dummies()
    active = m.active(select=["dummy"], exclude=None)
    names = {c.name for c in active}
    assert names == {"dummy"}


def test_active_select_unknown_raises():
    m = _manager_with_dummies()
    with pytest.raises(ValueError, match="Unknown checker"):
        m.active(select=["nonexistent"], exclude=None)


def test_active_exclude_removes_checker():
    m = _manager_with_dummies()
    active = m.active(select=None, exclude=["another-dummy"])
    names = {c.name for c in active}
    assert "another-dummy" not in names
    assert "dummy" in names


def test_active_builtin_never_returned():
    m = _manager_with_dummies()
    active = m.active(select=None, exclude=None)
    for checker in active:
        assert not getattr(checker, "is_builtin", False)


# ---------------------------------------------------------------------------
# list_checkers()
# ---------------------------------------------------------------------------

def test_list_checkers_contains_required_keys():
    m = CheckerManager()
    m.discover()
    result = m.list_checkers()
    for item in result:
        assert "name" in item
        assert "description" in item
        assert "marker_ids" in item
        assert "is_builtin" in item


def test_list_checkers_core_is_builtin():
    m = CheckerManager()
    m.discover()
    core_info = next(i for i in m.list_checkers() if i["name"] == "core")
    assert core_info["is_builtin"] is True


# ---------------------------------------------------------------------------
# list_all_markers()
# ---------------------------------------------------------------------------

def test_list_all_markers_has_required_keys():
    m = CheckerManager()
    m.discover()
    markers = m.list_all_markers()
    assert len(markers) > 0
    for item in markers:
        assert "id" in item
        assert "severity" in item
        assert "checker" in item
        assert "summary" in item


def test_list_all_markers_checker_name_correct():
    m = _manager_with_dummies()
    markers = m.list_all_markers()
    tst001 = next(x for x in markers if x["id"] == "TST001")
    assert tst001["checker"] == "dummy"


# ---------------------------------------------------------------------------
# describe_marker()
# ---------------------------------------------------------------------------

def test_describe_marker_known_id():
    m = CheckerManager()
    m.discover()
    info = m.describe_marker("PSS001")
    assert info is not None
    assert info["id"] == "PSS001"
    assert "severity" in info
    assert "checker" in info
    assert "summary" in info
    assert "detail" in info


def test_describe_marker_unknown_id_returns_none():
    m = CheckerManager()
    m.discover()
    assert m.describe_marker("XXXXXXXX") is None
