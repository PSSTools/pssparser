"""What a specialization is *called*, and what must not be decided from a name.

Two related things live here, and the second is the reason the first matters
more than cosmetics.

**Specializations were all named the same.**  ``mkTypename`` emitted
``name<>`` -- the brackets with nothing between them -- so every specialization
of ``S`` was called ``S<>``.  Identity was never affected, because
specializations are matched by comparing parameter lists rather than names, so
nothing *linked* incorrectly.  Everything a person or a tool reads was
affected: a diagnostic naming ``S<>`` cannot say which use it means, and an
outline built on the API showed one entry repeated.

**Types were being recognized by name.**  Three places asked whether something
was a built-in collection by testing its name, two of them by *prefix*
(``n.rfind("set", 0) == 0``).  That is wrong twice over: user type names begin
with those letters routinely -- ``setup_s``, ``map_cfg_s``, ``array_of_s`` --
and a user may declare their own ``array`` in their own package, which is not
the built-in one and does not have its methods.  With specializations all
named ``S<>``, a name test on a specialization scope could not have worked
even in principle.

The fix in both cases is the same idea: decide from the *declaration*, not
from the spelling.  A built-in is identified by being declared where the
built-ins are -- ``BuiltinsFactory`` builds them into a global scope with no
file behind it -- rather than by what it is called.

See ``docs/template-parameter-test-suite.md`` section 4.7.
"""
import pytest

from ..isolation import assert_clean, run_isolated
from ..test_helpers import parse_pss
from ..template_helpers import node_name, specializations


def link(src):
    return run_isolated([("t.pss", src)])


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------

_NAMES = """
package p {
    struct a_s { int a; }
    struct b_s { int b; }
    struct S<type T, int N> { T v; }
    struct Top { S<a_s,1> x; S<b_s,2> y; S<a_s,3> z; }
}
"""


def test_specialization_names_distinguish_arguments():
    """Three specializations, three different names.

    Asserting that *a* name exists would pass under the old behaviour too --
    ``S<>`` is a name.  The property is that the names differ, and that they
    differ in the way the arguments do.
    """
    names = [node_name(s) for s in specializations(parse_pss(_NAMES), "p::S")]
    assert len(names) == 3, names
    assert len(set(names)) == 3, (
        "specializations of the same generic share a name: %s" % names)
    assert names == ["S<a_s,1>", "S<b_s,2>", "S<a_s,3>"], names


def test_a_specialization_name_reads_as_its_argument_list():
    """The name is the base name with the *bound* arguments in it.

    The bound arguments, not the written ones: a use that falls back to a
    default names the default, so two uses that resolve to the same
    specialization also read the same.
    """
    root = parse_pss("""
        package p {
            struct base_s { int b; }
            struct d_s : base_s { int d; }
            struct S<struct T : base_s = base_s> { T v; }
            struct Top { S<d_s> x; S<> y; }
        }
    """)
    assert [node_name(s) for s in specializations(root, "p::S")] == \
        ["S<d_s>", "S<base_s>"]


def test_a_nested_specialization_appears_in_the_name():
    """Specializations are created innermost-first, so the inner one is
    already named by the time the outer one is."""
    root = parse_pss("""
        package p {
            struct a_s { int a; }
            struct S<type T, int N> { T v; }
            struct Q<type U> { U u; }
            struct Top { Q<S<a_s,1>> q; }
        }
    """)
    assert [node_name(s) for s in specializations(root, "p::Q")] == \
        ["Q<S<a_s,1>>"]


@pytest.mark.parametrize(
    "arg,expect",
    [
        ("int", "S<int[32]>"),
        ("bit", "S<bit[1]>"),
        ("bit[8]", "S<bit[8]>"),
        ("string", "S<string>"),
        ("bool", "S<bool>"),
    ],
    ids=["int", "bit", "bit8", "string", "bool"],
)
def test_a_primitive_argument_is_named_canonically(arg, expect):
    """``int`` and ``int[32]`` are the same type and get the same name.

    Rendering the width always is what makes that true -- two spellings of one
    type must not read as two types, since they *are* one specialization.
    """
    root = parse_pss("""
        package p {
            struct S<type T> { T v; }
            struct Top { S<%s> a; }
        }
    """ % arg)
    assert [node_name(s) for s in specializations(root, "p::S")] == [expect]


# ---------------------------------------------------------------------------
# Not deciding by name
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "name",
    ["setup_s", "map_cfg_s", "array_of_s", "listener_s"],
    ids=["set", "map", "array", "list"],
)
def test_a_struct_whose_name_starts_like_a_collection_has_no_collection_methods(name):
    """``setup_s.size()`` was accepted on a plain struct with no such member.

    The prefix test ``n.rfind("set", 0) == 0`` matched every one of these.
    """
    res = link("""
        package p {
            struct %s { int x; }
            struct Top { %s s; exec init_down { int n = s.size(); } }
        }
    """ % (name, name))
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
    assert not res.crashed, res.describe()


@pytest.mark.parametrize(
    "decl,expr",
    [
        ("array<my_s,4> c;", "c.size()"),
        ("list<my_s> c;", "c.size()"),
        ("set<my_s> c;", "c.size()"),
        ("map<int,my_s> c;", "c.size()"),
    ],
    ids=["array", "list", "set", "map"],
)
def test_the_real_collections_still_have_their_methods(decl, expr):
    """Control for the rows above.

    Without these, dropping the name test entirely -- recognizing nothing as a
    collection -- would pass the whole group.
    """
    assert_clean([("t.pss", """
        package p {
            struct my_s { int z; }
            struct Top { %s exec init_down { int n = %s; } }
        }
    """ % (decl, expr))])


def test_a_user_declared_array_is_not_the_builtin_array():
    """A package may declare its own ``array``.

    Subscripting it must not reach through to a template argument as though it
    were the built-in collection: this ``array`` has a field ``junk`` and no
    element type at all.
    """
    res = link("""
        package p {
            struct my_s { int z; }
            struct array<type T> { int junk; }
            struct Top { array<my_s> a; exec init_down { a[0].z = 1; } }
        }
    """)
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
    assert not res.crashed, res.describe()


def test_a_user_declared_list_does_not_gain_collection_methods():
    res = link("""
        package p {
            struct list<type T> { int junk; }
            struct Top { list<int> l; exec init_down { int n = l.size(); } }
        }
    """)
    assert res.rc == 1, "expected a reported error, got %s" % res.describe()
    assert not res.crashed, res.describe()


def test_a_user_declared_array_keeps_its_own_members():
    """Control: the user's type is still a perfectly good type."""
    assert_clean([("t.pss", """
        package p {
            struct array<type T> { int junk; }
            struct Top { array<int> a; exec init_down { a.junk = 1; } }
        }
    """)])
