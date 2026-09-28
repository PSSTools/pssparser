"""`instance a.b with T;` -- instance-override targets are bound (U5).

LRM 17.5: an `override` block replaces the declared type of a field, by type
or by instance. An instance override names the field by a hierarchical path
from the type the block is written in; the first element may be inherited
(Ex. 254's `reg2axi_top_x` overrides `xlator`, which it inherits). The path
used to be left unbound and unchecked, so a misspelled one was silently
accepted.
"""
from ..test_helpers import parse_collect


def errors(code):
    _, markers = parse_collect(code)
    return [(m["line"], m["message"]) for m in markers if m["severity"] == "error"]


# LRM Example 254, completed: the declarations in a component, `...` removed.
EX254 = """
component pss_top {
  action axi_write_action { }
  action xlator_action {
    axi_write_action axi_action;
    axi_write_action other_axi_action;
    activity {
      axi_action;
      other_axi_action;
    }
  }
  action axi_write_action_x : axi_write_action { }
  action axi_write_action_x2 : axi_write_action_x { }
  action axi_write_action_x3 : axi_write_action_x { }
  action axi_write_action_x4 : axi_write_action_x { }
  action reg2axi_top {
    override {
      type axi_write_action with axi_write_action_x;
      instance xlator.axi_action with axi_write_action_x2;
    }
    xlator_action xlator;
    activity {
      repeat (10) {
        xlator;
      }
    }
  }
  action reg2axi_top_x : reg2axi_top {
    override {
      type axi_write_action with axi_write_action_x4;
      instance %s with axi_write_action_x3;
    }
  }
}
"""


def test_lrm_example_254():
    assert errors(EX254 % "xlator.axi_action") == []


def test_an_unknown_member_in_the_path_is_reported():
    assert errors(EX254 % "xlator.nosuch") == [
        (31, "'xlator' has no member named 'nosuch'")]


def test_an_unknown_root_in_the_path_is_reported():
    msgs = errors(EX254 % "nosuch.axi_action")
    assert [line for line, _ in msgs] == [31], msgs
    assert "unknown identifier 'nosuch'" in msgs[0][1], msgs


def test_a_component_instance_path():
    assert errors("""
component sub_c { }
component sub2_c : sub_c { }
component mid_c { sub_c s; }
component pss_top {
  mid_c m;
  override { instance m.s with sub2_c; }
}
""") == []
