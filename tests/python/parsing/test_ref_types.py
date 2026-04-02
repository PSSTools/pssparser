"""
Tests for PSS reference types (LRM §7.10).

Covers: ref declarations for actions, components, flow/resource objects;
linkage resolution of referenced types; source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_ref_action(parser):
    """ref field referencing an action type; verify linkage"""
    code = """
component pss_top {
    action Target { rand int x; }
    action User {
        ref Target t;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    user = get_symbol(comp, "User")
    assert user is not None
    assert has_symbol(user, "t")

    loc = get_location(user.getTarget())
    assert loc is not None
    assert loc[0] == 4


def test_ref_component(parser):
    """ref field referencing a component type"""
    code = """
component sub_c { }
component pss_top {
    ref sub_c child_ref;
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "child_ref")


def test_ref_buffer(parser):
    """ref field referencing a buffer type"""
    code = """
buffer data_b { int payload; };
component pss_top {
    action Producer {
        ref data_b buf_ref;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    prod = get_symbol(comp, "Producer")
    assert prod is not None
    assert has_symbol(prod, "buf_ref")


def test_ref_in_function_param(parser):
    """ref as function parameter"""
    code = """
component pss_top {
    action A { rand int x; }
    function void process(ref A a_ref);
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "pss_top") is not None


def test_ref_null_assign(parser):
    """ref compared to null in exec block"""
    code = """
component pss_top {
    action A { rand int x; }
    action B {
        ref A a_ref;
        int result;
        exec post_solve {
            if (a_ref == null) {
                result = 0;
            }
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    b = get_symbol(comp, "B")
    assert b is not None
    assert has_symbol(b, "a_ref")
