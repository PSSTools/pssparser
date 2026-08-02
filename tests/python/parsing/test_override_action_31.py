"""
Tests for PSS 3.1 override action declarations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_parse_ok, assert_parse_error, get_symbol


def test_override_action_in_component():
    # LRM 19.2.2a: an action may be declared override only if a same-named
    # action is declared in a *base* component.  This test used to declare
    # `override action A` in a component with no base at all, which the parser
    # accepted only because overriding was a no-op.  The base is what makes
    # the input valid PSS; the declaration under test is unchanged.
    pss = """
    component B {
        action A { }
    }
    component C : B {
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
    # See the note above: `C` needs a base declaring `A` to be valid PSS.
    pss = """
    component B {
        action A { }
    }
    component C : B {
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
