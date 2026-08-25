"""
Tests for PSS typedef declarations (LRM §7.11).

Covers: basic typedef, typedef of sized types, typedef in package,
typedef in struct, typedef used as field type, linkage, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_typedef_basic_bit(parser):
    """Typedef aliasing a bit type"""
    code = """
typedef bit[32] word_t;
struct s {
    word_t data;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "data")


def test_typedef_int_sized(parser):
    """Typedef aliasing a sized int"""
    code = """
typedef int[16] short_t;
struct s {
    short_t value;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert has_symbol(sym, "value")


def test_typedef_string(parser):
    """Typedef aliasing string type"""
    code = """
typedef string name_t;
struct s {
    name_t label;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert has_symbol(sym, "label")


def test_typedef_bool(parser):
    """Typedef aliasing bool type"""
    code = """
typedef bool flag_t;
struct s {
    flag_t enabled;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert has_symbol(sym, "enabled")


def test_typedef_in_package(parser):
    """Typedef declared inside a package"""
    code = """
package my_pkg {
    typedef bit[8] byte_t;
    struct Data {
        byte_t payload;
    };
}
"""
    root = parse_pss(code, parser=parser)
    pkg = get_symbol(root, "my_pkg")
    assert pkg is not None
    assert has_symbol(pkg, "Data")


def test_typedef_in_component(parser):
    """Typedef declared inside a component"""
    code = """
component pss_top {
    typedef bit[32] addr_t;
    action MemAccess {
        addr_t address;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "MemAccess")
    assert action is not None
    assert has_symbol(action, "address")
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_typedef_in_struct(parser):
    """Typedef declared inside a struct"""
    code = """
struct container_s {
    typedef bit[16] element_t;
    element_t first;
    element_t second;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "container_s")
    assert sym is not None
    assert has_symbol(sym, "first")
    assert has_symbol(sym, "second")


def test_typedef_multiple(parser):
    """Multiple typedefs in same scope"""
    code = """
typedef bit[8] byte_t;
typedef bit[16] half_t;
typedef bit[32] word_t;
typedef bit[64] dword_t;
struct regs_s {
    byte_t ctrl;
    half_t status;
    word_t data;
    dword_t addr;
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "regs_s")
    assert sym is not None
    for name in ("ctrl", "status", "data", "addr"):
        assert has_symbol(sym, name), f"field {name} not found"


# ---------------------------------------------------------------------------
# PSS 3.1 alignment: the declared name is an `identifier` (plan item P1-G7)
# ---------------------------------------------------------------------------
# Annex B B.13 is `typedef_declaration ::= typedef data_type identifier ;`.
# The grammar previously used `type_identifier` for the declared name, which
# accepted a qualified name -- `typedef int a::b;` -- and then silently kept
# only the first element, so the typedef bound a name the source never wrote.

def test_typedef_qualified_name_rejected(parser):
    """A typedef declares a new name; it cannot name an existing scope."""
    from test_helpers import assert_parse_error
    assert_parse_error("package p { package q { } } typedef int p::q;")


def test_typedef_plain_name_still_accepted(parser):
    root = parse_pss("typedef int my_int; struct S { my_int a; }", parser=parser)
    assert get_symbol(root, "my_int") is not None


def test_typedef_name_binds_exactly_what_was_written(parser):
    """Guards the silent-truncation behaviour the old rule allowed."""
    root = parse_pss("typedef bit[8] byte_t; struct S { byte_t v; }", parser=parser)
    assert get_symbol(root, "byte_t") is not None
    sym = get_symbol(root, "S")
    assert has_symbol(sym, "v")
