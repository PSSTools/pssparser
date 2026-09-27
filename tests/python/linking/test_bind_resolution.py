"""Bind operands (LRM 11.9, 12.3; symbol-resolution plan 4.5, U2).

A pool bind names its pool by an ordinary path from the binding component.
Each target is a path of component instances from the binding component,
then an action type of the last component reached, then an input, output or
resource-claim field of that action type. The action type used to be looked
up in the binding component, which rejected `bind p { s1.sa.r }` (F-N15), and
nothing else in a bind was resolved: an unknown pool, instance or field
linked in silence. Pools were not even names in their component.

An activity bind's operands are ordinary paths in the activity, labels
included (4.3).
"""
import pssparser
from pssparser import refs

from ..test_helpers import parse_collect


def markers(code):
    _, ms = parse_collect(code)
    return [(m.get("code"), m["line"], m["message"]) for m in ms]


def bindings(code, *names):
    """(name, line of use, kind of declaration, line of its name) for each
    use of one of `names`."""
    p = pssparser.Parser()
    p.parses([("t.pss", code)])
    p.link()
    return [(o.text, o.line, type(o.decl).__name__,
             o.decl_location.line if o.decl_location else None)
            for o in refs.occurrences(p)
            if o.text in names and not o.is_declaration]


# -- LRM examples --------------------------------------------------------------

def test_lrm_example_125_activity_bind():
    code = """\
component top {
  buffer B { rand int a; };
  action P1 { output B out; };
  action P2 { output B out; };
  action C { input B inp; };
  pool B B_p;
  bind B_p {*};
  action T {
    P1 p1; P2 p2; C c;
    activity {
      p1; p2; c;
      bind p1.out c.inp;
    };
  }
};
"""
    assert markers(code) == []
    assert bindings(code, "p1", "out", "c", "inp")[-4:] == [
        ("p1", 12, "Field", 9), ("out", 12, "FieldRef", 3),
        ("c", 12, "Field", 9), ("inp", 12, "FieldRef", 5)]


def test_lrm_example_126_hierarchical_bind():
    code = """\
buffer data_buf { rand int d; }
component pss_top {
  pool data_buf p;
  bind p *;
  action sub_a { input data_buf din; output data_buf dout; }
  action compound_a {
    input data_buf data_in;
    output data_buf data_out;
    sub_a a1, a2;
    activity {
      a1;
      a2;
      bind a1.dout a2.din;
      bind data_in a1.din;
      bind data_out a2.dout;
    }
  }
}
"""
    assert markers(code) == []
    assert bindings(code, "data_in", "data_out") == [
        ("data_in", 14, "FieldRef", 7), ("data_out", 15, "FieldRef", 8)]


def test_lrm_example_130_default_binding():
    code = """\
struct mem_segment_s { rand bit[32] addr; };
buffer data_buff_s { rand mem_segment_s seg; };
resource channel_s { };
component dma_sub_c { };
component dma_c {
  dma_sub_c dmas1, dmas2;
  pool data_buff_s buff_p;
  bind buff_p {*};
  pool [4] channel_s chan_p;
  bind chan_p {dmas1.*, dmas2.*};
  action mem2mem_a {
    input data_buff_s in_data;
    output data_buff_s out_data;
  };
};
"""
    assert markers(code) == []
    assert bindings(code, "buff_p", "chan_p", "dmas1", "dmas2") == [
        ("buff_p", 8, "FieldPool", 7), ("chan_p", 10, "FieldPool", 9),
        ("dmas1", 10, "Field", 6), ("dmas2", 10, "Field", 6)]


def test_lrm_example_131_arrays_of_components():
    """An array of instances is named whole or by a range (12.3 b)."""
    code = """\
buffer mbuf { }
buffer mbuf2 { }
buffer mbuf3 { }
buffer mbuf4 { }
component mem_c { }
component top_c {
  mem_c mem[4];
  pool mbuf mbuf_p;
  pool mbuf2 mbufA_p;
  pool mbuf3 mbufB_p;
  pool mbuf4 mbufC_p;
  bind mbuf_p mem.*;
  bind mbufA_p mem[0..2].*;
  bind mbufB_p mem[1..].*;
  bind mbufC_p mem[2,3].*;
}
"""
    assert markers(code) == []
    assert [b[1] for b in bindings(code, "mem")] == [12, 13, 14, 15]


EX132 = """\
state power_state_s { rand int in [0..4] level; }
resource channel_s {}
component graphics_c {
  pool power_state_s power_state_var;
  bind power_state_var *;
  action power_transition_a {
    input power_state_s curr;
    output power_state_s next;
    lock channel_s chan;
  }
}
component my_multimedia_ss_c {
  graphics_c gfx0;
  graphics_c gfx1;
  pool [4] channel_s channels;
  bind channels {gfx0.*,gfx1.*};
  action observe_same_power_state_a {
    input power_state_s gfx0_state;
    input power_state_s gfx1_state;
    constraint gfx0_state.level == gfx1_state.level;
  }
  bind gfx0.power_state_var observe_same_power_state_a.gfx0_state;
  bind gfx1.power_state_var observe_same_power_state_a.gfx1_state;
}
"""


def test_lrm_example_132_pool_binding():
    """The pool is a path through a component instance."""
    assert markers(EX132) == []
    assert [b for b in bindings(EX132, "gfx0", "power_state_var", "gfx0_state")
            if b[1] == 22] == [
        ("gfx0", 22, "Field", 13), ("power_state_var", 22, "FieldPool", 4),
        ("gfx0_state", 22, "FieldRef", 18)]


def test_lrm_example_133_indexed_pool_and_field():
    code = """\
state power_state_s {
  rand int in [0..4] level;
  constraint initial -> level == 0;
}
component graphics_c {
  pool power_state_s power_state_var;
  bind power_state_var *;
  action power_transition_a {
    input power_state_s curr;
    output power_state_s next;
  }
}
component my_multimedia_ss_c {
  graphics_c gfx[2];
  action observe_same_power_state_a {
    rand int in [1..4] observed_level;
    input power_state_s gfx_state[2];
    constraint { foreach (s: gfx_state) { s.level == observed_level; } }
  }
  bind gfx[0].power_state_var observe_same_power_state_a.gfx_state[0];
  bind gfx[1].power_state_var observe_same_power_state_a.gfx_state[1];
}
"""
    assert markers(code) == []
    assert bindings(code, "power_state_var")[-2:] == [
        ("power_state_var", 20, "FieldPool", 6),
        ("power_state_var", 21, "FieldPool", 6)]


# -- The target's action type is in the component its path reaches (F-N15) ----

def test_action_type_in_the_component_reached():
    code = """\
resource res_s { }
component sub_c { action sa { lock res_s r; } }
component mid_c { sub_c s[2]; }
component pss_top {
  sub_c s1;
  mid_c m;
  pool [2] res_s rp;
  bind rp { s1.sa.r, m.s[0..1].sa.r };
}
"""
    assert markers(code) == []
    assert bindings(code, "s1", "m", "s", "sa", "r") == [
        ("s1", 8, "Field", 5), ("sa", 8, "Action", 2),
        ("r", 8, "FieldClaim", 2),
        ("m", 8, "Field", 6), ("s", 8, "Field", 3),
        ("sa", 8, "Action", 2), ("r", 8, "FieldClaim", 2)]


def test_an_action_type_is_not_looked_up_in_the_binding_component():
    """`P` is an action of `pss_top`, not of `sub_c`."""
    code = """\
resource res_s { }
component sub_c { }
component pss_top {
  sub_c s1;
  pool [2] res_s rp;
  action P { lock res_s r; }
  bind rp { P.r, s1.P.r };
}
"""
    assert markers(code) == [("PSS002", 7, "'sub_c' has no member named 'P'")]


def test_an_inherited_action_type():
    code = """\
resource res_s { }
component base_c { action A { lock res_s r; } }
component sub_c : base_c { }
component pss_top {
  sub_c s1;
  pool [2] res_s rp;
  bind rp { s1.A.r };
}
"""
    assert markers(code) == []


def test_order_does_not_matter():
    """The instance's component, and the bind's own component, may be
    declared after the bind (Q8)."""
    code = """\
component pss_top {
  pool [2] res_s rp;
  bind rp { s1.sa.r };
  sub_c s1;
}
component sub_c { action sa { lock res_s r; } }
resource res_s { }
"""
    assert markers(code) == []


def test_a_bind_in_a_component_extension():
    code = """\
resource res_s { }
component sub_c { action sa { lock res_s r; } }
component pss_top { sub_c s1; }
extend component pss_top {
  pool [2] res_s rp;
  bind rp { s1.sa.r };
}
"""
    assert markers(code) == []


# -- Unknown names (PSS002) ----------------------------------------------------

POOL_TOP = """\
resource res_s { }
struct st_s { }
component sub_c { action sa { lock res_s r; rand int x; } struct ss_s { } }
component pss_top {
  sub_c s1;
  int n;
  pool [2] res_s rp;
  action P { lock res_s r; rand int px; }
  %s
}
"""


def test_an_unknown_pool():
    assert markers(POOL_TOP % "bind nosuch *;") == [
        ("PSS002", 9, "unknown identifier 'nosuch'")]


def test_an_unknown_instance():
    assert markers(POOL_TOP % "bind rp { nosuch.* };") == [
        ("PSS002", 9, "'pss_top' has no member named 'nosuch'")]


def test_an_unknown_instance_further_down():
    """One error: the names past it are not looked up."""
    assert markers(POOL_TOP % "bind rp { s1.nosuch.sa.r };") == [
        ("PSS002", 9, "'sub_c' has no member named 'nosuch'")]


def test_an_unknown_action_type():
    assert markers(POOL_TOP % "bind rp { s1.nosuch.r };") == [
        ("PSS002", 9, "'sub_c' has no member named 'nosuch'")]


def test_an_unknown_field():
    assert markers(POOL_TOP % "bind rp { s1.sa.nosuch, P.nosuch };") == [
        ("PSS002", 9, "'sa' has no member named 'nosuch'"),
        ("PSS002", 9, "'P' has no member named 'nosuch'")]


# -- Names of the wrong kind (PSS049) ------------------------------------------

def test_the_pool_is_not_a_pool():
    assert markers(POOL_TOP % "bind n *;") == [
        ("PSS049", 9, "bind names 'n', which is not a pool (12.3)")]


def test_a_path_element_is_not_a_component_instance():
    assert markers(POOL_TOP % "bind rp { n.* };") == [
        ("PSS049", 9, "bind names 'n', which is not a component instance of "
                      "'pss_top' (12.3)")]


def test_the_action_type_is_not_an_action():
    assert markers(POOL_TOP % "bind rp { s1.ss_s.r };") == [
        ("PSS049", 9, "bind names 'ss_s', which is not an action type of "
                      "'sub_c' (12.3)")]


def test_the_field_is_not_a_flow_or_resource_reference():
    assert markers(POOL_TOP % "bind rp { s1.sa.x, P.px };") == [
        ("PSS049", 9, "bind names 'x', which is not an input, output or "
                      "resource-claim field of 'sa' (12.3)"),
        ("PSS049", 9, "bind names 'px', which is not an input, output or "
                      "resource-claim field of 'P' (12.3)")]


# -- Activity binds ------------------------------------------------------------

ABIND = """\
buffer B { rand int a; }
component pss_top {
  pool B B_p;
  bind B_p *;
  action P { output B out; }
  action C { input B inp; }
  action T {
    P p1; C c1;
    activity { L: sequence { P p2; p2; } p1; c1; %s }
  }
}
"""


def test_an_activity_bind_through_a_label():
    code = ABIND % "bind L.p2.out c1.inp;"
    assert markers(code) == []
    assert bindings(code, "L", "p2", "out")[1:] == [
        ("L", 9, "ActivitySequence", 9), ("p2", 9, "ActionHandleField", 9),
        ("out", 9, "FieldRef", 5)]


def test_an_activity_bind_to_an_unknown_handle():
    assert markers(ABIND % "bind nosuch.out c1.inp;") == [
        ("PSS002", 9, "unknown identifier 'nosuch'")]


def test_an_activity_bind_to_an_unknown_field():
    assert markers(ABIND % "bind p1.out c1.nosuch;") == [
        ("PSS002", 9, "Failed to find elem nosuch")]
