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


# A path through a member whose type is declared in a LATER file. Resolution
# runs in file order, so the walk reaches `r` in `regs.r.w(k)` before `r`'s own
# type reference has been visited. It used to stop there without a word,
# leaving `w` -- and the call's arguments -- unbound; the completeness gate
# (TaskCheckRefsResolved) then reported each as a pssparser defect. Such a
# path is now retried once every declaration is bound
# (TaskResolveRefs::deferUntilTypesBound).

DEF_HOP = """
package hop_pkg {
    struct s_t { int x; }
    component inner_c { function void w(int v) { } function void ws(s_t v) { } }
    component grp_c { inner_c r; inner_c rs[2]; }
}
"""

USE_HOP = """
import hop_pkg::*;
component pss_top {
    grp_c regs;
    function void f() {
        int k;
        s_t vec;
        regs.r.w(k);
        regs.r.ws(vec);
        regs.rs[1].w(k);
    }
}
"""


@pytest.mark.parametrize("use_first", [False, True], ids=["def-first", "use-first"])
def test_a_path_through_a_later_files_member_type_resolves(use_first):
    files = [("use.pss", USE_HOP), ("def.pss", DEF_HOP)]
    if not use_first:
        files.reverse()
    parse_multi_file(files)


@pytest.mark.parametrize("use_first", [False, True], ids=["def-first", "use-first"])
def test_a_missing_member_past_a_deferred_element_is_reported_once(use_first):
    """The retry must still report what is wrong in the part it reaches, and
    only once."""
    from ..isolation import assert_rejects
    files = [("use.pss", USE_HOP.replace("regs.r.w(k);", "regs.r.nosuch(k);")),
             ("def.pss", DEF_HOP)]
    if not use_first:
        files.reverse()
    res = assert_rejects(files, "nosuch")
    assert res.output.count("Failed to find elem nosuch") == 1, res.describe()


@pytest.mark.parametrize("use_first", [False, True], ids=["def-first", "use-first"])
def test_an_error_before_the_deferred_element_is_not_repeated(use_first):
    """An argument the first walk already diagnosed is walked again by the
    retry; it must not be reported twice."""
    from ..isolation import assert_rejects
    files = [("use.pss", USE_HOP.replace("regs.r.w(k);", "regs.r.w(nope);")),
             ("def.pss", DEF_HOP)]
    if not use_first:
        files.reverse()
    res = assert_rejects(files, "nope")
    assert res.output.count("unknown identifier 'nope'") == 1, res.describe()
