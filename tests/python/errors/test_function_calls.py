"""Function calls -- argument count, and the leaf of a qualified path.

Nothing about a call was checked beyond the callee's name.  ``f(1)`` against
``function void f(int a, int b)`` linked clean, and so did ``f(1,2,3)``.

Two things were in the way, and only the first is about functions:

* no arity check existed anywhere;
* the leaf of a *static-rooted* path -- the ``f`` of ``p::f(1)`` -- was never
  resolved at all.  ``visitExprRefPathStaticRooted`` resolved the root, visited
  the leaf to pick up the argument *expressions* (which is why ``p::f(nosuch)``
  was reported), and then hit a ``DEBUG("TODO")``.  The element names went
  unlooked-up, so ``p::nosuch_f(1)`` linked clean and no qualified call could
  be checked for anything.

Everything the arity check needs was already modelled: ``getDflt()`` on a
parameter and ``getIs_varargs()`` for the ``type... args`` form.  What was
missing was that the standard library declared its two variadic functions
with the varargs commented out -- ``function void message(message_verbosity_e,
string /*, type... args*/)`` -- which the corpus caught the moment the check
went in.

See ``docs/pssparser-fix-plan.md`` section 32.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# Argument count
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("proto,call,expected", [
    ("function void f(int a, int b);", "f(1)",     "too few arguments to 'f': expected 2, got 1"),
    ("function void f(int a);",        "f(1,2)",   "too many arguments to 'f': expected 1, got 2"),
    ("function void f();",             "f(1)",     "too many arguments to 'f': expected 0, got 1"),
    ("function void f(int a);",        "f()",      "too few arguments to 'f': expected 1, got 0"),
])
def test_a_wrong_argument_count_is_rejected(proto, call, expected):
    assert_rejects([("t.pss", """
        %s
        component C { action A { exec body { %s; } } }
    """ % (proto, call))], expected)


@pytest.mark.parametrize("call", ["f(1,2)", "f()"])
def test_an_exact_match_still_links(call):
    proto = "function void f(int a, int b);" if "," in call else "function void f();"
    assert_clean([("t.pss", """
        %s
        component C { action A { exec body { %s; } } }
    """ % (proto, call))])


@pytest.mark.parametrize("where,body", [
    ("an exec body",   "action A { exec body { f(); } }"),
    ("a post_solve",   "action A { exec post_solve { f(); } }"),
    ("a constraint",   "action A { rand int x; constraint { x == f(); } }"),
])
def test_it_is_checked_wherever_a_call_can_appear(where, body):
    assert_rejects([("t.pss", """
        function int f(int a);
        component C { %s }
    """ % body)], "too few arguments to 'f'")


def test_a_component_method_call_is_checked():
    assert_rejects([("t.pss", """
        component C {
            function void f(int a, int b) { }
            action A { exec body { comp.f(1); } }
        }
    """)], "too few arguments to 'f': expected 2, got 1")


def test_a_package_qualified_call_is_checked():
    """The form that needed the leaf of a static-rooted path resolved first."""
    assert_rejects([("t.pss", """
        package p { function void f(int a, int b); }
        component C { action A { exec body { p::f(1); } } }
    """)], "too few arguments to 'f': expected 2, got 1")


def test_a_call_through_a_nested_package_is_checked():
    assert_rejects([("t.pss", """
        package p { package q { function void f(int a); } }
        component C { action A { exec body { p::q::f(); } } }
    """)], "too few arguments to 'f'")


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

def test_a_defaulted_parameter_may_be_omitted():
    assert_clean([("t.pss", """
        function void f(int a, int b = 2);
        component C { action A { exec body { f(1); } } }
    """)])


def test_a_defaulted_parameter_may_still_be_supplied():
    assert_clean([("t.pss", """
        function void f(int a, int b = 2);
        component C { action A { exec body { f(1,2); } } }
    """)])


def test_every_parameter_defaulted_means_a_bare_call_links():
    assert_clean([("t.pss", """
        function void f(int a = 1);
        component C { action A { exec body { f(); } } }
    """)])


def test_below_the_non_defaulted_count_is_still_rejected():
    """And the message says "at least", since the two bounds differ."""
    assert_rejects([("t.pss", """
        function void f(int a, int b = 2);
        component C { action A { exec body { f(); } } }
    """)], "too few arguments to 'f': expected at least 1, got 0")


def test_past_the_total_count_is_still_rejected():
    assert_rejects([("t.pss", """
        function void f(int a, int b = 2);
        component C { action A { exec body { f(1,2,3); } } }
    """)], "too many arguments to 'f': expected at most 2, got 3")


# ---------------------------------------------------------------------------
# Varargs
# ---------------------------------------------------------------------------

def test_a_varargs_function_accepts_no_extra_arguments():
    assert_clean([("t.pss", """
        package p { function void m(string f, type... args); }
        component C { action A { exec body { p::m("x"); } } }
    """)])


def test_a_varargs_function_accepts_many_extra_arguments():
    assert_clean([("t.pss", """
        package p { function void m(string f, type... args); }
        component C { action A { exec body { p::m("x",1,2,3,4,5); } } }
    """)])


def test_a_varargs_function_still_requires_its_fixed_parameters():
    assert_rejects([("t.pss", """
        package p { function void m(string f, type... args); }
        component C { action A { exec body { p::m(); } } }
    """)], "too few arguments to 'm': expected at least 1, got 0")


@pytest.mark.parametrize("call", [
    'message(LOW, "x")',
    'message(LOW, "x=%d", 1)',
    'message(LOW, "x=%d y=%d", 1, 2)',
    'print("x")',
    'print("x=%d", 1)',
])
def test_the_standard_library_variadics_accept_extra_arguments(call):
    """``std_pkg`` declared ``message`` and ``print`` with their ``type...
    args`` *commented out*.  Harmless while nothing counted arguments; the
    moment something did, it rejected two of the language-reference examples.
    The grammar and the builder both support the form -- only the declaration
    did not use it."""
    assert_clean([("t.pss", """
        component C { action A { exec body { %s; } } }
    """ % call)])


def test_a_non_variadic_standard_library_function_is_still_checked():
    """Control for the above: relaxing two declarations must not relax the
    rest of the standard library."""
    assert_rejects([("t.pss", """
        component C { action A { exec body { bit[32] v; v = urandom_range(1); } } }
    """)], "too few arguments to 'urandom_range': expected 2, got 1")


# ---------------------------------------------------------------------------
# The leaf of a static-rooted path
# ---------------------------------------------------------------------------

def test_an_unknown_function_in_a_package_is_reported():
    assert_rejects([("t.pss", """
        package p { function void f(int a); }
        component C { action A { exec body { p::nosuch_f(1); } } }
    """)], "'p' has no member named 'nosuch_f'")


def test_an_unknown_member_of_a_nested_package_is_reported():
    assert_rejects([("t.pss", """
        package p { package q { function void f(); } }
        component C { action A { exec body { p::q::nosuch(); } } }
    """)], "has no member named 'nosuch'")


def test_an_unknown_enum_item_in_a_qualified_reference_is_reported():
    """Falls out of resolving the leaf: an enum item reference is the same
    shape as a qualified call without the parentheses."""
    assert_rejects([("t.pss", """
        package p { enum E { A, B } }
        component C {
            action act { rand p::E e; constraint { e == p::E::NOSUCH; } }
        }
    """)], "has no member named 'NOSUCH'")


def test_a_known_enum_item_still_links():
    assert_clean([("t.pss", """
        package p { enum E { A, B } }
        component C {
            action act { rand p::E e; constraint { e == p::E::A; } }
        }
    """)])


def test_a_package_constant_still_links():
    assert_clean([("t.pss", """
        package p { const int K = 4; }
        component C { action A { rand int x; constraint { x < p::K; } } }
    """)])


def test_a_correct_qualified_call_still_links():
    assert_clean([("t.pss", """
        package p { function void f(int a); }
        component C { action A { exec body { p::f(1); } } }
    """)])


def test_a_leaf_on_an_unresolvable_root_reports_only_the_root():
    """One cause, one diagnostic -- and the shape a single file of a
    multi-file model takes when it is opened on its own.  The leaf has no
    scope to be searched in, and saying so would blame the wrong thing."""
    res = assert_rejects([("t.pss", """
        component C { action A { exec body { other_pkg::f(1); } } }
    """)], "other_pkg")
    assert "has no member named" not in res.output, res.describe()


# ---------------------------------------------------------------------------
# What the check must not touch
# ---------------------------------------------------------------------------

def test_a_string_method_call_still_links():
    """The parser does not model the built-in methods' parameters, so the
    arity check has to stay off them entirely rather than treat an unknown
    signature as zero parameters."""
    assert_clean([("t.pss", """
        component C { action A { exec body { string s; int n; n = s.size(); } } }
    """)])


def test_a_collection_method_call_still_links():
    assert_clean([("t.pss", """
        component C {
            action A { exec body { array<int,4> a; int n; n = a.size(); } }
        }
    """)])


def test_a_collection_method_taking_an_argument_still_links():
    assert_clean([("t.pss", """
        component C {
            action A { exec body { list<int> l; l.push_back(1); } }
        }
    """)])
