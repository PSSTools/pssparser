"""Using a template parameter -- and using a generic that has a body.

Binding a parameter correctly only matters if uses resolve through it, so
these tests declare an argument type with a distinctively-named member and
then reach that member through the parameter.  A wrong binding produces "no
member ``zork``" rather than accidentally succeeding against a member that
happens to exist on both types.

Everything here runs **out of process**.  Most of these cases used to segfault,
and an in-process ``try/except`` cannot catch a segfault -- there is no
interpreter left to run the handler.  They are kept out of process now that
they pass, because a regression here would take the test session down with it
rather than failing one test.

Controls
--------

Every case below is paired with a *control*: the same model with the template
parameter replaced by the concrete type it is bound to.  Without that pairing
there is no way to tell a real parser defect from malformed PSS in the test
itself.  The controls passing while the templated forms failed is what
established these as template defects rather than test bugs.

The controls earned their keep: a ``foreach`` case originally drafted for this
module fails *identically* with and without a template, so it is a general
array-iteration defect and does not belong in this suite.  It was removed
rather than recorded here as a template bug.

See ``docs/template-parameter-test-suite.md`` section 4.6.
"""
import pytest

from ..isolation import assert_clean, assert_no_crash, run_isolated


def link(src):
    return run_isolated([("t.pss", src)])


# ---------------------------------------------------------------------------
# A generic with any body at all
# ---------------------------------------------------------------------------

# These cases all used to segfault, and between them they cover the three
# defects that caused it.  Kept as regression guards, since each failure mode
# was silent up to the moment the process died:
#
# 1. ``TaskCopyAst`` had empty visitor stubs for every body-bearing construct
#    (exec scopes and blocks, procedural statements, function definitions,
#    constraint scopes, ``FieldCompRef``).  An unhandled node set nothing, so
#    ``copy()`` returned null and the caller dereferenced it.  The body did not
#    have to mention the parameter -- an *empty* ``exec init_down { }`` was
#    enough -- so this was copier coverage, not parameter substitution.
# 2. ``TaskResolveSymbolPathRef::mkIterator`` read ``getParams()->getSpecialized()``
#    while walking up enclosing scopes, and ``getParams()`` is null for any
#    type that is not parameterized.  That is why a generic *action* crashed
#    regardless of body: its enclosing component is a type scope with no
#    parameter list.
# 3. ``TaskGetSymbolScope`` did not stop at a type scope, so the base visitor
#    walked on into the parameter list and each specialization, and the last
#    symbol scope visited won.  A parameterized type reported its ``<plist>``
#    as the enclosing scope, which is why a specialized generic's own fields
#    were invisible inside its own body.  Non-generic types were unaffected
#    only because their plist is null.
#
# All three are the same shape as the extension-merge bug fixed in plan phase
# 3.2: type-based visitor dispatch where an unhandled -- or un-terminated --
# case is silently wrong rather than diagnosed.


@pytest.mark.parametrize(
    "body",
    [
        "exec init_down { w = 1; }",
        "exec init_up { w = 1; }",
        "exec body { w = 1; }",
        "exec init_down { }",
    ],
    ids=["init_down", "init_up", "body", "empty"],
)
def test_generic_struct_with_exec_block_specializes(body):
    assert_clean([("t.pss", """
        package p {
            struct S<type T> { int w; %s }
            struct Top { S<int> s; }
        }
    """ % body)])


def test_generic_component_with_exec_block_specializes():
    assert_clean([("t.pss", """
        component C<type T> { int w; exec init_down { w = 1; } }
        component pss_top { C<int> c; }
    """)])


def test_generic_action_with_exec_block_specializes():
    assert_clean([("t.pss", """
        component pss_top {
            action A<type T> { exec body { } }
            A<int> a;
        }
    """)])


def test_generic_component_with_function_specializes():
    assert_clean([("t.pss", """
        component C<type T> { int w; function void go() { w = 1; } }
        component pss_top { C<int> c; }
    """)])


def test_non_generic_with_exec_block_links():
    """Control for the group above: identical body, no template parameter."""
    assert_clean([("t.pss", """
        package p {
            struct S { int w; exec init_down { w = 1; } }
            struct Top { S s; }
        }
    """)])


def test_uninstantiated_generic_with_exec_block_links():
    """Control: no specialization is created, so nothing is copied."""
    assert_clean([("t.pss", """
        package p {
            struct S<type T> { int w; exec init_down { w = 1; } }
            struct Top { int x; }
        }
    """)])


# ---------------------------------------------------------------------------
# Reaching a member through the parameter
# ---------------------------------------------------------------------------

def test_member_of_parameter_typed_field_resolves():
    assert_clean([("t.pss", """
        package p {
            struct my_s { int zork; }
            struct S<type T> { T v; exec init_down { v.zork = 1; } }
            struct Top { S<my_s> s; }
        }
    """)])


def test_parameter_as_function_parameter_type():
    assert_clean([("t.pss", """
        package p {
            struct my_s { int zork; }
            component C<type T> { function void go(T a) { a.zork = 1; } }
            component pss_top { C<my_s> c; }
        }
    """)])


def test_missing_member_of_parameter_typed_field_is_an_error():
    """A *bad* member must be reported, not crash.

    Paired deliberately with the test above: once the copier is fixed, this is
    what proves the member lookup actually runs against the bound type rather
    than silently succeeding against nothing.
    """
    res = link("""
        package p {
            struct my_s { int zork; }
            struct S<type T> { T v; exec init_down { v.nosuch = 1; } }
            struct Top { S<my_s> s; }
        }
    """)
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


# ---------------------------------------------------------------------------
# Crash guards
#
# These assert only that the parser survives, deliberately.  Each one names a
# null dereference that killed the process outright, and a segfault in the test
# session takes every other test down with it -- so a guard that says nothing
# about correctness still earns its place.
# ---------------------------------------------------------------------------

def test_value_parameter_with_no_default_does_not_crash():
    """``TaskGetElemSymbolScope`` read the parameter's dflt slot unguarded.

    On a specialized parameter list that slot holds the bound argument, but on
    an unspecialized one it holds the *declared default* -- and ``Q<int M>``
    has none.  Reaching a value parameter that way therefore dereferenced null.
    """
    assert not link("""
        package p {
            struct Q<int M> { bit[M] v; }
            struct S<int N> { Q<N> inner; }
            struct Top { S<8> x; }
        }
    """).crashed


def test_generic_nested_in_a_plain_component_does_not_crash():
    """``mkIterator`` read ``getParams()->getSpecialized()`` on every enclosing
    scope, and a plain component has no parameter list."""
    assert not link("""
        component pss_top {
            action A<type T> { rand T v; }
            A<int> a;
        }
    """).crashed


# ---------------------------------------------------------------------------
# Constraints and super types inside a generic
# ---------------------------------------------------------------------------

# These used to report "unknown identifier 'w'" for a field declared two lines
# above the constraint -- defect 3 in the note at the top of this module.  The
# constraint form is worth keeping alongside the exec form because it reproduced
# with a *value* parameter and no type parameter at all, which is what ruled out
# type substitution as the cause.


def test_generic_constraint_sees_own_field():
    assert_clean([("t.pss", """
        package p {
            struct S<type T> { rand int w; constraint { w < 4; } }
            struct Top { S<int> s; }
        }
    """)])


def test_generic_constraint_uses_value_parameter():
    assert_clean([("t.pss", """
        package p {
            struct S<int N> { rand int w; constraint { w < N; } }
            struct Top { S<4> s; }
        }
    """)])


def test_generic_constraint_reaches_member_of_parameter():
    assert_clean([("t.pss", """
        package p {
            struct my_s { rand int zork; }
            struct S<type T> { rand T v; constraint { v.zork == 1; } }
            struct Top { S<my_s> s; }
        }
    """)])


def test_non_generic_constraint_sees_own_field():
    """Control for the constraint group."""
    assert_clean([("t.pss", """
        package p {
            struct S { rand int w; constraint { w < 4; } }
            struct Top { S s; }
        }
    """)])


@pytest.mark.xfail(
    strict=True,
    reason="a type parameter used as a super type does not contribute its "
           "members: 'Failed to find elem zork', though the identical "
           "non-generic control resolves. Remove this marker when a bound "
           "parameter works as a super type.",
)
def test_parameter_as_super_type_contributes_members():
    assert_clean([("t.pss", """
        package p {
            struct base_s { int zork; }
            struct S<type T> : T { }
            struct Top { S<base_s> s; exec init_down { s.zork = 1; } }
        }
    """)])


def test_concrete_super_type_contributes_members():
    """Control for the super-type case."""
    assert_clean([("t.pss", """
        package p {
            struct base_s { int zork; }
            struct S : base_s { }
            struct Top { S s; exec init_down { s.zork = 1; } }
        }
    """)])


# ---------------------------------------------------------------------------
# Value parameters in type positions -- these work today
# ---------------------------------------------------------------------------

def test_value_parameter_as_array_bound():
    assert_clean([("t.pss", """
        package p {
            struct S<int N> { bit[8] v[N]; }
            struct Top { S<4> s; }
        }
    """)])


# ---------------------------------------------------------------------------
# array<> element access
# ---------------------------------------------------------------------------

def test_array_of_struct_subscript_member():
    assert_clean([("t.pss", """
        package p {
            struct my_s { int zork; }
            struct Top { array<my_s,4> arr; exec init_down { arr[0].zork = 1; } }
        }
    """)])


def test_array_of_component_subscript_member():
    assert_clean([("t.pss", """
        component ch_c { int zork; }
        component pss_top { array<ch_c,4> ch; exec init_down { ch[0].zork = 1; } }
    """)])


def test_two_arrays_of_different_element_types_subscript_independently():
    """Guards against one array's element type standing in for another's.

    This is the small-model form of the open whole-model error, where a
    subscripted element resolved to an unrelated enum.  It passes today, so it
    is a regression guard rather than a reproducer -- the whole-model failure
    needs more context than this to appear.
    """
    assert_clean([("t.pss", """
        package p {
            struct a_s { int za; }
            struct b_s { int zb; }
            struct Top {
                array<a_s,4> aa;
                array<b_s,4> bb;
                exec init_down { aa[0].za = 1; bb[0].zb = 2; }
            }
        }
    """)])


def test_array_of_parameter_type_subscript_member():
    """``array<T,N>`` inside a generic -- crashes, via the copier defect."""
    res = link("""
        package p {
            struct my_s { int zork; }
            struct S<type T> { array<T,4> arr; exec init_down { arr[0].zork = 1; } }
            struct Top { S<my_s> s; }
        }
    """)
    assert not res.crashed, res.describe()


_MULTIDIM = """
    package p {
        struct my_s { int zork; }
        struct Top {
            array<array<my_s,2>,4> arr;
            exec init_down { arr[0][1].%s = 1; }
        }
    }
"""


def test_multidim_array_subscript_resolves_the_inner_element():
    assert_clean([("t.pss", _MULTIDIM % "zork")])


def test_multidim_array_subscript_reports_a_bad_member():
    """``arr[0][1].nosuch`` is diagnosed, so the inner element type is
    genuinely consulted.

    Paired with the test above: together they show multi-dimensional subscript
    discriminates, rather than accepting anything.
    """
    res = link(_MULTIDIM % "nosuch")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


@pytest.mark.xfail(
    strict=True,
    reason="a multi-dimensional subscript emits the internal line "
           "\"Error: TaskResolveRefs: Handle multi-dim array subscript\" even "
           "on a successful parse. Resolution is correct -- the two tests "
           "above prove that -- but an 'Error:' line on a clean run is "
           "misleading to a user and to any tool scraping output. Remove this "
           "marker when the message is dropped or demoted to debug.",
)
def test_multidim_array_subscript_is_quiet_on_success():
    res = link(_MULTIDIM % "zork")
    assert "Handle multi-dim array subscript" not in res.output, res.describe()


# ---------------------------------------------------------------------------
# Core-library generics
# ---------------------------------------------------------------------------

def test_sizeof_s_of_scalar():
    assert_clean([("t.pss", """
        import addr_reg_pkg::*;
        component pss_top { int sz = sizeof_s<int>::nbits; }
    """)])


def test_sizeof_s_of_packed_struct():
    assert_clean([("t.pss", """
        import addr_reg_pkg::*;
        struct R : packed_s<> { bit[8] a; bit[8] b; }
        component pss_top { int sz = sizeof_s<R>::nbits; }
    """)])


def test_reg_c_specialization():
    assert_clean([("t.pss", """
        import addr_reg_pkg::*;
        pure component my_regs : reg_group_c { reg_c<int> r1; }
        component pss_top { my_regs regs; }
    """)])


def test_addr_region_s_with_trait():
    assert_clean([("t.pss", """
        import addr_reg_pkg::*;
        struct addr_region_s<struct TRAIT : addr_trait_s = empty_addr_trait_s> {
            TRAIT trait;
        }
        component pss_top { addr_region_s<> r1; }
    """)])
