"""
Static and instance members (symbol-resolution plan 7.3; LRM 18.3, 20.2, 20.4).

The linker used to ignore `static` entirely: instance and static members share
one symbol table and nothing filtered by it. One question -- is this member
the type's or an instance's (src/FunctionScopeUtil.h, declaredStatic and
isInstanceMember) -- now answers three rules:

- `T::m` reaches only the type's members (18.3), PSS040;
- a static function has no instance, so its body cannot use one (20.2), PSS040;
- an instance function cannot be imported (20.4), PSS019;
- `comp` is an instance, so it cannot reach a static member (9.1.4.1 f),
  PSS041.
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
# T::m (18.3): G-N3, CH20/p70, G work/s1
# ---------------------------------------------------------------------------

_SUB = """
component sub_c {
    function int inst_f(int a) { return a; }
    static function int st_f(int a) { return a; }
    static const int K = 1;
    enum e_e { A, B }
    int fld;
}
"""


@pytest.mark.parametrize("expr,name", [
    ("sub_c::inst_f(1)", "inst_f"),
    ("sub_c::fld", "fld"),
])
def test_an_instance_member_through_the_type(expr, name):
    assert errors(_SUB + """
component pss_top {
    exec init_up { int x; x = %s; }
}
""" % expr) == [(11, "PSS040",
                 "'%s' is an instance member of 'sub_c' and cannot be "
                 "referenced through the type; only types, static constants, "
                 "static functions and enum items can (18.3)" % name)]


def test_a_struct_field_through_the_type():
    assert [c for _, c, _ in errors("""
struct s_s { int fld; static const int K = 2; }
component pss_top {
    exec init_up { int x; x = s_s::K; x = s_s::fld; }
}
""")] == ["PSS040"]


def test_through_the_type_from_an_action_in_another_component():
    """An action inside pss_top has pss_top's instance, not sub_c's."""
    assert [c for _, c, _ in errors(_SUB + """
component pss_top {
    sub_c s;
    action a_a { exec post_solve { int x; x = sub_c::fld; x = comp.s.fld; } }
}
""")] == ["PSS040"]


@pytest.mark.parametrize("decls", [
    # The type's own members.
    _SUB + "component pss_top { exec init_up { int x; sub_c::e_e v;\n"
    "    x = sub_c::st_f(1) + sub_c::K; v = sub_c::e_e::A; } }",
    # A base-qualified call from a derived component: the LRM is silent, and
    # there is an instance to use.
    "component base_c { function int inst_f(int a) { return a; } int fld; }\n"
    "component pss_top : base_c {\n"
    "    exec init_up { int x; x = base_c::inst_f(1) + base_c::fld; } }",
    # Inside the type itself, and inside an extension of it.
    "component pss_top { int fld; function int g() { return pss_top::fld; } }\n"
    "extend component pss_top { function int h() { return pss_top::fld; } }",
])
def test_through_the_type_where_allowed(decls):
    # Not assert_links_and_binds: its reference walk counts every qualified
    # *call* (`p::f(1)`) as unbound, 7.3 or no, while resolution binds it.
    assert errors(decls) == []


# ---------------------------------------------------------------------------
# A static function's body (20.2): G-N4, CH20/p71, G work/s2
# ---------------------------------------------------------------------------


def _static_ctxt(name, fn):
    return ("cannot reference instance member '%s' from static function "
            "'%s': a static function has no component instance (20.2)"
            % (name, fn))


def test_a_static_function_uses_instance_members():
    assert errors("""
component pss_top {
    int fld;
    function int inst_f() { return 1; }
    static function int st_f() { return inst_f(); }
    static function int st_g() { return fld; }
}
""") == [(5, "PSS040", _static_ctxt("inst_f", "st_f")),
         (6, "PSS040", _static_ctxt("fld", "st_g"))]


def test_a_static_function_in_an_extension():
    assert errors("""
component pss_top {
    int fld;
}
extend component pss_top {
    static function int g() { return fld; }
}
""") == [(6, "PSS040", _static_ctxt("fld", "g"))]


def test_a_static_function_uses_an_inherited_instance_member():
    assert errors("""
component base_c { int fld; }
component pss_top : base_c {
    static function int g() { return fld; }
}
""") == [(4, "PSS040", _static_ctxt("fld", "g"))]


def test_a_static_target_template_uses_an_instance_member():
    """The qualifier is on the template node, not its prototype. The
    non-static template beside it is not reported."""
    assert errors('''
component pss_top {
    int fld;
    target C static function void t(int a) = """ x({{fld}}, {{a}}); """;
    target C function void u(int a) = """ x({{fld}}, {{a}}); """;
}
''') == [(4, "PSS040", _static_ctxt("fld", "t"))]


def test_what_a_static_function_may_use():
    assert errors("""
package p { function int pf(int a) { return a; } }
component pss_top {
    int fld;
    static const int K = 3;
    enum e_e { A, B }
    static function int s1(int a) { return a + K; }
    static function int s2() { e_e v = A; return s1(K) + p::pf(1); }
    static function int s3(int fld) { return fld + pss_top::s1(2); }
    function int inst() { return fld + s1(1); }
}
""") == []


# ---------------------------------------------------------------------------
# Imports (20.4, 20.4.1.1 b.1): CH20/p12, p12b, p72
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("decls,line", [
    # CH20/p12b: an import prototype with nothing else declares an instance
    # function.
    ("import C function void s(int a);", 3),
    # CH20/p72: a static function's import prototype must say so.
    ("static function void s(int a);\n"
     "    import C function void s(int a);", 4),
])
def test_an_import_prototype_without_static_in_a_component(decls, line):
    assert errors("""
component pss_top {
    %s
}
""" % decls) == [(line, "PSS019",
                  "cannot import function 's': a component function must be "
                  "declared 'static' to be imported; instance functions "
                  "cannot be imported (20.4)")]


def test_an_import_prototype_without_static_in_a_component_extension():
    assert [c for _, c, _ in errors("""
component pss_top { }
extend component pss_top { import C function void s(int a); }
""")] == ["PSS019"]


def test_the_name_form_import_of_an_instance_function():
    """CH20/p12."""
    assert errors("""
component pss_top {
    function void s(int a);
    import C function s;
}
""") == [(4, "PSS019",
          "cannot import function 's': it is an instance function of "
          "component 'pss_top', and instance functions cannot be imported "
          "(20.4)")]


def test_a_non_static_import_in_a_template_is_one_report():
    """The template rule is the reason; `static` would not fix it."""
    assert [c for _, c, _ in errors("""
component t_c<int N = 1> {
    import C function int g(int a);
}
component pss_top { t_c<2> t; t_c<3> u; }
""")] == ["PSS019"]


@pytest.mark.parametrize("decls", [
    # G work/f6.
    "component pss_top {\n"
    "    static function void s(int a);\n"
    "    import C static function void s(int a);\n}",
    # `static` on any declaration, including one in an extension, makes the
    # name form legal: it is checked after extensions merge.
    "component pss_top { function void s(int a); }\n"
    "extend component pss_top {\n"
    "    static function void s(int a);\n"
    "    import C function s;\n}",
    # A package function is always static (20.2), with or without the word.
    "package p { import C function void s(int a); }\n"
    "component pss_top { }",
])
def test_imports_of_static_functions(tmp_path, decls):
    assert_links_and_binds(tmp_path, decls)


# ---------------------------------------------------------------------------
# Static members through `comp` (9.1.4.1 f), PSS041
# ---------------------------------------------------------------------------

_COMP = """
component sub_c {
    static function int sst() { return 1; }
    static const int SK = 2;
    function int inst() { return 3; }
}
component my_ip_c {
    import target C static function int st();
    static const int K = 4;
    int fld;
    function int inst_f() { return 5; }
    sub_c sub;
    action a_a {
        int v;
        exec body { v = %s; }
    }
}
component pss_top { my_ip_c ip; }
"""


@pytest.mark.parametrize("expr,msg", [
    # LRM Example 289 with `static` added but the call left as it was.
    ("comp.st()",
     "cannot reach static member 'st' of 'my_ip_c' through 'comp'; name it "
     "without 'comp.', as 'st' (9.1.4.1 f)"),
    ("comp.K",
     "cannot reach static member 'K' of 'my_ip_c' through 'comp'; name it "
     "without 'comp.', as 'K' (9.1.4.1 f)"),
    # Through a sub-component: the plain name would not find it.
    ("comp.sub.sst()",
     "cannot reach static member 'sst' of 'sub_c' through 'comp'; name it "
     "through the type instead, as 'sub_c::sst' (9.1.4.1 f)"),
    ("comp.sub.SK",
     "cannot reach static member 'SK' of 'sub_c' through 'comp'; name it "
     "through the type instead, as 'sub_c::SK' (9.1.4.1 f)"),
])
def test_a_static_member_through_comp(expr, msg):
    assert errors(_COMP % expr) == [(15, "PSS041", msg)]


def test_what_comp_may_reach():
    assert errors(_COMP % (
        "comp.fld + comp.inst_f() + comp.sub.inst()"
        " + st() + K + my_ip_c::st() + sub_c::sst()")) == []


def test_a_static_member_through_comp_in_a_template_is_one_report():
    """Walked once per specialization; the name of a specialization is not
    PSS syntax, so it is not offered."""
    assert errors("""
component t_c<int N = 1> {
    static function int g() { return N; }
    action b_a { int v; exec body { v = comp.g(); } }
}
component pss_top { t_c<2> t; t_c<3> u; }
""") == [(4, "PSS041",
          "cannot reach static member 'g' of 't_c' through 'comp'; name it "
          "without 'comp.', as 'g' (9.1.4.1 f)")]
