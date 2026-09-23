"""Every name-bearing AST field is classified (symbol-resolution plan WS3.1).

``tests/python/baselines/reference-roles.yaml`` says, for each field that holds a name,
whether it is a reference that must be bound, a declaration, a piece of an
enclosing reference, or nothing the linker resolves.  This is what stops the
next reference field being added without anyone deciding who resolves it --
the way seventeen reference fields ended up with no slot for a binding (report
F §2.3).  The table's header describes the roles.
"""
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from refcov import load_schema  # noqa: E402

TABLE = ROOT / "tests" / "python" / "baselines" / "reference-roles.yaml"

NAME_TYPES = {
    "ExprId", "ExprHierarchicalId", "ExprMemberPathElem", "TypeIdentifier",
    "DataTypeUserDefined", "ExprRefPath", "ExprRefPathContext",
    "ExprRefPathStatic", "ExprRefPathStaticRooted", "ExprRefPathSuper",
    "ExprRefName",
}
# Types that can hold a binding: TypeIdentifier.target, ExprRefPath.target,
# ExprRefName.target, and DataTypeUserDefined through its TypeIdentifier.
BINDABLE_TYPES = {
    "TypeIdentifier", "DataTypeUserDefined", "ExprRefPath", "ExprRefPathContext",
    "ExprRefPathStatic", "ExprRefPathStaticRooted", "ExprRefPathSuper",
    "ExprRefName",
}
ROLES = {"ref", "decl", "part", "none"}


def _elem_type(t):
    m = re.match(r"^(?:list<)?\s*(?:UP|P|SP)<\s*(\w+)\s*>\s*>?$", (t or "").strip())
    return m.group(1) if m else (t or "").strip()


def _name_fields():
    """{"Class.field": element type} for every name-bearing field."""
    out = {}
    for cls, (_, _, fields) in load_schema().items():
        for fn, t, _ in fields:
            et = _elem_type(t)
            if et in NAME_TYPES or (et == "string" and re.search(r"name|path|id$", fn)):
                out["%s.%s" % (cls, fn)] = et
    return out


def _table():
    return yaml.safe_load(TABLE.read_text())


def test_every_name_bearing_field_is_classified():
    missing = sorted(set(_name_fields()) - set(_table()["roles"]))
    assert not missing, (
        "name-bearing AST fields with no role in "
        "tests/python/baselines/reference-roles.yaml -- decide whether each is a ref, "
        "decl, part or none:\n  " + "\n  ".join(missing))


def test_no_role_for_a_field_that_does_not_exist():
    stale = sorted(set(_table()["roles"]) - set(_name_fields()))
    assert not stale, ("tests/python/baselines/reference-roles.yaml names fields that "
                       "no longer exist:\n  " + "\n  ".join(stale))


def test_roles_are_known():
    bad = {k: v for k, v in _table()["roles"].items() if v not in ROLES}
    assert not bad, bad


def test_every_ref_can_hold_a_binding_or_is_tracked():
    """A `ref` field is bindable, or listed in `unbindable` with its fix."""
    fields = _name_fields()
    table = _table()
    unbindable = set(table.get("unbindable") or {})
    new = sorted(f for f, role in table["roles"].items()
                 if role == "ref" and fields.get(f) not in BINDABLE_TYPES
                 and f not in unbindable)
    assert not new, (
        "`ref` fields with no slot for a binding -- give them one (WS3.2), or "
        "track them under `unbindable`:\n  " + "\n  ".join(new))


def test_unbindable_list_is_not_stale():
    fields = _name_fields()
    table = _table()
    stale = sorted(f for f in (table.get("unbindable") or {})
                   if table["roles"].get(f) != "ref" or fields.get(f) in BINDABLE_TYPES)
    assert not stale, "`unbindable` entries that are bindable now, or not refs:\n  " \
        + "\n  ".join(stale)
