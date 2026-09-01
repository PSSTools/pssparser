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


def test_super_in_exec_is_accepted():
    """`super;` invokes the base type's same-kind exec (LRM 17.1, 20.1.4.2).

    Without it a derived exec silently *replaces* the base's, so this is the
    correct form of the most damaging inheritance mistake in PSS.

    Closed in plan section 37.  `exec_stmt` has two alternatives and
    ``visitExec_block`` handled only one, so ``procedural_stmt()`` came back
    null for ``super;`` and went straight into ``mkExecStmt()``, which
    dereferenced it.
    """
    assert_clean(SUPER_IN_EXEC)


def test_super_in_exec_does_not_crash():
    """Weaker companion to the above: survives even before the feature lands."""
    assert_no_crash(SUPER_IN_EXEC, description="super; in an exec block")


def test_super_in_exec_builds_a_node():
    """Not merely accepted -- represented.

    Skipping the statement would also have made the two tests above pass,
    while discarding the one thing that distinguishes extending a base exec
    from replacing it.  That is the shape of the LRM 17.5 ``override`` block
    defect, and worth a test rather than a comment.
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from pssparser.parser import Parser
    import pssparser.ast as ast

    assert hasattr(ast, "ProceduralStmtSuper")

    p = Parser()
    p.parses([("t.pss", SUPER_IN_EXEC)])
    root = p.link()
    assert root is not None

    # Walk for the node itself.  Asserting only that the class exists and
    # that the link succeeded -- which is all this test did at first -- is
    # exactly the check that a skipped statement passes.
    seen = []

    def walk(n, depth=0):
        if n is None or depth > 30:
            return
        if type(n).__name__ == "ProceduralStmtSuper":
            seen.append(n)
        for acc in ("getChildren", "getBody"):
            g = getattr(n, acc, None)
            if not callable(g):
                continue
            try:
                v = g()
            except Exception:
                continue
            if acc == "getChildren":
                for c in v:
                    walk(c, depth+1)
            else:
                walk(v, depth+1)

    walk(root)
    assert seen, "`super;` linked, but built no ProceduralStmtSuper node"


def test_statements_after_super_are_still_resolved():
    """The statement must not swallow the rest of the block."""
    assert_rejects([("t.pss", """
        component c {
            action a { exec body { } }
            action b : a { exec body { super; int v; v = nosuch; } }
        }
    """)], "nosuch")


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


def test_sizeof_user_type_is_accepted():
    """LRM 21.13.2. This is how a model computes layout without hard-coding it.

    Closed by the §4.9 static-ref-path fix, and the cause was not where phase
    1.3 recorded it. ``sizeof_s`` is declared in ``addr_reg_pkg``, and
    ``TaskResolveRefs::visitExprRefPathStatic`` never resolved a template
    argument at the *use* site, so the unqualified ``s`` was looked up in
    ``addr_reg_pkg`` rather than in ``p``, where it is declared. Hence the
    "did you mean 'set'?" suggestion the symptom carried: ``set`` is a builtin,
    and the builtins were the only types the lookup could see.
    """
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


# ---------------------------------------------------------------------------
# Cyclic inheritance -- a ring in the super-type graph
#
# Every case below overflowed the stack, in TaskFindPathElem's member search:
# it walks from a type to its base until it finds the name or runs out of
# bases, and a ring means it never runs out.
#
# Two properties make this worth a block of its own rather than one test.
#
# It is the FAILING lookup that crashes. A lookup that hits stops at the scope
# holding the name, so `x.a` was fine and `x.nope` was a segfault -- the bug
# was reachable only by a typo, which is why a cyclic model could sit in a
# suite looking healthy.
#
# And the cycle itself was accepted in silence. With no lookup through it at
# all, a model containing one linked with `0 errors`, so the illegal input was
# never rejected, only occasionally fatal. TaskCheckTypeCycles reports it now;
# the walkers carry loop guards so that they terminate even if it does not.
# ---------------------------------------------------------------------------

SELF_INHERIT = """
struct S : S { int a; };
component pss_top { S x; }
"""

MUTUAL_INHERIT = """
struct A : B { int a; };
struct B : A { int b; };
component pss_top { A x; }
"""

MUTUAL_INHERIT_MISS = """
struct A : B { int a; };
struct B : A { int b; };
component pss_top {
    A x;
    exec init_down { x.nope = 1; }
}
"""

MUTUAL_INHERIT_HIT = """
struct A : B { int a; };
struct B : A { int b; };
component pss_top {
    A x;
    exec init_down { x.a = 1; }
}
"""

THREE_CYCLE_MISS = """
struct A : C { };
struct B : A { };
struct C : B { };
component pss_top {
    A x;
    exec init_down { x.nope = 1; }
}
"""

COMPONENT_CYCLE_MISS = """
component C : D { }
component D : C { }
component pss_top {
    C c;
    exec init_down { c.nope = 1; }
}
"""

ACTION_CYCLE_MISS = """
component pss_top {
    action A : B { }
    action B : A { }
    action C { A a; constraint { a.nope == 1; } }
}
"""

TYPEDEF_CYCLE_MISS = """
typedef A B;
typedef B A;
component pss_top {
    A x;
    exec init_down { x.nope = 1; }
}
"""


def test_self_inheritance_is_rejected():
    assert_rejects(SELF_INHERIT, "cyclic inheritance: 'S' -> 'S'")


def test_mutual_inheritance_is_rejected():
    """Rejected on the declaration alone -- no lookup needed to provoke it."""
    assert_rejects(MUTUAL_INHERIT, "cyclic inheritance: 'A' -> 'B' -> 'A'")


def test_mutual_inheritance_is_reported_once():
    """One ring is one mistake.

    Both A and B start a walk that closes the same ring; naming it from each
    end says nothing extra and trains the reader to skim.
    """
    res = assert_rejects(MUTUAL_INHERIT)
    assert res.output.count("cyclic inheritance") == 1, res.describe()


def test_three_type_cycle_names_the_whole_loop():
    """The message has to name the loop, or the user has to find it.

    Order follows the inheritance edges from the reported type, so the text
    is a path the reader can check against the source.
    """
    assert_rejects(THREE_CYCLE_MISS, "cyclic inheritance: 'A' -> 'C' -> 'B' -> 'A'")


def test_failing_lookup_through_a_cycle_does_not_crash():
    """The original crash: the search goes round the ring looking for `nope`."""
    assert_no_crash(MUTUAL_INHERIT_MISS, description="failed lookup through an inheritance cycle")


def test_succeeding_lookup_through_a_cycle_does_not_crash():
    """The control. This shape always worked -- the search stops at `a`.

    Pinned because it is what made the crash look intermittent, so a future
    guard that breaks the hit path would otherwise look like a fix.
    """
    assert_no_crash(MUTUAL_INHERIT_HIT, description="successful lookup through an inheritance cycle")


def test_component_inheritance_cycle_does_not_crash():
    assert_rejects(COMPONENT_CYCLE_MISS, "cyclic inheritance: 'C' -> 'D' -> 'C'")


def test_action_inheritance_cycle_does_not_crash():
    assert_rejects(ACTION_CYCLE_MISS, "cyclic inheritance: 'A' -> 'B' -> 'A'")


def test_typedef_cycle_does_not_crash():
    """A second, independent ring: the typedef alias chain.

    Overflowed the stack in TaskGetElemSymbolScope::visitDataTypeUserDefined,
    which follows an alias to its target with nothing bounding the walk. The
    guard there stops it. Deliberately asserted as "does not crash" and not as
    a diagnostic: TaskCheckTypeCycles checks the *inheritance* graph, so this
    input is reported only through its consequences. Tighten this to
    assert_rejects with a cyclic-typedef message when that check grows an
    alias arm.
    """
    assert_no_crash(TYPEDEF_CYCLE_MISS, description="typedef alias cycle")


# ---------------------------------------------------------------------------
# P7-X3 -- a null child in a `foreach (iter : array)` symbol scope
#
# `visitForeach_constraint_item` pushed `IScopeChildUP(0)` into the scope's
# child list for the `iter : array` form, with the comment "No index is a bit
# odd, but put a placeholder in anyway".  Nothing referred to that slot; every
# visitor that walks a scope's children dereferenced it.
#
# What made it survive so long is that reaching the null needs the identifier to
# *miss* the foreach symtab.  A name found there -- the iteration variable
# itself -- resolves out of the symbol map and never walks the children, so the
# construct looked healthy under exactly the test anyone would write for it.
# Everything else in the body walked, and everything else died: a subscript on
# the iterated array, a subscript on any other array, and any undeclared name.
#
# The cases below are ordered miss-first for that reason.  `test_..._iteration_
# variable_alone` is the control that used to pass, and is pinned so that a
# future change which "fixes" only the hit path cannot look like a fix.
# ---------------------------------------------------------------------------

FOREACH_ITER_LITERAL_SUBSCRIPT = """
component c {
    action a {
        rand int arr[4];
        constraint { foreach (i : arr) { arr[0] == 1; } }
    }
}
"""

FOREACH_ITER_INDEXED_BY_ITERATOR = """
component c {
    action a {
        rand int arr[4];
        constraint { foreach (i : arr) { arr[i] == i; } }
    }
}
"""

FOREACH_ITER_OTHER_ARRAY = """
component c {
    action a {
        rand int arr[4];
        rand int other[4];
        constraint { foreach (i : arr) { other[i] == 1; } }
    }
}
"""

FOREACH_ITER_UNKNOWN_NAME = """
component c {
    action a {
        rand int arr[4];
        constraint { foreach (i : arr) { nope[i] == 1; } }
    }
}
"""

FOREACH_ITER_VARIABLE_ONLY = """
component c {
    action a {
        rand int arr[4];
        constraint { foreach (i : arr) { i == 1; } }
    }
}
"""

FOREACH_LEGACY_SUBSCRIPT_FORM = """
component c {
    action a {
        rand int arr[4];
        constraint { foreach (arr[i]) { arr[i] == i; } }
    }
}
"""


def test_foreach_iterator_form_with_a_literal_subscript_is_accepted():
    """The smallest case, and the one that shows the iterator is beside the point.

    `arr[0]` does not mention `i` at all.  It crashed because resolving `arr`
    misses the foreach symtab and falls through to the enum search, which walks
    every child of the scope -- including the null.
    """
    assert_clean(FOREACH_ITER_LITERAL_SUBSCRIPT)


def test_foreach_iterator_form_indexed_by_its_iterator_is_accepted():
    """The idiomatic spelling, and the one the PSS 3.1 corpus file uses."""
    assert_clean(FOREACH_ITER_INDEXED_BY_ITERATOR)


def test_foreach_iterator_form_indexing_another_array_is_accepted():
    assert_clean(FOREACH_ITER_OTHER_ARRAY)


def test_unknown_name_in_a_foreach_body_is_reported_not_crashed():
    """The assertion that keeps the fix honest.

    An undeclared name is the *deepest* path into the old crash: it misses the
    symtab, misses the enum search, and goes on to imports.  Pinning the
    diagnostic rather than mere survival is what stops a guard that silently
    swallows the miss from passing as a fix.
    """
    assert_rejects(FOREACH_ITER_UNKNOWN_NAME, "unknown identifier 'nope'")


def test_foreach_iteration_variable_alone_is_accepted():
    """The control.  This shape always worked -- `i` is in the foreach symtab.

    Pinned because it is the reason the defect looked absent: a test written
    for `foreach (i : arr)` naturally reaches for the iteration variable, and
    that is the one expression which never touches the null.
    """
    assert_clean(FOREACH_ITER_VARIABLE_ONLY)


def test_legacy_subscript_foreach_form_is_accepted():
    """The other control: `foreach (arr[i])` took a different builder branch.

    That branch pushes a real index field, so it never held a null and never
    crashed.  Pinned so the two forms are asserted side by side -- the pair is
    what localises a regression to the builder branch rather than to `foreach`.
    """
    assert_clean(FOREACH_LEGACY_SUBSCRIPT_FORM)
