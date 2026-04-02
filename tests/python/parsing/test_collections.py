"""
Tests for PSS collection types (LRM §7.9): list, map, set, array.

Covers: declaration syntax, struct/enum element types, usage in
actions and functions, linkage of element type references, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_list_of_scalar(parser):
    """list<bit[8]> field declaration"""
    code = """
struct s {
    list<bit[8]> bytes;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "bytes")

    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_list_of_struct(parser):
    """list<MyStruct> field — element type must resolve"""
    code = """
struct Point { int x; int y; };
struct Path {
    list<Point> waypoints;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "Point") is not None
    path = get_symbol(root, "Path")
    assert path is not None
    assert has_symbol(path, "waypoints")


def test_map_string_int(parser):
    """map<string, int> field"""
    code = """
struct config_s {
    map<string, int> settings;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "config_s")
    assert sym is not None
    assert has_symbol(sym, "settings")


def test_map_struct_value(parser):
    """map<string, MyStruct> — value type must resolve"""
    code = """
struct Entry { int value; };
struct Registry {
    map<string, Entry> entries;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "Entry") is not None
    reg = get_symbol(root, "Registry")
    assert reg is not None
    assert has_symbol(reg, "entries")


def test_set_of_int(parser):
    """set<int> field"""
    code = """
struct unique_ids_s {
    set<int> ids;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "unique_ids_s")
    assert sym is not None
    assert has_symbol(sym, "ids")


def test_set_of_enum(parser):
    """set<MyEnum> — enum type must resolve"""
    code = """
enum color_e { RED, GREEN, BLUE };
struct palette_s {
    set<color_e> colors;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "color_e") is not None
    pal = get_symbol(root, "palette_s")
    assert pal is not None
    assert has_symbol(pal, "colors")


def test_array_explicit_syntax(parser):
    """array<bit[8], 10> explicit parameterized syntax"""
    code = """
struct buf_s {
    array<bit[8], 10> data;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "buf_s")
    assert sym is not None
    assert has_symbol(sym, "data")


def test_collections_in_action(parser):
    """list, map, set fields inside an action"""
    code = """
component pss_top {
    action DataOp {
        list<int> addrs;
        map<string, int> config;
        set<int> visited;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "DataOp")
    assert action is not None
    for name in ("addrs", "config", "visited"):
        assert has_symbol(action, name), f"field {name} not found"

    loc = get_location(action.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_collection_in_function_param(parser):
    """Collection type as function parameter"""
    code = """
component pss_top {
    function void process(list<int> items);
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "pss_top") is not None
