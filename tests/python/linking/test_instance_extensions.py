"""Extending a template instance (17.2.6b; symbol-resolution plan 8.6, F17).

``extend struct S<2> { ... }`` applies to every instance of S "instantiated
with the same set of parameter values", and to no other. The extension is
registered on the generic with its full parameter list (``S<2>`` is
``S<2,7>`` when UB defaults to 7) and its members join the specialization
whose list is equal, when that is made. Two uses with equal lists share one
specialization (8.3), so the members are the statement's own nodes, bound
where they are written: a parameter in the body binds to the generic's
declaration of it, as in a generic extension's body.
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"]) for m in ms]


def messages(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, line its declaration's name is on) per use."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.text, o.line, o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


DOMAIN = """\
struct domain_s <int LB = 4, int UB = 7> {
  rand int attr;
  constraint attr >= LB && attr <= UB;
}
"""


def test_lrm_example_249():
    code = DOMAIN + """\
struct container_s {
  domain_s<2, 7> domA;
  domain_s<2, 8> domB;
  constraint domA.attr_all == 3 && domB.attr_all == 3;
  constraint domA.attr_2_7 == 3;
}
extend struct domain_s {
  rand int attr_all;
  constraint attr_all > LB && attr_all < UB;
}
extend struct domain_s<2> {
  rand int attr_2_7;
  constraint attr_2_7 > LB && attr_2_7 < UB;
}
"""
    assert markers(code) == []


def test_another_instance_does_not_have_the_member():
    code = DOMAIN + """\
extend struct domain_s<2> { rand int attr_2_7; }
struct c { domain_s<2,8> domB; constraint domB.attr_2_7 == 1; }
"""
    assert markers(code) == [("PSS002", 6)]


def test_the_body_binds_where_it_is_written():
    code = DOMAIN + """\
extend struct domain_s<2> {
  rand int x;
  constraint x > LB && x < UB && attr == 1;
}
struct c { domain_s<2> a; constraint a.x == 3; }
"""
    assert markers(code) == []
    assert bindings(code, "x", "LB", "UB", "attr")[4:] == [
        ("x", 7, 6), ("LB", 7, 1), ("x", 7, 6), ("UB", 7, 1), ("attr", 7, 2),
        ("x", 9, 6)]


def test_a_foreach_iterator_in_the_body():
    code = DOMAIN + """\
extend struct domain_s<2> {
  rand int arr[4];
  constraint c1 { foreach (arr[i]) { arr[i] > LB; } }
}
struct c { domain_s<2> a; constraint a.arr[0] == 3; }
"""
    assert markers(code) == []
    assert bindings(code, "i") == [("i", 7, 7)]


def test_arguments_resolve_where_the_extension_is_written():
    code = """\
package p {
  const int N = 2;
  struct d<int LB=4> { rand int attr; }
}
package q {
  import p::*;
  extend struct d<N> { rand int y; constraint y > LB; }
  struct c { d<2> a; constraint a.y == 3; }
}
"""
    assert markers(code) == []
    assert bindings(code, "N", "y", "LB") == [
        ("N", 7, 2), ("y", 7, 7), ("LB", 7, 3), ("y", 8, 7)]


def test_a_type_argument():
    code = """\
struct s<type T> { T v; }
extend struct s<bit[4]> { rand int w; }
struct c { s<bit[4]> a; s<int> b; constraint a.w == 1; constraint b.w == 1; }
"""
    assert markers(code) == [("PSS002", 3)]


def test_a_generic_action_and_component():
    code = """\
component C<int N=1> { }
extend component C<2> { int x; }
component pss_top {
  C<2> c;
  action A<int M=1> { rand int v; }
  extend action A<2> { rand int w; constraint w == M; }
  action B { A<2> a; activity { a; } constraint a.w == 1; }
  exec init_down { c.x = 1; }
}
"""
    assert markers(code) == []


def test_two_extensions_of_one_instance_and_a_generic_one():
    code = DOMAIN + """\
extend struct domain_s { rand int g; }
extend struct domain_s<2> { rand int x; constraint x == g; }
extend struct domain_s<2,7> { rand int y; }
struct c {
  domain_s<2> a; domain_s<3> b;
  constraint a.g == a.x && a.x == a.y; constraint b.g == 1;
}
"""
    assert markers(code) == []


def test_an_unused_instance_is_still_checked():
    """The `extend` names the instance, so it is made; its body's errors are
    reported once whether or not a use makes it too."""
    ext = "extend struct domain_s<3> { rand int x; constraint x > nosuch; }\n"
    assert markers(DOMAIN + ext) == [("PSS002", 5)]
    assert markers(DOMAIN + ext
                   + "struct c { domain_s<3> a; domain_s<3,7> b; }\n") == [
        ("PSS002", 5)]


def test_a_member_the_type_already_declares():
    code = DOMAIN + """\
extend struct domain_s { rand int g; }
extend struct domain_s<2> { rand int attr; rand int g; }
struct c { domain_s<2> a; }
"""
    assert messages(code) == [
        ("PSS003", 6,
         "duplicate declaration of 'attr' in an extension of an instance of "
         "'domain_s': the type already declares it (17.2.3)"),
        ("PSS003", 6,
         "duplicate declaration of 'g' in an extension of an instance of "
         "'domain_s': the type already declares it (17.2.3)")]


def test_a_type_that_is_not_generic():
    code = """\
struct t { }
extend struct t<1> { rand int x; }
"""
    assert messages(code) == [(
        "PSS056", 2,
        "'t' is not a generic type, so it takes no template arguments")]


def test_a_wrong_argument_list_and_an_unknown_argument():
    assert [c for c, _ in markers(DOMAIN + "extend struct domain_s<1,2,3> { }\n")] \
        == ["PSS060"]
    assert markers(DOMAIN + "extend struct domain_s<nosuch> { }\n") == [
        ("PSS002", 5)]


def test_a_type_inside_an_instance():
    code = """\
component C<int N=1> { struct s { } }
extend struct C<2>::s { rand int x; }
extend component C<3> { extend struct s { rand int y; } }
"""
    assert markers(code) == [("PSS057", 2), ("PSS057", 3)]


def files_markers(files):
    """(file, code, line) per marker for a multi-file model."""
    from ..test_helpers import _assign_codes
    p = pssparser.Parser()
    try:
        p.parses(files)
        p.link()
        ms = p.markers
    except Exception as e:
        ms = getattr(e, "markers", None)
        if ms is None:
            raise
    return [(m.get("file"), m.get("code"), m["line"]) for m in _assign_codes(ms)]


GENERICS = """\
package r { struct d_s { } struct g_s<struct T, struct A=d_s> { } }
package p2 {
  import r::*;
  struct h_s<struct T=d_s> { g_s<T> x; }
  struct k_s<struct T=h_s<d_s>> { T t; }
}
"""


def test_a_default_in_a_nested_specialization_binds_where_it_is_written():
    """The instance extension specializes k_s, then h_s<d_s>, then g_s<d_s>
    while extensions are applied, before the generic g_s has been visited, so
    the default `A=d_s` is still unbound in the copy. It was resolved in the
    enclosing specialization's body (h_s in p2), where p2's `import r::*`
    does not reach a name written in package r: a false PSS import-leak error
    at the default. A use as a field, made after g_s was visited, was fine."""
    ext = """\
import p2::*;
import r::*;
extend struct k_s<h_s<d_s>> { int y; }
struct c { k_s<h_s<d_s>> v; constraint v.y == 1; }
"""
    assert files_markers([("q7.pss", GENERICS), ("q8.pss", ext)]) == []


def test_a_core_library_default_in_a_nested_specialization():
    """The same through the core library: ALLOC_MODE's default in
    transparent_addr_claim_s was reported as an unknown type (at
    `<unknown>`: core-library locations had no file name then; they are now
    `<stdlib>/addr_reg_pkg.pss`)."""
    code = """\
import addr_reg_pkg::*;
struct tr_s : addr_trait_s { }
struct seg_s<struct T : addr_trait_s> : transparent_addr_claim_s<T> { }
buffer buf_b<struct S> { S s; }
extend buffer buf_b<seg_s<tr_s>> { int y; }
"""
    assert markers(code) == []
