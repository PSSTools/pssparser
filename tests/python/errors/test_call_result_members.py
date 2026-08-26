"""Member access on the result of a call: ``f().x``.

Two independent defects met here, and either one alone would have hidden the
other.

**The static root was dropped.**  ``mkExprRefPathStatic`` built the base of an
``ExprRefPathStatic`` from ``ctx->type_identifier_elem()`` alone.  For ``p::f.x``
the grammar puts ``p`` in ``static_ref_path_prefix`` and leaves
``type_identifier_elem()`` *empty*, so the static root came out with no elements
at all.  ``visitExprRefPathStatic`` then looped over nothing, left the target
null, and ``visitExprRefPathStaticRooted`` took its "failed root resolution"
early return -- silently.  Every qualified path with a member suffix linked
clean no matter what it named: ``p::f().zzz.qqq`` was accepted, and so was
``p::f(1,2).x`` for a one-parameter ``f``.  The sibling builder in
``mkExprRefPath``'s "case2" branch has always pushed the prefix explicitly,
which is exactly why ``p::f(1,2)`` *was* checked while ``p::f(1,2).x`` was not.

**A call's members were the function's.**  ``TaskGetElemSymbolScope`` had no
case for ``SymbolFunctionScope``, so the inherited ``visitSymbolScope`` matched
-- a function scope is a symbol scope -- and returned the function's own scope.
Member lookup after a call therefore searched the function's parameters and
locals.  This was not a near miss but an inversion: for
``struct S { int x; } function S f(int p);`` the parser accepted ``f(1).p`` and
rejected ``f(1).x``.

The ``declaredTypeOf`` change is the same idea one level down: a call is a
value, and the type of that value is the return type.  That is what lets the
built-in method machinery see ``f().size()`` on a string-returning ``f``.

Recorded rather than fixed, with controls below:

* ``resolveStaticRootedLeaf`` has no built-in/collection method handling at
  all, so ``p::f().nosuchmeth()`` is accepted where ``f().nosuchmeth()`` is
  reported.  That gap is not specific to call results -- it applies to every
  qualified path -- so it is pinned here rather than fixed alongside.
* ``f().x;`` in statement position is a syntax error.  The grammar's
  void-call statement rule requires the statement to *end* in a call, which
  ``f().x`` does not.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# The member of a call result is a member of the return type
# ---------------------------------------------------------------------------

STRUCT = "struct S { int x; }\n"


@pytest.mark.parametrize("src", [
    STRUCT + "function S f(); function void g() { int v; v = f().x; }",
    STRUCT + "function S f(int p); function void g() { int v; v = f(1).x; }",
    STRUCT + "component C { function S f(); function void g() { int v; v = f().x; } }",
    "package p { struct S { int x; } function S f(); }\n"
        "function void g() { int v; v = p::f().x; }",
    "package a { package b { struct S { int x; } function S f(); } }\n"
        "function void g() { int v; v = a::b::f().x; }",
    "package p { struct S { int x; } function S f(); }\n"
        "function void g() { int v; v = ::p::f().x; }",
])
def test_a_member_of_the_return_type_resolves(src):
    assert_clean([("t.pss", src)])


def test_an_inherited_member_of_the_return_type_resolves():
    assert_clean([("t.pss", """
        package p {
            struct B { int b; }
            struct S : B { int x; }
            function S f();
        }
        function void g() { int v; v = p::f().b; }
    """)])


def test_a_chain_of_members_on_a_call_result_resolves():
    assert_clean([("t.pss", """
        package p {
            struct I { int z; }
            struct S { I i; }
            function S f();
        }
        function void g() { int v; v = p::f().i.z; }
    """)])


def test_a_call_result_member_reached_through_a_component_instance():
    assert_clean([("t.pss", """
        struct S { int x; }
        component C { function S f(); }
        component pss_top { C c; function void g() { int v; v = c.f().x; } }
    """)])


# --- the inversion ---

def test_a_parameter_name_is_not_a_member_of_the_call_result():
    """The sharp end of the ``SymbolFunctionScope`` defect.  ``p`` is a
    parameter of ``f``, not a member of what ``f`` returns, and it used to
    resolve while ``x`` -- which *is* a member of the return type -- did not."""
    assert_rejects([("t.pss",
        STRUCT + "function S f(int p); function void g() { int v; v = f(1).p; }")],
        "Failed to find elem p")


@pytest.mark.parametrize("src,expected", [
    (STRUCT + "function S f(); function void g() { int v; v = f().zzz; }",
     "Failed to find elem zzz"),
    ("package p { struct S { int x; } function S f(); }\n"
        "function void g() { int v; v = p::f().zzz; }",
     "'S' has no member named 'zzz'"),
    ("package p { struct I { int z; } struct S { I i; } function S f(); }\n"
        "function void g() { int v; v = p::f().i.zzz; }",
     "'I' has no member named 'zzz'"),
])
def test_an_unknown_member_of_a_call_result_is_reported(src, expected):
    assert_rejects([("t.pss", src)], expected)


# ---------------------------------------------------------------------------
# The dropped static root
# ---------------------------------------------------------------------------

def test_a_qualified_call_with_a_member_suffix_is_checked_for_arity():
    """The clearest witness that the qualified path was not being walked at
    all.  ``p::f(1,2)`` on its own was already reported; adding ``.x`` made the
    whole path vanish from checking, because the static root came out empty and
    resolution returned early."""
    assert_rejects([("t.pss", """
        package p { struct S { int x; } function S f(int q); }
        function void g() { int v; v = p::f(1,2).x; }
    """)], "too many arguments to 'f'")


def test_a_qualified_non_call_path_with_a_member_suffix_is_checked():
    """Not a call at all -- the dropped root broke every ``pkg::name.member``
    path, which is why this fix is not confined to call results.

    Stated as a *rejection*, deliberately.  The first version of this test
    asserted that ``p::s.x`` links clean, and the neutralization run showed it
    passing with the fix reverted: dropping the root makes the path stop being
    walked, and "not walked" is indistinguishable from "walked successfully"
    to a clean-link assertion.  Only a rejection proves the walk happened.
    """
    assert_rejects([("t.pss", """
        package p { struct S { int x; } static const S s; }
        function void g() { int v; v = p::s.zzz; }
    """)], "'S' has no member named 'zzz'")


def test_a_qualified_non_call_path_with_a_good_member_still_links():
    """The control for the above.  It cannot carry the claim on its own -- see
    that test's docstring -- but it is what says the rejection is about the
    name and not about the shape."""
    assert_clean([("t.pss", """
        package p { struct S { int x; } static const S s; }
        function void g() { int v; v = p::s.x; }
    """)])


def test_a_nonsense_tail_on_a_qualified_call_is_reported():
    """``p::f().zzz.qqq`` linked clean before: two elements of pure invention
    after a root that never resolved."""
    assert_rejects([("t.pss", """
        package p { struct S { int x; } function S f(); }
        function void g() { int v; v = p::f().zzz.qqq; }
    """)], "has no member named 'zzz'")


# --- controls: qualified shapes that must keep linking ---

@pytest.mark.parametrize("src", [
    "package p { const int K = 3; }\n"
        "function void g() { int v; v = p::K; }",
    "package p { struct S { static const int K = 3; } }\n"
        "function void g() { int v; v = p::S::K; }",
    "package p { enum E { A, B } }\n"
        "function void g() { p::E v; v = p::E::A; }",
    "package a { package b { function int f(); } }\n"
        "function void g() { int v; v = a::b::f(); }",
    "package p { component C { int x; } }\n"
        "component pss_top { p::C c; function void g() { int v; v = c.x; } }",
    "package p { component C { function int m(); } }\n"
        "component pss_top { p::C c; function void g() { int v; v = c.m(); } }",
    "package p { struct S { int a[4]; } function S f(); }\n"
        "function void g() { int v; v = p::f().a[0]; }",
])
def test_qualified_paths_that_were_never_broken_still_link(src):
    """Pushing the prefix element widened checking over a path shape that had
    been walked as far as its first element and no further.  These are the
    shapes that were already reaching resolution correctly."""
    assert_clean([("t.pss", src)])


# ---------------------------------------------------------------------------
# A call result whose type is built-in, or has no members at all
# ---------------------------------------------------------------------------

def test_a_string_method_on_a_call_result_resolves():
    assert_clean([("t.pss",
        "function string f(); function void g() { int v; v = f().size(); }")])


def test_an_unknown_string_method_on_a_call_result_is_reported():
    assert_rejects([("t.pss",
        "function string f(); function void g() { int v; v = f().nosuchmeth(); }")],
        "unknown method 'nosuchmeth' on built-in type")


def test_a_collection_method_on_a_call_result_resolves():
    assert_clean([("t.pss",
        "function list<int> f(); function void g() { f().push_back(1); }")])


def test_an_unknown_collection_method_on_a_call_result_is_reported():
    assert_rejects([("t.pss",
        "function list<int> f(); function void g() { f().nosuchmeth(1); }")],
        "Failed to find elem nosuchmeth")


def test_a_member_of_a_scalar_call_result_is_reported():
    """Same message a scalar variable gets -- ``int a; a.x`` reports
    "root ref-path element a is not a composite scope".  A call result reaching
    the *same* diagnostic as a value of the same type is the point; before
    ``declaredTypeOf`` knew about functions, a call had no type at all and this
    branch could not tell a scalar from an unresolved type."""
    assert_rejects([("t.pss",
        "function int f(); function void g() { int v; v = f().x; }")],
        "is not a composite scope")


@pytest.mark.parametrize("src", [
    "function void f(); function void g() { int v; v = f().x; }",
    "function void f(int a); function void g() { int v; v = f(1).x; }",
    "package p { function void f(); }\n"
        "function void g() { int v; v = p::f().x; }",
    "component C { function void f(); }\n"
        "component pss_top { C c; function void g() { int v; v = c.f().x; } }",
])
def test_a_member_of_a_void_call_result_is_reported_as_a_void_use(src):
    """A void return gets the LRM 20.5 message rather than the scalar one, and
    gets it *instead of*, not as well as.

    Taking a member of a call result is a use of that result, so this is
    exactly what 20.5 forbids -- and saying so is far more use than "not a
    composite scope".  ``checkVoidCallUse`` therefore runs on every call
    element of a path rather than only the last, and the composite-scope
    branches stay quiet for a void function so that one mistake gets one
    message.
    """
    res = assert_rejects([("t.pss", src)],
        "returns void, so its result cannot be used as a value")
    assert "not a composite scope" not in res.output, res.describe()


def test_an_unresolved_return_type_is_reported_once_at_the_declaration():
    """The counterpart rule: a type that did not resolve is diagnosed where it
    is named, not again at every use.  If a call had no type, this path could
    not distinguish the two cases and would report both or neither."""
    res = assert_rejects([("t.pss",
        "function Missing f(); function void g() { int v; v = f().x; }")],
        "unknown type 'Missing'")
    assert "not a composite scope" not in res.output, res.describe()


# ---------------------------------------------------------------------------
# Which prototype's return type is used
# ---------------------------------------------------------------------------

def test_the_definitions_return_type_wins_over_a_declarations():
    """``visitSymbolFunctionScope`` stops at the *first* prototype declaring a
    return type, and §38 inserts a definition's prototype at the front of the
    list.  So a definition's return type takes precedence over a bare
    declaration's.

    This test exists because the neutralization run asked for it: dropping the
    ``break`` -- which makes the *last* prototype win instead -- failed nothing,
    and a loop-terminating condition that no test can see is a condition nobody
    can rely on.

    Rewritten in §40.  It used to assert this input was *clean*, which it no
    longer is: two declarations disagreeing about the return type is now the
    error LRM 20.2 says it is.  The precedence is still worth pinning, because
    the parser keeps checking after reporting -- so what it does next has to be
    the defensible thing rather than an arbitrary one.  ``f().y`` naming a
    member of the *definition's* return type is what says the definition won;
    the single-error assertion is what says nothing cascaded.
    """
    res = assert_rejects([("t.pss", """
        struct S { int x; }
        struct T { int y; }
        function S f();
        function T f() { T t; return t; }
        function void g() { int v; v = f().y; }
    """)], "declarations of 'f' disagree about the return type")
    assert "1 error" in res.output, res.describe()


# ---------------------------------------------------------------------------
# Recorded, not fixed
# ---------------------------------------------------------------------------

def test_builtin_methods_are_unchecked_on_a_qualified_path():
    """``resolveStaticRootedLeaf`` has no built-in or collection method
    handling -- the ``is_builtin_with_methods`` machinery lives only in
    ``visitExprRefPathContext``.  So the qualified spelling of a case the
    unqualified spelling reports is accepted silently.

    Pinned rather than fixed: the gap is not specific to call results, and
    closing it means giving the static-rooted leaf loop the whole built-in
    method path.  See ``test_an_unknown_string_method_on_a_call_result_is_reported``
    for the unqualified form that *is* reported.
    """
    assert_clean([("t.pss", """
        package p { function string f(); }
        function void g() { int v; v = p::f().nosuchmeth(); }
    """)])


def test_a_member_of_a_call_result_is_not_a_statement():
    """``f().x;`` does not parse.  The void-call statement rule requires the
    statement to end in a call, and ``f().x`` ends in a field.  Recorded
    because the failure is a syntax error rather than the "result of a
    non-void call discarded" that a reader might expect; the shape that *does*
    parse is a trailing call, covered by the collection-method case above."""
    assert_rejects([("t.pss",
        STRUCT + "function S f(); function void g() { f().x; }")],
        "syntax error")
