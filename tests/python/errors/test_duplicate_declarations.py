"""Duplicate declarations (PSS003).

Two declarations of one name in one scope is illegal PSS, and the second
silently wins the symbol table -- so a reference that names the first resolves
to the second, and every diagnostic that follows is measured against a
declaration the user did not write.

The check was there.  Three things stopped it reaching anyone:

* it built a ``Warn`` marker, so the run exited 0 while
  ``checkers/core_checker.py`` had always classified PSS003 as an error;
* ``Parser.link()`` collected markers *only* when the link had produced an
  error, so on a clean-but-for-warnings run the marker was built, handed to
  the collector, and dropped -- the CLI printed "0 errors in 0 files" and not
  the warning either way;
* what the user did see was a bare ``Error: TaskBuildSymbolTree: Duplicate
  declaration: A`` on stdout, with no file, no location, and no bearing on the
  exit code, because ``DEBUG_ERROR`` prints unconditionally when no debug
  manager is installed.

Function parameters were a separate hole again -- see the second section.

See ``docs/pssparser-fix-plan.md`` section 31.
"""
import pytest

from ..isolation import assert_clean, assert_rejects


# ---------------------------------------------------------------------------
# The duplicate is reported, as an error, once, with a location
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src,name", [
    ("component C { action A { } action A { } }", "A"),
    ("struct S { int a; int a; }", "a"),
    ("package p { component C { } component C { } }", "C"),
    ("struct S { int a; } struct S { int b; }", "S"),
    ("enum E { A, B, A }", "A"),
    ("component C { action A { } int A; }", "A"),
])
def test_a_duplicate_declaration_is_rejected(src, name):
    assert_rejects([("t.pss", src)], "duplicate declaration of '%s'" % name)


def test_the_report_carries_a_location():
    """It used to arrive as ``<unknown>:-1:0``, or as an unlocated stdout line
    that the summary did not count."""
    res = assert_rejects([("t.pss", "component C {\n  action A { }\n  action A { }\n}\n")],
                         "duplicate declaration of 'A'")
    assert "t.pss:3:" in res.output, res.describe()


def test_the_raw_debug_line_is_gone():
    """``DEBUG_ERROR`` prints straight to stdout with no debug manager
    installed, so this leaked into every ordinary run."""
    res = assert_rejects([("t.pss", "component C { action A { } action A { } }")])
    assert "TaskBuildSymbolTree" not in res.output, res.describe()


def test_it_carries_the_pss003_code_end_to_end():
    """``core_checker.py`` has always declared PSS003 an error.  Only the
    marker disagreed, and a marker that never reached the collector could not
    be classified at all."""
    import json

    res = assert_rejects([("t.pss", "component C { action A { } action A { } }")],
                         args=["--json"])
    diags = json.loads(res.stdout)["diagnostics"]
    assert [(d["code"], d["severity"]) for d in diags] == [("PSS003", "error")], res.describe()


def test_it_is_reported_once():
    res = assert_rejects([("t.pss", "component C { action A { } action A { } }")])
    assert res.output.count("duplicate declaration of 'A'") == 1, res.describe()


# ---------------------------------------------------------------------------
# Function parameters
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("src", [
    # A definition.  The check here looked the name up in the function's
    # *plist* and compared the result against the end of the function's own
    # symtab -- two different containers, and the plist was never populated on
    # this path, so it could not have hit.
    "function void f(int a, int a) { }",
    # A bare prototype.  This visitor did not look at the parameters at all.
    "function void f(int a, int a);",
    # An imported prototype.
    "import solve function void f(int a, int a);",
    # Inside a component, which reaches the definition path again.
    "component C { function void f(int a, int a) { } }",
])
def test_a_duplicate_parameter_name_is_rejected(src):
    assert_rejects([("t.pss", src)], "duplicate parameter name 'a'")


def test_a_duplicate_parameter_report_names_the_parameter():
    """It arrived as ``duplicate declaration of ''`` at ``<unknown>:-1:0``:
    the shared reporter reads a name that a parameter decl does not carry, and
    a location that lives on the name node rather than the decl."""
    res = assert_rejects([("t.pss", "function void f(int a, int a) { }")])
    assert "duplicate declaration of ''" not in res.output, res.describe()
    assert "t.pss:1:" in res.output, res.describe()


def test_a_duplicate_template_parameter_is_still_rejected():
    """Control: the template-parameter check was already correct, and is the
    shape the function-parameter one now follows."""
    assert_rejects([("t.pss", "component C { action A<int T, int T> { } }")],
                   "duplicate parameter name 'T'")


# ---------------------------------------------------------------------------
# Controls -- what must keep linking
# ---------------------------------------------------------------------------

def test_distinct_names_still_link():
    assert_clean([("t.pss", "component C { action A { } action B { } }")])


def test_the_same_name_in_two_scopes_still_links():
    """The check is per-scope.  Two components may each declare an ``A``."""
    assert_clean([("t.pss", """
        component C { action A { } }
        component D { action A { } }
    """)])


def test_the_same_name_in_two_packages_still_links():
    assert_clean([("t.pss", """
        package p { struct S { int a; } }
        package q { struct S { int b; } }
    """)])


def test_a_reopened_package_adding_new_types_still_links():
    """A package may be declared more than once; only a repeated *member*
    name is a duplicate."""
    assert_clean([("t.pss", """
        package p { struct S { } }
        package p { struct T { } }
    """)])


def test_a_subtype_redeclaring_a_base_member_still_links():
    """Shadowing across an inheritance edge is not a duplicate declaration --
    the two names are in different scopes."""
    assert_clean([("t.pss", """
        struct base_s { int a; }
        struct derived_s : base_s { }
        component C { action A { derived_s d; constraint { d.a > 0; } } }
    """)])


def test_a_local_shadowing_a_field_still_links():
    assert_clean([("t.pss", """
        component C {
            action A {
                rand int v;
                exec body { int v; v = 1; }
            }
        }
    """)])


def test_distinct_parameter_names_still_link():
    assert_clean([("t.pss", "function void f(int a, int b) { }")])


def test_two_functions_reusing_a_parameter_name_still_link():
    """The parameter scope is per-prototype, not per-package."""
    assert_clean([("t.pss", """
        function void f(int a) { }
        function void g(int a) { }
    """)])


# ---------------------------------------------------------------------------
# The dropped-warning path, independent of duplicates
# ---------------------------------------------------------------------------

def test_a_clean_link_still_exits_zero():
    """``Parser.link()`` now collects markers unconditionally.  Collecting
    them must not by itself turn a clean run into a failing one."""
    res = assert_clean([("t.pss", """
        component C {
            action A { rand int x; constraint { x > 0; } }
        }
    """)])
    assert res.rc == 0, res.describe()
