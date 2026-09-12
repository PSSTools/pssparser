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


# --- references (13.1.2): a generic constraint is referenced by name ---------
#
# Unlike a fixed constraint block, a generic constraint is *called*. That makes
# its name a symbol in the enclosing scope -- which it was not: the declaration
# linked clean while every reference to it failed with "unknown identifier",
# because GenericConstraintDeclBool derives from ConstraintBlock and so reached
# TaskBuildSymbolTree::visitConstraintBlock, which adds the node to the scope's
# children without naming it in the symtab.

def test_generic_constraint_reference_resolves():
    pss = """
    component pss_top {
        action A {
            rand int x;
            constraint lim_lt(int lim) { x < lim; }
            constraint c { lim_lt(20); }
        }
    }
    """
    assert_parse_ok(pss)


def test_zero_parameter_generic_constraint_reference_resolves():
    pss = """
    component pss_top {
        action A {
            rand int x;
            constraint g() { x < 20; }
            constraint c { g(); }
        }
    }
    """
    assert_parse_ok(pss)


def test_generic_constraint_may_reference_another():
    pss = """
    component pss_top {
        action A {
            rand int x;
            constraint inner(int lim) { x < lim; }
            constraint outer(int lim) { inner(lim); }
            constraint c { outer(20); }
        }
    }
    """
    assert_parse_ok(pss)


def test_package_scope_generic_constraint_is_a_package_member():
    pss = """
    package p {
        static constraint gt_zero(int v) { v > 0; }
    }
    component pss_top {
        action A {
            rand int x;
            constraint c { p::gt_zero(x); }
        }
    }
    """
    assert_parse_ok(pss)


def test_unknown_member_of_a_package_is_still_reported():
    """The control for the test above: a name that is not there must still fail,
    or "resolves" would only mean "resolution was skipped"."""
    pss = """
    package p {
        static constraint gt_zero(int v) { v > 0; }
    }
    component pss_top {
        action A {
            rand int x;
            constraint c { p::nope(x); }
        }
    }
    """
    assert_parse_error(pss, "has no member named 'nope'")


def test_too_many_arguments_to_a_generic_constraint_is_an_error():
    """A generic constraint has no IFunctionPrototype, so it needs its own arity
    check; without one the ordinary path rejects every reference as
    "'lim_lt' is not a function"."""
    pss = """
    component pss_top {
        action A {
            rand int x;
            constraint lim_lt(int lim) { x < lim; }
            constraint c { lim_lt(20, 30); }
        }
    }
    """
    assert_parse_error(pss, "too many arguments to constraint 'lim_lt'")


def test_too_few_arguments_to_a_generic_constraint_is_an_error():
    pss = """
    component pss_top {
        action A {
            rand int x;
            constraint lim_lt(int lim) { x < lim; }
            constraint c { lim_lt(); }
        }
    }
    """
    assert_parse_error(pss, "too few arguments to constraint 'lim_lt'")


def test_a_generic_constraint_may_not_share_a_name_with_a_field():
    """Now that the name is a symbol, a collision is a duplicate declaration --
    which it silently was not before."""
    pss = """
    component pss_top {
        action A {
            rand int lim_lt;
            constraint lim_lt(int lim) { lim_lt < lim; }
        }
    }
    """
    assert_parse_error(pss)
