"""Covergroup bodies are resolved (LRM 15; symbol-resolution plan 10.1, U1).

Every coverage expression used to be `visit: false`, so a misspelled
coverpoint target, `iff` guard, bin range, `with` expression, cross item or
port-map name linked in silence. Each is now resolved, in the scope the LRM
gives it:

- a coverpoint's target, `iff`, bin ranges and sizes, a cross's `iff`, and
  option values: the covergroup's context -- its ports, or the enclosing
  type's fields -- *without* the coverpoint names (`c : coverpoint c;`
  covers the port `c`, Ex. 199);
- a cross item: a coverpoint of the covergroup, or else a variable, an
  implicit coverpoint (15.1 d, 15.4);
- a bin's `with` expression and its `cp with (...)` form: the coverpoint's
  name is the candidate value (15.3.3.3); a cross bin's `with`: the crossed
  coverpoints (15.4.3);
- an instantiation's port names: the covergroup type's ports; its actuals:
  the instantiating scope (15.2).
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


E = "enum color_e {red, green, blue};\n"


# -- LRM examples --------------------------------------------------------------

def test_lrm_example_197_and_201_inline_covergroups():
    code = E + """\
struct s197 { rand color_e color; covergroup { c: coverpoint color; } cs1; }
struct s201 {
  rand color_e color;
  covergroup { option.at_least = 2; c: coverpoint color; } cs1_inst;
}
"""
    assert markers(code) == []
    assert bindings(code, "color") == [
        ("color", 2, "Field", 2), ("color", 5, "Field", 4)]


def test_lrm_example_198_implicit_coverpoints():
    """`color` and `pixel_adr` are variables, crossed as implicit coverpoints;
    `Hue` and `Offset` are coverpoints."""
    code = E + """\
struct s {
  rand color_e color;
  rand bit[4] pixel_adr, pixel_offset, pixel_hue;
  covergroup {
    Hue : coverpoint pixel_hue;
    Offset : coverpoint pixel_offset;
    AxC: cross color, pixel_adr;
    all : cross color, Hue, Offset;
  } cs2;
}
"""
    assert markers(code) == []
    assert bindings(code, "color", "pixel_adr", "Hue", "Offset") == [
        ("color", 8, "Field", 3), ("pixel_adr", 8, "Field", 4),
        ("color", 9, "Field", 3),
        ("Hue", 9, "CovergroupCoverpoint", 6),
        ("Offset", 9, "CovergroupCoverpoint", 7)]


def test_lrm_example_199_the_label_does_not_shadow_the_port():
    code = E + """\
struct s {
  rand color_e color;
  covergroup cs1(color_e c) {
    c : coverpoint c;
  }
  cs1 cs1_inst(color);
}
"""
    assert markers(code) == []
    assert bindings(code, "c", "color") == [
        ("c", 5, "Field", 4), ("color", 7, "Field", 3)]


def test_lrm_example_200_instance_options():
    code = E + """\
struct s {
  rand color_e color;
  covergroup cs1 (color_e color) { c: coverpoint color; }
  cs1 cs1_inst (color) with { option.at_least = 2; };
}
"""
    assert markers(code) == []


def test_lrm_example_202_iff():
    code = """\
struct s {
  rand bit[4] s0;
  rand bool is_s0_enabled;
  covergroup { coverpoint s0 iff (is_s0_enabled); } cs4;
}
"""
    assert markers(code) == []
    assert bindings(code, "s0", "is_s0_enabled") == [
        ("s0", 4, "Field", 2), ("is_s0_enabled", 4, "Field", 3)]


def test_lrm_example_203_bins():
    code = """\
struct s {
  rand bit[10] v_a;
  covergroup {
    coverpoint v_a {
      bins a = [0..63, 65];
      bins b[] = [127..150, 148..191];
      bins c[] = [200, 201, 202];
      bins d = [1000..];
      bins others[] = default;
    }
  } cs;
}
"""
    assert markers(code) == []


def test_lrm_examples_204_and_205_the_coverpoint_is_the_candidate_value():
    code = """\
struct s204 {
  rand bit[8] x;
  covergroup { a: coverpoint x { bins mod3[] = [0..255] with ((a % 3) == 0); } } cs;
}
struct s205 {
  rand bit[8] x;
  covergroup { a: coverpoint x { bins mod3[] = a with ((a % 3) == 0); } } cs;
}
"""
    assert markers(code) == []
    assert bindings(code, "a") == [
        ("a", 3, "CovergroupCoverpoint", 3),
        ("a", 7, "CovergroupCoverpoint", 7), ("a", 7, "CovergroupCoverpoint", 7)]


def test_lrm_example_209_cross_of_variables():
    code = """\
struct s { rand bit[4] a, b; covergroup { aXb : cross a, b; } cov; }
"""
    assert markers(code) == []
    assert bindings(code, "a", "b") == [("a", 1, "Field", 1), ("b", 1, "Field", 1)]


def test_lrm_example_210_cross_bins():
    """`b with (b%2 == 0)` names the unlabeled coverpoint `b`, and `X with
    (a<=10 && b<=10)` the crossed coverpoints."""
    code = """\
struct s {
  rand bit[8] a, b;
  covergroup {
    coverpoint a { bins low[] = [0..127]; bins high = [128..255]; }
    coverpoint b { bins two[] = b with (b%2 == 0); }
    X : cross a, b { bins small_a_b = X with (a<=10 && b<=10); }
  } cov;
}
"""
    assert markers(code) == []
    got = bindings(code, "a", "b", "X")
    # The targets of the two coverpoints are the fields...
    assert ("a", 4, "Field", 2) in got and ("b", 5, "Field", 2) in got
    # ...and everything else names a coverpoint or the cross. An unlabeled
    # coverpoint's name is its target's text, synthesized, so it has no
    # location of its own (it would coincide with the target's).
    assert [g for g in got if g[1] >= 5 and g not in [("b", 5, "Field", 2)]] == [
        ("b", 5, "CovergroupCoverpoint", None), ("b", 5, "CovergroupCoverpoint", None),
        ("a", 6, "CovergroupCoverpoint", None), ("b", 6, "CovergroupCoverpoint", None),
        ("X", 6, "CovergroupCross", 6),
        ("a", 6, "CovergroupCoverpoint", None), ("b", 6, "CovergroupCoverpoint", None)]


def test_named_port_map():
    code = E + """\
struct s {
  rand color_e color;
  covergroup cs1(color_e c) { c : coverpoint c; }
  cs1 i1(.c(color));
}
"""
    assert markers(code) == []
    assert bindings(code, "c", "color")[-2:] == [
        ("c", 5, "Field", 4), ("color", 5, "Field", 3)]


def test_a_covergroup_type_in_a_package():
    code = """\
package p {
  covergroup cg_t(int a, int b) {
    cp_a : coverpoint a iff (b > 0) { bins mirror = cp_a with (cp_a > 0); }
    ab : cross cp_a, b;
  }
  struct s { rand int x, y; cg_t cg1(.a(x), .b(y)); }
}
"""
    assert markers(code) == []


# -- Unknown names (PSS002) ----------------------------------------------------

BAD = """\
enum color_e {red, green, blue};
component pss_top {
  function int f() { return 1; }
  covergroup cs1(color_e c) { c : coverpoint c; }
  action e {
    rand bit[8] x, y;
    covergroup {
      option.weight = %s;
      a: coverpoint %s iff (%s);
      b: coverpoint x { bins m[%s] = [0..%s] with (%s > 1); }
      X : cross a, %s { bins q = X with (%s > 1); }
    } cs;
    cs1 i1(.%s(x));
    cs1 i2(%s);
  }
}
"""
OK = ["1", "x", "y", "2", "7", "b", "y", "a", "c", "x"]


def _bad(k, name="nosuch"):
    args = list(OK)
    args[k] = name
    return BAD % tuple(args)


def test_the_bad_template_is_legal_as_is():
    assert markers(BAD % tuple(OK)) == []


def test_each_unknown_name_is_reported():
    lines = [8, 9, 9, 10, 10, 10, 11, 11, 13, 14]
    for k, line in enumerate(lines):
        msg = ("covergroup 'cs1' has no port named 'nosuch'" if k == 8
               else "unknown identifier 'nosuch'")
        assert markers(_bad(k)) == [("PSS002", line, msg)], k


# -- Names of the wrong kind (PSS050), and duplicates (PSS003) -----------------

def test_a_bin_names_another_coverpoint():
    code = """\
struct s {
  rand bit[4] x, y;
  covergroup { a: coverpoint x { bins q = b with (b > 1); } b: coverpoint y; } cg;
}
"""
    assert markers(code) == [(
        "PSS050", 3,
        "bins 'q' names 'b', which is not its own coverpoint 'a' (15.3.3.3)")]


def test_a_cross_bin_names_another_cross():
    code = """\
struct s {
  rand bit[4] a, b;
  covergroup { X: cross a, b; Y: cross a, b { bins q = X with (a > 1); } } cg;
}
"""
    assert markers(code) == [(
        "PSS050", 3, "bins 'q' names 'X', which is not its own cross 'Y' (15.4.3)")]


def test_a_cross_of_a_cross():
    code = """\
struct s { rand bit[4] a, b, c; covergroup { X: cross a, b; Y: cross X, c; } cg; }
"""
    assert markers(code) == [(
        "PSS050", 1,
        "cross 'Y' names 'X', which is not a coverpoint or a data field (15.4)")]


def test_two_coverpoints_of_the_same_name():
    code = """\
struct s {
  rand bit[4] x, y;
  covergroup { x: coverpoint y; coverpoint x; } cg;
}
"""
    assert markers(code) == [("PSS003", 3, "duplicate declaration of 'x'")]
