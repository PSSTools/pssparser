"""
Checks of pssc's front-end group 6 (06-front-end-checks F5, F6, F7, F19,
F20, F22, F25, F27, F28, F31), each with a legal neighbour.

- PSS138 an integer width that folds to 0 or less (7.2.1 c, ruling R19).
- PSS139 a division/modulus by a constant zero, a shift by a constant
  negative amount (8.5.1, 8.5.7).
- PSS140 a channel of a type it cannot hold; a DEPTH that is not positive
  (21.9.1).
- PSS141 a register outside a register group; a register type extended
  (21.14.1, 21.14.2).
- PSS142 a rand field or randomize target that is not randomizable (7.1,
  13.4.6, ruling R18).
- PSS143 `yield` in solve code (20.7.14 a, ruling R20).
- PSS144 a call across the solve/target boundary (20.2.1.3, 20.1.2).
- PSS145 an exec of a kind its type does not have (20.1.2); a
  target-template exec of a solve kind (20.5).
- PSS146 a compile if condition referencing a type member (19.1.3 b).
- PSS147 a private/protected field reached from outside (17.4).
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
    return [c for c in (m.get("code") for m in _assign_codes(ms)
                        if m["severity"] == "error")]


def comp(body, pre=""):
    return ("import std_pkg::*;\nimport addr_reg_pkg::*;\nimport sync_pkg::*;\n"
            "%s\ncomponent pss_top {\n%s\n}\n" % (pre, body))


@pytest.mark.parametrize("body,want", [
    # F7
    ("bit[0] v;", ["PSS138"]),
    ("static const int W = 0; bit[W] v;", ["PSS138"]),
    ("static const int W = 1; bit[W - 2] v;", ["PSS138"]),
    ("bit[1] v; static const int W = 4; bit[W] u;", []),
    # F31
    ("target function void run() { int x = 3; int y = x / 0; }", ["PSS139"]),
    ("target function void run() { int x = 3; int y = x % 0; }", ["PSS139"]),
    ("target function void run() { int x = 3; int y = x << -1; }", ["PSS139"]),
    ("static const int Z = 0; target function void run() { int x = 3; int y = x / Z; }",
     ["PSS139"]),
    ("target function void run() { int x = 3; int z = 0; int y = x / z; }", []),
    ("target function void run() { int x = 3; int y = x / 2 + (x << 1); }", []),
    # F28
    ("channel_c<string> ch;", ["PSS140"]),
    ("channel_c<chandle> ch;", ["PSS140"]),
    ("channel_c<bit[8], 0> ch;", ["PSS140"]),
    ("channel_c<bit[8]> ch; channel_c<bool, 2> c2; channel_c<array<int, 2>> c3;", []),
    # F27
    ("reg_c<bit[32], READWRITE, 32> X;", ["PSS141"]),
    # F5
    ("struct s_s { rand chandle h; } s_s v;", ["PSS142"]),
    ("struct t_s { rand float64 f; } t_s v;", ["PSS142"]),
    ("solve function void initialize() { chandle c; randomize c; }", ["PSS142"]),
    ("struct s_s { rand int a; chandle h; } s_s v;", []),
    # F20
    ("solve function void initialize(addr_handle_t base) { yield; }", ["PSS143"]),
    ("exec init_down { yield; }", ["PSS143"]),
    ("function void f() { yield; } target function void run() { f(); yield; }", []),
    # F22, F25
    ("solve function void initialize(addr_handle_t base) { write32(base, 1); }",
     ["PSS144"]),
    ("solve function void initialize(addr_handle_t b) { bit[64] v = addr_value(b); }",
     ["PSS144"]),
    ('target function void run() { int y; if (file_exists("x")) { y = 1; } }',
     ["PSS144"]),
    ('function void ts(int x);\n  target C function void ts(int x) = """foo();""";\n'
     '  exec init_down { ts(1); }', ["PSS144"]),
    ('target function void run(addr_handle_t b) { write32(b, 1); }', []),
    # Held back pending a ruling: the core library's `print` is `solve`
    # (21.1.2), but target-side backends lower it in target code.
    ('action A { exec body { print("x"); } }', []),
    ('solve function void s() { bool e = file_exists("x"); }', []),
    ('function void ts(int x);\n  target C function void ts(int x) = """foo();""";\n'
     '  exec run_start { ts(1); }', []),
    ("exec pre_solve { int x = 1; }", ["PSS145"]),
    ("exec body { int x = 1; }", ["PSS145"]),
    ('exec init_down C = """int y;""";', ["PSS145"]),
    ('exec init_down { int x = 1; } exec run_start C = """int y;""";', []),
    # F6
    ("struct p_s { public int a; private int b; }\n"
     "  target function void run() { p_s v; v.b = 2; }", ["PSS147"]),
    ("struct p_s { protected int b; }\n"
     "  target function void run() { p_s v; int y = v.b; }", ["PSS147"]),
    ("struct p_s { public int a; private int b; }\n"
     "  target function void run() { p_s v; v.a = 2; }", []),
])
def test_check(body, want):
    assert codes(comp(body)) == want


def test_a_private_member_of_another_component():
    assert codes(comp("sib_c s;\n  target function void run() "
                      "{ message(LOW, \"%d\", s.x); }",
                      "component sib_c { private int x = 4; }")) == ["PSS147"]


def test_a_private_member_from_its_own_type():
    assert codes(comp("", "struct p_s { private int b; "
                          "exec post_solve { p_s o; o.b = b; } }")) == []


def test_a_protected_member_from_a_derived_type():
    assert codes(comp("", "struct b_s { protected int b; }\n"
                          "struct d_s : b_s { exec post_solve { d_s o; o.b = 1; } }")) == []


def test_a_register_in_a_register_group():
    assert codes(comp("regs_c r;", "pure component regs_c : reg_group_c {\n"
                      "  reg_c<bit[32], READWRITE, 32> X;\n"
                      "  function bit[64] get_offset_of_instance(string name) "
                      "{ return 0; }\n}")) == []


@pytest.mark.parametrize("ext", ["reg_group_c", "reg_c"])
def test_extending_a_register_type(ext):
    assert codes(comp("", "extend component %s { int q; }" % ext)) == ["PSS141"]


def test_compile_if_on_a_type_constant():
    assert codes("component pss_top { static const int LOC = 1;\n"
                 "  compile if (pss_top::LOC == 1) { int z; } }\n") == ["PSS146"]


def test_compile_if_on_a_package_constant():
    assert codes("package k { static const int LOC = 1; }\n"
                 "component pss_top {\n"
                 "  compile if (k::LOC == 1) { int z; } }\n") == []
