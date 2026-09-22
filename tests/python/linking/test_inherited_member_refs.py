"""Unqualified references to inherited members (CL-N4).

An unqualified name inside a type's body is resolved by
``TaskResolveRootRef``, which walks the symbol-table iterator *lexically*
outward and, at each type scope, also walks the inheritance chain.  The
iterator is popped as the lexical walk proceeds, so
``getScopeSymbolPath()`` names the scope being searched -- but it knows
nothing about the inheritance walk, and the recorded path was built from it
regardless.  The base type's child index was therefore appended to a path
naming the *derived* type:

* index 0 landed on whatever child sat at index 0 of the derived type and was
  reported as ``'f0' is not a function``;
* every higher index fell off the end of the derived type's child list and
  resolved to nothing, so the reference was silently accepted and **never
  checked** -- an inherited call with the wrong argument count produced no
  diagnostic at all.

``SymbolRefPathElemKind::ElemKind_Super`` existed for exactly this and was a
``DEBUG_ERROR("TODO: handle super ref")`` that left the running scope
untouched.  The fix records one ``Super`` element per step up the chain and
implements the step.

This went unnoticed because ``AstBuilderInt`` injected a parameterless
``set_executor`` prototype into every base-less component, which always
occupied index 0 and absorbed the only *visible* symptom.  Removing that
injection (CL-S3, required because it shadowed the normative
``executor_pkg::set_executor``) is what exposed this.  The first test below is
the one that failed then.

See ``docs/design/core-library-conformance-plan.md`` §3.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


def _src(body):
    return [("t.pss", "package u {\n%s\n}\n" % body)]


# ---------------------------------------------------------------------------
# The index-0 case: a false error
# ---------------------------------------------------------------------------

def test_the_first_declared_member_of_a_base_is_callable():
    """The regression that removing the `set_executor` injection uncovered."""
    assert_clean(_src("""
        component base_c {
            function void f0();
        }
        component d : base_c {
            exec init_down { f0(); }
        }
    """))


@pytest.mark.parametrize("call", ["f0();", "f1();", "f2();", "f3();"])
def test_every_inherited_function_is_callable_whatever_its_position(call):
    """Position in the base's child list must not matter.

    It did: only index 0 reported, and only because the derived type happened
    to have a child there.
    """
    assert_clean(_src("""
        component base_c {
            function void f0();
            function void f1();
            function void f2();
            function void f3();
        }
        component d : base_c {
            exec init_down { %s }
        }
    """ % call))


# ---------------------------------------------------------------------------
# The silent case: resolved to nothing, so never checked
# ---------------------------------------------------------------------------

def test_an_inherited_call_is_arity_checked():
    """The half of this defect that produced no diagnostic at all.

    A wrong-arity call to an inherited function used to be accepted in
    silence, because the reference resolved past the end of the derived type's
    child list and ``checkCallArity`` was handed nothing to check.
    """
    assert_rejects(_src("""
        component base_c {
            function void f(int a);
        }
        component d : base_c {
            exec init_down { f(1, 2, 3); }
        }
    """), "too many arguments to 'f'")


def test_an_inherited_call_is_arity_checked_two_levels_up():
    """One `Super` element per step: the chain may be longer than one."""
    assert_rejects(_src("""
        component base_c { function void f(int a); }
        component mid_c : base_c { }
        component d : mid_c {
            exec init_down { f(1, 2, 3); }
        }
    """), "too many arguments to 'f'")


def test_a_name_in_no_base_is_still_reported():
    """The control.  Widening the search must not swallow real errors."""
    assert_rejects(_src("""
        component base_c { function void f(); }
        component d : base_c {
            exec init_down { nosuchname(); }
        }
    """), "nosuchname")


# ---------------------------------------------------------------------------
# Fields, which resolved through the same path
# ---------------------------------------------------------------------------

def test_an_inherited_field_is_reachable_whatever_its_position():
    assert_clean(_src("""
        component base_c {
            int a;
            int b;
            int c;
        }
        component d : base_c {
            exec init_down {
                int x = a;
                int y = b;
                int z = c;
            }
        }
    """))


def test_an_inherited_field_two_levels_up_is_reachable():
    assert_clean(_src("""
        component base_c { int a; }
        component mid_c : base_c { }
        component d : mid_c {
            exec init_down { int x = a; }
        }
    """))


# ---------------------------------------------------------------------------
# The core library, which is what found this
# ---------------------------------------------------------------------------

def test_an_inherited_core_library_function_is_callable():
    """`get_context` is declared on `executor_base_c` (21.7.1.1.1)."""
    assert_clean([("t.pss", """
        package u {
            import executor_pkg::*;
            component c : executor_base_c {
                function chandle f() { return get_context(); }
            }
        }
    """)])
