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
