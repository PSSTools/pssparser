"""
Tests for PSS exec block variants (LRM §22.1).

Covers: exec body, exec pre_solve, exec post_solve, exec init_up,
exec init_down, linkage, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_exec_body(parser):
    """exec body block"""
    code = """
component pss_top {
    action A {
        rand int x;
        int result;
        exec body {
            result = x * 2;
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert action is not None
    assert has_symbol(action, "x")
    assert has_symbol(action, "result")
    loc = get_location(action.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_exec_pre_solve(parser):
    """exec pre_solve block"""
    code = """
component pss_top {
    action A {
        rand int x;
        exec pre_solve {
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")


def test_exec_post_solve(parser):
    """exec post_solve block"""
    code = """
component pss_top {
    action A {
        rand int x;
        int result;
        exec post_solve {
            result = x + 1;
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    action = get_symbol(comp, "A")
    assert has_symbol(action, "result")


def test_exec_init_down(parser):
    """exec init_down block"""
    code = """
component pss_top {
    action A {
        exec init_down {
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")


def test_exec_init_up(parser):
    """exec init_up block"""
    code = """
component pss_top {
    action A {
        exec init_up {
        }
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "A")
