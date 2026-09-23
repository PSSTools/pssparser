"""
Identifiers the AST used to drop (pss-scrambler FR-002).

Case B: a constraint block's name is an ExprId with its own location.
Case C: `exec file` filename templates -- only the triple-quoted form is a
template (LRM 4.7.1, 20.5.3; FR-002-Q1).
Case A (`compile if`) is in test_compile_if_regions.py.
"""
import pytest

import pssparser
import pssparser.ast as A
from pssparser import refs
from pssparser.refs import Resolution

M3 = """\
import std_pkg::*;
const int WIDTH = 8;
component pss_top {
  int a = 0xFF;
  bit[32] b = 32'hDEAD;
  action go_a {
    rand bit[8] v;
    rand bit[8] u;
    constraint lim_c { v < 5; }
    constraint { v > 1; }
    dynamic constraint dyn_c { u < 3; }
    constraint { dyn_c; }
    exec body { a = a/*c*/+b; message(LOW, "see http://x.com/doc"); }
  }
  exec file \"\"\"out_{{a}}.c\"\"\" = \"\"\" printf("{{a}} {{b}}"); \"\"\";
  exec file "plain_{{a}}.c" = \"\"\" x(); \"\"\";
}
"""

_LIVE = []


def _link(src):
    p = pssparser.Parser()
    p.parses([("m3.pss", src)])
    p.link()
    _LIVE.append(p)
    return p


def _nodes(p, cls):
    found = []

    class V(A.VisitorBase):
        pass

    def visit(self, n):
        found.append(n)
        getattr(A.VisitorBase, "visit" + cls)(self, n)
    setattr(V, "visit" + cls, visit)
    for u in p.user_units():
        u.accept(V())
    return found


def test_constraint_name_has_its_own_location():
    """AC3."""
    blocks = _nodes(_link(M3), "ConstraintBlock")
    named = {b.getName().getId(): b for b in blocks if b.getName() is not None}
    loc = named["lim_c"].getName().getLocation()
    assert (loc.lineno, loc.linepos, loc.extent) == (9, 16, 5)


def test_unnamed_constraint_has_no_name():
    """AC5 (FR-002-Q4): None, not an empty ExprId."""
    blocks = _nodes(_link(M3), "ConstraintBlock")
    assert sum(1 for b in blocks if b.getName() is None) == 2


def test_constraint_name_is_a_declaration_and_its_uses_bind():
    occs = refs.occurrences(_link(M3))
    lim = [o for o in occs if o.text == "lim_c"]
    assert len(lim) == 1 and lim[0].is_declaration
    dyn = [o for o in occs if o.text == "dyn_c"]
    assert [o.line for o in dyn] == [11, 12]
    assert dyn[0].is_declaration and not dyn[1].is_declaration
    assert dyn[1].decl == dyn[0].decl
    assert dyn[1].resolution is Resolution.USER


def test_triple_quoted_filename_is_a_template():
    """AC4, triple-quoted form: the filename's {{a}} binds to field a."""
    p = _link(M3)
    blocks = _nodes(p, "ExecTargetTemplateBlock")
    tmpl = [b for b in blocks if b.getFilename_template() is not None]
    assert len(tmpl) == 1
    occs = refs.occurrences(p)
    a = [o for o in occs if o.text == "a" and o.line == 15]
    assert len(a) == 2          # the filename's and the body's
    assert all(o.decl_location[:3] == (1, 4, 7) for o in a)


def test_double_quoted_filename_is_literal():
    """AC4, double-quoted form: literal text, no template, no reference."""
    p = _link(M3)
    blocks = _nodes(p, "ExecTargetTemplateBlock")
    plain = [b for b in blocks if b.getFilename() == "plain_{{a}}.c"]
    assert len(plain) == 1
    assert plain[0].getFilename_template() is None
    assert not [o for o in refs.occurrences(p) if o.line == 16 and o.text == "a"]
