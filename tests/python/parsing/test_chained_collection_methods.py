"""
A member chained on a collection method's result (LRM 7.9).

The path used to stop at the first collection method, so whatever followed it
was never resolved and the completeness check reported it as left unbound
(PSS042): ``l.to_list().size()``. Collection methods have no prototypes yet,
so what one returns is known by category (``TaskResolveRefs.cpp``,
``collectionMethodResult``): another collection of the same elements, one of
its elements -- typed by the collection's element parameter -- or something
with no members. String-method chains are in ``test_string_method_signatures``.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import assert_marker, assert_no_marker


def _model(body):
    return """
    struct s_s { int x; }
    component pss_top {
        list<int> l;
        list<s_s> ls;
        list<string> lstr;
        list<list<s_s>> ll;
        set<s_s> ss;
        map<int,s_s> m;
        array<s_s,4> a;
        exec init_up { %s }
    }
    """ % body


@pytest.mark.parametrize("expr", [
    "int n = l.to_list().size();",
    "int n = ls.to_set().to_list().size();",
    "int n = ls.front().x;",
    "int n = ls.to_list().back().x;",
    "int n = m.values().front().x;",
    "int n = a.to_list().pop_front().x;",
    "int n = ss.to_list().front().x;",
    "int n = ll.front().back().x;",
    "int n = lstr.front().upper().size();",
])
def test_a_member_of_a_collection_method_result(expr):
    assert_no_marker(_model(expr), severity="error")


def test_a_chained_method_is_name_checked():
    assert_marker(_model("int n = ls.to_list().nosuch();"), marker_id="PSS002",
                  text="unknown method 'nosuch' on built-in type")


def test_an_element_member_is_looked_up_in_the_element_type():
    assert_marker(_model("int n = ls.front().nosuch;"), marker_id="PSS002",
                  text="'front()' has no member named 'nosuch'")


@pytest.mark.parametrize("expr,method", [
    ("int n = l.size().x;", "size"),
    ("int n = l.front().x;", "front"),
])
def test_a_scalar_result_has_no_members(expr, method):
    assert_marker(_model(expr), marker_id="PSS004",
                  text="ref-path element %s is not a composite scope" % method)
