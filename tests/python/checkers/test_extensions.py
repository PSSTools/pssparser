"""Tests for the ``pssparser.extensions`` entry point (X1-X4).

Discovery must never depend on what happens to be pip-installed in the
developer's environment, so every test here fakes the entry-point groups by
monkeypatching ``manager._entry_points``.  The two tests that need a *real*
installed distribution live in ``test_extension_install.py`` and are skipped
unless explicitly enabled.
"""
from __future__ import annotations

import io
import sys
import types
from typing import Optional

import pytest

from pssparser.checkers import (
    API_VERSION,
    CHECKER_GROUP,
    EXTENSION_GROUP,
    NO_EXTENSIONS_ENV,
    CheckerBase,
    CheckerManager,
    MarkerDef,
)
from pssparser.checkers import manager as manager_mod


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

class _FakeDist:
    def __init__(self, name: str, version: str) -> None:
        self.name = name
        self.version = version


class FakeEP:
    """Stand-in for ``importlib.metadata.EntryPoint``."""

    def __init__(
        self,
        name: str,
        obj,
        *,
        dist: Optional[str] = None,
        version: str = "",
        raises: Optional[Exception] = None,
    ) -> None:
        self.name = name
        self._obj = obj
        self._raises = raises
        self.dist = _FakeDist(dist, version) if dist else None

    def load(self):
        if self._raises is not None:
            raise self._raises
        return self._obj


@pytest.fixture
def eps(monkeypatch):
    """Install fake entry-point groups; yields a mutable {group: [ep]} dict."""
    groups = {EXTENSION_GROUP: [], CHECKER_GROUP: []}
    monkeypatch.setattr(
        manager_mod, "_entry_points", lambda group: list(groups.get(group, []))
    )
    monkeypatch.delenv(NO_EXTENSIONS_ENV, raising=False)
    return groups


def make_checker(name: str, marker_id: str, *, severity: str = "warning"):
    """Build a throwaway checker class with a single marker."""
    return type(
        f"Checker_{marker_id}",
        (CheckerBase,),
        {
            "name": name,
            "description": f"test checker {name}",
            "marker_defs": [
                MarkerDef(id=marker_id, severity=severity, summary=f"{marker_id} summary")
            ],
            "runs_without_link": True,
            "check": lambda self, context: None,
        },
    )


def make_module(name: str, **attrs) -> types.ModuleType:
    """Build a throwaway module object carrying *attrs*."""
    mod = types.ModuleType(name)
    for key, value in attrs.items():
        setattr(mod, key, value)
    return mod


def codes(manager: CheckerManager) -> list:
    return [d["code"] for d in manager.load_diagnostics]


def messages(manager: CheckerManager) -> str:
    return "\n".join(d["message"] for d in manager.load_diagnostics)


# ---------------------------------------------------------------------------
# X2 -- an extension contributing a collection
# ---------------------------------------------------------------------------

def test_extension_contributes_several_checkers(eps):
    a = make_checker("acme-naming", "ACM001")
    b = make_checker("acme-coverage", "ACM002")
    c = make_checker("acme-flow", "ACM003")

    def register(reg):
        reg.description = "Acme house rules"
        reg.add_checker(a)
        reg.add_checker(b)
        reg.add_checker(c)

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register),
               dist="acme-pss-rules", version="2.3.0")
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == []
    names = {info["name"] for info in m.list_checkers()}
    assert {"acme-naming", "acme-coverage", "acme-flow"} <= names

    active = {c.name for c in m.active(select=None, exclude=None)}
    assert {"acme-naming", "acme-coverage", "acme-flow"} <= active


def test_extension_metadata_is_reported(eps):
    def register(reg):
        reg.description = "Acme house rules"
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register),
               dist="acme-pss-rules", version="2.3.0")
    ]

    m = CheckerManager()
    m.discover()

    info = m.list_extensions()[0]
    assert info["name"] == "acme-rules"
    assert info["version"] == "2.3.0"
    assert info["dist"] == "acme-pss-rules"
    assert info["description"] == "Acme house rules"
    assert info["checkers"] == ["acme-naming"]
    assert info["legacy"] is False


def test_provenance_records_the_contributing_extension(eps):
    def register(reg):
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    m = CheckerManager()
    m.discover()
    assert m.extension_of("acme-naming") == "acme-rules"


def test_checkers_shorthand_is_equivalent_to_register(eps):
    mod = make_module(
        "acme_rules",
        CHECKERS=[make_checker("acme-naming", "ACM001"),
                  make_checker("acme-coverage", "ACM002")],
    )
    eps[EXTENSION_GROUP] = [FakeEP("acme-rules", mod)]

    m = CheckerManager()
    m.discover()

    assert codes(m) == []
    assert m.list_extensions()[0]["checkers"] == ["acme-naming", "acme-coverage"]


def test_entry_point_may_name_the_register_callable_directly(eps):
    def register(reg):
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    # The `module:attr` entry-point form makes ep.load() return the function.
    eps[EXTENSION_GROUP] = [FakeEP("acme-rules", register)]

    m = CheckerManager()
    m.discover()
    assert codes(m) == []
    assert m.extension_of("acme-naming") == "acme-rules"


# ---------------------------------------------------------------------------
# X3 -- API versioning
# ---------------------------------------------------------------------------

def test_register_sees_the_real_api_version(eps):
    seen = {}

    def register(reg):
        seen["api"] = reg.api_version
        seen["name"] = reg.name
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    CheckerManager().discover()
    assert seen["api"] == API_VERSION
    assert seen["name"] == "acme-rules"


def test_requires_api_too_new_is_refused_with_pss032(eps):
    def register(reg):
        reg.requires_api = API_VERSION + 98
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register),
               dist="acme-pss-rules")
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS032"]
    assert "acme-naming" not in m._registered
    assert m.list_extensions() == []
    # Refusal is not a crash: core is still usable.
    assert "core" in m._registered


def test_module_level_requires_api_refuses_before_register_runs(eps):
    ran = {"register": False}

    def register(reg):
        ran["register"] = True
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    mod = make_module("acme_rules", register=register, REQUIRES_API=API_VERSION + 1)
    eps[EXTENSION_GROUP] = [FakeEP("acme-rules", mod)]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS032"]
    assert ran["register"] is False


def test_api_version_probing_can_register_conditionally(eps):
    def register(reg):
        reg.add_checker(make_checker("acme-stable", "ACM001"))
        if reg.api_version >= API_VERSION + 1:
            reg.add_checker(make_checker("acme-future", "ACM002"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    m = CheckerManager()
    m.discover()
    assert m.list_extensions()[0]["checkers"] == ["acme-stable"]


# ---------------------------------------------------------------------------
# X4 -- failure isolation
# ---------------------------------------------------------------------------

def test_import_failure_is_pss030_and_does_not_abort(eps):
    def good(reg):
        reg.add_checker(make_checker("good-checker", "GOO001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("aaa-broken", None, dist="broken-dist",
               raises=ImportError("no module named 'nope'")),
        FakeEP("zzz-good", make_module("good", register=good)),
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS030"]
    assert "broken-dist" in messages(m)
    # The healthy extension still loaded.
    assert "good-checker" in m._registered


def test_register_raising_is_pss030_and_does_not_abort(eps):
    def boom(reg):
        raise RuntimeError("kaboom")

    def good(reg):
        reg.add_checker(make_checker("good-checker", "GOO001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("aaa-boom", make_module("boom", register=boom)),
        FakeEP("zzz-good", make_module("good", register=good)),
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS030"]
    assert "kaboom" in messages(m)
    assert "good-checker" in m._registered


def test_module_without_register_or_checkers_is_pss030(eps):
    eps[EXTENSION_GROUP] = [FakeEP("acme-rules", make_module("acme_rules"))]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS030"]
    # The message must name the missing contract, not just "failed".
    assert "register" in messages(m)
    assert "CHECKERS" in messages(m)


def test_add_checker_misuse_is_reported_not_raised(eps):
    def register(reg):
        reg.add_checker("not a class")

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    m = CheckerManager()
    m.discover()
    assert codes(m) == ["PSS030"]
    assert "CheckerBase subclass" in messages(m)


def test_duplicate_marker_id_is_pss033_naming_both_extensions(eps):
    def first(reg):
        reg.add_checker(make_checker("first-checker", "DUP001"))

    def second(reg):
        reg.add_checker(make_checker("second-checker", "DUP001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("aaa-first", make_module("first", register=first)),
        FakeEP("zzz-second", make_module("second", register=second)),
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS033"]
    text = messages(m)
    assert "aaa-first" in text and "zzz-second" in text
    assert "DUP001" in text
    # The winner keeps its registration; only the loser is dropped.
    assert "first-checker" in m._registered
    assert "second-checker" not in m._registered


def test_duplicate_with_a_core_id_is_rejected(eps):
    def register(reg):
        reg.add_checker(make_checker("squatter", "PSS001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    m = CheckerManager()
    m.discover()

    assert codes(m) == ["PSS033"]
    assert "squatter" not in m._registered


def test_a_collision_costs_only_the_colliding_checker(eps):
    def first(reg):
        reg.add_checker(make_checker("first-checker", "DUP001"))

    def second(reg):
        reg.add_checker(make_checker("second-checker", "DUP001"))
        reg.add_checker(make_checker("innocent-checker", "INN001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("aaa-first", make_module("first", register=first)),
        FakeEP("zzz-second", make_module("second", register=second)),
    ]

    m = CheckerManager()
    m.discover()

    assert "innocent-checker" in m._registered
    assert m.list_extensions()[1]["checkers"] == ["innocent-checker"]


def test_extensions_load_in_sorted_order(eps):
    order = []

    def make_register(tag, marker_id):
        def register(reg):
            order.append(tag)
            reg.add_checker(make_checker(f"checker-{tag}", marker_id))
        return register

    # Registered out of order on purpose.
    eps[EXTENSION_GROUP] = [
        FakeEP("zebra", make_module("z", register=make_register("zebra", "ZEB001"))),
        FakeEP("alpha", make_module("a", register=make_register("alpha", "ALP001"))),
        FakeEP("mike", make_module("m", register=make_register("mike", "MIK001"))),
    ]

    m = CheckerManager()
    m.discover()
    assert order == ["alpha", "mike", "zebra"]


def test_sorted_order_decides_which_side_of_a_collision_loses(eps):
    def make_register(name, marker_id):
        def register(reg):
            reg.add_checker(make_checker(name, marker_id))
        return register

    eps[EXTENSION_GROUP] = [
        FakeEP("zebra", make_module("z", register=make_register("z-checker", "DUP001"))),
        FakeEP("alpha", make_module("a", register=make_register("a-checker", "DUP001"))),
    ]

    m = CheckerManager()
    m.discover()
    # 'alpha' sorts first, so it wins regardless of metadata order.
    assert "a-checker" in m._registered
    assert "z-checker" not in m._registered


# ---------------------------------------------------------------------------
# X4 -- the escape hatch
# ---------------------------------------------------------------------------

def test_no_extensions_argument_loads_core_only(eps):
    def register(reg):
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]

    m = CheckerManager()
    m.discover(load_extensions=False)

    assert list(m._registered) == ["core"]
    assert m.list_extensions() == []
    assert codes(m) == []


def test_no_extensions_env_var_loads_core_only(eps, monkeypatch):
    def register(reg):
        reg.add_checker(make_checker("acme-naming", "ACM001"))

    eps[EXTENSION_GROUP] = [
        FakeEP("acme-rules", make_module("acme_rules", register=register))
    ]
    monkeypatch.setenv(NO_EXTENSIONS_ENV, "1")

    m = CheckerManager()
    m.discover()
    assert list(m._registered) == ["core"]


def test_broken_entry_point_metadata_degrades_to_no_extensions(monkeypatch):
    """A malformed environment must degrade, not produce a traceback.

    Entry-point enumeration reads installed metadata that can be corrupt for
    reasons having nothing to do with pssparser; the linter still has to run.
    """
    def explode(**kwargs):
        raise ValueError("corrupt metadata")

    monkeypatch.setattr("importlib.metadata.entry_points", explode)
    monkeypatch.delenv(NO_EXTENSIONS_ENV, raising=False)

    assert manager_mod._entry_points(EXTENSION_GROUP) == []

    m = CheckerManager()
    m.discover()  # must not raise
    assert list(m._registered) == ["core"]


# ---------------------------------------------------------------------------
# X1 -- the entry-point key is not authoritative
# ---------------------------------------------------------------------------

def test_legacy_entry_point_still_loads(eps):
    cls = make_checker("legacy-checker", "LEG001")
    eps[CHECKER_GROUP] = [FakeEP("legacy-checker", cls, dist="legacy-dist")]

    m = CheckerManager()
    m.discover()

    assert codes(m) == []
    assert "legacy-checker" in m._registered
    info = m.list_extensions()[0]
    assert info["legacy"] is True
    assert info["checkers"] == ["legacy-checker"]


def test_key_mismatch_registers_under_the_declared_name(eps):
    cls = make_checker("naming-convention", "PSC001")
    eps[CHECKER_GROUP] = [FakeEP("naming", cls)]

    m = CheckerManager()
    m.discover()

    assert "naming-convention" in m._registered
    assert "naming" not in m._registered
    assert codes(m) == ["PSS031"]
    text = messages(m)
    assert "naming" in text and "naming-convention" in text


def test_key_mismatch_does_not_prevent_the_checker_running(eps):
    cls = make_checker("naming-convention", "PSC001")
    eps[CHECKER_GROUP] = [FakeEP("naming", cls)]

    m = CheckerManager()
    m.discover()
    active = {c.name for c in m.active(select=["naming-convention"], exclude=None)}
    assert active == {"naming-convention"}


def test_discover_then_load_checker_of_the_same_class_is_not_a_duplicate(eps, tmp_path, monkeypatch):
    """The CK-X1 crash: installed + --load-checker used to register twice."""
    mod_file = tmp_path / "dualchk.py"
    mod_file.write_text(
        "from pssparser.checkers import CheckerBase, MarkerDef\n"
        "class DualChecker(CheckerBase):\n"
        "    name = 'dual'\n"
        "    marker_defs = [MarkerDef(id='DUA001', severity='warning', summary='s')]\n"
        "    def check(self, context): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    import dualchk  # noqa: F401  (import through the same path the manager uses)

    eps[CHECKER_GROUP] = [FakeEP("dual", dualchk.DualChecker)]

    m = CheckerManager()
    m.discover()
    # Must not raise "Duplicate MarkerDef ID 'DUA001'".
    m.load("dualchk:DualChecker")
    assert m._registered["dual"] is dualchk.DualChecker


def test_legacy_entry_point_with_empty_name_is_pss030(eps):
    cls = type(
        "Nameless",
        (CheckerBase,),
        {"name": "", "marker_defs": [], "check": lambda self, ctx: None},
    )
    eps[CHECKER_GROUP] = [FakeEP("nameless", cls)]

    m = CheckerManager()
    m.discover()
    assert codes(m) == ["PSS030"]
    assert "empty 'name'" in messages(m)


# ---------------------------------------------------------------------------
# load_diagnostics shape
# ---------------------------------------------------------------------------

def test_load_diagnostics_carry_the_no_file_pseudo_path(eps):
    from pssparser.checkers import NO_FILE

    eps[EXTENSION_GROUP] = [FakeEP("acme-rules", make_module("acme_rules"))]
    m = CheckerManager()
    m.discover()

    diag = m.load_diagnostics[0]
    assert diag["file"] == NO_FILE
    assert diag["code"] == "PSS030"
    assert diag["message"].startswith("[PSS030] ")
    assert diag["severity"] == "warning"


# ---------------------------------------------------------------------------
# [extensions.<name>] enabled = false
# ---------------------------------------------------------------------------

def _two_checker_extension(eps, ext_name="acme"):
    a = make_checker("acme-a", "ACM001")
    b = make_checker("acme-b", "ACM002")

    def register(reg):
        reg.add_checker(a)
        reg.add_checker(b)

    eps[EXTENSION_GROUP].append(
        FakeEP(ext_name, make_module("acme_rules", register=register),
               dist="acme-rules", version="1.0")
    )
    m = CheckerManager()
    m.discover()
    return m


def test_disable_extension_removes_all_its_checkers(eps):
    m = _two_checker_extension(eps)
    assert {"acme-a", "acme-b"} <= set(m.registered)

    removed = m.disable_extension("acme")

    assert sorted(removed) == ["acme-a", "acme-b"]
    assert "acme-a" not in m.registered
    assert "acme-b" not in m.registered


def test_disable_extension_leaves_core_alone(eps):
    m = _two_checker_extension(eps)
    m.disable_extension("acme")
    assert "core" in m.registered


def test_a_disabled_extension_is_absent_from_list_checkers(eps):
    """Removing the checkers, rather than filtering them at selection time,
    is what makes `enabled = false` visible everywhere.

    A disabled extension's checker is genuinely unavailable, so asking for
    it by name should fail exactly the way asking for an uninstalled one
    does -- which is only true if it left the registry.
    """
    m = _two_checker_extension(eps)
    m.disable_extension("acme")
    assert "acme-a" not in [c["name"] for c in m.list_checkers()]
    with pytest.raises(ValueError, match="Unknown checker"):
        m.active(select=["acme-a"], exclude=None)


def test_disabling_releases_the_marker_ids(eps):
    """Otherwise a disabled extension keeps reserving IDs it no longer
    contributes, and a replacement extension collides with a ghost."""
    m = _two_checker_extension(eps)
    m.disable_extension("acme")
    assert "ACM001" not in [mk["id"] for mk in m.list_all_markers()]

    replacement = make_checker("other-a", "ACM001")
    assert m._accept_checker(replacement, "other", None) is True


def test_disabling_an_unknown_extension_is_a_no_op(eps):
    m = _two_checker_extension(eps)
    before = set(m.registered)
    assert m.disable_extension("not-installed") == []
    assert set(m.registered) == before


def test_disable_extension_updates_list_extensions(eps):
    m = _two_checker_extension(eps)
    m.disable_extension("acme")
    info = next(e for e in m.list_extensions() if e["name"] == "acme")
    assert info["checkers"] == []
