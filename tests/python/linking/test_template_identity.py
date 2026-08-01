"""Specialization identity: distinct arguments stay distinct, equal ones merge.

``TaskGetSpecializedTemplateType::find`` scans the generic's existing
specializations for a parameter list ``TaskCompareParamLists::equal`` to the
requested one, and only creates a new specialization on a miss.  So argument
binding and specialization dedup are the same mechanism viewed twice: a
comparison bug shows up as a binding bug and vice versa.

Both failure directions matter and neither is visible to a link-only test:

* **Over-merge** -- two genuinely different argument lists compare equal, so
  one specialization stands in for both.  Silently wrong: uses of the second
  see the first's bindings.
* **Under-merge** -- identical argument lists compare unequal, so every use
  site mints a fresh specialization.  Not wrong in the same way, but each new
  specialization runs a full ``TaskResolveRefs``, so cost is linear in use
  sites, and the model ends up with several nominally distinct types where it
  should have one.

See ``docs/template-parameter-test-suite.md`` section 4.3.
"""
import pytest

from ..test_helpers import parse_multi_file, parse_pss
from ..template_helpers import assert_specialization_count, bindings, specializations


PKG = """
package p {
    struct my_s { int zork; }
    struct other_s { int quux; }
    enum e_t { A, B }
    const int W = 4;
    const int W2 = 8;
%s
}
"""


def _link(body):
    return parse_pss(PKG % body)


# ---------------------------------------------------------------------------
# Scalar arguments -- these work today
# ---------------------------------------------------------------------------

def test_identical_scalar_arguments_share_one_specialization():
    root = _link("struct S<type T> { T v; } struct Top { S<int> a; S<int> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_different_scalar_arguments_are_distinct():
    root = _link("struct S<type T> { T v; } struct Top { S<int> a; S<bit[8]> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_identical_string_arguments_share_one_specialization():
    root = _link(
        "struct S<type T> { T v; } struct Top { S<string> a; S<string> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_identical_value_arguments_share_one_specialization():
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<4> a; S<4> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_different_value_arguments_are_distinct():
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<4> a; S<8> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_explicit_argument_equal_to_default_does_not_add_a_specialization():
    root = _link(
        "struct S<type T = int> { T v; } struct Top { S<int> a; S<> b; }")
    assert_specialization_count(root, "p::S", 1)


# ---------------------------------------------------------------------------
# Non-scalar arguments
# ---------------------------------------------------------------------------

# ``TaskCompareTypeRefs::equal`` -- which decides equality for *generic type*
# parameters -- used to recognize only ``DataTypeInt`` and ``DataTypeString``.
# ``visitDataTypeUserDefined`` was an empty stub and there was no visitor for
# bool, chandle, enum or pyobj at all, so those argument forms set neither
# capture slot and fell through to ``ret = false``: a specialization on a
# user-defined type never deduplicated.
#
# It now classifies all eight ``IDataType`` kinds, compares user-defined
# references by their *resolved* declaration, and falls back to the written
# name when a reference has not resolved -- the normal state when one file of
# a multi-file model is checked alone.


def test_identical_user_type_arguments_share_one_specialization():
    root = _link("struct S<type T> { T v; } struct Top { S<my_s> a; S<my_s> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_identical_bool_arguments_share_one_specialization():
    root = _link("struct S<type T> { T v; } struct Top { S<bool> a; S<bool> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_identical_chandle_arguments_share_one_specialization():
    root = _link(
        "struct S<type T> { T v; } struct Top { S<chandle> a; S<chandle> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_identical_enum_arguments_share_one_specialization():
    root = _link("struct S<type T> { T v; } struct Top { S<e_t> a; S<e_t> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_same_user_type_used_from_two_packages_shares_one_specialization():
    root = parse_pss(
        """
        package q { struct thing_s { int z; } }
        package p {
            import q::*;
            struct S<type T> { T v; }
            struct Top { S<thing_s> a; }
        }
        package r {
            import q::*;
            import p::*;
            struct Top2 { S<thing_s> b; }
        }
        """
    )
    assert_specialization_count(root, "p::S", 1)


def test_identical_user_type_arguments_across_files_share_one_specialization():
    root = parse_multi_file([
        ("defs.pss", "package q { struct thing_s { int z; } struct S<type T> { T v; } }"),
        ("a.pss", "package a { import q::*; struct A { S<thing_s> v; } }"),
        ("b.pss", "package b { import q::*; struct B { S<thing_s> v; } }"),
    ])
    assert_specialization_count(root, "q::S", 1)


def test_different_user_type_arguments_are_distinct():
    """The other direction: the fix must not over-correct into merging.

    This passed before the comparison was fixed too, but only incidentally --
    back then *every* pair of user-defined arguments compared unequal, so the
    count was right for the wrong reason.  It is meaningful now, and the
    binding assertion below is what makes it so.
    """
    root = _link(
        "struct S<type T> { T v; } struct Top { S<my_s> a; S<other_s> b; }")
    assert_specialization_count(root, "p::S", 2)
    assert sorted(bindings(root, s)[0] for s in specializations(root, "p::S")) == [
        "my_s", "other_s"]


def test_identical_nested_generic_arguments_share_one_specialization():
    """``S<V<int>>`` twice is one specialization.

    The argument is itself a specialization, so this is dedup applied to its
    own output: the two ``V<int>`` references must resolve to the same
    specialization before the enclosing ``S`` can merge.
    """
    root = _link(
        "struct V<type T> { T e; } struct S<type T> { T v; } "
        "struct Top { S<V<int>> a; S<V<int>> b; }")
    assert_specialization_count(root, "p::S", 1)


def test_different_nested_generic_arguments_are_distinct():
    """``S<V<int>>`` and ``S<V<bool>>`` differ only below the top-level name.

    Comparing the written name would merge these; comparing resolved targets
    keeps them apart.
    """
    root = _link(
        "struct V<type T> { T e; } struct S<type T> { T v; } "
        "struct Top { S<V<int>> a; S<V<bool>> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_arguments_differing_only_in_signedness_are_distinct():
    """``bit[32]`` and ``int`` are the same width and not the same type.

    These used to collapse into a single specialization: the int comparison
    evaluated only the width and never looked at ``getIs_signed()``.  Unlike
    the under-merges above -- which cost a redundant specialization -- this one
    was silently wrong, handing ``S<bit[32]>``'s bindings to uses of
    ``S<int>``.
    """
    root = _link(
        "struct S<type T> { T v; } struct Top { S<bit[32]> a; S<int> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_arguments_of_different_kinds_are_distinct():
    """A string and an int argument are never the same specialization."""
    root = _link(
        "struct S<type T> { T v; } struct Top { S<string> a; S<int> b; }")
    assert_specialization_count(root, "p::S", 2)


# ---------------------------------------------------------------------------
# Over-merge: unrecognized value-expression forms compare equal
# ---------------------------------------------------------------------------

#: ``TaskCompareParamLists::valueParamDfltEqual`` recognizes type identifiers,
#: unsigned numbers and plain ids, then ends in ``return true`` for every other
#: expression form.  The comment there justifies that for *implicit* defaults,
#: where two specializations of one generic share structurally identical copied
#: expressions -- and for those it is sound.  But the fallthrough does not
#: distinguish implicit from explicit, so two explicitly-supplied arguments of
#: the same unrecognized kind compare equal regardless of value.
#:
#: Note the asymmetry that hides this: ``S<2+2>`` vs ``S<8>`` *is* caught,
#: because one side is an ``ExprBin`` and the other an ``ExprUnsignedNumber``,
#: so the number branch sees a null and returns false.  The defect only bites
#: when both arguments reach the fallthrough, which is why the cases below
#: pair two compound expressions.
_OVER_MERGE = (
    "TaskCompareParamLists::valueParamDfltEqual returns true for any "
    "expression form it does not recognize, so two explicitly-supplied "
    "compound value arguments compare equal regardless of value and collapse "
    "into a single specialization. Remove this marker when explicit "
    "arguments are compared by value."
)


@pytest.mark.xfail(strict=True, reason=_OVER_MERGE)
def test_different_compound_value_arguments_are_distinct():
    """``S<2+2>`` (N=4) and ``S<3+7>`` (N=10) must not be one specialization."""
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<2+2> a; S<3+7> b; }")
    assert_specialization_count(root, "p::S", 2)


@pytest.mark.xfail(strict=True, reason=_OVER_MERGE)
def test_different_constant_expression_arguments_are_distinct():
    root = _link(
        "struct S<int N> { bit[N] v; } struct Top { S<W+0> a; S<W2+0> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_compound_versus_literal_value_arguments_are_distinct():
    """``S<2+2>`` vs ``S<8>`` -- caught today, by node-kind asymmetry.

    Recorded to protect that behaviour while the fallthrough above is fixed.
    """
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<2+2> a; S<8> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_different_constant_identifier_arguments_are_distinct():
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<W> a; S<W2> b; }")
    assert_specialization_count(root, "p::S", 2)


def test_identical_constant_identifier_arguments_share_one_specialization():
    root = _link("struct S<int N> { bit[N] v; } struct Top { S<W> a; S<W> b; }")
    assert_specialization_count(root, "p::S", 1)


# ---------------------------------------------------------------------------
# Order independence
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reverse", [False, True], ids=["a-first", "b-first"])
def test_specialization_count_is_file_order_independent(reverse):
    """Whatever the dedup rule is, file order must not change the outcome."""
    files = [
        ("defs.pss", "package q { struct S<type T> { T v; } }"),
        ("a.pss", "package a { import q::*; struct A { S<int> v; } }"),
        ("b.pss", "package b { import q::*; struct B { S<int> v; } }"),
    ]
    if reverse:
        files.reverse()
    root = parse_multi_file(files)
    assert_specialization_count(root, "q::S", 1)
