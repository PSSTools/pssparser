"""
Extension merging (symbol-resolution plan 7.1; LRM 17.2.3, 17.3, 7.5.1, 20.3).

`TaskApplyTypeExtensions::addChild` used to merge by name alone: any name the
extended type already had was "Type extension of X conflicts with an existing
declaration", with no code. That was wrong in three ways:

- a function declared in the type and defined in an extension is one
  function (F25);
- two packages may each add a field or type of one name (F16, 17.2.3);
- a duplicate enum item in `extend enum` was silent (CH07-44, CH17-14).

And an `extend` nested in `extend component` was merged as a stray child and
never applied (F-N1).
"""
import pytest

from ..test_helpers import parse_collect

from .test_activity_scopes import assert_links_and_binds


def errors(code):
    """(line, code, message) of each error."""
    _, markers = parse_collect(code)
    return [(m["line"], m.get("code"), m["message"])
            for m in markers if m["severity"] == "error"]


def codes(code):
    return [(line, c) for line, c, _ in errors(code)]


# ---------------------------------------------------------------------------
# Fields and types: 17.2.3
# ---------------------------------------------------------------------------


def test_extension_may_not_redeclare_a_member_of_the_initial_definition():
    """CH17/p13."""
    e = errors("""
struct S { rand int a; }
extend struct S { rand int a; }
component pss_top { }
""")
    assert [(line, c) for line, c, _ in e] == [(3, "PSS003")]
    assert e[0][2] == ("duplicate declaration of 'a' in an extension of 'S': "
                       "its initial definition already declares it (17.2.3)")


def test_two_extensions_in_one_package_may_not_declare_one_name():
    """CH17/p13b."""
    e = errors("""
struct S { rand int a; }
package p {
    extend struct S { rand int b; }
    extend struct S { rand int b; }
}
component pss_top { }
""")
    assert [(line, c) for line, c, _ in e] == [(5, "PSS003")]
    assert "another extension in package 'p' already declares it" in e[0][2]


def test_two_extensions_outside_any_package_are_one_package():
    e = errors("""
struct S { rand int a; }
extend struct S { rand int b; }
extend struct S { rand int b; }
component pss_top { }
""")
    assert [(line, c) for line, c, _ in e] == [(4, "PSS003")]
    assert "another extension outside any package already declares it" in e[0][2]


@pytest.mark.parametrize("pkgs", [
    # CH17/p13c.
    ("package p {", "package q {"),
    # The global package is a package too.
    ("", "package q {"),
])
def test_extensions_in_different_packages_may_each_declare_a_field(
        tmp_path, pkgs):
    def ext(p):
        return p + " extend struct S { rand int b; } " + ("}" if p else "")
    assert_links_and_binds(tmp_path, """
struct S { rand int a; }
%s
%s
component pss_top { }
""" % (ext(pkgs[0]), ext(pkgs[1])))


def test_every_earlier_contribution_of_the_name_is_checked():
    """q's second `b` conflicts with q's first, not with p's in the symtab."""
    assert codes("""
struct S { rand int a; }
package p { extend struct S { rand int b; } }
package q { extend struct S { rand int b; } }
package q { extend struct S { rand int b; } }
component pss_top { }
""") == [(5, "PSS003")]


def test_types_from_different_packages_may_share_a_name(tmp_path):
    assert_links_and_binds(tmp_path, """
component C { }
package p { extend component C { struct T { int x; } } }
package q { extend component C { struct T { int y; } } }
component pss_top { }
""")


def test_only_fields_and_types_may_share_a_name_across_packages():
    e = errors("""
struct S { rand int a; }
package q { extend struct S { rand int b; } }
package r { extend struct S { constraint b { a > 0; } } }
component pss_top { }
""")
    assert [(line, c) for line, c, _ in e] == [(4, "PSS003")]
    assert "only a field or a type may share its name" in e[0][2]


def test_the_error_points_at_the_first_declaration():
    _, markers = parse_collect("""
struct S { rand int a; }
extend struct S { rand int a; }
component pss_top { }
""")
    assert [(m["line"], [(r["line"], r["label"]) for r in m["related"]])
            for m in markers] == [(3, [(2, "first declared here")])]


def test_in_component_extension_belongs_to_the_enclosing_package():
    """17.2: the nearest *package* that encloses the `extend`, not the
    component it is written in."""
    assert codes("""
package p {
    component C { action A { } }
    extend component C { extend action A { rand int b; } }
    extend action C::A { rand int b; }
}
component pss_top { }
""") == [(5, "PSS003")]


# ---------------------------------------------------------------------------
# Enum items: 7.5.1 g
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decls,line", [
    # CH17/p15b.
    ("enum E { A = 1, B = 2 }\nextend enum E { A = 5 }", 3),
    # CH17/r03: no per-package exemption for an enum item.
    ("enum E { A, B }\npackage p { extend enum E { B } }", 3),
    # G work/e1: twice in one extension.
    ("enum E { A }\nextend enum E { C, C }", 3),
    # Two extensions.
    ("enum E { A }\nextend enum E { C }\nextend enum E { C }", 4),
])
def test_duplicate_enum_item_in_an_extension(decls, line):
    e = errors("""
%s
component pss_top { }
""" % decls)
    assert [(l, c) for l, c, _ in e] == [(line, "PSS003")]
    assert "must be unique across the enum and all its extensions" in e[0][2]


def test_distinct_enum_items_from_two_packages(tmp_path):
    """Example 248's shape."""
    assert_links_and_binds(tmp_path, """
enum E { A }
package p { extend enum E { B } }
package q { extend enum E { C } }
component pss_top {
    exec init_up { E v; v = B; v = C; }
}
""")


# ---------------------------------------------------------------------------
# Functions: 20.3 (F25)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decl,ext", [
    # CH20/p73b.
    ("function int f(int a);",
     "function int f(int a) { return a + 1; }"),
    # CH20/p73c.
    ("static function int f(int a);",
     "static function int f(int a) { return a + 1; }"),
    # G work/f4: the prototype repeated.
    ("function int f(int a);", "function int f(int a);"),
    # The other way round.
    ("function int f(int a) { return a; }", "function int f(int a);"),
])
def test_function_declared_in_the_type_and_extension(tmp_path, decl, ext):
    assert_links_and_binds(tmp_path, """
component pss_top {
    %s
    exec init_up { int x; x = f(1); }
}
extend component pss_top {
    %s
}
""" % (decl, ext))


@pytest.mark.parametrize("decl,ext,msg", [
    # CH20/p73.
    ("function int f(int a) { return a; }",
     "function int f(int a) { return a + 1; }",
     "function 'f' is already defined"),
    ("import solve static function int f(int a);",
     "function int f(int a) { return a; }",
     "function 'f' cannot be both defined and imported"),
    ("function int f(int a) { return a; }",
     "import solve static function int f(int a);",
     "function 'f' cannot be both defined and imported"),
    ("import solve static function int f(int a);",
     "import solve static function int f(int a);",
     "function 'f' is already imported"),
])
def test_function_implemented_twice_across_an_extension(decl, ext, msg):
    assert errors("""
component pss_top {
    %s
}
extend component pss_top {
    %s
}
""" % (decl, ext)) == [(6, "PSS003", msg)]


def test_functions_from_two_packages_are_one_function():
    """G work/f5: 17.2.3's exemption is for fields and types only."""
    assert errors("""
component c { }
package p { extend component c { function int f(int a) { return a; } } }
package q { extend component c { function int f(int a) { return a; } } }
component pss_top { }
""") == [(4, "PSS003", "function 'f' is already defined")]


def test_body_from_an_extension_is_checked():
    """G work/f2: the body is walked in its new home."""
    assert errors("""
component pss_top {
    function int f(int a);
    exec init_up { int x; x = f(1); }
}
extend component pss_top {
    function int f(int a) { return a + nosuch; }
}
""") == [(7, "PSS002", "unknown identifier 'nosuch'")]


def test_body_from_an_extension_sees_its_own_package(tmp_path):
    """CL-N1 holds for a body merged into an existing function."""
    assert_links_and_binds(tmp_path, """
package k { const int K = 3; }
component pss_top {
    function int f(int a);
    exec init_up { int x; x = f(1); }
}
package e {
    import k::*;
    extend component pss_top { function int f(int a) { return a + K; } }
}
""")


def test_declarations_across_an_extension_are_compared():
    """PSS009 sees every prototype, wherever it was written."""
    assert [c for _, c, _ in errors("""
component pss_top {
    function int f(int a);
}
extend component pss_top {
    function bit[4] f(int a) { return 1; }
}
""")] == ["PSS009"]


# ---------------------------------------------------------------------------
# An `extend` inside `extend component`: 17.3 (F-N1)
# ---------------------------------------------------------------------------


def test_nested_extension_is_applied(tmp_path):
    """CH17/p17c, with its members used."""
    assert_links_and_binds(tmp_path, """
component base_c {
    action base_a { rand int i; }
    enum e { A }
}
extend component base_c {
    extend action base_a { rand int j; constraint { j > i; } }
    extend enum e { B }
    action T {
        base_a a;
        exec post_solve { int x; x = a.j; e v; v = B; }
    }
}
component pss_top { base_c d; }
""")


def test_nested_extension_of_a_type_the_same_extension_adds(tmp_path):
    assert_links_and_binds(tmp_path, """
component base_c { }
extend component base_c {
    action added_a { rand int k; }
    extend action added_a { rand int m; }
    action T { added_a a; exec post_solve { int x; x = a.m; } }
}
component pss_top { base_c d; }
""")


def test_nested_extension_of_an_unknown_type():
    """F probes2/ext_nested: was silent."""
    assert errors("""
component base_c { action base_a { rand int i; } }
extend component base_c { extend action nosuch_a { } }
component pss_top { base_c d; }
""") == [(3, "PSS005",
          "cannot extend unknown type 'nosuch_a' in 'base_c'; an extension "
          "inside a component may extend only a type the component declares "
          "(17.3)")]


def test_nested_extension_duplicate_is_reported():
    assert codes("""
component base_c { action base_a { rand int i; } }
extend component base_c { extend action base_a { rand int i; } }
component pss_top { base_c d; }
""") == [(3, "PSS003")]


def test_in_component_extension_of_an_unknown_type():
    """F probes2/ext_nested2: was silent. The lookup failed quietly for an
    `override action`, which is built as an Action now."""
    assert codes("""
component pss_top { extend action nosuch_a { } }
""") == [(2, "PSS002")]


def test_extending_a_non_enum_as_an_enum_has_a_code():
    assert codes("""
struct s { }
extend enum s { A }
component pss_top { }
""") == [(3, "PSS005")]
