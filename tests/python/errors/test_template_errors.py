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
_MISSING_VALUE_ARG = (
    "a value parameter with no default and no supplied argument is accepted "
    "silently: TaskBuildParamValList's apply-defaults loop finds a null dflt "
    "but a non-null declared type, takes the 'else if (type)' branch and "
    "manufactures a generic type parameter instead of reporting. Remove this "
    "marker when it is diagnosed."
)


@pytest.mark.xfail(strict=True, reason=_MISSING_VALUE_ARG)
def test_too_few_arguments_is_reported():
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

_KIND_UNCHECKED = (
    "a template argument of the wrong kind is accepted silently -- a value "
    "supplied for a type parameter, or a type for a value parameter, produces "
    "no diagnostic. Remove this marker when argument kind is checked."
)


@pytest.mark.xfail(strict=True, reason=_KIND_UNCHECKED)
def test_value_supplied_for_a_type_parameter_is_reported():
    res = link("struct S<type T> { T v; } struct Top { S<4> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


@pytest.mark.xfail(strict=True, reason=_KIND_UNCHECKED)
def test_type_supplied_for_a_value_parameter_is_reported():
    res = link("struct S<int N> { bit[N] v; } struct Top { S<my_s> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


@pytest.mark.xfail(
    strict=True,
    reason="a category type parameter's restriction is not enforced: "
           "S<struct T : base_s> accepts an argument that does not derive "
           "from base_s. Remove this marker when the restriction is checked.",
)
def test_category_restriction_violation_is_reported():
    res = link(
        "struct S<struct T : base_s> { T v; } struct Top { S<unrelated_s> a; }")
    assert not res.crashed, res.describe()
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()


def test_category_restriction_satisfied_links():
    """Control: an argument that *does* satisfy the restriction must link.

    Guards the fix for the test above from over-correcting into rejecting
    valid arguments.
    """
    res = link(
        "struct S<struct T : base_s> { T v; } "
        "struct D : base_s { int d; } "
        "struct Top { S<D> a; }")
    assert res.ok, res.describe()


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------

_NO_LOCATION = (
    "the diagnostic is reported at <unknown>:-1:0 -- the marker is built "
    "without a source location, so it cannot be shown in an editor or "
    "attributed to a file. Remove this marker when the location is attached."
)


@pytest.mark.xfail(strict=True, reason=_NO_LOCATION)
def test_too_many_arguments_error_has_a_location():
    res = link("struct S<type T, int N> { T v; } struct Top { S<int,4,8> a; }")
    assert_has_location(res)


@pytest.mark.xfail(strict=True, reason=_NO_LOCATION)
def test_missing_default_error_has_a_location():
    res = link("struct S<type T> { T v; } struct Top { S<> a; }")
    assert_has_location(res)


@pytest.mark.xfail(strict=True, reason=_NO_LOCATION)
def test_non_generic_with_arguments_error_has_a_location():
    res = link("struct S { int v; } struct Top { S<int> a; }")
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
