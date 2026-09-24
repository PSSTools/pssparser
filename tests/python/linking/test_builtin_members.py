"""
Built-in data members (symbol-resolution plan 5.1 and 5.3).

`uid` (clause 9 intro) is a `bit[32]` on every modeling element: action,
monitor, component, buffer, stream, state and resource. Not on a plain struct.
`prev` (9.3.3.1g) is a state's reference to the previous state object, of the
state's own type, and is available only inside the state's declaration or an
extension of it. Both are members of the linked symbol tree only, flagged
`FieldAttr.Builtin`, and never AST nodes. A user declaration of either name,
or of `initial`/`instance_id`, is PSS003.

`comp` (5.3) is typed by the enclosing component, which was wrong in two
places: an abstract action declared in a component (C1) and any action of a
specialized template component (C2).
"""
import pytest

import pssparser
from pssparser import refs
from pssparser.refs import Resolution

from ..test_helpers import parse_collect
from .test_activity_scopes import assert_links_and_binds


def errors(code):
    _, markers = parse_collect(code)
    return [(m["code"], m["message"]) for m in markers
            if m["severity"] == "error"]


def occurrences(code):
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return refs.occurrences(p)


# ---------------------------------------------------------------------------
# uid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("code", [
    # `comp.uid`, and `uid` unqualified in the action's own constraint.
    """component pss_top {
  action A { rand bit[32] x; constraint x == comp.uid; constraint x != uid; }
}""",
    # A resource reference: `uid` next to the injected `instance_id`.
    """resource R { rand int a; }
component pss_top {
  pool[2] R rp;
  action A { lock R r; rand bit[32] v; constraint v == r.uid + r.instance_id; }
}""",
    # Action handles, an array element, and `this.uid` (21.x examples).
    """component pss_top {
  action B { }
  action A {
    B s[4]; B b; rand bit[32] t;
    constraint t == s[1].uid; constraint t != b.uid; constraint t != this.uid;
    activity { s[0]; s[1]; s[2]; s[3]; b; }
  }
}""",
    # A component-instance path from pss_top.
    """component c_c { }
component pss_top {
  c_c cl[2];
  action A { rand bit[32] t; constraint t == pss_top.cl[1].uid; }
}""",
    # Buffer, stream and state objects, and a monitor's action handle.
    """buffer D { rand int a; }
stream St { rand int a; }
state Sa { rand int a; constraint uid != 0; }
component pss_top {
  pool D dp; pool St sp; pool Sa ap;
  action P { output D d; output St s; input Sa a;
    constraint d.uid != s.uid; constraint a.uid != 0; }
  action B { }
  monitor M { B b; activity { b; } constraint b.uid != 0; }
}""",
])
def test_uid_resolves_on_every_modeling_element(tmp_path, code):
    assert_links_and_binds(tmp_path, code)


def test_uid_is_a_builtin_occurrence():
    occs = occurrences("""\
component pss_top {
  action A { rand bit[32] x; constraint x == comp.uid; }
}
""")
    [uid] = [o for o in occs if o.text == "uid"]
    assert uid.resolution is Resolution.BUILTIN
    assert uid.decl_location is None


def test_plain_struct_has_no_uid():
    assert errors("""
struct S { rand int a; }
component pss_top { action A { rand S s; rand bit[32] t; constraint t == s.uid; } }
""") == [("PSS002", "Failed to find elem uid")]


@pytest.mark.parametrize("code,name,kind", [
    ("component pss_top { action A { rand int uid; } }", "uid", "action"),
    ("component pss_top { bit[32] uid; }", "uid", "component"),
    ("state S { bool initial; }", "initial", "state"),
    ("state S { rand int prev; }", "prev", "state"),
    ("resource R { rand int instance_id; }", "instance_id", "resource"),
    # Through an extension: the same diagnosis, not "conflicts with an
    # existing declaration".
    ("component pss_top { action A { } extend action A { int uid; } }",
     "uid", "action"),
])
def test_redeclaring_a_builtin_member(code, name, kind):
    assert errors(code) == [
        ("PSS003", "duplicate declaration of '%s': every %s has a built-in "
                   "'%s'" % (name, kind, name))]


def test_a_plain_struct_may_declare_uid():
    assert errors("struct P { int uid; int prev; }") == []


# ---------------------------------------------------------------------------
# prev
# ---------------------------------------------------------------------------

def test_lrm_example_170():
    assert errors("""
state power_state_s {
  rand int in [0..3] domain_A, domain_B, domain_C;
  constraint domain_B in { prev.domain_B - 1,
                           prev.domain_B,
                           prev.domain_B + 1};
  constraint prev.domain_C==0 -> domain_C in [0,1] || domain_B==0;
};
component power_ctrl_c {
  pool power_state_s psvar;
  bind psvar *;
  action power_trans1 {
    output power_state_s next_state;
  };
  action power_trans2 {
    output power_state_s next_state;
    constraint next_state.domain_C == 0;
  };
};""") == []


def test_prev_in_an_extension_and_through_this_binds(tmp_path):
    assert_links_and_binds(tmp_path, """
state S1 { rand int d; constraint this.prev.d >= 0; }
extend state S1 { constraint prev.d != 5; }
component pss_top { pool S1 p; }""")


def test_prev_in_a_specialized_state():
    """The generic body's references are dependent, so only a clean link can
    be asserted; `test_prev_member_miss_in_a_specialization` is the check
    that the specialization's `prev` is searched at all."""
    assert errors("""
state S <int W=4> { rand bit[W] d; constraint prev.d <= d; }
component pss_top { pool S<8> p; bind p *; }""") == []


def test_prev_member_miss_in_a_specialization():
    assert errors("""
state S <int W=4> { rand bit[W] d; constraint prev.nosuch <= d; }
component pss_top { pool S<8> p; }""") == [
        ("PSS002", "Failed to find elem nosuch")]


def test_prev_in_a_derived_state_has_the_derived_type():
    """`prev.e` finds the derived state's own field; `prev.d` the base's."""
    occs = occurrences("""\
state S1 { rand int d; }
state S2 : S1 { rand int e; constraint prev.e == e; constraint prev.d == 1; }
""")
    uses = sorted((o.line, o.col, o.text, o.decl_location[1:3])
                  for o in occs
                  if o.text in ("d", "e") and not o.is_declaration)
    assert uses == [(2, 45, "e", (2, 26)), (2, 50, "e", (2, 26)),
                    (2, 69, "d", (1, 21))]
    assert {o.resolution for o in occs if o.text == "prev"} == {
        Resolution.BUILTIN}


def test_prev_outside_a_state():
    assert errors("""
struct T { rand int d; constraint prev.d == 1; }
component pss_top { action A { rand int d; constraint prev.d == 0; } }
""") == [("PSS002", "unknown identifier 'prev'")] * 2


def test_prev_of_another_state_object():
    """9.3.3.1g: only within the state type -- not `i.prev` on an input."""
    assert errors("""
state S1 { rand int d; }
component pss_top {
  pool S1 p; bind p *;
  action A { input S1 i; constraint i.prev.d == 0; }
}""") == [("PSS002", "'prev' is only valid in a state type or its "
                     "extension, and cannot be reached as a member of 'i'")]


# ---------------------------------------------------------------------------
# comp (5.3)
# ---------------------------------------------------------------------------

def test_comp_in_an_abstract_action_in_a_component(tmp_path):
    """C1: an abstract action in a component has that component as `comp`."""
    assert_links_and_binds(tmp_path, """
component pss_top {
  int n;
  abstract action AB { rand int y; constraint y == comp.n; }
  action C : AB { }
}""")


@pytest.mark.parametrize("code", [
    # C2: an action of a specialized template component.
    """component c_t <int W=4> {
  bit[W] n;
  action A { rand bit[W] y; constraint y == comp.n; }
}
component pss_top { c_t<8> c; c_t<16> d; }""",
    # C2, one level further: a specialization reached from another.
    """component c_t <int W=4> {
  bit[W] n;
  action A { rand bit[W] y; constraint y == comp.n; }
}
component d_t <int W=4> {
  c_t<W> c;
  action B { rand int z; constraint z == comp.c.n; }
}
component pss_top { d_t<8> d; }""",
])
def test_comp_in_a_specialized_component(code):
    """Generic bodies hold dependent references, so this asserts a clean
    link; the miss test below shows the specialization is searched."""
    assert errors(code) == []


def test_comp_in_a_with_block_on_a_specialized_action():
    """13.1.4: in the with-block `comp` is the traversed action's, c_t<8>."""
    occs = occurrences("""\
component c_t <int W=4> {
  bit[W] n;
  action A { rand bit[W] y; }
}
component pss_top {
  c_t<8> c;
  action T { c_t<8>::A a; activity { a with { y == comp.n; }; } }
}
""")
    [n] = [o for o in occs if o.text == "n" and not o.is_declaration]
    assert n.resolution is Resolution.USER
    assert n.decl_location[1:3] == (2, 10)


def test_comp_member_miss_in_a_specialization_is_reported():
    assert errors("""
component c_t <int W=4> {
  bit[W] n;
  action A { rand bit[W] y; constraint y == comp.nosuch; }
}
component pss_top { c_t<8> c; }
""") == [("PSS002", "Failed to find elem nosuch")]


def test_comp_in_an_abstract_action_outside_a_component():
    assert errors("""
package p { abstract action AB { rand int y; constraint y == comp.n; } }
""") == [("PSS002", "'comp' is only valid in an action declared in a "
                     "component, and 'AB' is declared outside one")]
