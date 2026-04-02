"""
Tests for PSS static const fields (LRM §7.1, §8.2).

Covers: const field declaration syntax with initializers,
various scalar types, usage in structs/actions, linkage, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_static_const_int(parser):
    """static const int with initializer"""
    code = """
struct config_s {
    static const int MAX_SIZE = 256;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "config_s")
    assert sym is not None
    assert has_symbol(sym, "MAX_SIZE")

    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_static_const_bit(parser):
    """static const bit[N] with hex initializer"""
    code = """
struct masks_s {
    static const bit[8] MASK = 0xFF;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "masks_s")
    assert sym is not None
    assert has_symbol(sym, "MASK")


def test_static_const_string(parser):
    """static const string"""
    code = """
struct info_s {
    static const string VERSION = "1.0";
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "info_s")
    assert sym is not None
    assert has_symbol(sym, "VERSION")


def test_static_const_in_action(parser):
    """static const fields inside an action"""
    code = """
component pss_top {
    action Config {
        static const int BASE_ADDR = 0x1000;
        static const int RANGE = 0x100;
        rand int addr;
        constraint {
            addr >= BASE_ADDR;
            addr < BASE_ADDR + RANGE;
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "Config")
    assert action is not None
    assert has_symbol(action, "BASE_ADDR")
    assert has_symbol(action, "RANGE")
    assert has_symbol(action, "addr")


def test_static_const_bool(parser):
    """static const bool"""
    code = """
struct flags_s {
    static const bool ENABLED = true;
    static const bool DISABLED = false;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "flags_s")
    assert sym is not None
    assert has_symbol(sym, "ENABLED")
    assert has_symbol(sym, "DISABLED")
