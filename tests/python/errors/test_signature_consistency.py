"""Declarations of one function that do not agree with each other (§40, §41).

LRM 20.2 lets a function be declared more than once -- a prototype and a
definition, a prototype and an import.  Nothing compared any part of those
declarations against each other: ``function int f(); function string f();``
linked clean, and so did every disagreement about the parameter list.

§40 closed the return type.  §41 closed the parameter list -- arity, kind,
type, direction, and LRM 20.2.4 c on default values -- and, in the course of
reading the LRM rather than inferring it, found that two things §40 had filed
as gaps were not gaps at all:

* **Parameter names are not part of a PSS signature.**  Calls are positional;
  the grammar has no named-argument form.  §40 asserted the opposite.
* **``pure`` on one declaration only is legal** in the direction that matters
  (LRM 20.2.6 b), and unaddressed in the other.

Both now have tests saying so, which is the more useful record: a check that
rejected either would reject valid code.

The whole family is deliberately one-sided.  A difference is reported only
when it is *certain*, and the check stays quiet whenever the comparison is
uncertain -- an alias, a width that will not fold, a name that did not
resolve, a data-type kind the comparator has no case for.  The reason is the
asymmetry of the two failures: a missed report leaves invalid input
undiagnosed, where a false report rejects a valid model at a declaration the
user has no way to change into something the tool accepts.  Every "not
reported" test below pins one such case.

The comparison itself is ``TaskCompareTypeRefs``, which already existed --
built to decide whether a requested template specialization matches one
already made.  §39 recorded this defect as needing type-equality machinery
that had to be built first; it did not.  What it needed was for that machinery
to distinguish "different" from "cannot tell", which for its first caller was
a distinction without a difference: an unnecessary specialization costs time,
so dedup folds doubt into "different" and is right to.  A diagnostic cannot.
``Rel::Unsure`` is that split; ``equal()`` is still the old two-valued reading
and every existing caller keeps it.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# Reported
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    # Two bare prototypes.
    "struct S { int x; } struct T { int y; }"
    " function S f(); function T f();",
    # A prototype and a definition.
    "struct S { int x; } struct T { int y; }"
    " function S f(); function T f() { T t; return t; }",
    # Scalars, where the difference is the kind.
    "function int f(); function string f();",
    "function bool f(); function int f();",
    "function chandle f(); function int f();",
    # An enum type and an integer are assignment-compatible in PSS and are
    # still not the same type, which is what a declaration has to give.
    "enum E { A } function E f(); function int f();",
    # Signedness is part of an integral type.
    "function int f(); function bit f();",
    # So is the width, whether both are written or one is left to default.
    "function int[8] f(); function int[16] f();",
    "function int f(); function int[16] f();",
])
def test_declarations_that_disagree_are_reported(src):
    assert_rejects([("t.pss", src)],
        "declarations of 'f' disagree about the return type")


@pytest.mark.parametrize("src", [
    "function void f(); function int f();",
    "function int f(); function void f();",
    "function void f(); function int f() { return 1; }",
])
def test_a_void_disagreement_says_so(src):
    """``void`` is the absence of a return type rather than a type, so it needs
    its own comparison -- and it is worth its own message, because it is both
    the commonest of these mistakes and the one whose general phrasing reads
    worst ("disagree about the return type" when one declaration has none).
    """
    res = assert_rejects([("t.pss", src)],
        "one returns void and the other does not")
    assert "1 error" in res.output, res.describe()


def test_three_disagreeing_declarations_are_reported_once():
    """One mistake, one report.  Three declarations that disagree pairwise
    would otherwise produce a report per pair, which says nothing the first
    one did not.
    """
    res = assert_rejects([("t.pss",
        "function int f(); function string f(); function bool f();")],
        "declarations of 'f' disagree about the return type")
    assert "1 error" in res.output, res.describe()


@pytest.mark.parametrize("src", [
    "package p { function int f(); function string f(); }",
    "component C { function int f(); function string f(); }",
])
def test_the_check_reaches_every_scope_a_function_can_be_declared_in(src):
    res = assert_rejects([("t.pss", src)],
        "declarations of 'f' disagree about the return type")
    assert "1 error" in res.output, res.describe()


@pytest.mark.parametrize("spec", ["C<8> a;", "C<8> a; C<16> b; C<32> c;"])
def test_a_generic_is_reported_once_however_many_specializations(spec):
    """A generic's body is walked once per specialization, so the naive
    outcome is one report per use.  It is one report, at the generic's own
    source location, because that is where the declarations are written.
    """
    res = assert_rejects([("t.pss",
        "component C<int W = 8> { function int f(); function string f(); }\n"
        "component pss_top { %s }\n" % spec)],
        "declarations of 'f' disagree about the return type")
    assert "1 error" in res.output, res.describe()
    assert "t.pss:1:" in res.output, res.describe()


def test_an_unspecialized_generic_is_not_checked():
    """Nothing inside a generic that is never specialized is checked -- not
    this, and not an unknown identifier either.  Pinned here so that the
    exemption is recorded as the parser-wide rule it is, rather than being
    mistaken for a gap in this check.
    """
    assert_clean([("t.pss",
        "component C<int W = 8> { function int f(); function string f(); }")])
    assert_clean([("t.pss",
        "component C<int W = 8> {"
        " function void g() { int v; v = nosuchthing; } }")])


def test_an_import_prototype_participates():
    """An imported declaration is a declaration.  ``visitFunctionImportProto``
    shares the function's symbol scope with the other two forms, so its
    prototype lands in the same list and is compared like any other.
    """
    assert_rejects([("t.pss",
        "import function int f(); function void f();")],
        "declarations of 'f' disagree about the return type")


def test_the_definition_is_the_one_measured_against():
    """The report lands on the *bare declaration*, not on the definition,
    because ``visitFunctionDefinition`` puts a definition's prototype at the
    front of the list and this check measures against the front.

    That is the same choice ``declaredTypeOf``, ``TaskGetElemSymbolScope`` and
    the ``return``-statement check all make -- see
    ``test_the_definitions_return_type_wins_over_a_declarations``.  One
    authority, or the diagnostics contradict each other about what ``f``
    returns.
    """
    res = assert_rejects([("t.pss",
        "struct S { int x; }\n"
        "struct T { int y; }\n"
        "function S f();\n"
        "function T f() { T t; return t; }\n")],
        "declarations of 'f' disagree about the return type")
    # Line 3 is the bare declaration; line 4 is the definition.
    assert "t.pss:3:" in res.output, res.describe()


# ---------------------------------------------------------------------------
# Not reported: the comparison could not be sure
# ---------------------------------------------------------------------------

def test_identical_declarations_are_clean():
    assert_clean([("t.pss",
        "struct S { int x; }"
        " function S f(int a); function S f(int a);")])


def test_a_typedef_and_its_underlying_type_are_not_a_disagreement():
    """An alias *is* the type it aliases.  Nothing in this parser expands one,
    so a comparison involving one is declined rather than answered -- both when
    the alias hides a kind difference (``myint`` is a user-defined reference
    and ``int`` is not) and when it hides an identity difference (``myS`` and
    ``S`` resolve to two different declarations).
    """
    assert_clean([("t.pss", "typedef int myint;"
        " function myint f(); function int f();")])
    assert_clean([("t.pss", "struct S { int x; } typedef S myS;"
        " function myS g(); function S g();")])


def test_one_type_named_two_ways_is_not_a_disagreement():
    """``p::S`` and ``S`` are one type seen from two places.  This is why the
    check runs after the prototypes have been walked rather than in the symbol
    tree builder, where nothing has resolved and the only thing available to
    compare is the spelling.
    """
    assert_clean([("t.pss", """
        package p { struct S { int x; } }
        import p::*;
        function p::S f();
        function S f();
    """)])


@pytest.mark.parametrize("src", [
    "function int f(); function int[32] f();",
    "function bit f(); function bit[1] f();",
])
def test_a_written_width_matching_the_default_is_not_a_disagreement(src):
    """``int`` and ``int[32]`` are the same type, and are compared on the
    merits rather than waved through: the builder materializes the default
    width, so both sides carry an expression that folds to 32.

    Worth pinning because the obvious guess about how this passes is wrong.
    The neutralization run asked the question -- making ``widthEqual`` call an
    absent width *different* from a written one failed nothing, which is only
    possible if no width is ever absent.  ``int`` vs ``int[16]`` is reported,
    for the same reason.
    """
    assert_clean([("t.pss", src)])


def test_a_globally_qualified_name_is_not_a_disagreement():
    """``::p::S`` and ``p::S`` are one type written two ways, and the leading
    ``::`` is compared before anything is resolved.  So it has to be declined
    rather than answered, even though the two spellings visibly differ.
    """
    assert_clean([("t.pss",
        "package p { struct S { int x; } }"
        " function ::p::S f(); function p::S f();")])


def test_two_unknown_type_names_are_two_mistakes_not_three():
    """Both names are reported as unknown.  Adding "and they disagree" counts
    a comparison between two things neither of which was read.

    This is the same-kind counterpart of
    ``test_an_unresolved_return_type_is_one_mistake_not_two``: there the
    unresolved reference was measured against an integer and the *kinds*
    differed; here both sides are user-defined references and the comparison
    falls through to their spellings.  Two different guards, one rule.
    """
    res = assert_rejects([("t.pss",
        "function Missing1 f(); function Missing2 f();")],
        "unknown type 'Missing1'")
    assert "disagree about the return type" not in res.output, res.describe()


def test_an_unresolved_return_type_is_one_mistake_not_two():
    """``Missing`` names nothing, which is reported.  Adding "and these
    declarations disagree" describes a comparison against a type that was never
    read, and points the user at the wrong line.
    """
    res = assert_rejects([("t.pss",
        "function Missing f(); function int f();")],
        "unknown type 'Missing'")
    assert "disagree about the return type" not in res.output, res.describe()


# ---------------------------------------------------------------------------
# The parameter list (§41)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "function void f(int a); function void f(int a, int b);",
    "function void f(); function void f(int a);",
    "function void f(int a); function void f(int a, type... args);",
])
def test_a_differing_parameter_count_is_reported(src):
    """The count is compared before anything else, because a mismatch makes
    every positional comparison after it meaningless -- ``parameter 2`` of one
    declaration is not the same parameter as ``parameter 2`` of the other.

    A varargs tail is an ordinary parameter carrying ``is_varargs``, so it is
    counted like one; adding it to one declaration only changes the count.
    """
    assert_rejects([("t.pss", src)],
        "disagree about the number of parameters")


def test_a_varargs_tail_on_one_declaration_only_is_reported():
    """``int... a`` and ``int a`` differ in nothing a *count* comparison can
    see -- same arity, same kind, same type, same direction -- so this is the
    only shape that reaches the varargs comparison.

    Written because the neutralization run demanded it: removing the varargs
    check failed nothing, since the case above is caught by the arity check
    two lines earlier.
    """
    assert_rejects([("t.pss",
        "function void f(int... a); function void f(int a);")],
        "disagree about whether parameter 1 ('a') is varargs")


@pytest.mark.parametrize("src", [
    "function void f(int a); function void f(string a);",
    "function void f(int[8] a); function void f(int[16] a);",
    "struct S { int x; } struct T { int y; }"
    " function void f(S a); function void f(T a);",
])
def test_a_differing_parameter_type_is_reported(src):
    """Through the same three-valued comparison §40 built for return types,
    with the same conservative reading: a difference is reported only when it
    is certain.
    """
    assert_rejects([("t.pss", src)],
        "disagree about the type of parameter 1 ('a')")


def test_a_differing_parameter_direction_is_reported():
    assert_rejects([("t.pss",
        "import function void f(input int a);"
        " import function void f(output int a);")],
        "disagree about the direction of parameter 1 ('a')")


def test_an_omitted_direction_is_input_not_a_disagreement():
    """LRM 20.2.1: the direction modifiers are optional, and an omitted one is
    input.  ``f(int a)`` and ``f(input int a)`` are one declaration written two
    ways.

    The *presence* of a modifier does carry a consequence -- it makes the
    function importable only (LRM 20.3.2) -- but that is
    ``checkNativeParamDir``'s rule, already applied across every prototype,
    and it does not need this check to call the two spellings different.
    """
    assert_clean([("t.pss",
        "function void f(int a); function void f(input int a);")])


def test_a_differing_parameter_kind_is_reported():
    """``int a`` and ``type a`` are not two spellings of one parameter, and
    comparing their *types* would be comparing things that are not comparable
    -- a type parameter has no data type at all.  Checked before the type.
    """
    assert_rejects([("t.pss",
        "function void f(int a); function void f(type a);")],
        "disagree about what kind of parameter 1 ('a') is")


@pytest.mark.parametrize("src", [
    # LRM 20.2.4 c is explicit that this is illegal "even if the value is the
    # same", so both spellings are errors and the values are never compared.
    "function void f(int a = 1); function void f(int a = 1);",
    "function void f(int a = 1); function void f(int a = 2);",
])
def test_a_default_given_twice_is_reported(src):
    """LRM 20.2.4 c: "A default parameter value shall not be specified in the
    redeclaration of a function if already declared for the same parameter in a
    previous declaration, even if the value is the same."

    The message says "more than one declaration" rather than naming an earlier
    one, because the prototype list is not in lexical order -- a definition's
    prototype is moved to the front.  The rule is symmetric, so nothing is lost.
    """
    assert_rejects([("t.pss", src)],
        "is given a default value by more than one declaration")


def test_a_definition_alone_may_give_a_default():
    """A definition with no preceding declaration is ONE declaration, so
    LRM 20.2.4 c does not apply and the default is legal.

    It was rejected. ``visitFunctionDefinition`` registered the definition's
    prototype twice when it also had to create the function symbol -- once at
    creation, once via the insert that puts a definition at the front -- so
    ``checkDeclarationConsistency`` compared that one prototype against itself.

    Only this rule could see the duplicate. Return type, parameter type,
    direction and kind all report a DISAGREEMENT, which a prototype cannot have
    with itself; the default-value rule reports both prototypes merely HAVING a
    default (20.2.4 c does not compare values), which a self-comparison always
    satisfies. That is why the ordinary shape below was the only casualty.
    """
    assert_clean([("t.pss", "function void f(int a = 1) { }")])
    assert_clean([("t.pss", 'function void f(string s = "x") { }')])
    assert_clean([("t.pss",
        "component C { function void f(int a = 1) { } }")])
    assert_clean([("t.pss",
        "package p { function void f(int a = 1) { } }")])
    # The duplicate was invisible to every other rule, so guard the shape
    # itself rather than only this one diagnostic: two params, one defaulted.
    assert_clean([("t.pss",
        "function void f(int a, int b = 2) { g(); } function void g() { }")])


def test_a_definition_that_repeats_a_declarations_default_is_still_reported():
    """The other half: with a real second declaration the rule must still fire.

    This is what stops the fix above from being "delete the check". Removing
    the duplicate registration must not remove the genuine pair.
    """
    assert_rejects([("t.pss",
        "function void f(int a = 1); function void f(int a = 1) { }")],
        "is given a default value by more than one declaration")
    assert_rejects([("t.pss",
        "function void f(int a = 1) { } function void f(int a = 2);")],
        "is given a default value by more than one declaration")


def test_a_definition_and_a_declaration_still_disagree_about_types():
    """A definition alone now contributes ONE prototype instead of two; the
    consistency check must still see the pair when a declaration exists.
    """
    assert_rejects([("t.pss",
        "function int f(int a); function int f(string a) { return 0; }")],
        "disagree about the type of")


def test_a_default_given_by_only_one_declaration_is_clean():
    """LRM 20.2.4 c again, read the other way: a default "is in effect for
    redeclarations", so one declaration supplying it is the *expected* shape,
    in either order, and the call may omit the argument.
    """
    assert_clean([("t.pss",
        "function void f(int a = 1); function void f(int a);"
        " function void g() { f(); }")])
    assert_clean([("t.pss",
        "function void f(int a); function void f(int a = 1);"
        " function void g() { f(); }")])


def test_a_call_is_now_measured_against_a_signature_that_agrees():
    """§40 pinned the consequence of the gap: ``checkCallArity`` measures every
    call against the *first* prototype, so two disagreeing declarations meant
    calls were silently checked against one of them chosen arbitrarily.

    Restated as a rejection.  The disagreement is now reported, which is what
    makes the arbitrary choice harmless -- the input never reaches the point of
    being checked against the wrong list without the user being told.
    """
    assert_rejects([("t.pss",
        "function void f(int a); function void f(int a, int b);"
        " function void g() { f(1); }")],
        "disagree about the number of parameters")


# ---------------------------------------------------------------------------
# The parameter list: what is deliberately not compared
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    # A typedef alias against what it aliases.
    "typedef int myint; function void f(myint a); function void f(int a);",
    "struct S { int x; } typedef S myS;"
    " function void f(myS a); function void f(S a);",
    # One type named two ways.
    "package p { struct S { int x; } } import p::*;"
    " function void f(p::S a); function void f(S a);",
    "package p { struct S { int x; } }"
    " function void f(::p::S a); function void f(p::S a);",
    # A written width matching the materialized default.
    "function void f(int a); function void f(int[32] a);",
])
def test_an_uncertain_parameter_type_comparison_is_not_reported(src):
    """The parameter-type path uses the same three-valued comparison as the
    return type, and therefore inherits the same five sources of ``Unsure``.
    Pinned separately rather than assumed: these are two call sites, and only
    one of them was covered.

    The neutralization run is what asked.  Making the parameter comparison
    report on ``Unsure`` as well as ``NotEqual`` failed nothing, which meant
    no test reached the parameter path with an uncertain type at all -- so
    nothing would have caught a change that made it report on doubt.
    """
    assert_clean([("t.pss", src)])


@pytest.mark.parametrize("src", [
    "function void f(Missing a); function void f(int a);",
    "function void f(Missing1 a); function void f(Missing2 a);",
])
def test_an_unknown_parameter_type_is_one_mistake_not_two(src):
    """The unknown type is reported.  A second report claiming the
    declarations disagree describes a comparison against something that was
    never read -- the parameter-list counterpart of
    ``test_an_unresolved_return_type_is_one_mistake_not_two``.
    """
    res = assert_rejects([("t.pss", src)], "unknown type")
    assert "disagree" not in res.output, res.describe()


def test_differing_parameter_names_are_not_a_disagreement():
    """PSS calls are positional.  The grammar's ``function_parameter_list`` is
    a bare list of expressions -- there is no named-argument form -- and
    nothing in the LRM requires a redeclaration to reuse the names.  So a
    definition is free to name its parameters whatever suits its body, exactly
    as in C.

    §40 recorded the opposite ("names are part of a PSS signature, they can be
    supplied by name at a call site").  That was wrong, and checking the
    grammar took one grep.

    What *is* broken here is separate and worse: see
    ``test_a_definitions_own_parameter_name_does_not_resolve_in_its_body``.
    """
    assert_clean([("t.pss",
        "function void f(int a); function void f(int b);")])


@pytest.mark.parametrize("src", [
    # LRM 20.2.6 b: legal, and the case the rule exists for.
    "pure function int f(int a); function int f(int a) { return a; }",
    # Not addressed by the LRM in either direction; not guessed at.
    "function int f(int a); pure function int f(int a);",
])
def test_a_pure_qualifier_on_one_declaration_only_is_not_reported(src):
    """LRM 20.2.6 b: "The pure keyword may be omitted in a function definition
    if its original declaration contains the pure keyword; it is still
    considered pure."  So the first of these is explicitly legal, and a check
    that compared qualifiers naively would reject the one shape the rule was
    written to permit.

    The second -- adding ``pure`` in a redeclaration -- the LRM does not
    address.  Left alone rather than guessed at.

    §40 filed this under "parameter lists are not compared", which was two
    mistakes: ``pure`` is not a parameter-list property, and it is not
    unchecked by oversight.
    """
    assert_clean([("t.pss", src)])


def test_a_static_function_may_be_shadowed_with_a_different_signature():
    """LRM 20.2: "A static function declared in a component scope may be
    shadowed by a function declaration with the same name in a derived
    component... may have a different return type or arguments than in the base
    component."

    This passes because a derived component's function gets its own symbol
    scope rather than joining the base's prototype list.  Pinned so that a
    future change which merges them has to confront the exemption rather than
    discover it as a bug report.
    """
    assert_clean([("t.pss",
        "component B { static function int f(int a); }\n"
        "component D : B { static function string f(string a, int b); }\n"
        "component pss_top { D d; }\n")])


# ---------------------------------------------------------------------------
# Recorded, not fixed
# ---------------------------------------------------------------------------

def test_a_definitions_own_parameter_name_does_not_resolve_in_its_body():
    """``function void f(int a); function void f(int b) { v = b; }`` reports
    ``unknown identifier 'b'`` -- and ``v = a`` resolves instead.  Exactly
    backwards: the name the definition wrote is rejected, and a name from a
    declaration that is not this body's is accepted.

    A consequence of §36: the plist is built by whichever visitor creates the
    function's scope, which for a declaration-then-definition pair is the
    declaration.  The fix is to make a body resolve against its own
    prototype's names, not to report the mismatch -- see
    ``test_differing_parameter_names_are_not_a_disagreement`` for why the
    mismatch is legal.
    """
    assert_rejects([("t.pss",
        "function void f(int a); function void f(int b) { int v; v = b; }")],
        "unknown identifier 'b'")
    assert_clean([("t.pss",
        "function void f(int a); function void f(int b) { int v; v = a; }")])


def test_the_const_qualifier_is_not_part_of_the_compared_signature():
    """LRM 20.2.3 c: "The const qualifier is an essential part of the function
    signature and must appear in redeclarations (and overrides) of a
    function."

    Not checkable yet: ``const`` is parsed and discarded, with no AST field to
    compare.  Blocked on that, not on this check.
    """
    assert_clean([("t.pss",
        "function void f(const int a); function void f(int a);")])


def test_an_instance_function_shadow_may_differ_unchecked():
    """LRM 20.2: an *instance* function shadowing one in a base component
    "must have the same return type and arguments as that in the base
    component" -- the opposite of the static rule pinned above.

    Unchecked.  It is not a redeclaration in this parser's sense (the two live
    in different symbol scopes), so closing it means walking the inheritance
    chain rather than one prototype list.
    """
    assert_clean([("t.pss",
        "component B { function int f(int a); }\n"
        "component D : B { function string f(string a); }\n"
        "component pss_top { D d; }\n")])
