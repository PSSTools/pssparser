"""
Enum item values (TaskCheckOperands; pssc's front-end check F2, LRM 7.5.1).

- PSS134: two items with one value (e), across extensions too; a value
  outside the base type, an implicit value past its greatest (c); a base
  type with a domain.
- PSS135: a variable of an enum with no items (j).
"""
import pytest

import pssparser

from ..test_helpers import _assign_codes


def codes(src):
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        ms = p.markers
    except Exception as e:
        ms = getattr(e, "markers", None)
        if ms is None:
            raise
    return [(m["line"], m.get("code")) for m in _assign_codes(ms)]


@pytest.mark.parametrize("decl,line", [
    ("enum e_e { A = 1, B = 1 }", 1),                       # e
    ("enum e_e { A = 1 }\nextend enum e_e { C = 1 }", 2),   # e, across an extension
    ("enum e_e { A, B = 0 }", 1),                           # an implicit 0 and an explicit 0
    ("enum e_e { A = 5, B = 4, C }", 1),                    # C is implicitly 5
    ("enum f_e : bit[2] { A = 3, B }", 1),                  # c: past the greatest
    ("enum g_e : bit[4] { A = -1 }", 1),                    # c: negative, unsigned base
    ("enum g_e : bit[4] { A = 16 }", 1),                    # c: too wide
    ("enum g_e : int[4] { A = 8 }", 1),
    ("enum h_e : int in [1..10] { A = 1 }", 1),             # a base with a domain
    ("enum b_e : bit { A, B, C }", 1),                      # `bit` is one bit
])
def test_illegal_enum_values(decl, line):
    assert codes(decl + "\ncomponent pss_top { }\n") == [(line, "PSS134")]


@pytest.mark.parametrize("decl", [
    "enum e_e { A = 1, B = 2, C }",
    "enum e_e { A = 10, B = 0, C }",                        # not ascending (d)
    "enum e_e { A = -3, B }",                               # negative, no base (d)
    "enum f_e : bit[2] { A = 2, B }",
    "enum f_e : bit[2] { A = 3, B = 0 }",
    "enum g_e : int[4] { A = -8, B = 7 }",
    "enum e_e { A = 1 }\nextend enum e_e { C = 2, D }",
    "enum e_e { A, B = A + 1 }",                            # not folded: not judged
    "enum b_e : bit { A, B }",
    "enum c_e : bit[7:0] { A = 255 }",
])
def test_legal_enum_values(decl):
    assert codes(decl + "\ncomponent pss_top { }\n") == []


def test_a_variable_of_an_itemless_enum():
    assert codes("enum n_e { }\ncomponent pss_top { n_e v; }\n") == [(2, "PSS135")]


def test_a_local_of_an_itemless_enum():
    assert codes("enum n_e { }\ncomponent pss_top {\n"
                 "  target function void run() { n_e v; }\n}\n") == [(3, "PSS135")]


def test_an_itemless_enum_filled_by_an_extension():
    assert codes("enum n_e { }\nextend enum n_e { X }\n"
                 "component pss_top { n_e v; }\n") == []


def test_an_itemless_enum_with_no_variable():
    assert codes("enum n_e { }\ncomponent pss_top { }\n") == []
