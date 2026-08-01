"""Generics nested inside generics, and generics that refer to themselves.

Two questions, and they are not the same question.

The first is whether a *nested* argument binds correctly: given ``S<Q<int>>``,
is ``S``'s parameter bound to the specialization ``Q<int>``, or to something
else?  It used to be bound to ``int`` -- the argument of the *inner* generic --
because the code that decided whether an argument names a template parameter
did so by walking the argument's whole subtree and seeing which visitor fired.
Walking ``Q`` reached the parameter reference in ``Q``'s own body, so the
argument reported itself as a reference to ``U``.  That was the root cause of
the whole-model ``Failed to find elem \\init`` failure, which had resisted
isolation for a long time because its symptom pointed at escaped identifiers
and array subscripts, none of which had anything to do with it.

The second is termination.  A chain of specializations resolves each body as it
goes, and that body may specialize again.  Most chains terminate because the
argument list repeats and the existing specialization is reused; some -- like
``struct S<type T> { S<S<T>> next; }`` -- name a strictly larger argument every
step and have no fixed point.  Those must be *diagnosed*.  Whether a given
cyclic shape terminates with an error or with a valid model is recorded here
rather than presumed, per the suite's stated policy.

See ``docs/template-parameter-test-suite.md`` section 4.4.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from isolation import assert_clean, assert_rejects  # noqa: E402

from ..test_helpers import parse_pss
from ..template_helpers import (
    assert_binds_to,
    assert_specialization_count,
    binding_decl,
    find_specialization,
    lookup,
    specializations,
)


# ---------------------------------------------------------------------------
# A generic supplied as an argument
# ---------------------------------------------------------------------------

def test_generic_argument_binds_to_the_inner_specialization():
    """``S<Q<int>>`` binds ``T`` to ``Q<int>``, not to ``int``.

    The distinction is the whole point: ``int`` is what the *inner* generic was
    specialized on, and binding to it discards a level of the type.
    """
    root = parse_pss(
        """
        package p {
            struct Q<type U> { U u; }
            struct S<type T> { T v; }
            struct Top { S<Q<int>> a; }
        }
        """
    )
    q_int = find_specialization(root, "p::Q", "int")
    s_spec = specializations(root, "p::S")[0]
    assert_binds_to(root, s_spec, "T", q_int)


def test_three_deep_binds_at_every_level():
    """``S<Q<R<int>>>``: each level binds to the specialization below it."""
    root = parse_pss(
        """
        package p {
            struct R<type X> { X x; }
            struct Q<type U> { U u; }
            struct S<type T> { T v; }
            struct Top { S<Q<R<int>>> a; }
        }
        """
    )
    r_int = find_specialization(root, "p::R", "int")
    q_r = specializations(root, "p::Q")[0]
    s_q = specializations(root, "p::S")[0]

    assert_binds_to(root, q_r, "U", r_int)
    assert_binds_to(root, s_q, "T", q_r)


def test_distinct_inner_arguments_give_distinct_outer_specializations():
    """``S<Q<int>>`` and ``S<Q<bool>>`` are two different types.

    Every ``Q`` specialization is *named* ``Q<>``, so a name-based comparison
    cannot tell these apart.  The assertion is by declaration handle instead:
    each ``S`` must bind to its own ``Q``.
    """
    root = parse_pss(
        """
        package p {
            struct Q<type U> { U u; }
            struct S<type T> { T v; }
            struct Top { S<Q<int>> a; S<Q<bool>> b; }
        }
        """
    )
    assert_specialization_count(root, "p::Q", 2)
    assert_specialization_count(root, "p::S", 2)

    q_int = find_specialization(root, "p::Q", "int")
    q_bool = find_specialization(root, "p::Q", "bool")

    targets = [binding_decl(root, s, "T")
               for s in specializations(root, "p::S")]
    assert q_int in targets, "no S specialization is bound to Q<int>"
    assert q_bool in targets, "no S specialization is bound to Q<bool>"


def test_identical_nested_arguments_share_one_specialization():
    """``S<Q<int>>`` twice is one type, and the inner ``Q<int>`` is one type."""
    root = parse_pss(
        """
        package p {
            struct Q<type U> { U u; }
            struct S<type T> { T v; }
            struct Top { S<Q<int>> a; S<Q<int>> b; }
        }
        """
    )
    assert_specialization_count(root, "p::Q", 1)
    assert_specialization_count(root, "p::S", 1)


def test_four_levels_of_generics_each_pass_the_parameter_down():
    """``S<int>`` threaded through four generics reaches the innermost as int.

    Nesting by *declaration* rather than by argument: each body specializes the
    next generic on its own parameter, so a substitution that dropped a level
    would show up as an unbound innermost parameter.
    """
    root = parse_pss(
        """
        package p {
            struct D<type X> { X x; }
            struct R<type X> { D<X> d; }
            struct Q<type U> { R<U> r; }
            struct S<type T> { Q<T> q; }
            struct Top { S<int> a; }
        }
        """
    )
    for qname, param in (("p::S", "T"), ("p::Q", "U"), ("p::R", "X"), ("p::D", "X")):
        assert_specialization_count(root, qname, 1)
        assert_binds_to(root, specializations(root, qname)[0], param, "int")


def test_default_expression_that_itself_specializes():
    """A default whose value comes from specializing another generic.

    ``sz_t<R>::xz`` is the shape the core library uses for sizing.  The
    parameter it depends on is bound first, and the default is evaluated
    against that binding.
    """
    root = parse_pss(
        """
        package p {
            struct sz_t<type R> { int xz; }
            struct my_s { int f; }
            struct Q<type R, int SZ = 4> { bit[SZ] v; }
            struct Top { Q<my_s> a; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    spec = specializations(root, "p::Q")[0]
    assert_binds_to(root, spec, "R", my_s)
    assert_binds_to(root, spec, "SZ", "4")


# ---------------------------------------------------------------------------
# Supers that are specializations
# ---------------------------------------------------------------------------

def test_super_is_a_specialization_of_another_generic():
    root = parse_pss(
        """
        package p {
            struct Q<type U> { U u; }
            struct S : Q<int> { int extra; }
            struct Top { S a; }
        }
        """
    )
    assert_specialization_count(root, "p::Q", 1)
    assert_binds_to(root, specializations(root, "p::Q")[0], "U", "int")


def test_generic_super_is_a_specialization_on_its_own_parameter():
    """``struct S<type T> : Q<T>`` -- the super is specialized on ``T``."""
    root = parse_pss(
        """
        package p {
            struct Q<type U> { U u; }
            struct S<type T> : Q<T> { int extra; }
            struct my_s { int f; }
            struct Top { S<my_s> a; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    assert_binds_to(root, specializations(root, "p::S")[0], "T", my_s)
    assert_binds_to(root, specializations(root, "p::Q")[0], "U", my_s)


# ---------------------------------------------------------------------------
# Cycles -- the contract is termination, not success
# ---------------------------------------------------------------------------

def test_directly_self_referential_generic_terminates():
    """``struct S<type T> { S<T> next; }`` links clean.

    It terminates because the inner argument list is identical to the outer
    one, so the specialization already under construction is reused.  This is
    the shape a linked list takes, so accepting it is the right outcome.
    """
    assert_clean("package p { struct S<type T> { S<T> next; } struct Top { S<int> a; } }")


def test_self_reference_on_a_different_argument_terminates():
    assert_clean(
        "package p { struct S<type T> { S<int> next; } struct Top { S<bool> a; } }")


def test_mutually_recursive_generics_terminate():
    assert_clean(
        "package p { struct A<type T> { B<T> b; } struct B<type T> { A<T> a; } "
        "struct Top { A<int> x; } }")


def test_generic_whose_super_is_a_specialization_of_itself_terminates():
    assert_clean(
        "package p { struct S<type T> : S<int> { int f; } struct Top { S<bool> a; } }")


def test_unbounded_self_specialization_is_diagnosed_not_crashed():
    """``struct S<type T> { S<S<T>> next; }`` has no fixed point.

    Every step specializes on a strictly larger argument -- ``S<T>``,
    ``S<S<T>>``, ``S<S<S<T>>>`` -- so nothing is ever reused and the chain runs
    until the stack does.  It now stops at a depth limit and reports.

    This one crashed only *after* the nested-binding fix: while a nested
    argument was collapsing to the inner generic's argument, the chain
    accidentally reached a fixed point and terminated.  Getting the binding
    right exposed the missing bound, which is why the depth limit and the
    binding fix belong to the same change.
    """
    res = assert_rejects(
        "package p { struct S<type T> { S<S<T>> next; } struct Top { S<int> a; } }",
        "recursive specialization",
    )
    assert "S" in res.output


def test_generic_used_inside_its_own_default_is_diagnosed_not_crashed():
    """``struct S<type T, type U = S<int>>`` -- the same non-terminating chain.

    Reached through a default rather than a member, and this one segfaulted
    before the depth limit existed as well as after the binding fix.
    """
    assert_rejects(
        "package p { struct S<type T, type U = S<int>> { int f; } "
        "struct Top { S<bool> a; } }",
        "recursive specialization",
    )


@pytest.mark.parametrize(
    "src",
    [
        "package p { struct S<type T> { S<S<T>> next; } struct Top { S<int> a; } }",
        "package p { struct S<type T, type U = S<int>> { int f; } struct Top { S<bool> a; } }",
    ],
    ids=["member", "default"],
)
def test_a_non_terminating_generic_still_reports_unrelated_errors(src):
    """The depth limit must not swallow the rest of the run.

    A bail-out that abandons resolution would leave the second, unrelated error
    unreported -- and a user fixing one error at a time would never see it.
    """
    res = assert_rejects(src + " package q { struct T2 { does_not_exist_s f; } }")
    assert "does_not_exist_s" in res.output, (
        "the unrelated error was lost: %s" % res.describe())
