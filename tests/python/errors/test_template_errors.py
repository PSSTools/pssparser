"""Diagnostics for malformed template arguments.

Two things are asserted, and the second is the one that tends to be missing:

1. **An invalid model is rejected.**  Silently accepting a bad argument list is
   worse than a confusing error -- the user gets no signal at all and the
   defect surfaces later as nonsense somewhere else.
2. **The error carries a usable source location.**  A marker reported at
   ``<unknown>:-1:0`` cannot be clicked, cannot be shown in an editor gutter,
   and cannot be attributed to a file by a pre-commit hook.  Several template
   diagnostics report exactly that today.

Runs out of process: some inputs here are close relatives of ones that crash.

See ``docs/template-parameter-test-suite.md`` section 4.5.
"""
import re

import pytest

from ..isolation import run_isolated


PKG = """
package p {
    struct my_s { int z; }
    struct base_s { int b; }
    struct unrelated_s { int u; }
%s
}
"""


def link(body):
    return run_isolated([("t.pss", PKG % body)])


def assert_reports(res, expected: str):
    """The run failed with an error, and the message mentions ``expected``."""
    assert not res.crashed, "crashed instead of reporting an error: %s" % res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
    assert expected in res.output, (
        "expected an error mentioning %r, got %s" % (expected, res.describe()))


def assert_has_location(res):
    """At least one error names a real file, line and column.

    ``<unknown>:-1:0`` is the sentinel emitted when a marker is built without a
    location, so this asserts a marker that is *not* that.
    """
    located = re.search(r"[^\s:]+\.pss:(\d+):(\d+): error:", res.output)
    assert located, (
        "no error carried a usable source location (all were reported at "
        "<unknown>:-1:0 or similar): %s" % res.describe())


# ---------------------------------------------------------------------------
# Arity -- diagnosed today
# ---------------------------------------------------------------------------

def test_too_many_arguments_is_reported():
    res = link("struct S<type T, int N> { T v; } struct Top { S<int,4,8> a; }")
    assert_reports(res, "type accepts 2 template parameter(s) but 3 supplied")


def test_no_arguments_where_none_default_is_reported():
    res = link("struct S<type T> { T v; } struct Top { S<> a; }")
    assert_reports(res, "No default provided for template parameter T")


def test_undefined_argument_type_is_reported():
    res = link("struct S<type T> { T v; } struct Top { S<nosuch_t> a; }")
    assert_reports(res, "unknown type 'nosuch_t'")


def test_undefined_argument_type_has_a_location():
    """This one gets it right, and is the model for the cases below."""
    res = link("struct S<type T> { T v; } struct Top { S<nosuch_t> a; }")
    assert_has_location(res)


def test_arguments_on_a_non_generic_type_is_reported():
    res = link("struct S { int v; } struct Top { S<int> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
    assert "not templated" in res.output, res.describe()


# ---------------------------------------------------------------------------
# Arity -- accepted silently today
# ---------------------------------------------------------------------------

#: ``TaskBuildParamValList::build``'s apply-defaults loop asks each unsupplied
#: parameter for a default.  For a *value* parameter it reads
#: ``getDflt()`` into ``value`` and ``getType()`` into ``type``; when there is
#: no default, ``value`` is null but ``type`` is not, so control reaches the
#: ``else if (type)`` branch and quietly manufactures a **generic type
#: parameter** out of the value parameter's declared type.  The
#: "No default provided" error is only reachable when *both* are null, which is
#: the type-parameter case.
#:
#: So a missing argument for a value parameter is not merely undiagnosed -- it
#: is bound to something meaningless.
#: The apply-defaults case above is fixed.  What remains is narrower: a
#: generic used with *no argument list at all* -- ``S a;`` rather than ``S<>``
#: -- is accepted for both parameter kinds.  ``S<>`` does reach the
#: "No default provided" error, so the check exists; a bare use never gets to
#: it, because argument validation runs only when there is an argument list to
#: validate.
_MISSING_VALUE_ARG = (
    "a generic used with no argument list at all ('S a;', as opposed to "
    "'S<>') never enters argument validation, so neither a missing type "
    "argument nor a missing value argument is reported. Remove this marker "
    "when a bare use of a generic is diagnosed."
)


def test_too_few_arguments_is_reported():
    """``S<int>`` for ``S<type T, int N>``: N has no argument and no default.

    Fixed by giving the apply-defaults loop a *kind* test.  The declared type
    (`int`) is not a default, so it must not be used as one.
    """
    res = link("struct S<type T, int N> { T v; } struct Top { S<int> a; }")
    assert_reports(res, "template parameter")


@pytest.mark.xfail(strict=True, reason=_MISSING_VALUE_ARG)
def test_bare_use_of_a_generic_is_reported():
    """``S a;`` where ``S`` is generic with no defaults."""
    res = link("struct S<type T> { T v; } struct Top { S a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


# ---------------------------------------------------------------------------
# Argument kind -- not checked today
# ---------------------------------------------------------------------------

#: Half of this is fixed: a *value* supplied for a type parameter is now
#: reported.  The converse is harder, and the difficulty is worth recording.
#:
#: When the declared parameter wants a value and the argument parses as a type
#: reference, ``visitDataTypeUserDefined`` optimistically records it as a value
#: expression -- and it has to, because a constant reference is spelled exactly
#: like a type reference.  ``S<C>`` for a package constant and ``S<E::A>`` for
#: an enum item are both legal and both arrive on that path; the project model
#: relies on it.  So rejecting type-looking arguments outright would reject
#: valid code.  Telling them apart means classifying the *resolved target* as
#: type-denoting or value-denoting, which ``probe`` does not do today (it
#: recognizes only ``IEnumItem``).
_KIND_UNCHECKED = (
    "a type supplied where a value parameter is declared is accepted "
    "silently: a type reference and a constant reference are spelled alike, "
    "so the argument is optimistically taken as a value. Remove this marker "
    "when the resolved target is classified as type- or value-denoting."
)


def test_value_supplied_for_a_type_parameter_is_reported():
    """``S<4>`` for ``struct S<type T>``.

    ``TaskExpr2DataType`` returns null for an expression that does not denote
    a type, and that null used to be passed straight into the parameter,
    binding the type parameter to nothing.  It is now diagnosed.

    The converse -- a type supplied for a *value* parameter -- is still open;
    see :func:`test_type_supplied_for_a_value_parameter_is_reported`.
    """
    res = link("struct S<type T> { T v; } struct Top { S<4> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


@pytest.mark.xfail(strict=True, reason=_KIND_UNCHECKED)
def test_type_supplied_for_a_value_parameter_is_reported():
    res = link("struct S<int N> { bit[N] v; } struct Top { S<my_s> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


# ---------------------------------------------------------------------------
# Category type parameters -- LRM 10.3.2.1
# ---------------------------------------------------------------------------
#
# A category type parameter constrains its argument twice over, and the LRM's
# own example turns on the distinction: for ``struct T : base_t``, the buffers
# ``b1`` and ``b2`` are excluded *even though both derive from base_t*, because
# they are not of the struct category.  Checking only the restriction would
# admit them; checking only the category would admit any struct at all.
#
# The positive cases are as load-bearing as the negative ones here.  The
# standard library declares ``addr_region_s<struct TRAIT : addr_trait_s =
# empty_addr_trait_s>`` and passes ``TRAIT`` straight through to further
# generics, so an over-strict check breaks every model that allocates an
# address.

def test_category_restriction_violation_is_reported():
    res = link(
        "struct S<struct T : base_s> { T v; } struct Top { S<unrelated_s> a; }")
    assert_reports(res, "does not derive from 'base_s'")


def test_category_restriction_satisfied_links():
    """Control: an argument that *does* satisfy the restriction must link.

    Guards the test above from over-correcting into rejecting valid arguments.
    """
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "struct D : base_s { int d; } "
        "struct Top { S<D> a; }")
    assert res.ok, res.describe()


def test_the_restriction_type_itself_is_admitted():
    """LRM 10.3.2.1: the argument may be "base_t or one of its subtypes"."""
    res = link(
        "struct S<struct T : base_s> { T v; } struct Top { S<base_s> a; }")
    assert res.ok, res.describe()


def test_an_indirect_subtype_is_admitted():
    """The restriction is satisfied anywhere up the chain, not just one hop."""
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "struct mid_s : base_s { int m; } "
        "struct leaf_s : mid_s { int l; } "
        "struct Top { S<leaf_s> a; }")
    assert res.ok, res.describe()


def test_a_derived_type_of_the_wrong_category_is_rejected():
    """The LRM's b1/b2 case: derives from the restriction, wrong category.

    This is the row that distinguishes a real implementation of 10.3.2.1 from
    a restriction-only one -- ``buf_b`` passes the subtype test and must still
    be rejected.
    """
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "buffer buf_b : base_s { } "
        "struct Top { S<buf_b> a; }")
    assert_reports(res, "type category 'struct'")


def test_a_buffer_parameter_admits_a_buffer():
    """Control for the row above: the same argument under a buffer parameter.

    Also the only coverage of the ``buffer`` category reaching the parameter
    intact -- it was missing from the builder's category table, so the lookup
    read past the end of the map and the parameter carried whatever that
    happened to be.
    """
    res = link(
        "struct S<buffer T : base_s> { } "
        "buffer buf_b : base_s { } "
        "struct Top { S<buf_b> a; }")
    assert res.ok, res.describe()


@pytest.mark.parametrize(
    "decl,arg,wanted",
    [
        ("struct T", "comp_c", "'struct'"),
        ("action T", "unrelated_s", "'action'"),
        ("component T", "unrelated_s", "'component'"),
        ("stream T", "unrelated_s", "'stream'"),
    ],
    ids=["struct-given-component", "action-given-struct",
         "component-given-struct", "stream-given-struct"],
)
def test_a_category_mismatch_is_reported(decl, arg, wanted):
    """The category gate alone, with no restriction in play."""
    res = link(
        "component comp_c { } "
        "struct S<%s> { } struct Top { S<%s> a; }" % (decl, arg))
    assert_reports(res, wanted)


def test_a_default_violating_the_restriction_is_reported():
    """A default is an argument too.

    It is diagnosed at the first use that falls back to it rather than at the
    declaration, because that is where the default becomes a binding.
    """
    res = link(
        "struct S<struct T : base_s = unrelated_s> { T v; } "
        "struct Top { S<> a; }")
    assert_reports(res, "does not derive from 'base_s'")


def test_a_default_satisfying_the_restriction_links():
    res = link(
        "struct S<struct T : base_s = base_s> { T v; } struct Top { S<> a; }")
    assert res.ok, res.describe()


def test_an_unresolvable_restriction_is_reported():
    """The restriction is now resolved even though the generic is never used.

    Before, an unspecialized generic's parameter list was never resolved at
    all, so a restriction naming a type that does not exist went unnoticed.
    """
    res = link("struct S<struct T : nosuch_s> { T v; }")
    assert_reports(res, "unknown type 'nosuch_s'")
    assert_has_location(res)


def test_a_restriction_passed_through_an_enclosing_generic_links():
    """The standard library's shape, and the one an over-strict check breaks.

    Inside ``Outer``, the argument ``T`` names a parameter of the enclosing
    generic, not a type: there is nothing to check it against until ``Outer``
    itself is specialized.  Checking it as though it were a type would reject
    the declaration outright.
    """
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "struct D : base_s { int d; } "
        "struct Outer<struct U : base_s> { S<U> inner; } "
        "struct Top { Outer<D> o; }")
    assert res.ok, res.describe()


def test_a_generic_inheriting_from_its_parameter_satisfies_a_restriction():
    """``Q<base_s>`` derives from ``base_s`` -- through its own parameter.

    The subtype walk has to follow the binding, exactly as member lookup does.
    Stopping at the parameter declaration made this a false rejection: valid
    code refused because the walk could not see past ``: T``.
    """
    res = link(
        "struct Q<type T> : T { } "
        "struct R<struct T : base_s> { T v; } "
        "struct Top { R<Q<base_s>> r; }")
    assert res.ok, res.describe()


def test_a_generic_inheriting_from_an_unrelated_parameter_is_rejected():
    """Control for the row above: following the binding is not blanket assent."""
    res = link(
        "struct Q<type T> : T { } "
        "struct R<struct T : base_s> { T v; } "
        "struct Top { R<Q<unrelated_s>> r; }")
    assert_reports(res, "does not derive from 'base_s'")


def test_a_restriction_violated_through_an_enclosing_generic_is_reported():
    """...and the binding is checked once it is known.

    ``Outer<unrelated_s>`` is rejected at its own parameter; this pins that
    passing a parameter through does not launder it past the check.
    """
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "struct Outer<struct U : base_s> { S<U> inner; } "
        "struct Top { Outer<unrelated_s> o; }")
    assert_reports(res, "does not derive from 'base_s'")


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

# Every diagnostic about an argument list is now reported at the **use site**
# -- the reference that spells the arguments -- rather than at the generic's
# declaration or at <unknown>:-1:0.
#
# The use site is the right choice on two counts.  It is where the reader has
# to go to fix the problem: the declaration is usually correct and is often in
# another file (or in the standard library, where it cannot be edited at all).
# And a single generic has many uses, so a marker on the declaration cannot say
# *which* use was wrong.
#
# It is not the ideal location, which would be the offending argument itself.
# That is out of reach: neither ``ITemplateParamValue`` nor ``IExpr`` carries a
# location, so there is no node to point at.  Naming the parameter in the
# message is the substitute.

@pytest.mark.parametrize(
    "src",
    [
        "struct S<type T, int N> { T v; } struct Top { S<int,4,8> a; }",
        "struct S<type T> { T v; } struct Top { S<> a; }",
        "struct S { int v; } struct Top { S<int> a; }",
        "struct S<type T> { T v; } struct Top { S<4> a; }",
        "struct S<type T, int N> { T v; } struct Top { S<int> a; }",
        "struct S<struct T : base_s> { T v; } struct Top { S<unrelated_s> a; }",
        "struct S<action T> { } struct Top { S<unrelated_s> a; }",
    ],
    ids=["too-many", "no-default", "not-templated", "value-for-type",
         "missing-value", "restriction", "category"],
)
def test_every_argument_list_error_has_a_location(src):
    assert_has_location(link(src))


def test_the_location_names_the_file_the_use_is_in():
    """Declaration in one file, bad use in another: the *use* is reported.

    This is the test that distinguishes the two candidate locations.  Merely
    asserting that some file:line:col appears does not: the parameter
    declarations carry locations too, so pointing at the declaration also
    satisfies that, and every single-file test passes either way.

    Splitting the files also covers the case that motivates the choice -- a
    generic declared in a package the user cannot edit (the standard library
    is full of them) and used wrongly in their own code.
    """
    res = run_isolated([
        ("decl.pss", "package q { struct S<type T, int N> { T v; } }"),
        ("use.pss", "package p { import q::*; struct Top { S<int,4,8> a; } }"),
    ])
    assert re.search(r"use\.pss:\d+:\d+: error:", res.output), (
        "the argument-list error was not reported at the use site: %s"
        % res.describe())
    assert "decl.pss" not in res.output, (
        "the error was reported against the declaration rather than the use: "
        "%s" % res.describe())


def test_the_location_points_at_the_use_not_the_declaration():
    """The same distinction within one file, by line.

    Keeps the property pinned even if the multi-file case above ever stops
    being able to express it.
    """
    res = run_isolated([("t.pss", "\n".join([
        "package p {",                              # 1
        "    struct S<type T, int N> { T v; }",     # 2  <- declaration
        "    struct Top {",                         # 3
        "        S<int,4,8> a;",                    # 4  <- use
        "    }",                                    # 5
        "}",                                        # 6
    ]))])
    m = re.search(r"t\.pss:(\d+):\d+: error:", res.output)
    assert m, res.describe()
    assert int(m.group(1)) == 4, (
        "expected the error on line 4 (the use), got line %s: %s"
        % (m.group(1), res.describe()))


def test_a_duplicate_parameter_name_error_has_a_location():
    """A declaration-side diagnostic, and the one case where the declaration
    *is* the right place to point.

    The parameter declarations were built without a location at all, so this
    marker had nothing to report.  They now take the location of their own
    name.
    """
    res = link("struct S<type T, type T> { T v; } struct Top { S<int> a; }")
    assert_reports(res, "duplicate parameter name 'T'")
    assert_has_location(res)


# ---------------------------------------------------------------------------
# Error recovery
# ---------------------------------------------------------------------------

def test_a_bad_argument_list_does_not_suppress_later_errors():
    """One bad specialization must not stop the rest of the model being checked.

    ``build`` returns null on the arity errors above, and a null return that
    aborted the walk would make the first template mistake in a file hide every
    later one -- the worst shape for an error report.
    """
    res = link(
        "struct S<type T, int N> { T v; } "
        "struct Top { S<int,4,8> a; nosuch_t b; }")
    assert not res.crashed, res.describe()
    assert "type accepts 2 template parameter(s) but 3 supplied" in res.output, \
        res.describe()
    assert "nosuch_t" in res.output, (
        "the unrelated later error was suppressed by the template error: %s"
        % res.describe())
