"""Template shapes taken from the real core library.

The unit tests elsewhere use invented generics.  This module uses the ones in
``src/stdlib`` -- ``reg_c<R>``, ``reg_group_c``, ``packed_s<>``,
``addr_region_s<TRAIT>``, ``sizeof_s<T>`` -- because that is where the
whole-model failures actually came from.  The overlap with the invented cases
is deliberate: these are the versions that failed in practice.

Most of the family turned out to be healthy.  The defect this section found is
in something none of the invented tests reached: a **static reference path**,
``G<args>::member``, as opposed to a field type ``G<args> f;``.

``TaskResolveRefs::visitExprRefPathStatic`` never resolved the template
arguments at the use site before specializing, which
``TaskResolveRef::visitTypeIdentifier`` does for a type reference.  The
arguments therefore reached ``TaskBuildParamValList`` unresolved and were
looked up wherever it happened to be -- the *generic's* declaring package.
For ``sizeof_s``, which lives in ``addr_reg_pkg``, that meant a user type was
never found; the "did you mean 'set'?" suggestion in the old symptom is the
tell, since the builtins were the only types visible from there.  Worse, when
both packages declared the name, the argument silently bound to the wrong one
while the field-typed form on the same source line bound the right one.

The same function also did not null-check ``specialize()``, so a wrong
argument count segfaulted where the field form reported it.

See ``docs/template-parameter-test-suite.md`` section 4.9.
"""
import pytest

from ..isolation import assert_clean, assert_rejects, run_isolated


def link(src):
    return run_isolated([("t.pss", src)])


# ---------------------------------------------------------------------------
# addr_reg_pkg: the TRAIT family
# ---------------------------------------------------------------------------

_TRAIT = """
package p {
    import addr_reg_pkg::*;
    struct my_trait_s : addr_trait_s { int x; }
    %s
}
"""


def test_a_trait_parameterized_address_space_links():
    """``contiguous_addr_space_c<TRAIT>`` with a matching region argument.

    ``add_region`` takes ``addr_region_s<TRAIT>`` -- the parameter is passed
    through from the component to the function signature, which is the shape
    that has to keep working for the standard library to be usable at all.
    """
    assert_clean([("t.pss", _TRAIT % """
        component Top {
            contiguous_addr_space_c<my_trait_s> aspace;
            exec init_down {
                addr_region_s<my_trait_s> r;
                aspace.add_region(r);
            }
        }
    """)])


def test_the_defaulted_trait_links():
    """``<>`` falls back to ``empty_addr_trait_s`` on both sides."""
    assert_clean([("t.pss", _TRAIT % """
        component Top {
            contiguous_addr_space_c<> aspace;
            exec init_down { addr_region_s<> r; aspace.add_region(r); }
        }
    """)])


def test_the_trait_passes_through_two_levels_of_inheritance():
    """``transparent_addr_space_c<TRAIT> : contiguous_addr_space_c<TRAIT>``.

    ``add_region`` is inherited, and its signature mentions the parameter, so
    this only works if the binding survives the super-type hop.
    """
    assert_clean([("t.pss", _TRAIT % """
        component Top {
            transparent_addr_space_c<my_trait_s> aspace;
            exec init_down {
                transparent_addr_region_s<my_trait_s> r;
                aspace.add_region(r);
            }
        }
    """)])


def test_the_bound_trait_is_reachable_as_a_field():
    """``addr_region_s`` declares ``TRAIT trait;``, so ``r.trait.x`` is the
    user's own field, reached through the binding."""
    assert_clean([("t.pss", _TRAIT %
        "struct Top { addr_region_s<my_trait_s> r; constraint { r.trait.x == 1; } }")])


def test_a_member_the_trait_does_not_have_is_rejected():
    """Control for the row above."""
    assert_rejects([("t.pss", _TRAIT %
        "struct Top { addr_region_s<my_trait_s> r; constraint { r.trait.nosuch == 1; } }")],
        "nosuch")


def test_an_inherited_member_is_reachable_through_a_specialization():
    """``size`` comes from ``addr_region_base_s``, not from the generic."""
    assert_clean([("t.pss", _TRAIT %
        "struct Top { addr_region_s<my_trait_s> r; constraint { r.size == 4; } }")])


def test_the_trait_restriction_is_enforced_by_the_real_declaration():
    """``struct TRAIT : addr_trait_s`` in ``addr_reg_pkg``, not an invented one."""
    assert_rejects([("t.pss", """
        package p {
            import addr_reg_pkg::*;
            struct not_a_trait_s { int x; }
            struct Top { addr_region_s<not_a_trait_s> r; }
        }
    """)], "does not derive from 'addr_trait_s'")


# ---------------------------------------------------------------------------
# addr_reg_pkg: the register model
# ---------------------------------------------------------------------------

_REGS = """
package p {
    import addr_reg_pkg::*;
    struct my_reg_s : packed_s<> { bit[8] f0; bit[8] f1; }
    %s
}
"""


def test_a_register_group_of_parameterized_registers_links():
    """``reg_c<R>``'s third parameter defaults to ``(8*sizeof_s<R>::nbytes)``.

    That default is a static reference path whose argument *is* a template
    parameter, which is why it kept working while the same shape with a
    concrete user type did not.
    """
    assert_clean([("t.pss", _REGS % """
        pure component my_regs_c : reg_group_c {
            reg_c<my_reg_s> r0;
            reg_c<my_reg_s> r1;
        }
    """)])


def test_a_register_method_is_callable_through_the_group():
    assert_clean([("t.pss", _REGS % """
        pure component my_regs_c : reg_group_c { reg_c<my_reg_s> r0; }
        component Top {
            my_regs_c regs;
            action A { exec body { comp.regs.r0.write_val(1); } }
        }
    """)])


def test_a_method_a_register_does_not_have_is_rejected():
    """Control: reaching the register is not the same as accepting anything."""
    assert_rejects([("t.pss", _REGS % """
        pure component my_regs_c : reg_group_c { reg_c<my_reg_s> r0; }
        component Top {
            my_regs_c regs;
            action A { exec body { comp.regs.r0.nosuch_method(1); } }
        }
    """)])


def test_a_user_struct_deriving_from_packed_s_links():
    assert_clean([("t.pss", _REGS %
        "struct Top { my_reg_s s; constraint { s.f0 == 1; } }")])


# ---------------------------------------------------------------------------
# sizeof_s: a static reference path into an imported generic
# ---------------------------------------------------------------------------

def test_sizeof_of_a_user_type_resolves_the_argument_at_the_use_site():
    """The plan's phase 1.3, and the reason it never worked.

    ``sizeof_s`` is declared in ``addr_reg_pkg``; ``s_s`` is declared here.
    The argument has to be resolved where it is *written*, not where the
    generic lives.
    """
    assert_clean([("t.pss", """
        package p {
            import addr_reg_pkg::*;
            struct s_s : packed_s<> { bit[16] a; }
            struct Top { int n; constraint { n == sizeof_s<s_s>::nbytes; } }
        }
    """)])


def test_sizeof_of_a_builtin_still_resolves():
    """Control: builtins are visible from the generic's package too, so this
    row passed even when the one above did not.  It is here to show the fix
    did not simply move the lookup somewhere else."""
    assert_clean([("t.pss", """
        package p {
            import addr_reg_pkg::*;
            struct Top { int n; constraint { n == sizeof_s<bit[16]>::nbytes; } }
        }
    """)])


def test_sizeof_of_a_type_declared_after_the_use_resolves():
    """Declaration order must not matter."""
    assert_clean([("t.pss", """
        package p {
            import addr_reg_pkg::*;
            struct Top { int n; constraint { n == sizeof_s<s_s>::nbytes; } }
            struct s_s : packed_s<> { bit[16] a; }
        }
    """)])


def test_sizeof_of_a_type_that_does_not_exist_is_reported():
    """Control.  Resolving at the use site is not the same as accepting
    anything written there."""
    assert_rejects([("t.pss", """
        package p {
            import addr_reg_pkg::*;
            struct Top { int n; constraint { n == sizeof_s<nosuch_s>::nbytes; } }
        }
    """)], "nosuch_s")


# ---------------------------------------------------------------------------
# The general shape: a static reference path vs. a field type
# ---------------------------------------------------------------------------

#: `q::s_s` derives from `base_q`; `p::s_s` does not, and the parameter is
#: restricted to `base_q`.  Which package the argument came from is therefore
#: observable: binding `p::s_s` must be rejected, binding `q::s_s` accepted.
_SHADOW = """
package q {
    struct base_q { int b; }
    struct s_s : base_q { bit[8] z; }
    struct Q<struct T : base_q> { int nbytes; }
}
package p {
    import q::*;
    struct s_s { bit[16] a; }
    %s
}
"""


@pytest.mark.parametrize(
    "use",
    [
        "struct Top { int n; constraint { n == Q<s_s>::nbytes; } }",
        "struct Top { Q<s_s> q; }",
    ],
    ids=["static-path", "field-type"],
)
def test_both_reference_forms_bind_the_same_argument(use):
    """The pair is the whole test.

    Identical text -- ``Q<s_s>`` -- in one file, once as a static path and once
    as a field type.  The field form bound ``p::s_s`` and was rejected by the
    restriction; the static form bound ``q::s_s`` and linked cleanly.  Two
    different types from one spelling, and no diagnostic to say so.

    Testing either form alone proves nothing: each was self-consistent.
    """
    assert_rejects([("t.pss", _SHADOW % use)], "does not derive from 'base_q'")


def test_an_explicitly_qualified_argument_is_honoured():
    """``q::s_s`` names the one that *does* satisfy the restriction."""
    assert_clean([("t.pss", _SHADOW %
        "struct Top { int n; constraint { n == Q<q::s_s>::nbytes; } }")])


def test_an_explicitly_qualified_local_argument_is_still_checked():
    """``p::s_s`` spelled out must be rejected, as the field form is.

    This row is what separates "resolves at the use site" from "resolves to
    whatever passes": before the fix, the qualified form linked too.
    """
    assert_rejects([("t.pss", _SHADOW %
        "struct Top { int n; constraint { n == Q<p::s_s>::nbytes; } }")],
        "does not derive from 'base_q'")


_COUNT = """
package q { struct P<type T, int N> { int nbytes; } }
package p {
    import q::*;
    %s
}
"""


@pytest.mark.parametrize(
    "use,expect",
    [
        ("struct Top { int n; constraint { n == P<int,1,2,3>::nbytes; } }",
         "type accepts 2 template parameter(s) but 4 supplied"),
        ("struct Top { int n; constraint { n == P<int>::nbytes; } }",
         "no value supplied for template parameter 'N'"),
    ],
    ids=["too-many", "too-few"],
)
def test_a_wrong_argument_count_in_a_static_path_is_diagnosed_not_crashed(use, expect):
    """Both of these segfaulted.

    ``specialize()`` returns null once it has reported an argument error; the
    null was then dereferenced.  Checked out of process, since that is the
    only way to tell a crash from a rejection.
    """
    res = link(_COUNT % use)
    assert not res.crashed, res.describe()
    assert res.rc == 1, res.describe()
    assert expect in res.output, res.describe()


@pytest.mark.parametrize(
    "use",
    [
        "struct Top { P<int,1,2,3> x; }",
        "struct Top { P<int> x; }",
    ],
    ids=["too-many", "too-few"],
)
def test_the_field_form_diagnoses_the_same_counts(use):
    """Control for the pair above: the field form always reported these, which
    is what made the static form's crash a difference between the two rather
    than a missing feature."""
    assert_rejects([("t.pss", _COUNT % use)])


# ---------------------------------------------------------------------------
# Collections of user types
# ---------------------------------------------------------------------------

def test_an_array_of_a_user_component_is_subscriptable():
    assert_clean([("t.pss", """
        package p {
            component Sub { int v; }
            component Top {
                array<Sub,4> subs;
                exec init_down { subs[0].v = 1; }
            }
        }
    """)])


def test_a_member_the_element_does_not_have_is_rejected():
    assert_rejects([("t.pss", """
        package p {
            component Sub { int v; }
            component Top {
                array<Sub,4> subs;
                exec init_down { subs[0].nosuch = 1; }
            }
        }
    """)], "nosuch")


def test_a_list_and_a_map_of_a_user_struct_are_subscriptable():
    assert_clean([("t.pss", """
        package p {
            struct s_s { int a; }
            struct Top {
                list<s_s> l;
                map<int,s_s> m;
                exec init_down { l[0].a = 1; m[0].a = 2; }
            }
        }
    """)])


# ---------------------------------------------------------------------------
# Trailing members of a static path
#
# Only the *root* of a static path used to be resolved.  Every element after
# it was visited and the result thrown away, so a specialization could be
# asked for a member it does not have and the reference linked.  The controls
# here matter more than usual: a check newly applied to a path that was never
# checked can just as easily reject something valid, and the inherited-member
# case below is exactly where that would happen.
# ---------------------------------------------------------------------------

def test_a_member_a_specialization_does_not_have_is_reported():
    assert_rejects([("t.pss", _SHADOW %
        "struct Top { int n; constraint { n == Q<q::s_s>::nosuch; } }")],
        "has no member named 'nosuch'")


def test_a_member_a_specialization_does_have_still_links():
    """Control for the above, and for every argument-binding test in this file:
    they all read a member through a static path, so a check that rejected
    valid members would take the whole group with it."""
    assert_clean([("t.pss", _SHADOW %
        "struct Top { int n; constraint { n == Q<q::s_s>::nbytes; } }")])


def test_an_inherited_member_is_found_through_a_static_path():
    """A member declared in a base type, reached through a specialization.

    The lookup walks the super chain, but a symbol path cannot encode a step
    through a base type, so this is the case where the new check has to accept
    without extending the path.  Nothing else in the suite covers it.
    """
    assert_clean([("t.pss", """
        package q {
            struct base_q { int nbytes; }
            struct Q<type T> : base_q { int own; }
        }
        package p {
            import q::*;
            struct Top { int n; constraint { n == Q<int>::nbytes; } }
        }
    """)])


def test_a_generic_used_with_no_argument_list_in_a_static_path_is_reported():
    """`P::nbytes` names the generic itself, not one of its instances.

    The static-path form of the bare-use defect still marked xfail in
    ``test_template_errors.py``: argument validation runs from the specialize
    step, which only runs when arguments are present, so a name with no
    argument list at all slipped past everything.  Diagnosed here at the point
    the path resolves instead.
    """
    assert_rejects([("t.pss", _COUNT %
        "struct Top { int n; constraint { n == P::nbytes; } }")],
        "requires a template argument list")


def test_a_generic_with_its_argument_list_still_links():
    """Control: the check above must fire on the missing list, not on P."""
    assert_clean([("t.pss", _COUNT %
        "struct Top { int n; constraint { n == P<int,8>::nbytes; } }")])


def test_a_non_template_static_path_is_unaffected():
    """Control: the overwhelming majority of static paths name no template at
    all, and must not acquire a demand for arguments."""
    assert_clean([("t.pss", """
        package q { struct P { static const int nbytes = 4; } }
        package p {
            import q::*;
            struct Top { int n; constraint { n == P::nbytes; } }
        }
    """)])
