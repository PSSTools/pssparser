"""A struct literal's member names (4.8.4, 4.8.5; U4, symbol-resolution
plan 8.9).

`{.a = 1}` names attribute `a` of the literal's context type (8.7.1). The
names were never resolved, so a misspelled one linked silently. The context
type is now taken from whatever holds the literal: a field or variable
initializer, an exec block's tag, the left-hand side of an assignment, a call
argument's parameter, a function's return type, or -- for a nested literal --
the enclosing literal's member. A literal anywhere else keeps its names
unresolved and marked `ctx_unknown`, and is not reported.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m["severity"], m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, kind of declaration, line of declaration) for each
    use of one of `names`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.text, o.line, type(o.decl).__name__.lstrip("I"),
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


def test_example_6():
    code = """\
struct s {
  int a, b, c, d;
};
struct t {
  s s1 = {.a=1,.b=2,.c=0,.d=0};
  s s2 = {.b=2,.a=1};
  constraint s1 == s2;
}
"""
    assert markers(code) == []
    assert bindings(code, "a", "b", "c", "d") == [
        ("a", 5, "Field", 2), ("b", 5, "Field", 2), ("c", 5, "Field", 2),
        ("d", 5, "Field", 2), ("b", 6, "Field", 2), ("a", 6, "Field", 2)]


def test_example_7_a_list_of_literals():
    code = """\
struct s {
  int a, b, c, d;
};
struct t {
  list<s> my_l = {
    {.a=1,.d=4},
    {.b=2,.c=8}
  };
}
"""
    assert markers(code) == []
    assert {k for (_, _, k, _) in bindings(code, "a", "b", "c", "d")} == {"Field"}


def test_nested_literals_and_an_array_member():
    code = """\
struct I { bit[8] x; }
struct O { I i; I arr[2]; bit[8] y; }
struct T { O o = {.i = {.x = 1}, .arr = {{.x = 2}, {.x = 3}}, .y = 4}; }
"""
    assert markers(code) == []
    assert bindings(code, "x", "i", "arr", "y") == [
        ("i", 3, "Field", 2), ("x", 3, "Field", 1), ("arr", 3, "Field", 2),
        ("x", 3, "Field", 1), ("x", 3, "Field", 1), ("y", 3, "Field", 2)]


def test_an_inherited_attribute():
    code = """\
struct B { bit[8] a; }
struct D : B { bit[8] b; }
struct T { D d = {.a = 1, .b = 2}; }
"""
    assert markers(code) == []
    assert bindings(code, "a", "b") == [("a", 3, "Field", 1), ("b", 3, "Field", 2)]


def test_procedural_contexts():
    code = """\
struct S { bit[8] a; }
function S mk(const S p) { return {.a = 1}; }
component pss_top {
  exec init_down {
    S v = {.a = 2};
    v = {.a = 3};
    v = mk({.a = 4});
  }
}
"""
    assert markers(code) == []
    assert [ln for (_, ln, k, _) in bindings(code, "a") if k == "Field"] \
        == [2, 5, 6, 7]


def test_an_exec_block_tag():
    code = """\
struct tag_s { string nm; }
component pss_top {
  exec header C = tag_s { .nm = "x" } : \"\"\" hi \"\"\";
}
"""
    assert markers(code) == []
    assert bindings(code, "nm") == [("nm", 3, "Field", 1)]


def test_generic_typedef_and_qualified_types():
    code = """\
struct S1 { bit[8] a; }
struct G<type T> { T x; bit[4] y; }
typedef S1 s_t;
package p { struct PS { int q; } }
component pss_top {
  G<int> g = {.x = 1, .y = 2};
  G<S1> g2 = {.x = {.a = 1}};
  s_t z = {.a = 1};
  p::PS ps = {.q = 1};
}
"""
    assert markers(code) == []
    assert {k for (_, _, k, _) in bindings(code, "a", "x", "y", "q")} == {"Field"}


def test_a_literal_in_a_generic_body():
    """Resolved in each specialization; reported where one lacks the name."""
    code = """\
struct S1 { bit[8] a; }
struct S2 { bit[8] b; }
struct H<type T> { exec init_down { T v = {.a = 1}; } }
component pss_top { H<S1> h1; H<S2> h2; }
"""
    assert markers(code) == [("error", 3, "'S2' has no member named 'a'")]


def test_an_enum_attribute_expects_its_enum():
    """The attribute's type is the value's expected type (8.4.3): no PSS046."""
    code = """\
enum color_e { RED, GREEN }
struct S { color_e c; }
struct T { S s = {.c = GREEN}; }
"""
    assert markers(code) == []
    assert bindings(code, "GREEN") == [("GREEN", 3, "EnumItem", 1)]


# -- Rejected ---------------------------------------------------------------

def test_an_unknown_name_in_an_assignment():
    code = """\
struct S { bit[8] a; }
component pss_top {
  S sl;
  exec init_down { sl = { .nosuch = 1 }; }
}
"""
    assert markers(code) == [("error", 4, "'S' has no member named 'nosuch'")]


def test_an_unknown_name_in_an_exec_tag():
    code = """\
struct tag_s { string nm; }
component pss_top {
  exec header C = tag_s { .nosuch = "x" } : \"\"\" hi \"\"\";
}
"""
    assert markers(code) == [("error", 3, "'tag_s' has no member named 'nosuch'")]


def test_an_unknown_name_in_a_field_initializer():
    code = "struct S { bit[8] a; }\nstruct T { S s = {.nosuch = 1}; }\n"
    assert markers(code) == [("error", 2, "'S' has no member named 'nosuch'")]


def test_an_unknown_name_in_a_nested_literal():
    code = """\
struct I { bit[8] x; }
struct O { I i; }
struct T { O o = {.i = {.nosuch = 1}}; }
"""
    assert markers(code) == [("error", 3, "'I' has no member named 'nosuch'")]


def test_an_unknown_name_in_a_call_argument_and_a_return():
    code = """\
struct S { bit[8] a; }
function S mk(const S p) { return {.nosuch_r = 1}; }
component pss_top { exec init_down { S v; v = mk({.nosuch_a = 1}); } }
"""
    assert markers(code) == [
        ("error", 2, "'S' has no member named 'nosuch_r'"),
        ("error", 3, "'S' has no member named 'nosuch_a'")]


def test_an_attribute_named_twice():
    code = "struct S { bit[8] a; }\nstruct T { S s = {.a = 1, .a = 2}; }\n"
    assert markers(code) == [
        ("error", 2, "struct literal names 'a' more than once (4.8.4)")]


def test_a_name_that_is_not_a_data_attribute():
    code = """\
struct S { bit[8] a; constraint c1 { a < 3; } }
struct T { S s = {.c1 = 1}; }
"""
    assert markers(code) == [
        ("error", 2, "struct literal names 'c1', which is not a data "
                     "attribute of 'S' (4.8.4)")]


# -- Not checked --------------------------------------------------------------

def test_no_context_type_is_not_reported():
    """An operand of `==` has no context type yet (case b of U4)."""
    code = """\
struct S { bit[8] a; }
struct T { rand S s; constraint s == {.nosuch = 1}; }
"""
    assert markers(code) == []


def test_a_collection_is_not_a_context_type():
    """A struct literal cannot build a list; that is a shape error, not an
    unknown name."""
    code = "component pss_top { list<int> k = {.a = 1}; }\n"
    assert not [m for m in markers(code) if "no member named" in m[2]]
