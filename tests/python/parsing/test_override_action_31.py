"""
Tests for PSS 3.1 override action declarations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol


def test_override_action_in_component():
    pss = """
    component C {
        override action A {
            activity {
            }
        }
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "C")
    assert comp is not None


def test_override_action_with_fields_and_constraints():
    pss = """
    component C {
        override action A {
            rand int x;
            constraint {
                x > 0;
            }
        }
    }
    """
    root = assert_parse_ok(pss)
    comp = get_symbol(root, "C")
    assert comp is not None


def test_override_action_not_valid_at_package_scope():
    pss = """
    override action A {
    }
    """
    assert_parse_error(pss)
