"""Function declarations -- one implementation, and `return` against the
declared return type.

Two groups, both of which used to link clean:

* **Redefinition.**  ``function void f() { } function void f() { }`` was
  accepted, and the second body silently overwrote the first via
  ``ISymbolFunctionScope::setBody()``.  So did a definition alongside an
  ``import``, and two imports.  The checks are at the two sites that already
  carried ``// TODO: Report duplicate function error`` and ``// TODO: Cannot
  both define and import an implementation``.
* **Return statements.**  ``IProceduralStmtReturn`` was constructed and never
  looked at again, so ``function int f() { return; }`` and ``function void
  f() { return 1; }`` were both fine.  It also carried no location, which is
  why the check had to gain one before it could point anywhere useful.

What is deliberately *not* checked here: whether a non-void function returns on
every path.  That needs flow analysis, and getting it wrong rejects correct
code -- see ``docs/pssparser-fix-plan.md`` section 33.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# One implementation per function
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    "function void f() { } function void f() { }",
    "function void f(int a) { } function void f(string s) { }",
    "component C { function void f() { } function void f() { } }",
    "package p { function void f() { } function void f() { } }",
])
def test_a_second_definition_is_rejected(src):
    assert_rejects([("t.pss", src)], "function 'f' is already defined")


@pytest.mark.parametrize("src", [
    # Both declaration orders reach a different site, so both are exercised.
    "function void f() { } import solve function void f();",
    "import solve function void f(); function void f() { }",
])
def test_defining_and_importing_the_same_function_is_rejected(src):
    assert_rejects([("t.pss", src)],
                   "function 'f' cannot be both defined and imported")


def test_a_second_import_is_rejected():
    """The import specs were simply appended, and nothing downstream chooses
    between them."""
    assert_rejects([("t.pss", """
        import solve function void f();
        import target function void f();
    """)], "function 'f' is already imported")


def test_a_function_colliding_with_a_type_is_still_a_duplicate_declaration():
    """Control for the boundary: this was the *one* redeclaration form already
    reported, through the general duplicate-symbol path rather than these
    checks."""
    assert_rejects([("t.pss", "function void f() { } struct f { }")],
                   "duplicate declaration of 'f'")


# --- controls: what must keep linking ---

def test_two_distinct_functions_still_link():
    assert_clean([("t.pss", "function void f() { } function void g() { }")])


def test_the_same_function_name_in_two_packages_still_links():
    assert_clean([("t.pss", """
        package p { function void f(); }
        package q { function void f(); }
    """)])


def test_a_package_function_and_a_component_method_still_link():
    assert_clean([("t.pss", """
        package p { function void f(); }
        component C { function void f() { } }
    """)])


def test_a_single_definition_still_links():
    assert_clean([("t.pss", "function void f(int a) { }")])


def test_a_single_import_still_links():
    assert_clean([("t.pss", "import solve function void f(int a);")])


@pytest.mark.parametrize("src", [
    "function void f(); function void f() { }",
    "function void f() { } function void f();",
    "function void f(); function void f();",
])
def test_a_bare_prototype_alongside_a_declaration_still_links(src):
    """Left permitted on purpose.  A prototype carries no implementation, so
    none of these is the "two implementations" conflict the checks are for,
    and the LRM does not plainly forbid the combination.  Rejecting it would
    be guessing -- see section 33.3."""
    assert_clean([("t.pss", src)])


# ---------------------------------------------------------------------------
# `return` against the declared return type
# ---------------------------------------------------------------------------

def test_returning_a_value_from_a_void_function_is_rejected():
    assert_rejects([("t.pss", "function void f() { return 1; }")],
                   "'f' returns void, so 'return' cannot take a value")


def test_a_bare_return_from_a_non_void_function_is_rejected():
    assert_rejects([("t.pss", "function int f() { return; }")],
                   "'f' has a return type, so 'return' must supply a value")


def test_a_component_method_is_checked_too():
    assert_rejects([("t.pss", "component C { function void g() { return 1; } }")],
                   "'g' returns void, so 'return' cannot take a value")


def test_the_report_points_at_the_offending_return():
    """Not at the function name.  ``IProceduralStmtReturn`` had no location at
    all, and a body with several returns needs to say which one."""
    res = assert_rejects([("t.pss",
        "function int f() {\n"
        "  if (1) {\n"
        "    return;\n"
        "  }\n"
        "  return 1;\n"
        "}\n")], "must supply a value")
    assert "t.pss:3:" in res.output, res.describe()


def test_only_the_wrong_return_is_reported():
    res = assert_rejects([("t.pss",
        "function int f() {\n"
        "  if (1) {\n"
        "    return;\n"
        "  }\n"
        "  return 1;\n"
        "}\n")])
    assert res.output.count("must supply a value") == 1, res.describe()


def test_a_bad_reference_inside_a_returned_expression_is_still_reported():
    """The return check runs after the expression is resolved, not instead
    of it."""
    assert_rejects([("t.pss", "function int f() { return nosuch; }")],
                   "nosuch")


# --- controls ---

def test_a_valid_value_return_still_links():
    assert_clean([("t.pss", "function int f() { return 1; }")])


def test_a_valid_bare_return_still_links():
    assert_clean([("t.pss", "function void f() { return; }")])


def test_a_void_function_with_no_return_at_all_still_links():
    assert_clean([("t.pss", "function void f() { int v; v = 1; }")])


def test_a_non_void_function_returning_from_a_nested_block_still_links():
    assert_clean([("t.pss", """
        function int f(int a) {
            if (a > 0) {
                return 1;
            }
            return 0;
        }
    """)])


def test_a_bit_vector_return_type_is_treated_as_non_void():
    assert_clean([("t.pss", "function bit[32] f() { return 1; }")])


def test_a_user_defined_return_type_is_treated_as_non_void():
    assert_rejects([("t.pss", """
        struct S { int a; }
        function S f() { return; }
    """)], "must supply a value")


def test_a_missing_return_in_a_non_void_function_is_not_reported():
    """Deliberately unchecked: deciding whether every path returns needs flow
    analysis, and a wrong answer rejects correct code.  This test records the
    current behaviour so that implementing it is a visible change rather than
    a silent one."""
    assert_clean([("t.pss", "function int f() { int v; v = 1; }")])


# ---------------------------------------------------------------------------
# Where parameters live, and the body that was never resolved
# ---------------------------------------------------------------------------
#
# The three function forms stored their parameters in three different places:
#
#     definition      plist 0, scope children 2
#     import proto    plist 2, scope children 0
#     bare prototype  no plist at all
#
# A consumer asking "what are this function's parameters?" got a different
# answer for each, and ``TaskResolveRootRef`` and ``TaskResolveSymbolPathRef``
# both open with ``getPlist()->...`` unguarded.  All three now populate the
# plist, which is canonical because ``ElemKind_ArgIdx`` resolves through it.

def test_a_prototype_followed_by_a_definition_resolves_its_body():
    """The defect that made this worth reconciling rather than tidying.

    ``visitFunctionDefinition`` registered parameters only when it was the
    visitor that *created* the function scope.  With a prototype seen first,
    the scope already existed, so the parameters went nowhere and the plist
    stayed null -- and nothing in the body resolved at all.  The body was
    walked; every name in it silently failed to be checked.
    """
    assert_rejects([("t.pss", """
        function void f(int a);
        function void f(int a) { int v; v = nosuch; }
    """)], "unknown identifier 'nosuch'")


def test_the_same_holds_for_a_component_method():
    assert_rejects([("t.pss", """
        component C {
            function void f(int a);
            function void f(int a) { int v; v = nosuch; }
        }
    """)], "unknown identifier 'nosuch'")


def test_a_parameter_still_resolves_after_a_prototype():
    """Control for the above: the point is to check the body, not to break
    it."""
    assert_clean([("t.pss", """
        function void f(int a);
        function void f(int a) { int v; v = a; }
    """)])


@pytest.mark.parametrize("src", [
    "function void f(int a) { int v; v = a; }",
    "function int f(int a) { return a; }",
    "component C { function void g(int a, int b) { int v; v = a+b; } }",
    # This case read `function void f(output int a) { a = 1; }` until the
    # direction rule landed.  A direction modifier on a function with a PSS
    # body is illegal (LRM 20.2.2, 20.3.2, and see section 38), so the case
    # was asserting that invalid input links clean.  Assigning to a plain
    # parameter keeps what it was here to exercise -- a parameter reached as
    # the target of an assignment rather than as an operand.
    "function void f(int a) { a = 1; }",
])
def test_parameters_resolve_from_a_definition_body(src):
    """These passed before the move as well, by a different route:
    ``TaskResolveRootRef`` missed in the plist and fell back to the scope's
    own symtab.  They are here to hold that behaviour across the change, not
    to demonstrate it."""
    assert_clean([("t.pss", src)])


def test_a_parameter_resolves_from_an_unnamed_body_position():
    assert_rejects([("t.pss", "function void f(int a) { int v; v = nosuch; }")],
                   "unknown identifier 'nosuch'")


@pytest.mark.parametrize("src", [
    "function void f(int a, int b) { }",
    "import solve function void f(int a, int b);",
    "function void f(int a, int b);",
])
def test_every_declaration_form_puts_parameters_in_the_plist(src):
    """The tree shape itself, which is what the reconciliation is *for*.

    Nothing else asserts it.  Moving the definition's parameters from the
    function scope's own symtab into the plist changes no diagnostic, because
    ``TaskResolveRootRef`` falls back to the scope symtab when the plist
    misses -- so a neutralization that puts them back fails no other test.
    Without this, the only guarantee that the three forms agree would be the
    source comment.

    ``getPlist()`` returning None is the state that made
    ``TaskResolveRootRef::visitSymbolFunctionScope`` and
    ``TaskResolveSymbolPathRef`` -- both of which dereference it unguarded --
    a latent crash.
    """
    import sys, pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
    from pssparser.parser import Parser

    p = Parser()
    p.parses([("t.pss", src)])
    root = p.link()

    fn = None
    for ch in root.getChildren():
        get_name = getattr(ch, "getName", None)
        if not callable(get_name):
            continue
        try:
            if ch.getName() == "f":
                fn = ch
                break
        except Exception:
            continue

    assert fn is not None, "function scope for 'f' not found"

    plist = fn.getPlist()
    assert plist is not None, "%r left getPlist() null" % src
    assert len(plist.getChildren()) == 2, (
        "%r put %d parameter(s) in the plist"
        % (src, len(plist.getChildren())))
