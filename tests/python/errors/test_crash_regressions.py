"""Regression tests for known crashes.

Every case here killed the process at the time it was written.  Each runs
out-of-process (see ``tests/python/isolation.py``) because an in-process test
cannot survive a segfault -- there is no interpreter left to report the
failure.

Cases that are still open carry ``xfail(strict=True)`` and a ``# PLAN:`` note
naming the phase in ``docs/pssparser-fix-plan.md`` that closes them.  When a
fix lands, the test XPASSes and strict mode turns that into a hard failure --
that is the signal to delete the marker, not to change the test.

The assertion is deliberately stronger than "did not crash": each case pins
the diagnostic the crash should have been, so a fix that merely swallows the
input silently still fails.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from isolation import assert_no_crash, assert_clean, assert_rejects  # noqa: E402


# ---------------------------------------------------------------------------
# 1.1 -- unresolved ref-path in the linker
# ---------------------------------------------------------------------------

UNRESOLVED_ARRAY_REFPATH = """
component c {
    unknown_t ch[4];
    solve function void go() {
        foreach (ch[i]) {
            ch[i].go(i);
        }
    }
}
component pss_top { c c0; }
"""

UNRESOLVED_SCALAR_REFPATH = """
component c {
    unknown_t regs;
    solve function void go() { regs.set_handle(0); }
}
component pss_top { c c0; }
"""


def test_unresolved_scalar_refpath_reports_an_error():
    """The control case: this shape already reports properly.

    It is the behaviour the array form below must converge on, so it is
    pinned here to catch a "fix" that regresses the working path.
    """
    assert_rejects(UNRESOLVED_SCALAR_REFPATH, "unknown type 'unknown_t'")


def test_unresolved_array_refpath_reports_an_error():
    """An unresolved element type must diagnose, not dereference null.

    This is the crash a user hits parsing one file of a multi-file model --
    the normal state while editing -- so it also gates per-file checking in
    an editor or a pre-commit hook.
    """
    assert_rejects(UNRESOLVED_ARRAY_REFPATH, "unknown type 'unknown_t'")


# ---------------------------------------------------------------------------
# 1.2 -- super; in an exec block
# ---------------------------------------------------------------------------

SUPER_IN_EXEC = """
component c {
    action a { exec body { } }
    action b : a { exec body { super; } }
}
component pss_top { c c0; }
"""


# PLAN: phase 1.2 -- AstBuilderInt::mkExecStmt has no case for super
@pytest.mark.xfail(strict=True, reason="phase 1.2: crash in AstBuilderInt::mkExecStmt")
def test_super_in_exec_is_accepted():
    """`super;` invokes the base type's same-kind exec (LRM 17.1, 20.1.4.2).

    Without it a derived exec silently *replaces* the base's, so this is the
    correct form of the most damaging inheritance mistake in PSS.
    """
    assert_clean(SUPER_IN_EXEC)


@pytest.mark.xfail(strict=True, reason="phase 1.2: crash in AstBuilderInt::mkExecStmt")
def test_super_in_exec_does_not_crash():
    """Weaker companion to the above: survives even before the feature lands."""
    assert_no_crash(SUPER_IN_EXEC, description="super; in an exec block")


# ---------------------------------------------------------------------------
# 1.3 -- sizeof_s on a user-defined packed struct
# ---------------------------------------------------------------------------

SIZEOF_USER_TYPE = """
package p {
    import addr_reg_pkg::*;
    struct s : packed_s<> { bit[32] v; }
    static const int N = sizeof_s<s>::nbytes;
}
component pss_top { }
"""

SIZEOF_BUILTIN = """
package p {
    import addr_reg_pkg::*;
    static const int N = sizeof_s<int>::nbytes;
}
component pss_top { }
"""


def test_sizeof_builtin_type_is_accepted():
    """Control: builtins already work, so the fault is specific to user types."""
    assert_clean(SIZEOF_BUILTIN)


# PLAN: phase 1.3 -- TaskComputeTypePackedSize resolves an unresolved path
@pytest.mark.xfail(strict=True, reason="phase 1.3: crash in TaskComputeTypePackedSize")
def test_sizeof_user_type_is_accepted():
    """LRM 21.13.2. This is how a model computes layout without hard-coding it."""
    assert_clean(SIZEOF_USER_TYPE)


def test_sizeof_user_type_does_not_crash():
    assert_no_crash(SIZEOF_USER_TYPE, description="sizeof_s on a user packed struct")


# ---------------------------------------------------------------------------
# 1.4 -- channel_c<T> instance declaration
# ---------------------------------------------------------------------------

CHANNEL_INSTANCE = """
component c {
    import sync_pkg::*;
    channel_c<int> ch;
}
component pss_top { c c0; }
"""

SYNC_IMPORT_ONLY = """
component c { import sync_pkg::*; }
component pss_top { c c0; }
"""


def test_sync_pkg_import_is_accepted():
    """Control: the import alone is fine; the instance declaration is not."""
    assert_clean(SYNC_IMPORT_ONLY)


# Phase 1.4.  Fixed as a side effect of the template-specialization work: the
# crash was TaskCopyAst returning null on ``channel_c``'s body, not anything
# specific to channels.  Kept as a regression guard.
def test_channel_instance_is_accepted():
    """LRM 21.9.1. Without this, all target-time synchronization is unreachable."""
    assert_clean(CHANNEL_INSTANCE)


def test_channel_instance_does_not_crash():
    assert_no_crash(CHANNEL_INSTANCE, description="channel_c<T> instance declaration")


# ---------------------------------------------------------------------------
# 1.5 -- prev in a state-object constraint
# ---------------------------------------------------------------------------

PREV_CONSTRAINT = """
package p {
    enum m_e { A, B }
    state s_s { rand m_e m; constraint m != prev.m; }
}
component c {
    import p::*;
    pool s_s sp;
    bind sp *;
    action w { output s_s o; }
}
component pss_top { c c0; }
"""


# PLAN: phase 1.5/3.7 -- `prev` is not registered as a built-in state reference
@pytest.mark.xfail(strict=True, reason="phase 3.7: `prev` does not resolve")
def test_prev_reference_is_accepted():
    """`prev` refers to the previous state object (LRM 9.3.3.1 g)."""
    assert_clean(PREV_CONSTRAINT)


def test_prev_reference_does_not_abort():
    """Even unresolved, `prev` must not reach the user as an abort.

    In a larger model this path hits ``DEBUG_FATAL`` in AstSymbolTableIterator,
    which throws ``std::runtime_error`` with an empty ``what()`` and aborts
    (exit 134).  An internal invariant must never terminate the CLI.
    """
    assert_no_crash(PREV_CONSTRAINT, description="prev in a state constraint")
