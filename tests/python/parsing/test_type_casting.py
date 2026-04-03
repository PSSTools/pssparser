"""
Tests for PSS type casting / conversion (LRM §7.12).

The grammar implements C-style cast syntax: (type)expr.
Covers: integer casts, bool casts, enum casts in exec blocks,
linkage, source locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_cast_to_int(parser):
    """Cast expression to int in exec block"""
    code = """
component pss_top {
    action A {
        rand bit[8] x;
        int result;
        exec post_solve {
            result = (int)(x);
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "x")
    assert has_symbol(action, "result")

    loc = get_location(action.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_cast_to_bool(parser):
    """Cast int to bool"""
    code = """
component pss_top {
    action A {
        rand int x;
        bool flag;
        exec post_solve {
            flag = (bool)(x);
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "flag")


def test_cast_to_bit(parser):
    """Cast int to bit[N]"""
    code = """
component pss_top {
    action A {
        rand int x;
        bit[8] narrow;
        exec post_solve {
            narrow = (bit[8])(x);
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "narrow")


def test_cast_in_expression(parser):
    """Cast used inside a larger expression"""
    code = """
component pss_top {
    action A {
        rand int x;
        int y;
        exec post_solve {
            y = (int)(x) + 1;
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "y")
