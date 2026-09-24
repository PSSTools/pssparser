"""addr_reg_pkg forwards endianness_e, packed_s and sizeof_s to std_pkg (F28).

LRM 21.13, footnotes 1 and 2: PSS 2.0 declared these in addr_reg_pkg. PSS 2.1
moved them to std_pkg, and "tools shall support referencing these declarations
in either std_pkg or addr_reg_pkg as if they were the same types". Only these
names are forwarded; addr_reg_pkg's own imports are still not re-exported.
"""
from ..test_helpers import parse_collect
from ..template_helpers import sizeof_values


def link(code):
    root, markers = parse_collect(code)
    return root, [m["message"] for m in markers if m["severity"] == "error"]


def test_a_wildcard_import_of_addr_reg_pkg_provides_them():
    root, errs = link("""
import addr_reg_pkg::*;
struct s : packed_s<BIG_ENDIAN> { rand bit[6] a; rand bit[4] b; }
component pss_top {
  action A {
    rand endianness_e e;
    constraint e == LITTLE_ENDIAN;
    constraint sizeof_s<s>::nbytes == 2;
  }
}
""")
    assert errs == []
    # The one sizeof_s, and `s` is packed through the forwarded packed_s.
    assert sizeof_values(root)["s"] == (10, 2)


def test_importing_both_packages_is_not_ambiguous():
    _, errs = link("""
import std_pkg::*;
import addr_reg_pkg::*;
struct s : packed_s<> { rand bit[8] a; }
component pss_top {
  action A { rand endianness_e e; constraint sizeof_s<s>::nbytes == 1; }
}
""")
    assert errs == []


def test_qualified_names_through_addr_reg_pkg():
    root, errs = link("""
struct s : addr_reg_pkg::packed_s<> { rand bit[12] a; }
component pss_top {
  action A {
    rand addr_reg_pkg::endianness_e e;
    constraint addr_reg_pkg::sizeof_s<s>::nbytes == 2;
  }
}
""")
    assert errs == []
    assert sizeof_values(root)["s"] == (12, 2)


def test_a_named_import_through_addr_reg_pkg():
    _, errs = link("""
import addr_reg_pkg::packed_s;
struct s : packed_s<> { rand bit[8] a; }
component pss_top { }
""")
    assert errs == []


def test_addr_reg_pkg_does_not_re_export_its_other_imports():
    """addr_reg_pkg imports executor_pkg; that is not forwarded."""
    _, errs = link("""
import addr_reg_pkg::*;
component pss_top { executor_base_c x; }
""")
    assert len(errs) == 1 and "executor_base_c" in errs[0]
