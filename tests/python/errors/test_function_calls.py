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


# ---------------------------------------------------------------------------
# Calling something that is not a function
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src,name", [
    ("component C { action A { rand int x; exec body { x(1); } } }", "x"),
    ("component C { action A { exec body { int v; v(1); } } }", "v"),
    ("component C { action A { rand string s; exec body { s(1); } } }", "s"),
])
def test_calling_a_field_or_variable_is_rejected(src, name):
    assert_rejects([("t.pss", src)], "'%s' is not a function" % name)


@pytest.mark.parametrize("body", [
    # Every one of these resolves the call to something that is *not* an
    # ISymbolFunctionScope, which is why the check tests positively for a
    # field or a local variable rather than negatively for "not a function
    # scope".  A negative test would reject all of them.
    'string s; int n; n = s.size();',
    'string s; string t; t = s.substr(1,2);',
    'list<int> l; l.push_back(1);',
    'map<int,int> m; m.insert(1,2);',
    'array<int,4> a; int n; n = a.size();',
    'set<int> s; s.insert(1);',
    'bit[32] v; v = urandom();',
])
def test_a_builtin_method_call_is_not_reported_as_a_non_function(body):
    assert_clean([("t.pss", """
        component C { action A { exec body { %s } } }
    """ % body)])


def test_a_component_method_call_is_not_reported_as_a_non_function():
    assert_clean([("t.pss", """
        component C {
            function void f(int a) { }
            action A { exec body { comp.f(1); } }
        }
    """)])


# ---------------------------------------------------------------------------
# Defaults must be trailing
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("proto,expected", [
    ("function void f(int a = 1, int b);",
     "parameter 'b' has no default, but follows 'a' which does"),
    ("function void f(int a, int b = 1, int c);",
     "parameter 'c' has no default, but follows 'b' which does"),
])
def test_a_non_defaulted_parameter_after_a_defaulted_one_is_rejected(proto, expected):
    """The default would be unreachable -- no call omits it while supplying
    what follows -- and the arity check would silently treat it as required."""
    assert_rejects([("t.pss", proto)], expected)


def test_it_is_reported_once_per_prototype():
    res = assert_rejects([("t.pss", "function void f(int a = 1, int b, int c);")])
    assert res.output.count("has no default, but follows") == 1, res.describe()


@pytest.mark.parametrize("proto", [
    "function void f(int a, int b = 1, int c = 2);",
    "function void f(int a = 1, int b = 2);",
    "function void f(int a, int b);",
    "function void f();",
])
def test_trailing_defaults_still_link(proto):
    assert_clean([("t.pss", proto)])


def test_a_varargs_parameter_after_a_default_still_links():
    """A varargs parameter is always last and carries no default, so it is not
    the mistake this rule is about."""
    assert_clean([("t.pss",
        "package p { function void m(string f, int n = 1, type... args); }")])


def test_the_rule_reaches_a_definition_and_an_import_too():
    """reportDuplicateParams() is called from all three function visitors, and
    this rides along with it."""
    assert_rejects([("t.pss", "function void f(int a = 1, int b) { }")],
                   "has no default, but follows")
    assert_rejects([("t.pss", "import solve function void f(int a = 1, int b);")],
                   "has no default, but follows")


@pytest.mark.parametrize("src,name", [
    ("struct S { } component C { action A { exec body { S(1); } } }", "S"),
    ("enum E { A } component C { action A { exec body { E(1); } } }", "E"),
    ("component C { sub_c s; action A { exec body { s(1); } } } component sub_c { }", "s"),
])
def test_calling_a_type_or_a_component_instance_is_rejected(src, name):
    """The inputs that decided the shape of this check.

    It began as a positive test on ``IField``/``IProceduralStmtData-
    Declaration``, on the reasoning that a wider test would also catch
    ``s.size()`` and the other built-in methods.  That was wrong -- those are
    matched against the method list earlier in the loop and never reach the
    check at all -- and the neutralization row that widened the test failed
    nothing, which is what exposed it.  These are the only inputs the two
    versions disagree about, and the wider one is right about them.
    """
    assert_rejects([("t.pss", src)], "'%s' is not a function" % name)


def test_an_unresolvable_callee_is_not_reported_as_a_non_function():
    """The null guard, which is the caution the check does need: a single file
    of a multi-file model resolves the callee to nothing, and the cause is
    diagnosed where the name is, not at the call."""
    res = assert_rejects([("t.pss", """
        component C { action A { exec body { other_pkg::f(1); } } }
    """)], "other_pkg")
    assert "is not a function" not in res.output, res.describe()


# ---------------------------------------------------------------------------
# Argument types -- categories only
# ---------------------------------------------------------------------------
#
# There is no expression-type inference in this parser, and building one means
# deciding PSS's assignment compatibility: numeric widths, signedness,
# enum-to-integer, struct subtyping.  A wrong rule there rejects valid code at
# every call site in every model.
#
# So this check reasons in four coarse categories -- numeric, string,
# composite, and Unknown -- and reports only when the argument certainly
# cannot be what the parameter declares.  `Unknown` is the answer for anything
# not certainly in one of the other three, and is never reported against.  The
# controls below are the more important half of this section: they pin the
# cases the check must stay silent about.

@pytest.mark.parametrize("proto,call,expected", [
    ("function void f(int a);",
     'f("s")', "argument 1 of 'f' is a string, but parameter 'a' is numeric"),
    ("function void f(string s);",
     "f(1)",   "argument 1 of 'f' is numeric, but parameter 's' is a string"),
])
def test_a_literal_of_the_wrong_category_is_rejected(proto, call, expected):
    assert_rejects([("t.pss", """
        %s
        component C { action A { exec body { %s; } } }
    """ % (proto, call))], expected)


def test_a_composite_where_a_scalar_is_declared_is_rejected():
    assert_rejects([("t.pss", """
        struct S { }
        function void f(int a);
        component C { action A { S s; exec body { f(s); } } }
    """)], "argument 1 of 'f' is a composite type, but parameter 'a' is numeric")


def test_a_scalar_where_a_composite_is_declared_is_rejected():
    assert_rejects([("t.pss", """
        struct S { }
        function void f(S s);
        component C { action A { exec body { f(1); } } }
    """)], "argument 1 of 'f' is numeric, but parameter 's' is a composite type")


def test_the_argument_position_is_named():
    assert_rejects([("t.pss", """
        function void f(int a, string b, int c);
        component C { action A { exec body { f(1, 2, 3); } } }
    """)], "argument 2 of 'f'")


# --- controls: valid PSS that must keep linking -----------------------------

@pytest.mark.parametrize("src", [
    # Numeric is one category on purpose: int, bit, bool and enum are
    # mutually convertible in PSS, and distinguishing them would mean taking
    # a position on width and signedness.
    'enum E { A, B } function void f(int a); component C { action A { exec body { f(E::A); } } }',
    'enum E { A } function void f(int a); component C { action A { rand E e; exec body { f(e); } } }',
    'enum E { A } function void f(E e); component C { action A { rand int x; exec body { f(x); } } }',
    'function void f(int a); component C { action A { exec body { f(true); } } }',
    'function void f(int a); component C { action A { rand bool b; exec body { f(b); } } }',
    'function void f(bool b); component C { action A { rand int x; exec body { f(x); } } }',
    'function void f(int a); component C { action A { rand bit[8] v; exec body { f(v); } } }',
    'typedef int my_int_t; function void f(my_int_t a); component C { action A { rand int x; exec body { f(x); } } }',
    'typedef bit[8] byte_t; function void f(byte_t a); component C { action A { exec body { f(3); } } }',
])
def test_numeric_kinds_are_interchangeable(src):
    assert_clean([("t.pss", src)])


@pytest.mark.parametrize("src", [
    # Everything here is Unknown by design -- the classifier declines to have
    # an opinion rather than guess.
    'function void f(int a); component C { action A { rand int x; exec body { f(x+1); } } }',
    'function void f(bool b); component C { action A { rand int x; exec body { f(x>0); } } }',
    'struct S { int a; } function void f(int a); component C { action A { S s; exec body { f(s.a); } } }',
    'function int g(); function void f(int a); component C { action A { exec body { f(g()); } } }',
    'function void f(chandle h); component C { action A { exec body { chandle h; f(h); } } }',
    'function void f(string s); component C { action A { exec body { string a; string b; f(a+b); } } }',
])
def test_expressions_the_classifier_does_not_type_are_left_alone(src):
    assert_clean([("t.pss", src)])


@pytest.mark.parametrize("src", [
    # Struct subtyping, in both directions.  Deciding which way round is legal
    # is exactly the judgement this check refuses to make; both are composite,
    # so both pass.
    'struct B { } struct D : B { } function void f(B b); component C { action A { D d; exec body { f(d); } } }',
    'struct B { } struct D : B { } function void f(D d); component C { action A { B b; exec body { f(b); } } }',
])
def test_composite_types_are_not_told_apart(src):
    assert_clean([("t.pss", src)])


def test_an_unresolved_argument_type_is_not_reported_as_a_mismatch():
    """The unknown type is reported where it is declared.  Adding a second
    complaint at the call site would be the cascade section 29.4 removed."""
    res = assert_rejects([("t.pss", """
        function void f(int a);
        component C { action A { nosuch_t v; exec body { f(v); } } }
    """)], "unknown type 'nosuch_t'")
    assert "argument 1" not in res.output, res.describe()


@pytest.mark.parametrize("src", [
    # Collection methods DO resolve to function scopes in the standard
    # library, so they reach this check -- unlike the callable check in
    # section 34.2, where they break out earlier.  Their parameters are
    # template-typed, which classifies as Unknown, so nothing is reported.
    'component C { action A { list<int> l; exec post_solve { l.push_back(42); } } }',
    'component C { action A { list<string> l; exec post_solve { l.push_back("x"); } } }',
    'struct S{} component C { action A { list<S> l; S s; exec post_solve { l.push_back(s); } } }',
    'component C { action A { map<string,int> m; exec post_solve { m.insert("k",1); } } }',
    'component C { action A { set<string> s; exec post_solve { s.insert("x"); } } }',
])
def test_collection_method_calls_are_left_alone(src):
    assert_clean([("t.pss", src)])


def test_a_collection_element_mismatch_is_a_known_miss():
    """``list<int>`` given a string is a real error and is *not* caught: the
    parameter's type is the template parameter, which classifies as Unknown.
    Catching it needs the specialized element type.  Recorded so that
    implementing it is a visible change."""
    assert_clean([("t.pss",
        'component C { action A { list<int> l; exec post_solve { l.push_back("x"); } } }')])


def test_the_check_reaches_a_qualified_call():
    assert_rejects([("t.pss", """
        package p { function void f(int a); }
        component C { action A { exec body { p::f("s"); } } }
    """)], "argument 1 of 'f' is a string")


def test_the_check_reaches_a_component_method():
    assert_rejects([("t.pss", """
        component C {
            function void f(string s) { }
            action A { exec body { comp.f(1); } }
        }
    """)], "argument 1 of 'f' is numeric")


# ---------------------------------------------------------------------------
# The category boundaries themselves
# ---------------------------------------------------------------------------
#
# Every test below was added because a neutralization row failed nothing.
# Three rows -- dropping enum from numeric, dropping bool from numeric, and
# dropping the built-in-collection exclusion -- each reported zero failures,
# and none of them meant "this line does not matter".  Two were gaps in these
# tests.  The third, the enum one, was a live defect: an enum resolves to an
# ISymbolEnumScope, which is not an ISymbolTypeScope, so the branch could
# never fire and every enum control in this file was passing vacuously.

@pytest.mark.parametrize("proto,call,expected", [
    ("function void f(string s);", "f(true)", "is numeric, but parameter 's' is a string"),
    ("function void f(S s); struct S { }", "f(true)", "is numeric, but parameter 's' is a composite type"),
])
def test_a_bool_literal_is_numeric(proto, call, expected):
    """The control for this was ``f(true)`` against an *int* parameter, which
    passes whether ``true`` is numeric or Unknown.  It demonstrated nothing."""
    assert_rejects([("t.pss", """
        %s
        component C { action A { exec body { %s; } } }
    """ % (proto, call))], expected)


@pytest.mark.parametrize("src,expected", [
    ('enum E { A } function void f(string s); component C { action A { rand E e; exec body { f(e); } } }',
     "is numeric, but parameter 's' is a string"),
    ('enum E { A } struct S { } function void f(S s); component C { action A { rand E e; exec body { f(e); } } }',
     "is numeric, but parameter 's' is a composite type"),
    ('enum E { A } function void f(E e); component C { action A { exec body { f("x"); } } }',
     "is a string, but parameter 'e' is numeric"),
])
def test_an_enum_is_numeric(src, expected):
    """These are the tests that were missing while the enum branch was dead.
    The interchangeability controls above cannot show it: they pass when an
    enum is numeric *and* when it is Unknown."""
    assert_rejects([("t.pss", src)], expected)


@pytest.mark.parametrize("src", [
    'function void f(int a); component C { action A { list<int> l; exec body { f(l); } } }',
    'function void f(string s); component C { action A { list<int> l; exec body { f(l); } } }',
    'function void f(int a); component C { action A { array<int,4> a2; exec body { f(a2); } } }',
    'function void f(int a); component C { action A { map<int,int> m; exec body { f(m); } } }',
])
def test_a_built_in_collection_is_left_unknown(src):
    """Passing a ``list<int>`` where an ``int`` is declared *is* an error, but
    "is a composite type" is the wrong thing to say about it -- the element
    type is what matters -- so the classifier declines.  Recorded as a known
    miss, like the ``push_back`` case above.

    Note what these pin and what they do not.  ``catOfDataType`` carries an
    explicit guard excluding built-in collections, and that guard is currently
    *unreachable*: a parameterized type reference does not resolve to a target
    there, so collections come out Unknown by falling off the end instead.
    These tests hold the behaviour from the outside, so they pass either way --
    which is exactly why neutralizing the guard failed nothing.  See plan
    section 35.3."""
    assert_clean([("t.pss", src)])
