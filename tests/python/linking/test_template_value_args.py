"""A name given for a template value parameter (symbol-resolution plan 8.4, PF-A1).

`template_param_value` is `data_type | constant_expression`, and a bare name is
both, so `S<X>` always parses as a type. Which it is depends on the parameter
it is given for. For a value parameter the name is looked up as a value:

- the argument initializes the parameter, so the parameter's type is its
  expected type (8.4.3), and step a of 18.3 searches that enum's items first;
- otherwise the ordinary lookup, where an enum item found only as the fallback
  warns (PSS046), as in any other expression (8.2);
- a miss is an unknown *identifier* (PSS002), not an unknown type;
- a type is reported (PSS047).

A name given for a type parameter is unchanged: a miss is an unknown type.
"""
import pytest

import pssparser
from pssparser import refs

from ..test_helpers import parse_collect, parse_pss
from ..template_helpers import assert_specialization_count


def markers(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["message"]) for m in ms]


def located(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["line"], m["col"], m["message"]) for m in ms]


def bindings(code, name):
    """(line of use, kind of declaration, line of declaration) for each use
    of `name`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.line, type(o.decl).__name__.lstrip("I"),
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text == name and not o.is_declaration]


# ---------------------------------------------------------------------------
# A name that resolves to nothing
# ---------------------------------------------------------------------------


def test_an_undefined_name_is_an_unknown_identifier():
    """The PF-A1 repro. It used to say "unknown type 'no_such_thing'"."""
    code = """\
package p {
  struct S <int M = 1> { int x; }
  component c { S<no_such_thing> a; }
}
"""
    assert located(code) == [
        ("error", 3, 19, "unknown identifier 'no_such_thing'")]


def test_the_suggestion_prefers_the_enclosing_scope():
    """A value is usually a constant of the enclosing scope; the global `N`
    is as close to `Kx` by spelling as the local `K` is not."""
    code = """\
struct N <int W = 1> { rand bit[W] x; }
component pss_top {
  static const int K = 4;
  N<Kx> f;
}
"""
    assert markers(code) == [
        ("error", "unknown identifier 'Kx'; did you mean 'K'?")]


def test_a_qualified_miss_is_an_unknown_identifier_reported_once():
    """A super type is resolved twice; the miss is reported once."""
    code = """\
package q { const int K = 1; }
struct N <int W = 1> { rand bit[W] x; }
struct D : N<q::KK> { }
"""
    assert markers(code) == [("error", "unknown identifier 'KK' in 'q'")]


def test_a_type_parameter_miss_is_still_an_unknown_type():
    code = """\
struct T <type U> { U u; }
component pss_top { T<no_such_type> t; }
"""
    assert markers(code) == [("error", "unknown type 'no_such_type'")]


# ---------------------------------------------------------------------------
# A name that resolves to a value
# ---------------------------------------------------------------------------


def test_a_package_constant():
    code = """\
package p { const int K = 4; }
struct N <int W = 1> { rand bit[W] x; }
component pss_top { N<p::K> a; }
"""
    assert markers(code) == []


def test_a_constant_of_the_enclosing_scope():
    code = """\
struct N <int W = 1> { rand bit[W] x; }
component pss_top {
  static const int K = 4;
  N<K> a;
}
"""
    assert markers(code) == []
    assert bindings(code, "K") == [(4, "Field", 3)]


def test_an_enclosing_value_parameter():
    code = """\
struct N <int W = 1> { rand bit[W] x; }
struct M <int V = 2> { N<V> n; }
component pss_top { M<3> m; }
"""
    assert markers(code) == []


# ---------------------------------------------------------------------------
# An enumeration parameter: the expected type (report E, enum_tparam)
# ---------------------------------------------------------------------------

ENUM = """\
enum mode_e {A, B};
enum color_e {RED, B2};
struct S <mode_e m = A> { rand int x; }
"""


def test_an_item_of_the_parameters_enum():
    code = ENUM + "component pss_top { S<B> a; S<mode_e::B> b; }\n"
    assert markers(code) == []
    assert bindings(code, "B") == [(4, "EnumItem", 1), (4, "EnumItem", 1)]


def test_the_bare_and_qualified_item_share_one_specialization():
    root = parse_pss(ENUM + "struct Top { S<B> a; S<mode_e::B> b; S<A> c; }\n")
    assert_specialization_count(root, "S", 2)


def test_the_item_hides_a_field_of_the_same_name():
    """Step a comes first (18.3), so `B` is mode_e::B, not the constant."""
    code = ENUM + """\
component pss_top {
  static const int B = 7;
  S<B> a;
}
"""
    assert markers(code) == [(
        "warning",
        "'B' is read as the enum item mode_e::B, which hides the field 'B' "
        "(18.3 a); qualify one of them")]
    assert bindings(code, "B") == [(6, "EnumItem", 1)]


def test_an_item_of_another_enum_warns():
    code = ENUM + "component pss_top { S<RED> a; }\n"
    assert markers(code) == [(
        "warning",
        "enum item 'RED' is used where 'mode_e' is expected, but it is an "
        "item of 'color_e' (7.5 i, 8.4.3); qualify it as 'color_e::RED'")]


def test_an_item_for_an_int_parameter_warns():
    code = """\
enum mode_e {A, B};
struct N <int W = 1> { rand bit[W] x; }
component pss_top { N<B> a; }
"""
    assert markers(code) == [(
        "warning",
        "enum item 'B' is used where no enumeration type is expected "
        "(7.5 i, 8.4.3); qualify it as 'mode_e::B'")]


def test_a_generic_declared_later():
    """The parameter's enum type is bound on demand, in the generic's scope,
    when the generic has not been visited yet."""
    code = """\
component pss_top { p::S<B> a; }
package p {
  enum mode_e {A, B};
  struct S <mode_e m = A> { rand int x; }
}
"""
    assert markers(code) == []


def test_the_core_library():
    """std_pkg is linked after the user's files."""
    code = """\
import std_pkg::*;
struct Q : packed_s<BIG_ENDIAN> { bit[8] a; }
"""
    assert markers(code) == []


def test_an_item_the_scope_cannot_see():
    """Step a reaches the enum's items even where the enum is not visible,
    as for any expected type (Ex. 272)."""
    code = """\
package p {
  enum mode_e {A, B};
  struct S <mode_e m = A> { rand int x; }
}
component pss_top { p::S<B> a; }
"""
    assert markers(code) == []


# ---------------------------------------------------------------------------
# A name that resolves to something that is not a value
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decl,arg", [
    ("struct my_s { int x; }", "my_s"),
    ("enum my_e { X }", "my_e"),
    ("typedef bit[4] my_t;", "my_t"),
])
def test_a_type_is_reported(decl, arg):
    code = decl + """
struct N <int W = 1> { rand bit[W] x; }
component pss_top { N<%s> a; }
""" % arg
    assert markers(code) == [(
        "error",
        "template parameter 'W' expects a value, but '%s' is a type" % arg)]


def test_an_enclosing_type_parameter_is_reported():
    code = """\
struct N <int W = 1> { rand bit[W] x; }
struct M <type T> { N<T> n; }
component pss_top { M<int> m; }
"""
    assert markers(code) == [(
        "error", "template parameter 'W' expects a value, but 'T' is a type")]


# ---------------------------------------------------------------------------
# A qualified generic: `p::N<K>`
# ---------------------------------------------------------------------------
#
# The arguments of a generic named by a qualified path were resolved only
# inside the specialization, in the generic's declaring scope, so a name that
# is visible only where the argument is written was not found at all.


def test_a_qualified_generic_takes_a_constant_of_the_use_site():
    code = """\
package p { struct N <int W = 1> { rand bit[W] x; } }
component pss_top {
  static const int K = 4;
  p::N<K> a;
}
"""
    assert markers(code) == []
    assert bindings(code, "K") == [(4, "Field", 3)]


def test_a_qualified_generic_takes_a_type_of_the_use_site():
    code = """\
package p { struct T <type U> { U u; } }
component pss_top {
  struct my_s { int zork; }
  p::T<my_s> c;
  exec init_down { int z = c.u.zork; }
}
"""
    assert markers(code) == []


def test_a_qualified_generic_reports_an_undefined_value():
    code = """\
package p { struct N <int W = 1> { rand bit[W] x; } }
component pss_top { p::N<nosuch> b; }
"""
    assert markers(code) == [("error", "unknown identifier 'nosuch'")]


# ---------------------------------------------------------------------------
# `pkg::ITEM`: an enum item qualified by the namespace that declares its enum
# ---------------------------------------------------------------------------
#
# 18.3: a namespace's static members include enum items, and `ITEM` alone is
# found inside the package, so `pkg::ITEM` names the same item (decision of
# 2026-09-25). A member of the same name comes first.


def test_a_package_qualified_item_in_an_expression():
    code = """\
package p { enum mode_e {A, B}; }
component pss_top {
  exec init_down { p::mode_e m = p::B; }
}
"""
    assert markers(code) == []
    assert bindings(code, "B") == [(3, "EnumItem", 1)]


def test_a_package_qualified_item_as_a_template_argument():
    code = """\
package p { enum mode_e {A, B}; }
struct S <p::mode_e m = p::A> { rand int x; }
component pss_top { S<p::B> s; }
"""
    assert markers(code) == []
    assert bindings(code, "B") == [(3, "EnumItem", 1)]


def test_an_item_an_extension_in_the_package_adds():
    """Ex. 248's shape: the item is declared in p2, and lives in p's enum.
    An extension's item binds to the `extend enum` by every route, the
    unqualified and `p::mode_e::C` forms included."""
    code = """\
package p { enum mode_e {A, B}; }
package p2 { extend enum p::mode_e { C } }
component pss_top {
  exec init_down { p::mode_e m = p2::C; }
}
"""
    assert markers(code) == []
    assert bindings(code, "C") == [(4, "ExtendEnum", 2)]


def test_an_item_of_an_enum_a_base_component_declares():
    code = """\
component base_c { enum lvl_e {LO, HI}; }
component sub_c : base_c { }
component pss_top {
  exec init_down { int l = sub_c::HI; }
}
"""
    assert markers(code) == []
    assert bindings(code, "HI") == [(4, "EnumItem", 1)]


def test_a_member_of_the_same_name_comes_first():
    code = """\
package p { enum mode_e {A, B}; const int B = 7; }
component pss_top {
  exec init_down { int x = p::B; }
}
"""
    assert markers(code) == []
    assert bindings(code, "B") == [(3, "Field", 1)]


def test_addr_reg_pkg_forwards_the_endian_items():
    """21.13 footnotes 1-2 (F28): the CH21 addr_reg_alias probe's line."""
    code = """\
import std_pkg::*;
struct Q : packed_s<addr_reg_pkg::BIG_ENDIAN> { bit[8] a; }
component pss_top {
  exec init_down { endianness_e e = addr_reg_pkg::LITTLE_ENDIAN; }
}
"""
    assert markers(code) == []


def test_a_package_qualified_miss_is_still_reported():
    code = """\
package p { enum mode_e {A, B}; }
component pss_top {
  exec init_down { int x = p::C; }
}
"""
    assert markers(code) == [("error", "'p' has no member named 'C'")]


def test_a_package_qualified_item_is_not_a_type():
    code = """\
package p { enum mode_e {A, B}; }
component pss_top { p::B b; }
"""
    assert markers(code) == [("error", "unknown type 'B' in 'p'")]
