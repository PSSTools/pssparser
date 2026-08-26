"""`extend` and template types, and where the two mechanisms meet.

Four defects live behind this file, and only one of them is about templates.

**A generic's extension never reached its instances.**  LRM 17.2.6a says
extending the generic template type "will apply to all instances of the
template type".  It applied to none of them: a specialization is built by
copying the generic's *AST* type scope, and ``TaskApplyTypeExtensions`` merged
extension members into the *symbol* scope only, so the copy never saw them.
``extend struct p::S { int added; }`` followed by ``S<int> s; s.added``
reported "Failed to find elem added".

**Extending a template instance crashed.**  ``extend struct p::S<int> {...}``
(LRM 17.2.6b) resolved to a reference path ending in a ``TypeSpec`` step.  No
specialization exists yet when extensions are applied -- they are created later,
by ``TaskResolveRefs`` -- so the step indexed into an empty list and landed on
an unrelated node, which was then written to as though it were a scope.  The
LRM's own Example247 segfaulted.  It is now diagnosed; instance extension
remains unimplemented.

**An unqualified extend target never resolved.**  Nothing to do with
templates: ``package p { struct S {} extend struct S {} }`` reported "unknown
type 'S'; did you mean 'p'?", and only a fully-qualified ``p::S`` worked.  The
resolver was handed a symbol-table iterator sitting at the root, so the only
names in scope were package names.  LRM Example247 is written unqualified.

**An extension written inside a component did nothing at all.**  Also not about
templates, and the worst of the four, because it is silent: the target
resolved, no diagnostic was issued, and the members simply were not there.
``visitSymbolTypeScope`` did not recurse, so the walk never entered a component
-- which LRM 17.3 makes the *expected* place to write an extension, since a
component-scope type may only be extended from that same scope.

See ``docs/template-parameter-test-suite.md`` section 4.8.
"""
import pytest

from ..isolation import assert_clean, assert_rejects, run_isolated


def link(src):
    return run_isolated([("t.pss", src)])


# ---------------------------------------------------------------------------
# LRM 17.2.6a -- extending the generic applies to every instance
# ---------------------------------------------------------------------------

def test_a_generic_extension_member_is_visible_in_a_specialization():
    assert_clean([("t.pss", """
        package p {
            struct S<type T> { T v; }
            extend struct p::S { int added; }
            struct Top { S<int> s; exec init_down { s.added = 1; } }
        }
    """)])


def test_a_member_the_extension_did_not_add_is_still_rejected():
    """Control.  Without it, resolving every member of a specialization
    permissively would pass the test above."""
    assert_rejects([("t.pss", """
        package p {
            struct S<type T> { T v; }
            extend struct p::S { int added; }
            struct Top { S<int> s; exec init_down { s.nosuch = 1; } }
        }
    """)], "nosuch")


def test_the_extension_reaches_every_specialization():
    """"...will apply to all instances", not just the first one built."""
    assert_clean([("t.pss", """
        package p {
            struct a_s { int a; }
            struct S<type T> { T v; }
            extend struct p::S { int added; }
            struct Top {
                S<int> x;
                S<a_s> y;
                exec init_down { x.added = 1; y.added = 2; }
            }
        }
    """)])


def test_the_extension_applies_to_a_specialization_written_before_it():
    """Order of declaration must not matter.

    ``Top`` names ``S<int>`` on a line above the ``extend``.  Extensions are
    all applied before any specialization is created, so both orders have to
    give the same answer -- and this is the order that would break if they
    were interleaved.
    """
    assert_clean([("t.pss", """
        package p {
            struct S<type T> { T v; }
            struct Top { S<int> s; }
            extend struct p::S { int added; }
            struct Top2 { S<int> t; exec init_down { t.added = 1; } }
        }
    """)])


def test_the_extension_is_visible_through_a_derived_generic():
    """``D<T> : B<T>`` inherits what an extension added to ``B``."""
    assert_clean([("t.pss", """
        package p {
            struct B<type T> { T v; }
            struct D<type T> : B<T> { int d; }
            extend struct p::B { int added; }
            struct Top { D<int> s; exec init_down { s.added = 1; } }
        }
    """)])


# ---------------------------------------------------------------------------
# An extension body that mentions a template parameter
# ---------------------------------------------------------------------------

_PARAM_BODY = """
package p {
    struct a_s { int a; }
    struct S<type T> { T v; }
    extend struct p::S { T w; }
    // `v` is declared, `w` is added by the extension; both are typed `T`.
    struct Top { S<int> i; S<a_s> s; exec init_down { %s } }
}
"""


def test_an_extension_member_typed_by_the_parameter_binds_per_instance():
    """``T w;`` in the extension body is a different type in each instance.

    This is the property that forces the extension to be *copied* into each
    specialization rather than shared: one node merged into the generic could
    only ever carry one binding.  ``i.w`` is an int and ``s.w`` is an ``a_s``,
    in the same model.
    """
    assert_clean([("t.pss", _PARAM_BODY % "i.w = 1; s.w.a = 2;")])


def test_the_parameter_typed_member_is_the_struct_in_the_struct_instance():
    """Control for the row above.

    ``i.w = 1; s.w.a = 2;`` alone does not prove much -- it would also pass if
    ``w`` resolved permissively.  Asking for a member ``a_s`` does *not* have
    is what shows ``s.w`` is really an ``a_s`` and not something anonymous.

    Only this direction can be asserted.  The int direction cannot: member
    access on a primitive-typed field is not checked at all, so ``i.w.nosuch``
    links, exactly as ``i.v.nosuch`` does on the *declared* field.  That gap is
    neither template- nor extension-specific, and is recorded separately.
    """
    assert_rejects([("t.pss", _PARAM_BODY % "s.w.nosuch = 1;")], "nosuch")


@pytest.mark.parametrize("member", ["v", "w"], ids=["declared", "extension"])
def test_an_extension_member_behaves_exactly_like_a_declared_one(member):
    """The pair is the point.

    ``v`` is declared in the generic and ``w`` is added by an extension; both
    are typed ``T``.  Running the same two probes over both is what says the
    extension member is not merely *present* but bound the same way.
    """
    assert_clean([("t.pss", _PARAM_BODY % ("s.%s.a = 1;" % member))])
    assert_rejects([("t.pss", _PARAM_BODY % ("s.%s.nosuch = 1;" % member))])


def test_an_extension_constraint_may_reference_a_value_parameter():
    """LRM Example247 constrains an added field against ``LB``/``UB``."""
    assert_clean([("t.pss", """
        package p {
            struct S<int N = 4> { rand int v; }
            extend struct p::S { rand int w; constraint { w < N; } }
            struct Top { S<8> s; }
        }
    """)])


# ---------------------------------------------------------------------------
# LRM 17.2.6b -- extending a template instance
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "target",
    ["p::S<int>", "p::S<>"],
    ids=["explicit-arg", "empty-arg-list"],
)
def test_extending_a_template_instance_is_diagnosed_not_crashed(target):
    """This was a segfault, so it is checked out of process.

    Instance extension (LRM 17.2.6b) is unimplemented.  What must not happen
    is what did happen: the reference path ends in a specialization step, no
    specialization exists when extensions are applied, and the step resolved to
    an unrelated node that was then written to.
    """
    res = link("""
        package p {
            struct S<type T = int> { T v; }
            extend struct %s { int added; }
            struct Top { S<int> s; }
        }
    """ % target)
    assert not res.crashed, res.describe()
    assert res.rc == 1, res.describe()
    assert "cannot extend a template instance" in res.output, res.describe()


def test_the_lrm_template_extension_example_does_not_crash():
    """LRM Example247, whole.

    Its generic extension must work; its instance extension is diagnosed.  The
    point of keeping the example intact is that it is the standard's own
    statement of what this feature means.
    """
    res = link("""
        package p {
            struct domain_s <int LB = 4, int UB = 7> {
                rand int attr;
                constraint attr >= LB && attr <= UB;
            }
            struct container_s {
                domain_s<2, 7> domA;
                domain_s<2, 8> domB;
            }
            extend struct p::domain_s {
                rand int attr_all;
                constraint attr_all > LB && attr_all < UB;
            }
            extend struct p::domain_s<2> {
                rand int attr_2_7;
                constraint attr_2_7 > LB && attr_2_7 < UB;
            }
        }
    """)
    assert not res.crashed, res.describe()
    assert "cannot extend a template instance" in res.output, res.describe()
    # Only the instance extension is refused: the generic half of the example
    # links, so `attr_all` and its constraint are not among the complaints.
    assert "attr_all" not in res.output, res.describe()


def test_the_generic_half_of_the_lrm_example_links_on_its_own():
    """The same model with the instance extension removed is clean."""
    assert_clean([("t.pss", """
        package p {
            struct domain_s <int LB = 4, int UB = 7> {
                rand int attr;
                constraint attr >= LB && attr <= UB;
            }
            struct container_s {
                domain_s<2, 7> domA;
                domain_s<2, 8> domB;
            }
            extend struct p::domain_s {
                rand int attr_all;
                constraint attr_all > LB && attr_all < UB;
            }
        }
    """)])


# ---------------------------------------------------------------------------
# An unqualified extend target
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "decl,ext,use",
    [
        ("struct S { int v; }", "extend struct S { int added; }",
         "struct Top { S s; constraint { s.added > 0; } }"),
        ("struct S<type T> { T v; }", "extend struct S { int added; }",
         "struct Top { S<int> s; constraint { s.added > 0; } }"),
        ("component C { int v; }", "extend component C { int added; }",
         "component Top { C c; exec init_down { c.added = 1; } }"),
    ],
    ids=["struct", "generic-struct", "component"],
)
def test_an_unqualified_extend_target_resolves_in_its_own_package(decl, ext, use):
    """``extend struct S`` beside ``struct S``, with no ``p::`` prefix.

    The resolver used to start at the root, where the only names are package
    names -- hence the old "did you mean 'p'?" suggestion.
    """
    assert_clean([("t.pss", "package p { %s %s %s }" % (decl, ext, use))])


def test_an_unqualified_extend_target_resolves_through_an_import():
    assert_clean([("t.pss", """
        package q { struct S { int v; } }
        package p {
            import q::*;
            extend struct S { int added; }
            struct Top { S s; constraint { s.added > 0; } }
        }
    """)])


def test_an_unqualified_extend_target_that_does_not_exist_is_still_reported():
    """Control.  Resolving the name is not the same as accepting any name."""
    assert_rejects([("t.pss", """
        package p {
            struct S { int v; }
            extend struct nosuch_s { int added; }
        }
    """)], "nosuch_s")


# ---------------------------------------------------------------------------
# An extension written inside a component (LRM 17.3)
# ---------------------------------------------------------------------------

_IN_COMPONENT = """
package p {
    component C {
        %s
        extend %s { %s added; }
        action B { %s x; constraint { x.added > 0; } }
    }
}
"""


@pytest.mark.parametrize(
    "decl,target,mod,inst",
    [
        ("action A { rand int v; }", "action A", "rand int", "A"),
        ("struct S { int v; }", "struct S", "int", "S"),
        ("struct S<type T> { T v; }", "struct S", "int", "S<int>"),
    ],
    ids=["action", "struct", "generic-struct"],
)
def test_an_extension_inside_a_component_takes_effect(decl, target, mod, inst):
    """LRM 17.3 makes a component scope the only place these may be written.

    The walk never entered a component, so all three of these were dropped in
    silence -- no diagnostic, no members.
    """
    assert_clean([("t.pss", _IN_COMPONENT % (decl, target, mod, inst))])


def test_a_member_not_added_inside_a_component_is_still_rejected():
    """Control for the group above."""
    assert_rejects([("t.pss", """
        package p {
            component C {
                struct S { int v; }
                extend struct S { int added; }
                action B { S x; constraint { x.nosuch > 0; } }
            }
        }
    """)], "nosuch")


def test_an_extension_inside_a_component_is_visible_from_outside_it():
    assert_clean([("t.pss", """
        package p {
            component C {
                struct S { int v; }
                extend struct S { int added; }
            }
            struct Top { C::S s; constraint { s.added > 0; } }
        }
    """)])


# ---------------------------------------------------------------------------
# override -- adjacent, and deliberately left alone
# ---------------------------------------------------------------------------

def test_the_lrm_override_example_links():
    """LRM Example57.

    ``override action A {...}`` is built as an extension of ``A``, so it comes
    through the same code as everything above.  Its target lives in a *base*
    component, which cannot be resolved during this pass, so the lookup is
    allowed to fail quietly rather than putting "unknown type 'base_a'" on a
    valid model.
    """
    assert_clean([("t.pss", """
        package p {
            component base_c { action base_a { } }
            component inh1_c : base_c { override action base_a { } }
            component inh2_c : inh1_c { override action base_a { } }
        }
    """)])


def test_an_override_does_not_contribute_to_the_overridden_action():
    """Whatever overriding should do, it must not modify the base action.

    LRM 19.2.2: an overriding action is a new action in the declaring
    component that implicitly inherits from the one it overrides.  Overriding
    is unimplemented -- this pins the half of it that is currently *right*, so
    that implementing it cannot quietly turn an override into an extension of
    the base.
    """
    assert_rejects([("t.pss", """
        package p {
            component base_c {
                action base_a { }
                action user_a { base_a a; constraint { a.x > 0; } }
            }
            component inh1_c : base_c {
                override action base_a { rand int x; }
            }
        }
    """)], "x")


def test_an_override_declares_the_action_in_the_declaring_component():
    """LRM 19.2.2: the overriding action is a new action in the declaring
    component that inherits from the one it overrides.

    So `inh1_c::base_a` has `x` and `base_c::base_a` does not -- which is what
    ``test_an_override_does_not_contribute_to_the_overridden_action`` above
    pins from the other side.
    """
    assert_clean([("t.pss", """
        package p {
            component base_c { action base_a { } }
            component inh1_c : base_c {
                override action base_a { rand int x; }
                action user_a { base_a a; constraint { a.x > 0; } }
            }
        }
    """)])
