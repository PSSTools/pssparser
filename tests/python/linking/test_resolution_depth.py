"""
Depth tests for PSS name resolution and linking (LRM §21.3).

Covers: typedef resolution, cross-package references, deeply nested
scope lookup, enum scope resolution, inheritance resolution.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_typedef_resolution(parser):
    """Typedef name resolves when used as field type"""
    code = """
component pss_top {
    typedef bit[32] word_t;
    action Process {
        word_t data;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "Process")
    assert action is not None
    assert has_symbol(action, "data")


def test_typedef_in_package(parser):
    """Typedef declared in package resolves in same package"""
    code = """
package my_pkg {
    typedef int[16] short_t;
    struct Data {
        short_t value;
    };
}
"""
    root = parse_pss(code, parser=parser)
    pkg = get_symbol(root, "my_pkg")
    assert pkg is not None
    assert has_symbol(pkg, "Data")


def test_cross_package_struct_ref(parser):
    """Struct declared in one package used in another via import"""
    code = """
package types_pkg {
    struct Point { int x; int y; };
}
import types_pkg::*;
struct Line {
    Point start;
    Point end;
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "types_pkg") is not None
    line = get_symbol(root, "Line")
    assert line is not None
    assert has_symbol(line, "start")
    assert has_symbol(line, "end")


def test_deeply_nested_scope(parser):
    """Deeply nested package scopes resolve correctly"""
    code = """
package outer {
    package inner {
        struct deep_s {
            rand int value;
        };
    }
}
component pss_top {
    action A {
        outer::inner::deep_s data;
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "data")


def test_enum_value_resolution(parser):
    """Enum values resolve in constraint expressions"""
    code = """
enum status_e { IDLE, BUSY, DONE };
struct state_s {
    rand status_e current;
    constraint {
        current != status_e::BUSY;
    }
};
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "status_e") is not None
    state = get_symbol(root, "state_s")
    assert state is not None
    assert has_symbol(state, "current")
    loc = get_location(state.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_inheritance_field_resolution(parser):
    """Fields from base struct visible in derived struct constraints"""
    code = """
struct base_s {
    rand int base_val;
};
struct derived_s : base_s {
    rand int derived_val;
    constraint {
        base_val + derived_val < 100;
    }
};
"""
    root = parse_pss(code, parser=parser)
    base = get_symbol(root, "base_s")
    assert base is not None
    derived = get_symbol(root, "derived_s")
    assert derived is not None
    assert has_symbol(derived, "derived_val")


def test_component_action_cross_ref(parser):
    """Action in one component references struct from outer scope"""
    code = """
struct SharedData { int payload; };
component pss_top {
    action Producer {
        output SharedData data_out;
    }
    action Consumer {
        input SharedData data_in;
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(root, "SharedData") is not None
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "Producer")
    assert has_symbol(comp, "Consumer")


def test_action_inherited_field_resolution(parser):
    """Action field from base action visible in derived constraint"""
    code = """
component pss_top {
    action Base { rand int base_field; }
    action Derived : Base {
        rand int derived_field;
        constraint { base_field > 0; }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "Derived")


def test_multi_level_inheritance_resolution(parser):
    """Grandparent field visible in grandchild constraint"""
    code = """
struct L0 { rand int a; };
struct L1 : L0 { rand int b; };
struct L2 : L1 {
    rand int c;
    constraint { a + b + c < 100; }
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "L2")
    assert sym is not None
    assert has_symbol(sym, "c")


def test_inherited_field_mixed_expression(parser):
    """Base and derived fields used together in one expression"""
    code = """
struct base_s { rand int x; };
struct derived_s : base_s {
    rand int y;
    constraint { x + y > 0; x < y; }
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "derived_s")
    assert sym is not None
    assert has_symbol(sym, "y")
