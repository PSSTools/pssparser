"""What a template parameter is actually bound to.

This is the core group of the template-parameter suite.  Every test here
asserts the *identity* of the declaration a parameter resolved to, rather than
asserting that the model linked without an error.

The distinction matters because a wrong binding is silent.  It either resolves
to something and produces a confusing error far downstream in an unrelated
file, or it resolves to something with a compatible-looking member and produces
no error at all.  ``assert_parse_ok`` -- the assertion every pre-existing
template test uses -- cannot see either case.

See ``docs/template-parameter-test-suite.md`` section 4.2.
"""
import pytest

from ..isolation import run_isolated
from ..test_helpers import parse_pss, parse_multi_file
from ..template_helpers import (
    assert_binds_to,
    assert_specialization_count,
    binding_decl,
    bindings,
    find_specialization,
    lookup,
    specializations,
)


# ---------------------------------------------------------------------------
# Builtin scalar arguments
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "arg,expected",
    [
        ("int", "int"),
        ("bit", "bit"),
        ("bit[8]", "bit[8]"),
        ("int[16]", "int[16]"),
        ("bool", "bool"),
    ],
)
def test_scalar_argument_binds(arg, expected):
    """A builtin scalar argument binds to that exact scalar type.

    ``bit[8]`` and ``int[16]`` are the interesting rows: width is carried
    separately from signedness, so a binding that dropped the width would still
    describe as ``bit``/``int`` and pass a name-only check.
    """
    root = parse_pss(
        """
        package p {
            struct S<type T> { T v; }
            struct Top { S<%s> a; }
        }
        """ % arg
    )
    spec = find_specialization(root, "p::S", expected)
    assert_binds_to(root, spec, "T", expected)


# ---------------------------------------------------------------------------
# User-defined type arguments -- asserted by declaration identity
# ---------------------------------------------------------------------------

def test_user_struct_argument_binds_to_that_declaration():
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct S<type T> { T v; }
            struct Top { S<my_s> a; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    spec = find_specialization(root, "p::S", "my_s")
    assert_binds_to(root, spec, "T", my_s)


def test_distinct_user_arguments_bind_to_their_own_declarations():
    """Two specializations, each bound to its own struct -- not to each other's.

    This is the assertion a link-only test cannot make.  Both uses link
    cleanly whether or not the bindings got crossed.
    """
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct other_s { int quux; }
            struct S<type T> { T v; }
            struct Top { S<my_s> a; S<other_s> b; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    other_s = lookup(root, "p::other_s")

    assert_binds_to(root, find_specialization(root, "p::S", "my_s"), "T", my_s)
    assert_binds_to(root, find_specialization(root, "p::S", "other_s"), "T", other_s)


def test_same_named_types_in_different_packages_stay_distinct():
    """Two packages each declaring ``item_s``: bindings must not be confused.

    Name-based comparison passes here regardless of which one each
    specialization actually bound to, which is exactly why the helper compares
    declaration identity.
    """
    root = parse_pss(
        """
        package a { struct item_s { int za; } }
        package b { struct item_s { int zb; } }
        package p {
            import a::*;
            struct S<type T> { T v; }
            struct Top { S<a::item_s> x; S<b::item_s> y; }
        }
        """
    )
    a_item = lookup(root, "a::item_s")
    b_item = lookup(root, "b::item_s")

    bound = [binding_decl(root, s, "T") for s in specializations(root, "p::S")]

    assert a_item in bound, "no specialization bound T to a::item_s"
    assert b_item in bound, (
        "no specialization bound T to b::item_s -- both uses likely bound to "
        "the same declaration")


def test_qualified_argument_binds():
    root = parse_pss(
        """
        package q { struct thing_s { int z; } }
        package p {
            struct S<type T> { T v; }
            struct Top { S<q::thing_s> a; }
        }
        """
    )
    thing_s = lookup(root, "q::thing_s")
    spec = find_specialization(root, "p::S", "thing_s")
    assert_binds_to(root, spec, "T", thing_s)


def test_imported_argument_binds():
    """Binding must survive import resolution, not just qualified lookup."""
    root = parse_pss(
        """
        package q { struct thing_s { int z; } }
        package p {
            import q::*;
            struct S<type T> { T v; }
            struct Top { S<thing_s> a; }
        }
        """
    )
    thing_s = lookup(root, "q::thing_s")
    spec = find_specialization(root, "p::S", "thing_s")
    assert_binds_to(root, spec, "T", thing_s)


def test_argument_declared_in_another_file_binds():
    root = parse_multi_file([
        ("defs.pss", "package q { struct thing_s { int z; } }"),
        ("use.pss", """
            package p {
                import q::*;
                struct S<type T> { T v; }
                struct Top { S<thing_s> a; }
            }
        """),
    ])
    thing_s = lookup(root, "q::thing_s")
    spec = find_specialization(root, "p::S", "thing_s")
    assert_binds_to(root, spec, "T", thing_s)


def test_enum_argument_binds():
    root = parse_pss(
        """
        package p {
            enum e_t { A, B }
            struct S<type T> { T v; }
            struct Top { S<e_t> a; }
        }
        """
    )
    e_t = lookup(root, "p::e_t")
    spec = find_specialization(root, "p::S", "e_t")
    assert_binds_to(root, spec, "T", e_t)


# ---------------------------------------------------------------------------
# Value parameters and defaults
# ---------------------------------------------------------------------------

def test_value_argument_binds():
    root = parse_pss(
        """
        package p {
            struct S<int N> { bit[N] v; }
            struct Top { S<8> a; }
        }
        """
    )
    assert_binds_to(root, find_specialization(root, "p::S", "8"), "N", "8")


def test_mixed_type_and_value_arguments_bind_independently():
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct S<type T, int N> { T v; }
            struct Top { S<my_s, 8> a; }
        }
        """
    )
    spec = find_specialization(root, "p::S", "my_s", "8")
    assert_binds_to(root, spec, "T", lookup(root, "p::my_s"))
    assert_binds_to(root, spec, "N", "8")


def test_unsupplied_parameter_takes_declared_default():
    """A parameter the use did not supply falls back to its declared default.

    This is the boundary in ``TaskBuildParamValList::build`` between the
    supplied-value loop and the apply-defaults loop, so it is worth pinning at
    exactly one supplied argument.
    """
    root = parse_pss(
        """
        package p {
            struct S<type T, int N = 4> { T v; }
            struct Top { S<int> a; }
        }
        """
    )
    spec = find_specialization(root, "p::S", "int", "4")
    assert_binds_to(root, spec, "T", "int")
    assert_binds_to(root, spec, "N", "4")


def test_all_parameters_default():
    root = parse_pss(
        """
        package p {
            struct S<type T = int, int N = 4> { T v; }
            struct Top { S<> a; }
        }
        """
    )
    spec = find_specialization(root, "p::S", "int", "4")
    assert_binds_to(root, spec, "T", "int")
    assert_binds_to(root, spec, "N", "4")


def test_explicit_argument_overrides_default():
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct S<type T = int> { T v; }
            struct Top { S<my_s> a; }
        }
        """
    )
    spec = find_specialization(root, "p::S", "my_s")
    assert_binds_to(root, spec, "T", lookup(root, "p::my_s"))


# A default naming an earlier parameter used to bind to that parameter's
# *declaration* rather than to the argument bound in this specialization.
# ``TaskBuildParamValList`` copied the declared default verbatim; it now
# resolves the name against the parameters already bound in the list being
# built.
def test_type_default_referencing_an_earlier_parameter():
    """``struct S<type T, type U = T>`` -- U's default names T.

    The default is resolved in the specialization's own scope, so U must come
    out bound to whatever T was bound to, not to the declaration of T.

    The pattern is unambiguously intended: the pre-existing
    ``test_specialized_default_value_param_resolves`` uses
    ``struct Q<type R, int SZ = sz_t<R>::xz>``, whose default likewise names an
    earlier parameter.
    """
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct S<type T, type U = T> { T a; U b; }
            struct Top { S<my_s> x; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    spec = specializations(root, "p::S")[0]
    assert_binds_to(root, spec, "T", my_s)
    assert_binds_to(root, spec, "U", my_s)


# ---------------------------------------------------------------------------
# A parameter as an argument -- the shape behind the open whole-model defect
# ---------------------------------------------------------------------------

# Specializing a generic on an *enclosing generic's parameter* was broken
# three ways at once, all of them silent once the copier stopped crashing:
#
# 1. ``TaskBuildParamValList::visitDataTypeUserDefined`` followed the resolved
#    argument reference and let that hop overwrite the *declaration*-side
#    capture, so ``S<type T> { Q<T> inner; }`` produced a specialization of Q
#    whose parameter was named ``T``.  Q's body refers to ``U``, which was
#    therefore bound to nothing -- the origin of the old "unknown type 'U'"
#    message.
# 2. The argument was recorded as the parameter *reference* rather than what
#    the parameter is bound to, so every specialization of S shared one Q.
# 3. ``TaskGetSpecializedTemplateType::mk`` never recorded which
#    specialization it had just created, so specializations after the first
#    resolved their own parameters through specialization 0.
#
# The tests below fail on any one of the three, which is why they are kept
# separate rather than collapsed into one.


def test_outer_parameter_passed_as_inner_argument():
    """``S<type T> { Q<T> inner; }`` used as ``S<my_s>``.

    The inner specialization's parameter must bind to the *outer
    specialization's argument* (``my_s``), not to the outer declaration's
    parameter or its default.  This is the small-model analogue of the open
    whole-model defect, where an element type was taken from a parameter's
    declared default rather than from the specialization's bound argument.
    """
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct Q<type U> { U u; }
            struct S<type T> { Q<T> inner; }
            struct Top { S<my_s> x; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")

    q_specs = specializations(root, "p::Q")
    bound = [bindings(root, s) for s in q_specs]
    assert ["my_s"] in bound, (
        "Q was never specialized on the outer argument my_s; Q's "
        "specializations bound %r" % (bound,))
    assert_binds_to(root, find_specialization(root, "p::Q", "my_s"), "U", my_s)


def test_outer_parameter_passed_through_two_levels():
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct R<type V> { V v; }
            struct Q<type U> { R<U> r; }
            struct S<type T> { Q<T> q; }
            struct Top { S<my_s> x; }
        }
        """
    )
    my_s = lookup(root, "p::my_s")
    assert_binds_to(root, find_specialization(root, "p::R", "my_s"), "V", my_s)


def test_two_outer_specializations_produce_two_inner_bindings():
    """``S<my_s>`` and ``S<other_s>`` must each drive their own ``Q``.

    If the inner argument were taken from the declaration rather than the
    enclosing specialization, both would bind the same way and this fails.
    """
    root = parse_pss(
        """
        package p {
            struct my_s { int zork; }
            struct other_s { int quux; }
            struct Q<type U> { U u; }
            struct S<type T> { Q<T> inner; }
            struct Top { S<my_s> a; S<other_s> b; }
        }
        """
    )
    bound = [bindings(root, s) for s in specializations(root, "p::Q")]
    assert ["my_s"] in bound and ["other_s"] in bound, (
        "each outer specialization should drive its own Q; Q bound %r"
        % (bound,))


def test_value_parameter_passed_as_inner_argument():
    root = parse_pss(
        """
        package p {
            struct Q<int M> { bit[M] v; }
            struct S<int N> { Q<N> inner; }
            struct Top { S<8> x; }
        }
        """
    )
    bound = [bindings(root, s) for s in specializations(root, "p::Q")]
    assert ["8"] in bound, (
        "inner value parameter should bind to the outer argument 8, bound %r"
        % (bound,))


# ---------------------------------------------------------------------------
# Which specialization is "this" one
# ---------------------------------------------------------------------------

def test_each_specialization_resolves_its_own_parameter():
    """Three specializations; the second and third must not read the first's.

    ``TaskGetSpecializedTemplateType::mk`` did not record a specialization's
    position in the generic's ``spec_types`` vector, so every specialization
    reported itself as index 0.  A reference to a parameter from inside the
    second or third one then resolved through the *first* specialization and
    picked up its binding.

    Nothing above catches this on its own: the outer bindings were always
    right, and the symptom appears only where a parameter is *used* -- as an
    argument here, so that a wrong binding shows up as a missing inner
    specialization rather than as an error.
    """
    root = parse_pss(
        """
        package p {
            struct a_s { int f; }
            struct b_s { int f; }
            struct c_s { int f; }
            struct Q<type U> { U u; }
            struct S<type T> { Q<T> inner; }
            struct Top { S<a_s> a; S<b_s> b; S<c_s> c; }
        }
        """
    )
    bound = sorted(bindings(root, s)[0] for s in specializations(root, "p::Q"))
    assert bound == ["a_s", "b_s", "c_s"], (
        "each of the three specializations should drive its own Q; Q bound %r"
        % (bound,))


# ---------------------------------------------------------------------------
# Expression arguments resolve at the use site (plan 1.4; K5/F5 in
# docs/design/symbol-resolution/A-crashes.md). `S<N+1>` used to resolve
# nothing where it was written; its `N` was resolved inside the new
# specialization instead, where the callee's own `N` captured it.
# ---------------------------------------------------------------------------

def _arg_lhs_binding(src):
    """For every specialization of p::S: the declaration that the left
    operand of its first (compound) argument binds to, and that
    declaration's bound value."""
    from pssparser.core import resolveSymbolPathRef
    from ..template_helpers import _param
    root = parse_pss(src)
    out = []
    for s in specializations(root, "p::S"):
        lhs = _param(s, 0).getDflt().getLhs()
        assert lhs.getTarget() is not None, "argument operand is unbound"
        decl = resolveSymbolPathRef(root, lhs.getTarget())
        out.append((type(decl).__name__, decl.getDflt().getValue()))
    return out


@pytest.mark.parametrize("callee_param", ["N", "W"],
                         ids=["same-name", "different-name"])
def test_compound_argument_binds_the_callers_parameter(callee_param):
    src = """
package p {
    struct S<int %s=1> { rand bit[%s] v; }
    struct T<int N=1> { rand S<N+1> s; }
    struct Top { T<3> t; }
}
""" % (callee_param, callee_param)
    assert _arg_lhs_binding(src) == [("TemplateValueParamDecl", 3)]


def test_undefined_name_in_a_compound_argument_is_reported_where_written():
    """`M` is not in scope where `S<M+1>` is written. S's own parameter is
    called M, and the argument used to bind to it and link cleanly."""
    res = run_isolated([("t.pss", """
struct S<int M=1> { rand bit[M] v; }
struct T<int N=1> { rand S<M+1> s; }
component pss_top { action A { rand T<3> t; } }
""")])
    assert res.rc == 1, res.describe()
    assert "t.pss:3:28: error: unknown identifier 'M'" in res.output, res.describe()
    assert res.output.count("error:") == 1, res.describe()


# ---------------------------------------------------------------------------
# An expression inside a type argument resolves at the use site too. The `N`
# of `g_s<bit[N]>` used to be resolved in the copy inside the specialization,
# in the generic's declaring scope: a false "unknown identifier 'N'", or a
# silent binding to a same-named symbol declared next to the generic.
# ---------------------------------------------------------------------------

_G_S = "package r { %s struct g_s<type T> { T f; } struct k_s<type T> { g_s<T> y; } }\n"


def _width_bindings(root, qname="r::g_s"):
    """For every specialization of ``qname`` whose argument is an integer
    type: the declaration its width binds to, as (kind, name, init value)."""
    from pssparser.core import resolveSymbolPathRef
    from ..template_helpers import _param
    out = []
    for s in specializations(root, qname):
        dflt = _param(s, 0).getDflt()
        if type(dflt).__name__ != "DataTypeInt":
            continue
        w = dflt.getWidth()
        assert w.getTarget() is not None, "width of %r is unbound" % s.getName()
        decl = resolveSymbolPathRef(root, w.getTarget())
        out.append((type(decl).__name__, decl.getName().getId(),
                    decl.getInit().getValue()))
    return out


@pytest.mark.parametrize("r_decl", ["", "const int N = 2;"],
                         ids=["plain", "shadowed-in-generic-package"])
def test_width_in_type_argument_binds_at_use_site(r_decl):
    root = parse_pss(_G_S % r_decl + """
package p { import r::*; const int N = 8; struct u_s { g_s<bit[N]> x; } }
""")
    assert _width_bindings(root) == [("Field", "N", 8)]


def test_width_in_type_argument_binds_in_the_generics_own_package():
    root = parse_pss("""
package p { struct g_s<type T> { T f; } const int N = 8; struct u_s { g_s<bit[N]> x; } }
""")
    assert _width_bindings(root, "p::g_s") == [("Field", "N", 8)]


def test_width_in_nested_and_forwarded_type_arguments():
    root = parse_pss(_G_S % "const int N = 2;" + """
package p { import r::*; const int N = 8;
  struct u_s { g_s<g_s<bit[N]>> a; k_s<bit[N]> b; } }
""")
    # Shared by the inner g_s<bit[N]> and k_s's forwarded g_s<T>.
    assert _width_bindings(root) == [("Field", "N", 8)]
    assert _width_bindings(root, "r::k_s") == [("Field", "N", 8)]


@pytest.mark.parametrize("arg", [
    "bit[q::M]",
    "bit[e_t::B]",
    "e_t in [e_t::A]",
    "int in [0..N]",
    "bit[N] in [1..N]",
])
def test_type_argument_expression_forms_link(arg):
    from ..test_helpers import assert_parse_ok
    assert_parse_ok(_G_S % "" + """
package q { const int M = 3; enum e_t { A, B=5 } }
package p { import r::*; import q::*; const int N = 8;
  struct u_s { g_s<%s> x; } }
""" % arg)


@pytest.mark.parametrize("n,count", [(8, 1), (4, 2)])
def test_symbolic_width_shares_a_specialization_with_its_value(n, count):
    """`bit[N]` with N == 8 is `bit[8]`: one specialization, not two."""
    root = parse_pss(_G_S % "" + """
package p { import r::*; const int N = %d;
  struct u_s { g_s<bit[N]> a; g_s<bit[8]> b; g_s<bool> c; } }
""" % n)
    assert_specialization_count(root, "r::g_s", count + 1)


def test_enclosing_parameter_as_width_gives_one_specialization_per_value():
    root = parse_pss(_G_S % "" + """
package p { import r::*;
  struct w_s<int W=1, type E=bool> { g_s<bit[W]> x; g_s<E> y; }
  struct u_s { w_s<4> a; w_s<8, int> b; } }
""")
    descs = sorted(bindings(root, s)[0] for s in specializations(root, "r::g_s"))
    assert descs == ["bit", "bit", "bool", "int"], descs


@pytest.mark.parametrize("r_decl", ["", "const int M = 2;"],
                         ids=["undeclared", "declared-only-in-generic-package"])
def test_unknown_width_in_type_argument_is_reported_where_written(r_decl):
    """`M` is not visible where it is written. An `M` next to the generic
    must not capture it."""
    res = run_isolated([("t.pss", _G_S % r_decl + """
package p { struct u_s { r::g_s<bit[M]> x; } }
""")])
    assert res.rc == 1, res.describe()
    assert "t.pss:3:37: error: unknown identifier 'M'" in res.output, res.describe()
    assert res.output.count("error:") == 1, res.describe()


def test_width_in_type_default_binds_in_the_declaring_package():
    """The mirror image: a default means what it means where the generic
    declares it, so the caller's `K` does not capture it."""
    root = parse_pss("""
package r { const int K = 4; struct g_s<type T = bit[K]> { T f; } }
package p { const int K = 9; struct u_s { r::g_s<> x; r::g_s<bit[4]> y; } }
""")
    assert _width_bindings(root) == [("Field", "K", 4)]
