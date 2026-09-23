"""
`compile if` keeps its condition and reports the branches it left out
(pss-scrambler FR-002 case A; questions FR-002-Q2/-Q3).

The builder still chooses the branch from the parse tree, as before. What
is new: the condition is an expression whose names are bound (and reported
by pssparser.refs), `compile has` and `compile assert` included, and
Parser.inactive_regions() lists every branch not elaborated.
"""
import pytest

import pssparser
from pssparser import InactiveRegion, refs
from pssparser.refs import Resolution

M3 = """\
import std_pkg::*;
const int WIDTH = 8;
component pss_top {
  int a = 0xFF;
  bit[32] b = 32'hDEAD;
  compile if (WIDTH > 16) { int wide_f; } else { int narrow_f; }
  action go_a {
    rand bit[8] v;
  }
}
"""


def _link(src, expect_error=False, name="t.pss"):
    p = pssparser.Parser()
    p.parses([(name, src)])
    if expect_error:
        with pytest.raises(pssparser.ParseException):
            p.link()
    else:
        p.link()
    return p


def _occ(p, line, text):
    hits = [o for o in refs.occurrences(p) if o.line == line and o.text == text]
    assert len(hits) == 1, (line, text, hits)
    return hits[0]


def test_condition_reference_resolves():
    """AC1: WIDTH on line 6 resolves to the declaration on line 2."""
    o = _occ(_link(M3), 6, "WIDTH")
    assert o.resolution is Resolution.USER
    assert o.decl_location[:3] == (1, 2, 11)


def test_dropped_branch_is_reported():
    """AC2: `{ int wide_f; }`, brace to brace, `else` excluded."""
    assert _link(M3).inactive_regions() == [InactiveRegion(1, 6, 27, 6, 41)]


def test_branch_selection_is_unchanged():
    """AC5: the else branch is the one elaborated; the if branch is not."""
    p = _link(M3)
    names = {o.text for o in refs.occurrences(p) if o.is_declaration}
    assert "narrow_f" in names and "wide_f" not in names


def test_true_condition_drops_the_else_branch():
    p = _link(M3.replace("WIDTH > 16", "WIDTH < 16"))
    assert p.inactive_regions() == [InactiveRegion(1, 6, 48, 6, 64)]


def test_no_else_and_false_condition():
    p = _link(M3.replace(" else { int narrow_f; }", ""))
    assert p.inactive_regions() == [InactiveRegion(1, 6, 27, 6, 41)]


def test_unevaluable_condition_drops_both_branches():
    """FR-002-Q3 (b). The condition is already an error, and Parser drops a
    file whose build reported one, so this is checked on the builder's
    output directly."""
    from io import StringIO
    from pssparser.core import Factory
    f = Factory.inst()
    ml = f.mkMarkerCollector()
    g = f.getAstFactory().mkGlobalScope(1)
    f.mkAstBuilder(ml).build(g, StringIO(M3.replace("WIDTH > 16", "nosuch > 16")))
    top = [g.getChild(i) for i in range(g.numChildren())
           if type(g.getChild(i)).__name__ == "Component"][0]
    assert top.numCompile_conds() == 1
    cc = top.getCompile_cond(0)
    assert cc.getEval_failed() and cc.getTaken() == -1
    got = [(r.start_line, r.start_col, r.end_line, r.end_col)
           for r in cc.getInactiveList()]
    assert got == [(6, 28, 6, 42), (6, 49, 6, 65)]


def test_nested_compile_if_in_a_dropped_branch_is_not_reported():
    """FR-002-Q3 (c)."""
    src = """\
const int W = 8;
component pss_top {
  compile if (W > 16) {
    compile if (W > 32) { int a; }
    int b;
  }
}
"""
    assert _link(src).inactive_regions() == [InactiveRegion(1, 3, 23, 6, 3)]


def test_multi_line_region_and_fileid():
    src = "\n" + M3
    p = pssparser.Parser()
    p.parses([("a.pss", "package unused_p { }\n"), ("b.pss", src)])
    p.link()
    assert p.inactive_regions() == [InactiveRegion(2, 7, 27, 7, 41)]


@pytest.mark.parametrize("where,src,line", [
    ("package", """\
package p {
  const int K = 1;
  compile if (K == 2) { struct x_s { } }
}
""", 3),
    ("action", """\
const int K = 1;
component pss_top {
  action a {
    compile if (K == 2) { rand int x; }
  }
}
""", 4),
    ("struct", """\
const int K = 1;
struct s {
  compile if (K == 2) { rand int x; }
}
""", 3),
    ("constraint", """\
const int K = 1;
struct s {
  rand int y;
  constraint { compile if (K == 2) { y < 3; } }
}
""", 4),
    ("procedural", """\
const int K = 1;
component pss_top {
  int y;
  exec init_down { compile if (K == 2) { y = 3; } }
}
""", 4),
])
def test_every_context(where, src, line):
    p = _link(src)
    assert _occ(p, line, "K").decl_location[:3] == (1, (2 if where == "package" else 1),
                                                    (13 if where == "package" else 11))
    regions = p.inactive_regions()
    assert len(regions) == 1 and regions[0].start_line == line


def test_compile_has_argument_is_bound_and_a_missing_one_is_silent():
    """FR-002-Q2: `compile has` keeps its argument; a name that does not
    exist is not an error -- that is what `compile has` asks."""
    src = """\
struct present_s { }
component pss_top {
  compile if (compile has(present_s)) { int x; }
  compile if (compile has(absent_s)) { int y; }
}
"""
    p = _link(src)
    assert _occ(p, 3, "present_s").decl_location[:3] == (1, 1, 8)
    assert _occ(p, 4, "absent_s").resolution is Resolution.UNRESOLVED
    assert p.inactive_regions() == [InactiveRegion(1, 4, 38, 4, 47)]


def test_compile_assert_condition_is_bound():
    src = """\
const int K = 1;
component pss_top {
  compile assert (K == 1, "K must be 1");
}
"""
    p = _link(src)
    assert _occ(p, 3, "K").decl_location[:3] == (1, 1, 11)
    assert p.inactive_regions() == []


def test_condition_names_do_not_add_diagnostics():
    """AC5: binding the condition reports nothing new."""
    src = M3.replace("WIDTH > 16", "compile has(nowhere::thing)")
    p = _link(src)
    assert not [m for m in p.markers if m["severity"] == "error"]


def test_before_link_there_are_no_regions():
    p = pssparser.Parser()
    p.parses([("t.pss", M3)])
    assert p.inactive_regions() == []
