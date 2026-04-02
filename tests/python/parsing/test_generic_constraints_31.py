"""
Tests for PSS 3.1 generic constraint declarations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol


def test_generic_constraint_bool_in_package():
    pss = """
    static constraint gt_zero(numeric x) {
        x > 0;
    }
    """
    root = assert_parse_ok(pss)
    assert root is not None


def test_generic_constraint_bool_in_action():
    pss = """
    component pss_top {
        action A {
            constraint in_range(int x, const int y) {
                x < y;
            }
        }
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "pss_top")
    assert comp is not None


def test_generic_constraint_value_numeric():
    pss = """
    component pss_top {
        action A {
            static constraint numeric plus1(numeric x) x + 1;
        }
    }
    """
    assert_parse_ok(pss)


def test_generic_constraint_value_typed():
    pss = """
    component pss_top {
        struct S {
            constraint int clamp(int x, int y) x + y;
        }
    }
    """
    assert_parse_ok(pss)


def test_generic_constraint_missing_params_is_error():
    pss = """
    constraint bad numeric x) {
        x > 0;
    }
    """
    assert_parse_error(pss)
