"""Linking must not depend on the order files are handed to the linker.

PSS has no declare-before-use rule: a package, type or extension may appear in
any file, and the files may be presented in any order.  A build system that
globs a directory, an editor that opens one file, and a user who lists files
by hand all produce different orders, so an order-sensitive linker fails
seemingly at random.

Each test below links the same model twice, with the declaration first and
with the use first, and requires both to succeed.
"""
import pytest

from ..test_helpers import parse_multi_file


DEF_BASE = """
package defs_pkg {
    import addr_reg_pkg::*;
    pure component my_regs_c : reg_group_c { }
}
"""

USE_BASE = """
import addr_reg_pkg::*;
import defs_pkg::*;
component user_c {
    my_regs_c regs;
    solve function void go(addr_handle_t h) { regs.set_handle(h); }
}
component pss_top { user_c u; }
"""


@pytest.mark.parametrize("use_first", [False, True], ids=["def-first", "use-first"])
def test_inherited_member_resolves_in_either_file_order(use_first):
    """A member reached through a super type, with the base declared elsewhere.

    The super-type reference used to be resolved only when the walk reached
    the declaring type, so a use in an earlier file saw a null super and
    reported "Failed to find elem set_handle". See TaskResolveSuperTypes.
    """
    files = [("use.pss", USE_BASE), ("def.pss", DEF_BASE)]
    if not use_first:
        files.reverse()
    parse_multi_file(files)


DEF_EXT = """
package t_pkg { struct s_s { bit[4] f; } }
"""

USE_EXT = """
import t_pkg::*;
component c { }
extend component c {
    s_s fld;
    target function void go() { fld.f = 1; }
}
component pss_top { c c0; }
"""


@pytest.mark.parametrize("use_first", [False, True], ids=["def-first", "use-first"])
def test_extension_member_resolves_in_either_file_order(use_first):
    """An extension in one file contributing a field typed from another."""
    files = [("use.pss", USE_EXT), ("def.pss", DEF_EXT)]
    if not use_first:
        files.reverse()
    parse_multi_file(files)
