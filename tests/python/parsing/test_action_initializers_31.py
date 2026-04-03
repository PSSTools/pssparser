"""
Tests for PSS 3.1 action-handle declarations and traversal initializers.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error


def test_action_handle_single_initializer():
    pss = """
    component pss_top {
        action Inner {
            int x;
            int y;
        }

        action Outer {
            Inner a1 { .x = 1, .y = 2 };
        }
    }
    """
    assert_parse_ok(pss)


def test_action_handle_multidim_array():
    pss = """
    component pss_top {
        action Inner { }

        action Outer {
            Inner a2[4][2];
        }
    }
    """
    assert_parse_ok(pss)


def test_action_traversal_handle_initializer():
    pss = """
    component pss_top {
        action Inner {
            int x;
        }

        action Outer {
            Inner a1;

            activity {
                a1 { .x = 3 };
            }
        }
    }
    """
    assert_parse_ok(pss)


def test_action_traversal_type_initializer():
    pss = """
    component pss_top {
        action Inner {
            int x;
            int y;
        }

        action Outer {
            activity {
                do Inner { .x = 4, .y = 5 };
            }
        }
    }
    """
    assert_parse_ok(pss)


def test_action_traversal_handle_multisubscript_initializer():
    pss = """
    component pss_top {
        action Inner {
            int x;
        }

        action Outer {
            Inner a[2][3];

            activity {
                a[1][2] { .x = 9 };
            }
        }
    }
    """
    assert_parse_ok(pss)


def test_action_initializer_requires_dot():
    pss = """
    component pss_top {
        action Inner {
            int x;
        }

        action Outer {
            Inner a1 { x = 1 };
        }
    }
    """
    assert_parse_error(pss)
