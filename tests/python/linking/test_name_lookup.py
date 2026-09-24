"""One lookup procedure (symbol-resolution plan WS6.2, "stage 1").

``NameLookup`` (src/NameLookup.h) implements report D §A
(``docs/design/symbol-resolution/D-namespaces.md``). These are the orderings the
old per-scope-kind visitor got wrong, each against the repro in
``repros/D-namespace/`` it was found with: divergences #9, #10, #11 and #13,
ND-4, ND-5, ND-7 and ND-8.
"""
import pytest

import pssparser
from pssparser import core
from pssparser.utils import SymbolScopeUtil

from ..test_helpers import parse_collect
from .test_activity_scopes import assert_links_and_binds


def errors(code):
    _, markers = parse_collect(code)
    return [m["message"] for m in markers if m["severity"] == "error"]


# ---------------------------------------------------------------------------
# A type level: members, own parameters, bases, then imports (18.3 b.1-b.4)
# ---------------------------------------------------------------------------

def test_an_inherited_member_hides_a_component_import(tmp_path):
    """#9 (d1): b.3 before b.4. `s` is base_c's, not P's."""
    assert_links_and_binds(tmp_path, """
package P { struct s { rand int from_p; } }
component base_c { struct s { rand int from_base; } }
component der_c : base_c {
  import P::*;
  struct w { rand s f; constraint f.from_base == 1; }
}
component pss_top { der_c d; }
""")


def test_a_base_components_imports_do_not_reach_a_derived_component():
    """#10 (d2): b.3 searches a base type's members, never its imports."""
    assert errors("""
package P { struct s { rand int from_p; } }
component base_c { import P::*; }
component der_c : base_c {
  struct w { rand s f; }
}
component pss_top { der_c d; }
""") == ["unknown type 's'; did you mean 'P'?"]


def test_own_template_parameter_hides_a_component_import():
    """#11, ND-7 (d3b): a type's own parameters are searched with its members
    (Q3), so `T` is the parameter, not P::T."""
    assert errors("""
package P { struct T { rand int from_p; } }
struct T2 { rand int x; }
component c<type T = T2> {
  import P::*;
  struct w { rand T f; constraint f.x == 1; }
}
component pss_top { c<> i; }
""") == []


def test_an_enum_item_declared_in_a_base_component(tmp_path):
    """ND-8 (d9): the enum items searched at a base type are the base's, not
    the derived type's a second time."""
    assert_links_and_binds(tmp_path, """
component base_c { enum e_t {AA, BB}; }
component der_c : base_c {
  action a { rand e_t v; constraint v == BB; }
}
component pss_top { der_c d; }
""")


# ---------------------------------------------------------------------------
# An extension member's package chain is the `extend` statement's (17.2)
# ---------------------------------------------------------------------------

def test_the_extension_package_comes_before_the_global_package(tmp_path):
    """ND-5 (d6): `s` in an extension declared in p is p::s, not ::s."""
    assert_links_and_binds(tmp_path, """
struct s { rand int glob; }
package p {
  struct s { rand int in_p; }
  extend component pss_top { struct w { rand s f; constraint f.in_p == 1; } }
}
component pss_top { }
""")


def test_the_extension_package_chain_is_walked_outward(tmp_path):
    """ND-4 (d8): an extension in a::b sees a's members."""
    assert_links_and_binds(tmp_path, """
component pss_top { }
package a {
  struct x { rand int ax; }
  package b {
    extend component pss_top { struct w { rand x f; constraint f.ax == 1; } }
  }
}
""")


def test_the_extended_types_own_members_still_win(tmp_path):
    """The extended type's levels come before the extension's package: an
    extension can refer to what it extends."""
    assert_links_and_binds(tmp_path, """
package q { const int K = 1; }
package p {
  struct m_s { rand int m; }
  struct c { rand m_s K; }
}
package q {
  extend struct p::c { constraint K.m == 1; }
}
""")


# ---------------------------------------------------------------------------
# Imports: resolved once, before any lookup
# ---------------------------------------------------------------------------

def test_imports_in_an_extension_are_resolved():
    """LRM Ex. 248 (b2): the imports inside `extend component` were never
    resolved, and the completeness gate reported each as unbound."""
    assert errors("""
package mem_defs_pkg {
  enum mem_block_tag_e {};
  buffer mem_buff_s { rand mem_block_tag_e mem_block; }
}
package AB_subsystem_pkg {
  import mem_defs_pkg::*;
  extend enum mem_block_tag_e {A_MEM, B_MEM};
}
package soc_config_pkg {
  import mem_defs_pkg::*;
  extend enum mem_block_tag_e {SYS_MEM, DDR};
}
component dma_c {
  import mem_defs_pkg::*;
  action mem2mem_xfer {
    input mem_buff_s src_buff;
    output mem_buff_s dst_buff;
  }
}
extend component dma_c {
  import AB_subsystem_pkg::*;
  import soc_config_pkg::*;
  action dma_test {
    activity {
      do mem2mem_xfer with {
        src_buff.mem_block == A_MEM;
        dst_buff.mem_block == DDR;
      };
    }
  }
}
component pss_top { dma_c d; }
""") == []


def test_an_unresolved_import_is_reported_once():
    assert errors("""
package A { struct s {} }
component pss_top {
  import A::nope;
  import nopkg::*;
}
""") == ["unknown type 'nope' in 'A'", "unknown type 'nopkg'"]


def test_a_specializations_imports_are_resolved():
    """A specialization's imports are copies made after the early pass."""
    assert errors("""
package P { struct s { rand int a; } }
component c<int N = 1> {
  import P::*;
  struct w { rand s f; constraint f.a == N; }
}
component pss_top { c<2> i; c<3> j; }
""") == []


# ---------------------------------------------------------------------------
# A qualified step records the base types it crosses
# ---------------------------------------------------------------------------

def test_a_qualified_inherited_constant_binds_the_base_member():
    """`der_c::N` found N in base_c but left the path on der_c itself: a
    symbol path "could not encode" the step, and it can (ElemKind_Super)."""
    p = pssparser.Parser()
    p.parses([("t.pss", """
component base_c { static const int N = 5; }
component der_c : base_c { }
component pss_top { static const int M = der_c::N; }
""")])
    root = p.link()
    top = SymbolScopeUtil(root).getQname("pss_top")
    m = [c for c in top.getChildren()
         if type(c).__name__ == "Field" and c.getName().getId() == "M"][0]
    target = core.resolveSymbolPathRef(root, m.getInit().getTarget())
    assert type(target).__name__ == "Field"
    assert target.getName().getId() == "N"
