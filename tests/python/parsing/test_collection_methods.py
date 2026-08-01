"""
Tests for PSS collection methods (LRM §7.9.2–7.9.5).

Covers: list, array, set, map method calls in exec blocks,
including size, push_back, clear, contains, sort, keys, etc.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import (parse_pss, get_symbol, has_symbol, get_location,
                          assert_parse_ok, assert_parse_error)


def test_list_size(parser):
    """list.size() method"""
    code = """
component pss_top {
    action A {
        list<int> items;
        int n;
        exec post_solve { n = items.size(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    action = get_symbol(get_symbol(root, "pss_top"), "A")
    assert has_symbol(action, "items")
    assert has_symbol(action, "n")
    loc = get_location(action.getTarget())
    assert loc is not None
    assert loc[0] == 3


def test_list_push_back(parser):
    """list.push_back() method"""
    code = """
component pss_top {
    action A {
        list<int> items;
        exec post_solve { items.push_back(42); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_list_clear(parser):
    """list.clear() method"""
    code = """
component pss_top {
    action A {
        list<int> items;
        exec post_solve { items.clear(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_list_sort(parser):
    """list.sort() method"""
    code = """
component pss_top {
    action A {
        list<int> items;
        exec post_solve { items.sort(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_array_size(parser):
    """array.size() method"""
    code = """
component pss_top {
    action A {
        int data[10];
        int n;
        exec post_solve { n = data.size(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_set_insert(parser):
    """set.insert() method"""
    code = """
component pss_top {
    action A {
        set<int> ids;
        exec post_solve { ids.insert(1); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_set_contains(parser):
    """set.contains() method"""
    code = """
component pss_top {
    action A {
        set<int> ids;
        bool r;
        exec post_solve { r = ids.contains(5); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_map_keys(parser):
    """map.keys() method"""
    code = """
component pss_top {
    action A {
        map<string, int> config;
        exec post_solve { config.keys(); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


def test_map_contains(parser):
    """map.contains() method"""
    code = """
component pss_top {
    action A {
        map<string, int> config;
        bool r;
        exec post_solve { r = config.contains("key"); }
    }
}
"""
    root = parse_pss(code, parser=parser)
    assert get_symbol(get_symbol(root, "pss_top"), "A") is not None


# ============================================================================
# Methods that were missing from the built-in whitelist
# ============================================================================
#
# The accepted method names are a hardcoded list in TaskResolveRefs.cpp, not
# declarations in the standard library. It was duplicated at two call sites
# and had drifted from the LRM: `size()` resolved while `sum()` did not,
# on fields and on parameters alike.

def test_array_sum_on_field(parser):
    """LRM 7.9.2.2: sum() returns the total of a numeric array."""
    assert_parse_ok("""
    component pss_top {
        action A {
            array<int,3> a;
            int n;
            exec post_solve { n = a.sum(); }
        }
    }
    """, parser)


def test_array_sum_on_parameter(parser):
    """The same call with the array arriving as a function parameter."""
    assert_parse_ok("""
    package p { function int f(array<int,3> a) { return a.sum(); } }
    component pss_top { }
    """, parser)


def test_array_to_list(parser):
    """LRM 7.9.2.2: to_list()."""
    assert_parse_ok("""
    package p { function void f(array<int,3> a) { list<int> l = a.to_list(); } }
    component pss_top { }
    """, parser)


def test_array_to_set(parser):
    """LRM 7.9.2.2: to_set()."""
    assert_parse_ok("""
    package p { function void f(array<int,3> a) { set<int> s = a.to_set(); } }
    component pss_top { }
    """, parser)


def test_array_size_still_resolves(parser):
    """Control: size() was already accepted and must stay accepted."""
    assert_parse_ok("""
    component pss_top {
        action A {
            array<int,3> a;
            int n;
            exec post_solve { n = a.size(); }
        }
    }
    """, parser)


def test_unknown_collection_method_is_still_rejected(parser):
    """Widening the list must not turn it into "accept anything"."""
    assert_parse_error("""
    component pss_top {
        action A {
            array<int,3> a;
            int n;
            exec post_solve { n = a.no_such_method(); }
        }
    }
    """)
