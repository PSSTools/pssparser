"""
Tests for PSS address space group (LRM §24.9, new in PSS 3.0).

Covers: addr_space_group_c declaration, add_addr_space() calls,
multiple groups, linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_addr_space_group_basic(parser):
    """Basic addr_space_group_c instantiation"""
    code = """
import addr_reg_pkg::*;
component my_system {
    addr_space_group_c mem_group;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "my_system")
    assert comp is not None
    assert has_symbol(comp, "mem_group")
    loc = get_location(comp.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_addr_space_group_add_spaces(parser):
    """addr_space_group_c with add_addr_space() in exec init_down"""
    code = """
import addr_reg_pkg::*;
component my_system {
    contiguous_addr_space_c<> mema;
    contiguous_addr_space_c<> memb;
    addr_space_group_c mem_group;
    exec init_down {
        mem_group.add_addr_space(mema);
        mem_group.add_addr_space(memb);
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "my_system")
    assert comp is not None
    assert has_symbol(comp, "mema")
    assert has_symbol(comp, "memb")
    assert has_symbol(comp, "mem_group")


def test_addr_space_group_multiple(parser):
    """Multiple addr_space_group_c instances"""
    code = """
import addr_reg_pkg::*;
component my_system {
    contiguous_addr_space_c<> mem1;
    contiguous_addr_space_c<> mem2;
    contiguous_addr_space_c<> mem3;
    addr_space_group_c group_a;
    addr_space_group_c group_b;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "my_system")
    assert comp is not None
    assert has_symbol(comp, "group_a")
    assert has_symbol(comp, "group_b")
