"""
Depth tests for PSS constraint features (LRM §16).

Covers: dist directives, unique constraints, default constraints,
scheduling constraints, constraint in various contexts, linkage, locations.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import parse_pss, get_symbol, has_symbol, get_location


def test_dist_directive(parser):
    """Distribution constraint with weighted values"""
    code = """
struct s {
    rand int x;
    constraint { dist x in [1 [:= 10], 2 [:= 20], 3 [:= 70]]; }
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert sym is not None
    assert has_symbol(sym, "x")
    loc = get_location(sym.getTarget())
    assert loc is not None
    assert loc[0] == 2


def test_dist_range_weights(parser):
    """Distribution constraint with range and proportional weight"""
    code = """
struct s {
    rand int x;
    constraint { dist x in [0..9 [:/ 1], 10..99 [:/ 2], 100..999 [:/ 7]]; }
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert has_symbol(sym, "x")


def test_unique_constraint(parser):
    """Unique constraint on array"""
    code = """
struct s {
    rand int arr[4];
    constraint { unique {arr}; }
};
"""
    root = parse_pss(code, parser=parser)
    sym = get_symbol(root, "s")
    assert has_symbol(sym, "arr")


def test_scheduling_constraint_parallel(parser):
    """Scheduling constraint with parallel keyword in action body"""
    code = """
component pss_top {
    action A { }
    action B { }
    action Top {
        A a;
        B b;
        constraint parallel { a, b };
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert has_symbol(comp, "Top")


def test_scheduling_constraint_sequence(parser):
    """Scheduling constraint with sequence keyword in action body"""
    code = """
component pss_top {
    action A { }
    action B { }
    action Top {
        A a;
        B b;
        constraint sequence { a, b };
    }
}
"""
    root = parse_pss(code, parser=parser)
    comp = get_symbol(root, "pss_top")
    assert has_symbol(comp, "Top")
