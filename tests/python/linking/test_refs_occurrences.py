"""
pssparser.refs.occurrences(): every identifier in the user's files, with the
declaration it names (pss-scrambler FR-001).

The reproducer and acceptance criteria are the request's own
(../pss-scrambler/requests/FR-001-*.md), with AC3 and AC5 read as the
answers to FR-001-Q1 and -Q2 settled them: a collection method, `comp` and
`this` are `builtin`, with no source declaration.
"""
import pytest

import pssparser
from pssparser import refs, tokens
from pssparser.refs import Resolution

M1 = """\
package my_pkg {
  enum mode_e { FAST, SLOW };
  struct cfg_s { rand bit[8] depth; mode_e mode; }
  function bit[8] calc(bit[8] x) { return x + 1; }
}
"""

M2 = """\
import std_pkg::*;
import my_pkg::*;
component sub_c {
  int count = 0xFF;
  list<int> items;
  action work_a {
    rand my_pkg::cfg_s cfg;
    rand bit[8] val;
    constraint val_c { val < cfg.depth; cfg.mode == FAST; }
    exec body {
      items.push_back(calc(val));
      comp.count = comp.count + 1;
      message(LOW, "doing //work");
    }
  }
}
component pss_top {
  sub_c sub;
  action entry_a {
    activity {
      do sub_c::work_a with { val == 3; };
    }
  }
}
extend component sub_c { int extra; }
"""

# Contextual keywords that the lexer returns as ID tokens but that name
# nothing (AC1).
NOT_NAMES = {"body"}


def _link(files, expect_error=False):
    p = pssparser.Parser()
    p.parses(files)
    if expect_error:
        with pytest.raises(pssparser.ParseException):
            p.link()
    else:
        p.link()
    return p


def _occs(files, expect_error=False):
    return refs.occurrences(_link(files, expect_error))


def _at(occs, fileid, line, text, nth=0, decl=None):
    hits = [o for o in occs
            if (o.fileid, o.line, o.text) == (fileid, line, text)
            and (decl is None or o.is_declaration == decl)]
    assert len(hits) > nth, "no occurrence of %r on %d:%d" % (text, fileid, line)
    return hits[nth]


@pytest.fixture(scope="module")
def occs():
    return _occs([("m1.pss", M1), ("m2.pss", M2)])


def test_every_id_token_is_an_occurrence(occs):
    """AC1: one entry per ID token that names something."""
    for fileid, src in ((1, M1), (2, M2)):
        want = {(t.line, t.col + 1, t.text)
                for t in tokens.tokenize(src).code()
                if t.type_name == "ID" and t.text not in NOT_NAMES}
        have = {(o.line, o.col, o.text) for o in occs if o.fileid == fileid}
        assert want - have == set(), "ID tokens with no occurrence"
        assert have - want == set(), "occurrences that are not ID tokens"


def test_occurrences_are_sorted_and_unique(occs):
    keys = [(o.fileid, o.line, o.col) for o in occs]
    assert keys == sorted(keys)
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize("fileid,line,text,decl_at", [
    (2, 9, "depth", (1, 3, 30)),     # member of a member path
    (2, 12, "count", (2, 4, 7)),     # member through `comp`
    (2, 7, "my_pkg", (1, 1, 9)),     # qualifier of a qualified type name
    (1, 4, "x", (1, 4, 31)),         # function parameter
    (2, 21, "val", (2, 8, 17)),      # field named in `with { ... }`
    (2, 25, "sub_c", (2, 3, 11)),    # `extend` target
    (2, 7, "cfg_s", (1, 3, 10)),
    (2, 9, "mode", (1, 3, 44)),
    (2, 9, "FAST", (1, 2, 17)),
    (2, 11, "calc", (1, 4, 19)),
    (2, 21, "work_a", (2, 6, 10)),
])
def test_resolves_to_user_declaration(occs, fileid, line, text, decl_at):
    """AC2."""
    o = _at(occs, fileid, line, text, decl=False)
    assert o.resolution is Resolution.USER
    assert not o.is_declaration
    assert o.decl is not None
    assert o.decl_location[:3] == decl_at


@pytest.mark.parametrize("line,text,resolution", [
    (13, "message", Resolution.LIBRARY),
    (13, "LOW", Resolution.LIBRARY),
    (1, "std_pkg", Resolution.LIBRARY),
    (11, "push_back", Resolution.BUILTIN),
    (5, "list", Resolution.BUILTIN),
    (12, "comp", Resolution.BUILTIN),
])
def test_resolves_to_library_or_builtin(occs, line, text, resolution):
    """AC3, as FR-001-Q1 restated it: classified by `resolution`."""
    o = _at(occs, 2, line, text)
    assert o.resolution == resolution
    if resolution is Resolution.LIBRARY:
        assert o.decl_location.fileid == 0
    else:
        assert o.decl_location is None


def test_same_declaration_same_decl(occs):
    """AC4: occurrences group by `decl` -- by equality and by hash."""
    val = [o for o in occs if o.text == "val"]
    assert len(val) == 4
    assert all(o.decl == val[0].decl for o in val)
    assert len({o.decl for o in val}) == 1
    assert [o.is_declaration for o in val] == [True, False, False, False]

    # And different declarations do not group.
    located = [o for o in occs if o.decl_location is not None]
    assert len({o.decl for o in located}) == len({o.decl_location for o in located})


def test_decl_is_the_most_derived_wrapper(occs):
    assert type(_at(occs, 2, 9, "depth").decl).__name__ == "Field"
    assert type(_at(occs, 2, 11, "calc").decl).__name__ == "FunctionPrototype"
    assert type(_at(occs, 2, 7, "my_pkg").decl).__name__ == "PackageScope"


def test_declarations_are_flagged(occs):
    for line, text in [(3, "sub_c"), (4, "count"), (6, "work_a"), (7, "cfg"),
                       (9, "val_c"), (25, "extra")]:
        o = _at(occs, 2, line, text)
        assert o.is_declaration, text
        assert o.resolution is Resolution.USER
        assert o.decl_location == o.location


def test_link_failure_still_reports_everything():
    """AC5, as FR-001-Q2 restated it: only the names the missing import
    would have supplied are unresolved."""
    m2 = M2.replace("import std_pkg::*;\n", "")
    occs = _occs([("m1.pss", M1), ("m2.pss", m2)], expect_error=True)
    unresolved = sorted(o.text for o in occs
                        if o.resolution is Resolution.UNRESOLVED)
    assert unresolved == ["LOW", "message"]
    assert all(o.decl is None for o in occs
               if o.resolution is Resolution.UNRESOLVED)
    assert len(occs) == len(_occs([("m1.pss", M1), ("m2.pss", M2)])) - 1


def test_resolution_is_a_closed_string_enum():
    assert [r.value for r in Resolution] == [
        "user", "library", "builtin", "unresolved", "dependent"]
    assert Resolution.BUILTIN == "builtin"


def test_this_is_builtin():
    # The linker does not support `this` yet (known-issues.md, R-THIS), so
    # the member after it is unbound. `this` itself is still a built-in.
    occs = _occs([("t.pss", """\
component pss_top {
  action sub_a { rand int g; }
  action top_a {
    rand int f;
    activity {
      do sub_a with { g == this.f; };
    }
  }
}
""")], expect_error=True)
    this = _at(occs, 1, 6, "this")
    assert this.resolution is Resolution.BUILTIN
    assert this.decl is None
    assert _at(occs, 1, 6, "g").decl_location[:3] == (1, 2, 27)


# ---------------------------------------------------------------------------
# Overrides and shadowing (FR-001-Q4)
# ---------------------------------------------------------------------------

INHERIT = """\
struct base_s {
  rand bit[8] v;
  constraint lim_c { v < 10; }
}
struct mid_s : base_s {
  constraint lim_c { v < 5; }
}
struct leaf_s : mid_s {
  rand bit[8] v;
  constraint lim_c { v < 2; }
}
"""


def test_base_decl_is_the_immediate_base():
    occs = _occs([("t.pss", INHERIT)])
    lim = [o for o in occs if o.text == "lim_c"]
    assert [o.line for o in lim] == [3, 6, 10]
    assert lim[0].base_decl is None
    assert lim[1].base_decl == lim[0].decl
    assert lim[2].base_decl == lim[1].decl


def test_shadowing_field_has_base_decl():
    occs = _occs([("t.pss", INHERIT)])
    base_v = _at(occs, 1, 2, "v")
    leaf_v = _at(occs, 1, 9, "v")
    assert leaf_v.is_declaration
    assert leaf_v.decl != base_v.decl
    assert leaf_v.base_decl == base_v.decl
    # A reference binds to the nearest declaration.
    assert _at(occs, 1, 10, "v").decl == leaf_v.decl
    assert _at(occs, 1, 6, "v").decl == base_v.decl


# ---------------------------------------------------------------------------
# Templates (FR-001-Q3, -Q5)
# ---------------------------------------------------------------------------

TEMPLATE = """\
struct tmpl_s <int W = 4> {
  rand bit[W] depth;
}
component pss_top {
  tmpl_s<8> a;
  tmpl_s<16> b;
  exec init_down {
    a.depth = 1;
    b.depth = 2;
  }
}
"""


def test_member_of_a_specialization_is_the_generics_member():
    occs = _occs([("t.pss", TEMPLATE)])
    depth = [o for o in occs if o.text == "depth"]
    assert [o.line for o in depth] == [2, 8, 9]
    assert all(o.decl == depth[0].decl for o in depth)
    assert all(o.decl_location[:3] == (1, 2, 15) for o in depth)
    assert _at(occs, 1, 5, "tmpl_s").decl_location[:3] == (1, 1, 8)
    assert _at(occs, 1, 2, "W").decl_location[:3] == (1, 1, 20)


GENERIC = """\
struct a_s { rand bit[8] x; }
struct b_s { rand bit[8] x; }
const int K = 3;
struct tmpl_s <int W = 4, type T = a_s> {
  rand bit[W] depth;
  rand T t;
  constraint { t.x < K; depth < W; }
}
component pss_top {
  tmpl_s<8> a;
  tmpl_s<16, b_s> b;
}
"""


def test_generic_body_binds_through_its_specializations():
    """A name in a generic body is bound when every specialization binds it
    to the same declaration; one that depends on a parameter is
    `dependent` (FR-001-Q5)."""
    occs = _occs([("t.pss", GENERIC)])
    assert _at(occs, 1, 7, "t").decl_location[:3] == (1, 6, 10)
    assert _at(occs, 1, 7, "K").decl_location[:3] == (1, 3, 11)
    assert _at(occs, 1, 7, "W").decl_location[:3] == (1, 4, 20)
    assert _at(occs, 1, 6, "T").decl_location[:3] == (1, 4, 32)
    x = _at(occs, 1, 7, "x")
    assert x.resolution is Resolution.DEPENDENT
    assert x.decl is None


# ---------------------------------------------------------------------------
# Functions and packages spelled more than once
# ---------------------------------------------------------------------------

def test_prototype_and_definition_group():
    occs = _occs([("t.pss", """\
package p {
  function int f(int a);
  function int f(int a) { return a; }
}
component pss_top {
  exec init_down { int x = p::f(1); }
}
""")])
    f = [o for o in occs if o.text == "f"]
    assert [o.line for o in f] == [2, 3, 6]
    assert f[0].decl == f[1].decl == f[2].decl
    assert f[0].is_declaration and f[1].is_declaration


def test_package_split_across_files_groups():
    occs = _occs([
        ("a.pss", "package p { const int A = 1; }\n"),
        ("b.pss", "package p { const int B = 2; }\n"),
        ("c.pss", "component pss_top { int x = p::A + p::B; }\n")])
    p = [o for o in occs if o.text == "p"]
    assert len(p) == 4
    assert len({o.decl for o in p}) == 1
    assert _at(occs, 3, 1, "B").decl_location[:3] == (2, 1, 23)


def test_occurrences_outlive_the_parser():
    occs = refs.occurrences(_link([("m1.pss", M1), ("m2.pss", M2)]))
    import gc
    gc.collect()
    assert _at(occs, 2, 9, "depth").decl.getName().getId() == "depth"


def test_occurrences_needs_a_linked_parser():
    with pytest.raises(ValueError):
        refs.occurrences(pssparser.Parser())
