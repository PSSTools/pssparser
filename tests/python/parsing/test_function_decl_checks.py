"""
Function declaration consistency, overrides, generic/varargs parameters and
import/export signature types (pssc front-end checks F11, F14, F15, F26).

- PSS009: `target` on one declaration and `solve` on another (20.3.1,
  20.4.1 b); `const` differing between declarations (20.2.3 c); an override
  of an instance function with another signature, const or default, a
  static shadow of an instance function, a non-pure function made pure
  (20.2, 20.2.3 c, 20.2.4 c, 20.2.6).
- PSS136: a generic or varargs parameter of a user-written function (20.2.5,
  ruling R23).
- PSS137: an import/export parameter or result type the foreign mapping does
  not take; an export's non-const struct parameter (20.4.1 c, 20.4.2.1).
"""
import pytest

import pssparser

from ..test_helpers import _assign_codes


def codes(src):
    p = pssparser.Parser()
    try:
        p.parses([("t.pss", src)])
        p.link()
        ms = p.markers
    except Exception as e:
        ms = getattr(e, "markers", None)
        if ms is None:
            raise
    return [(m["line"], m.get("code")) for m in _assign_codes(ms)]


# -- F14: platform qualifiers -------------------------------------------------

@pytest.mark.parametrize("decls", [
    "target function int f(int x);\n  solve function int f(int x) { return x; }",
    "solve function int f(int x);\n  target function int f(int x) { return x; }",
])
def test_target_and_solve_declarations(decls):
    assert codes("component pss_top {\n  %s\n}\n" % decls) == [(3, "PSS009")]


@pytest.mark.parametrize("decls", [
    # Example 297: an unqualified declaration, a qualified definition, and
    # the other way round.
    "function int f(int x);\n  solve function int f(int x) { return x; }",
    "target function int f(int x);\n  function int f(int x) { return x; }",
    "target function int f(int x);\n  target function int f(int x) { return x; }",
])
def test_compatible_platform_qualifiers(decls):
    assert codes("component pss_top {\n  %s\n}\n" % decls) == []


# -- F15: const and overrides --------------------------------------------------

def test_a_redeclaration_dropping_const():
    assert codes("component pss_top {\n  function int f(const int x);\n"
                 "  function int f(int x) { return x; }\n}\n") == [(2, "PSS009")]


def test_a_redeclaration_keeping_const():
    assert codes("component pss_top {\n  function int f(const int x);\n"
                 "  function int f(const int x) { return x; }\n}\n") == []


BASE = """\
component base_c {
  target function int f(const int x, int y = 2) { return x; }
  static function int s(int x) { return x; }
}
component der_c : base_c {
  %s
}
component pss_top { der_c d; }
"""


@pytest.mark.parametrize("decl", [
    "target function int f(int x, int y = 2) { return x; }",          # const
    "target function int f(const int x, int y = 5) { return x; }",    # default
    "target function int f(const int x) { return x; }",               # arity
    "target function bit[8] f(const int x, int y = 2) { return 0; }", # return
    "static function int f(const int x, int y = 2) { return x; }",    # static shadow
    "pure function int f(const int x, int y = 2) { return x; }",      # made pure
])
def test_an_illegal_override(decl):
    assert codes(BASE % decl) == [(6, "PSS009")]


@pytest.mark.parametrize("decl", [
    "target function int f(const int x, int y = 2) { return x + 1; }",
    "target function int f(const int x, int y) { return x; }",        # default inherited
    "function int s(string t) { return 1; }",                         # a static shadowed freely
    "static function bit[8] s() { return 1; }",
    "function int g(int x) { return x; }",                             # a new function
])
def test_a_legal_override(decl):
    assert codes(BASE % decl) == []


# -- F11: generic and varargs parameters ---------------------------------------

@pytest.mark.parametrize("decl", [
    "target function int f(int k, int ... rest) { return k; }",
    "function int g(struct x) { return 1; }",
    "function void h(struct x);",                        # Example 293, bodiless
    "function string fmt(string f, type ... args);",     # Example 294
    "function void r(ref action a);",
])
def test_a_generic_or_varargs_parameter(decl):
    assert codes("component pss_top {\n  %s\n}\n" % decl) == [(2, "PSS136")]


def test_a_core_library_varargs_call():
    assert codes('import std_pkg::*;\ncomponent pss_top {\n'
                 '  exec init_down { message(LOW, "%d %d", 1, 2); print("%d", 3); }\n'
                 '}\n') == []


# -- F26: import and export types ----------------------------------------------

@pytest.mark.parametrize("decl", [
    "function void put(bit[65] v);\nimport target function put;",
    "function void put(list<string> l);\nimport target function put;",
    "function void put(list<chandle> l);\nimport target function put;",
    "function void put(map<int, int> m);\nimport target function put;",
    "function void put(float64 f);\nimport target function put;",
    "import target function bit[128] get();",
    "struct p_s { int a; }\nfunction int sf(p_s p) { return p.a; }\n"
    "export target function sf;",
    "function int sf(array<int, 2> a) { return a[0]; }\nexport target function sf;",
])
def test_an_illegal_import_or_export_type(decl):
    assert [c for _, c in codes(decl + "\ncomponent pss_top { }\n")] == ["PSS137"]


@pytest.mark.parametrize("decl", [
    "function void put(bit[64] v, int i, bool b, string s, chandle h);\n"
    "import target function put;",
    "enum e_e { A }\nstruct p_s { int a; }\n"
    "function void put(e_e e, p_s p, array<int, 4> a, list<int> l);\n"
    "import target function put;",
    "import target function bit[64] get();",
    "struct p_s { int a; }\nfunction int sf(const p_s p, float64 f) { return p.a; }\n"
    "export target function sf;",
])
def test_a_legal_import_or_export_type(decl):
    assert codes(decl + "\ncomponent pss_top { }\n") == []


def test_an_exported_instance_function_is_not_judged():
    """Exporting a component's instance function is an extension (LINT301);
    20.4.2.1 governs only the static functions 20.4.2 exports."""
    src = ("struct p_s { int a; }\n"
           "component pss_top {\n"
           "  function int f(p_s p) { return p.a; }\n"
           "  export target function f;\n"
           "}\n")
    assert [c for _, c in codes(src)] == ["LINT301"]


def test_an_exported_static_component_function_is_judged():
    src = ("struct p_s { int a; }\n"
           "component pss_top {\n"
           "  static function int f(p_s p) { return p.a; }\n"
           "  export target function f;\n"
           "}\n")
    assert [c for _, c in codes(src)] == ["PSS137"]
