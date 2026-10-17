"""
A method of a string reached through a subscript (pssc 06-front-end-checks
F24): an element of an array of strings, `s[1].size()`, and a sub-string,
`u[0..1].size()` (8.6.3: the sub-string operator returns a string). These
were "cannot resolve 'size': the enclosing scope is unknown".
"""
import pytest

import pssparser

from ..test_helpers import _assign_codes


def errors(src):
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        ms = p.markers
    except Exception as e:
        ms = e.markers
    return [m["message"] for m in _assign_codes(ms) if m["severity"] == "error"]


MODEL = """component pss_top {
  struct p_s { array<string, 2> ss; }
  target function void run() {
    array<string, 2> s = {"a", "bc"}; p_s p; string u = "abc";
    %s
  }
}
"""


@pytest.mark.parametrize("stmt", [
    "int n = s[1].size();",
    "string t = s[0].upper();",
    "int m = p.ss[1].size();",
    'int k = u[0..1].size();',
    'int j = s[1][0..1].size();',
])
def test_a_string_element_has_string_methods(stmt):
    assert errors(MODEL % stmt) == []


def test_an_unknown_method_of_a_string_element():
    assert errors(MODEL % "int n = s[1].nosuch();") == [
        "unknown method 'nosuch' on built-in type"]


def test_an_int_element_still_has_no_methods():
    assert errors(MODEL % "array<int, 2> a; int n = a[0].size();") != []
