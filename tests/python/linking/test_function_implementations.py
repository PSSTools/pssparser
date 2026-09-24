"""
Function implementations and imports (symbol-resolution plan 7.2; LRM 20.2,
20.4.1, 20.6).

A function is assembled from declarations written in one scope, in
extensions, and in `import C function f;` statements that are only bound at
link time. The at-most-one-implementation rule is stated once
(src/FunctionScopeUtil.h) and applied at each of them, and it counts a target
template as an implementation too. The parameter-name side (G-N1) is pinned in
tests/python/errors/test_signature_consistency.py.
"""
import pytest

from ..test_helpers import parse_collect

from .test_activity_scopes import assert_links_and_binds


def errors(code):
    """(line, code, message) of each error."""
    _, markers = parse_collect(code)
    return [(m["line"], m.get("code"), m["message"])
            for m in markers if m["severity"] == "error"]


# ---------------------------------------------------------------------------
# One implementation: 20.2, 20.4, 20.6 (CH20-14)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decls,line,msg", [
    # CH20/p74: the type-form import between a declaration and a body.
    ("static function int f(int a);\n"
     "    import C function f;\n"
     "    function int f(int a) { return a; }",
     4, "function 'f' cannot be both defined and imported"),
    # A target template is a definition.
    ("target function void f(int a);\n"
     "    target C function void f(int a) = \"\"\" x({{a}}); \"\"\";\n"
     "    function void f(int a) { }",
     5, "function 'f' is already defined"),
    ("target C function void f(int a) = \"\"\" x({{a}}); \"\"\";\n"
     "    import target C static function void f(int a);",
     4, "function 'f' cannot be both defined and imported"),
])
def test_second_implementation(decls, line, msg):
    assert errors("""
component pss_top {
    %s
}
""" % decls) == [(line, "PSS003", msg)]


def test_target_template_from_an_extension_is_an_implementation():
    assert errors("""
component pss_top {
    target function void f(int a) { }
}
extend component pss_top {
    target C function void f(int a) = \"\"\" x({{a}}); \"\"\";
}
""") == [(6, "PSS003", "function 'f' is already defined")]


# ---------------------------------------------------------------------------
# Where a component's function may be imported: 20.4.1 (CH20-46, CH20-47)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decls", [
    # CH20/p40: a derived component.
    "component base_c { static function int f(int a); }\n"
    "component pss_top : base_c { import C function f; }",
    # An unrelated component.
    "component other_c { static function int f(int a); }\n"
    "component pss_top { import C function other_c::f; }",
    # A package.
    "component other_c { static function int f(int a); }\n"
    "package q { import C function other_c::f; }\n"
    "component pss_top { }",
])
def test_component_function_imported_outside_its_component(decls):
    e = errors(decls)
    assert [c for _, c, _ in e] == ["PSS019"]
    assert "may be imported only in that component type (20.4.1)" in e[0][2]


@pytest.mark.parametrize("decls", [
    # CH20/p40b: an extension of the same component.
    "component pss_top { static function int f(int a); }\n"
    "extend component pss_top { import C function f; }",
    # A package function has no such restriction.
    "package p { function int f(int a); }\n"
    "package q { import C function p::f; }\n"
    "component pss_top { }",
    "package p { function int f(int a); }\n"
    "component pss_top { import C function p::f; }",
])
def test_function_imported_where_allowed(tmp_path, decls):
    assert_links_and_binds(tmp_path, decls)


def test_type_form_import_in_a_template_component():
    """CH20/p41. Only specializations are walked; the two here are one
    report, naming the template."""
    assert errors("""
component t_c<int N = 1> {
    static function int f(int a);
    import C function f;
}
component pss_top { t_c<2> t; t_c<3> u; }
""") == [(4, "PSS019",
          "cannot import function 'f': it is declared in template component "
          "'t_c' (20.4.1)")]


def test_prototype_form_import_in_a_template_component():
    assert errors("""
component t_c<int N = 1> {
    import C static function int g(int a);
}
component pss_top { t_c<2> t; t_c<3> u; }
""") == [(3, "PSS019",
          "cannot import function 'g': it is declared in template component "
          "'t_c' (20.4.1)")]
