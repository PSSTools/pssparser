"""``extend monitor`` and the extension-kind check (symbol-resolution plan 11.5, F27).

Syntax 85 (17.2.1) has an ``extend monitor`` form that Annex B's
``extend_stmt`` leaves out (pss31-prd-spec-comments item 9). pssparser follows
Syntax 85, which Example 246, 16.1 d) and 16.6 rely on.

LRM 17.2: "An extension statement explicitly specifies the kind of type being
extended, which shall agree with the specific type named". A mismatch is
PSS058.
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


# Example 246, with the component's name corrected: the example declares
# `pcie_c` and extends `pci_c::read_after_write` (spec comment 9).
EX246 = """\
component pcie_c {
  action read { bit [32] addr; }
  action write { bit [32] addr; }

  monitor read_after_write {
    read r;
    write w;
    activity {
      w;
      r;
    }
  }
}

package additional_checks_pkg {
  extend monitor pcie_c::read_after_write {
    constraint { r.addr == w.addr; }
  }
}
"""


def test_lrm_example_246():
    assert markers(EX246) == []


def test_the_extension_body_binds_to_the_monitors_fields():
    assert sorted(bindings(EX246, "r", "w")) == [
        ("r", 10, 6), ("r", 17, 6), ("w", 9, 7), ("w", 17, 7)]


def test_lrm_example_246_as_written_names_an_unknown_component():
    ms = messages(EX246.replace("extend monitor pcie_c", "extend monitor pci_c"))
    assert len(ms) == 1 and ms[0][1] == 16 and "pci_c" in ms[0][2]


def test_a_member_the_extension_adds_is_visible():
    code = """\
component pss_top {
  action A { rand bit[8] v; }
  monitor m {
    A a;
    activity { a; }
  }
  extend monitor m {
    A b;
    constraint { b.v == a.v; }
  }
  monitor n {
    m mm;
    activity { mm; }
    constraint { mm.b.v == 1; }
  }
}
"""
    assert markers(code) == []
    assert ("b", 14, 8) in bindings(code, "b")


def test_an_extension_may_supply_the_activity():
    code = """\
component pss_top {
  action A { }
  monitor m {
    A a;
  }
  extend monitor m {
    activity { a; }
  }
}
"""
    assert markers(code) == []


def test_an_abstract_monitor_may_be_extended():
    # 16.1 d): "Abstract monitors may be extended, but the monitor remains
    # abstract".
    code = """\
component pss_top {
  action A { }
  abstract monitor m {
    A a;
  }
  extend monitor m {
    constraint { true; }
  }
}
"""
    assert markers(code) == []


def test_extend_monitor_nested_in_a_component_extension():
    # 17.3: an extension inside a component extends a type the component
    # declares.
    code = """\
component C {
  action A { rand bit[8] v; }
  monitor m {
    A a;
    activity { a; }
  }
}
extend component C {
  extend monitor m {
    constraint { a.v == 1; }
  }
}
"""
    assert markers(code) == []
    assert ("a", 10, 4) in bindings(code, "a")


def test_an_unknown_member_in_a_monitor_extension_is_reported():
    code = """\
component pss_top {
  action A { }
  monitor m {
    A a;
  }
  extend monitor m {
    constraint { nope == 1; }
  }
}
"""
    assert [line for _, line in markers(code)] == [7]


def test_extending_a_monitor_instance():
    code = """\
component pss_top {
  action A { rand bit[8] v; }
  monitor m <int N = 1> {
    A a;
    activity { a; }
  }
  extend monitor m<2> {
    constraint { a.v == N; }
  }
  monitor top {
    m<2> x;
    m<3> y;
    activity { x; y; }
  }
}
"""
    assert markers(code) == []


# --- The extension kind must agree with the type (17.2) ---------------------

KINDS = """\
struct s { int f; }
buffer b { int f; }
resource r { int f; }
state st { int f; }
stream sm { int f; }
annotation an { int f; }
component pss_top {
  action A { }
  monitor M { }
}
"""


def test_every_matching_kind_links():
    code = KINDS + """\
extend struct s { int g; }
extend buffer b { int g; }
extend resource r { int g; }
extend state st { int g; }
extend stream sm { int g; }
extend annotation an { int g; }
extend action pss_top::A { int g; }
extend monitor pss_top::M { constraint { true; } }
extend component pss_top { int g; }
"""
    assert markers(code) == []


def test_extend_action_on_a_monitor_is_reported():
    ms = messages(KINDS + "extend action pss_top::M { }\n")
    assert ms == [("PSS058", 11,
                   "'extend action' names 'M', which is a monitor; "
                   "write 'extend monitor M' (17.2)")]


def test_extend_monitor_on_an_action_is_reported():
    ms = messages(KINDS + "extend monitor pss_top::A { }\n")
    assert ms == [("PSS058", 11,
                   "'extend monitor' names 'A', which is an action; "
                   "write 'extend action A' (17.2)")]


def test_each_mismatch_is_reported():
    code = KINDS + """\
extend struct b { int g; }
extend buffer s { int g; }
extend resource st { int g; }
extend component s { int g; }
extend struct pss_top { int g; }
extend annotation s { int g; }
extend struct an { int g; }
"""
    assert markers(code) == [("PSS058", n) for n in range(11, 18)]


def test_a_mismatched_extension_adds_nothing():
    code = KINDS + """\
extend buffer s { int g; }
struct u {
  s x;
  constraint { x.g == 1; }
}
"""
    codes = [c for c, _ in markers(code)]
    assert codes[0] == "PSS058"
    assert len(codes) == 2


def test_a_mismatched_nested_extension_is_reported():
    code = """\
component C {
  struct s { int f; }
}
extend component C {
  extend buffer s { int g; }
}
"""
    assert markers(code) == [("PSS058", 5)]


def test_a_mismatched_instance_extension_is_reported():
    code = """\
struct s <int N = 1> { int f; }
extend buffer s<2> { int g; }
"""
    assert markers(code) == [("PSS058", 2)]


def test_extend_struct_on_an_enum_is_reported():
    ms = messages("enum E { A, B }\nextend struct E { int x; }\n")
    assert ms == [("PSS058", 2,
                   "'extend struct' names 'E', which is an enum; "
                   "write 'extend enum E' (17.2)")]


def test_extend_enum_on_a_struct_is_pss005():
    # Already reported before 11.5, as "not an enum type".
    assert markers("struct S { int a; }\nextend enum S { Q }\n") == [("PSS005", 2)]
