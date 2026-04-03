"""
Tests for PSS access modifiers (LRM §20.4): public, protected, private.

Covers: per-field modifiers, modifier blocks, mixed modifiers in
structs and actions, linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_public_field(parser):
    """public modifier on a struct field"""
    code = """
struct s {
    public rand bit[8] x;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "x")

    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_protected_field(parser):
    """protected modifier on a struct field"""
    code = """
struct s {
    protected rand int y;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "y")


def test_private_field(parser):
    """private modifier on a struct field"""
    code = """
struct s {
    private string name;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "name")


def test_mixed_modifiers_in_action(parser):
    """Multiple access modifiers in an action"""
    code = """
component pss_top {
    action Secured {
        public rand int addr;
        protected rand int data;
        private int internal_state;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "Secured")
    assert action is not None
    for name in ("addr", "data", "internal_state"):
        assert has_symbol(action, name), f"field {name} not found"


def test_access_modifier_block(parser):
    """Access modifier block syntax: 'protected:' applies to following fields"""
    code = """
struct base_s {
    public:
        rand int visible;
    protected:
        rand int inherited_only;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "base_s")
    assert sym is not None
    assert has_symbol(sym, "visible")
    assert has_symbol(sym, "inherited_only")
