"""LRM 19.2.2 -- override actions.

``override action A { ... }`` used to be built as an ``IExtendType`` targeting
``A``, which made it indistinguishable from ``extend action A``.  Since an
override's target lives in a *base* component and an in-component ``extend``
may only target a type in the same component (LRM 17.3), the two need opposite
lookups from the same node, so the lookup was deliberately silenced and the
whole construct was a no-op: nothing resolved, nothing was checked, and the
body was never even walked.

It is now built as an ``Action`` carrying ``is_override`` -- a flag that had
been sitting in ``ast/coretypes.yaml``, generated and exposed through the
Python bindings, with nothing in the parser setting or reading it.

The part that needs care is the super type.  An override's super type spells
its **own name** (``inh1_c::base_a`` inherits ``base_c::base_a``), so the
ordinary lookup finds the override itself and makes the type its own base.
``TaskResolveOverrideActions`` starts from the declaring component's base
chain instead.

See ``docs/pssparser-fix-plan.md`` section 30.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# The construct itself
# ---------------------------------------------------------------------------

def test_the_lrm_example_links():
    """LRM Example57, all three levels.

    ``inh2_c::base_a`` overrides ``inh1_c::base_a``, which overrides
    ``base_c::base_a`` -- so the second level's target is itself an override,
    and resolution has to be happy finding one.
    """
    assert_clean([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c { override action base_a { } }
        component inh2_c : inh1_c { override action base_a { } }
    """)])


def test_the_target_may_be_further_up_than_the_immediate_base():
    """The base chain is walked, not just the immediate parent.

    This is why resolution is its own pass after ``TaskResolveSuperTypes``
    rather than part of it: reaching ``base_c`` from ``leaf_c`` requires
    ``mid_c``'s super type to be resolved already.
    """
    assert_clean([("t.pss", """
        component base_c { action base_a { } }
        component mid_c : base_c { }
        component leaf_c : mid_c { override action base_a { } }
    """)])


# ---------------------------------------------------------------------------
# What overriding actually means (LRM 19.2.2, opening paragraph)
# ---------------------------------------------------------------------------

def test_the_override_declares_the_action_in_the_declaring_component():
    """The overriding action is a *new* action in the declaring component."""
    assert_clean([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c {
            override action base_a { rand int x; }
            action user_a { base_a a; constraint { a.x > 0; } }
        }
    """)])


def test_the_override_inherits_from_the_action_it_overrides():
    """"An overriding action implicitly inherits from the action that it
    overrides" -- so a member of the base action is reachable through it."""
    assert_clean([("t.pss", """
        component base_c { action base_a { rand int b; } }
        component inh1_c : base_c {
            override action base_a { rand int x; }
            action user_a { base_a a; constraint { a.b > 0; } }
        }
    """)])


def test_the_override_does_not_modify_the_overridden_action():
    """The control that matters most: an extension would have added `x` to
    ``base_c::base_a`` for every user of it.  That is what the old
    implementation did, and it is the opposite of overriding."""
    assert_rejects([("t.pss", """
        component base_c {
            action base_a { }
            action user_a { base_a a; constraint { a.x > 0; } }
        }
        component inh1_c : base_c { override action base_a { rand int x; } }
    """)], "x")


def test_the_override_is_not_visible_in_a_sibling_component():
    """A sibling subtype of the same base gets the *base* action, not this
    override -- overriding is scoped to the declaring component's subtree."""
    assert_rejects([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c { override action base_a { rand int x; } }
        component sib_c : base_c {
            action user_a { base_a a; constraint { a.x > 0; } }
        }
    """)], "x")


def test_the_override_body_is_resolved():
    """The body used to be inside a swallowed extension, so nothing in it was
    ever checked.  A bad reference in there must now be reported like any
    other."""
    assert_rejects([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c {
            override action base_a { constraint { nosuch == 1; } }
        }
    """)], "nosuch")


# ---------------------------------------------------------------------------
# LRM 19.2.2 a), b), c)
# ---------------------------------------------------------------------------

def test_a_target_declared_in_no_base_component_is_reported():
    """19.2.2a: override is only permitted when a base component declares the
    name."""
    assert_rejects([("t.pss", """
        component base_c { action base_a { } }
        component derived_c : base_c { override action nosuch_a { } }
    """)], "no action of that name is declared in a base component")


def test_an_override_in_a_component_with_no_base_is_reported():
    """19.2.2a with no base chain at all to search."""
    assert_rejects([("t.pss", """
        component C { override action A { } }
    """)], "no action of that name is declared in a base component")


def test_a_subtype_redeclaring_an_override_without_the_keyword_is_reported():
    """19.2.2b: once a component declares an action override, a subtype
    declaring the same name shall also declare it override."""
    assert_rejects([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c { override action base_a { } }
        component inh2_c : inh1_c { action base_a { } }
    """)], "must be declared 'override'")


def test_a_plain_action_over_a_plain_base_action_is_not_reported():
    """Control for 19.2.2b, and the reason the check keys on the *base* being
    an override rather than merely on the name being reused.  The LRM imposes
    the keyword only once an override exists; a base component declaring a
    plain action of the same name is a different situation and is left alone
    here."""
    assert_clean([("t.pss", """
        component base_c { action base_a { } }
        component inh1_c : base_c { action base_a { } }
    """)])


def test_an_unrelated_component_reusing_the_name_is_not_reported():
    """Control: the search is over the base chain, not over every component
    that happens to declare the name."""
    assert_clean([("t.pss", """
        component base_c { action base_a { } }
        component other_c { action base_a { } }
    """)])


def test_overriding_a_template_action_is_reported():
    """19.2.2c: template actions shall not be overridden."""
    assert_rejects([("t.pss", """
        component base_c { action base_a<int N> { } }
        component inh1_c : base_c { override action base_a { } }
    """)], "cannot override template action")
