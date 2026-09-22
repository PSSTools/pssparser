"""The built-in core library, checked against Annex C of PSS 3.1.

Annex C (pp. 529-535 of the 2026-08-28 Public Review Draft) is the normative
listing of ``std_pkg``, ``executor_pkg``, ``addr_reg_pkg`` and ``sync_pkg``,
and it states that it takes precedence over the core-library material anywhere
else in the standard -- including the Syntax boxes in Clause 21.  These tests
assert that each Annex C declaration is *present and resolvable from user
code*, which is the property nothing else in the suite notices: a missing
core-library symbol produces no failure until somebody writes a model that
uses it.

Deliberately *not* asserted here:

* **Types of float fields.**  ``pyastbuilder`` has no ``DataTypeFloat``
  (known-issues P1-G2a), so a consumer reading ``float64 f;`` still gets a
  null-typed field.  The declarations link; what a downstream reader makes of
  them is a separate defect.
* **Qualifier enforcement.**  Whether calling a ``solve function`` from a
  target ``exec`` is rejected is the business of
  ``tests/python/errors/test_function_qualifiers.py``.  Here the question is
  only whether the declaration exists with the qualifier Annex C gives it.

See ``docs/design/core-library-conformance-plan.md``.
"""
import pytest

from ..isolation import assert_clean, assert_rejects, run_isolated


def _uses(body, imports="import std_pkg::*;"):
    """A package that imports the core library and exercises *body*."""
    return [("t.pss", """
        package u {
            %s
            %s
        }
        """ % (imports, body))]


# ---------------------------------------------------------------------------
# std_pkg 21.2 -- file operations
# ---------------------------------------------------------------------------

def test_file_api_types_resolve():
    """``file_handle_t``, ``nullfilehandle`` and ``file_option_e``."""
    assert_clean(_uses("""
        function void f() {
            file_handle_t h = nullfilehandle;
            file_option_e o = TRUNCATE;
            o = APPEND;
            o = READ;
        }
    """))


@pytest.mark.parametrize("call", [
    'file_handle_t h = file_open("f.txt", TRUNCATE);',
    'file_close(nullfilehandle);',
    'bool e = file_exists("f.txt");',
    'file_write(nullfilehandle, "x=%d", 1);',
    'string s = file_read(nullfilehandle);',          # size defaults to -1
    'string s = file_read(nullfilehandle, 10);',
    'file_write_lines("f.txt", lines, APPEND);',
    'list<string> l = file_read_lines("f.txt");',
])
def test_file_functions_are_callable(call):
    assert_clean(_uses("""
        function void f() {
            list<string> lines;
            %s
        }
    """ % call))


# ---------------------------------------------------------------------------
# std_pkg 21.3 -- error reporting
# ---------------------------------------------------------------------------

def test_error_and_fatal_are_callable():
    """``error`` was the reported gap: normative in 21.3, absent from the tree.

    Neither is ``solve``- or ``target``-qualified in Annex C, so both are
    callable from a plain function.
    """
    assert_clean(_uses("""
        function void f() {
            error("bad value %d", 1);
            fatal(1, "giving up on %s", "x");
        }
    """))


# ---------------------------------------------------------------------------
# std_pkg 21.5 -- floating point
# ---------------------------------------------------------------------------

def test_float_storage_types_resolve():
    assert_clean(_uses("""
        struct s : float_base_s<23, 8> { }
        struct t {
            float32_s a;
            float64_s b;
        }
    """))


#: Every one-argument math function in Annex C, in annex order.
_UNARY_MATH = [
    "log", "log10", "exp", "sqrt", "round", "floor", "ceil",
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sinh", "cosh", "tanh", "asinh", "acosh", "atanh",
]


@pytest.mark.parametrize("fn", _UNARY_MATH)
def test_unary_math_function_is_callable(fn):
    assert_clean(_uses("""
        pure function float64 f(float64 x) {
            return %s(x);
        }
    """ % fn))


@pytest.mark.parametrize("call", ["pow(x, y)", "atan2(x, y)", "hypot(x, y)"])
def test_binary_math_function_is_callable(call):
    """The three two-argument functions.

    Kept separate from the unary list because getting an arity wrong here is
    invisible until somebody calls it -- which is exactly how the gap this
    suite closes went unnoticed.
    """
    assert_clean(_uses("""
        pure function float64 f(float64 x, float64 y) {
            return %s;
        }
    """ % call))


def test_float_decomposition_functions_are_callable():
    assert_clean(_uses("""
        pure function float64 f(float64 v) {
            bit[52] m = float_mantissa(v);
            bit[11] e = float_exponent(v);
            bit     s = float_sign(v);
            return to_float(m, e, s);
        }
    """))


# ---------------------------------------------------------------------------
# executor_pkg
# ---------------------------------------------------------------------------

def test_get_context_is_declared_on_executor_base_c():
    """21.7.1.1.1 -- the item that prompted the conformance review.

    An exported function's foreign realization uses it to identify the
    executor context it is running in (Annex D.1.1).
    """
    assert_clean(_uses("""
        component c : executor_base_c {
            function chandle f() {
                return get_context();
            }
        }
    """, imports="import executor_pkg::*;"))


def test_target_execution_unit_api_resolves():
    """All of 21.8."""
    assert_clean(_uses("""
        component c {
            target_execution_unit_c tu;
            exec init_down {
                tu.set_filename("out.c");
                tu.set_target_language(C);
                tu.set_target_language(CPP);
                tu.set_target_language(SV);
            }
        }
        function void g(ref target_execution_unit_c u) {
            string          fn = u.get_filename();
            target_language_e l = u.get_target_language();
        }
    """, imports="import executor_pkg::*;"))


def test_executor_target_execution_unit_accessors_resolve():
    assert_clean(_uses("""
        component c : executor_base_c {
            target_execution_unit_c tu;
            exec init_down {
                set_target_execution_unit(tu);
            }
        }
    """, imports="import executor_pkg::*;"))


def test_set_executor_is_callable():
    """Syntax 131.  ``executor()`` was already present; its setter was not.

    Adding the declaration was necessary but not sufficient: a parameterless
    ``set_executor`` was injected into every base-less component and won the
    lookup here, inside the ``exec init_down`` block where 21.7.2.6 puts the
    call.  Removing that injection is what makes this pass (CL-S3).
    """
    assert_clean(_uses("""
        component c {
            executor_c<> e;
            exec init_down {
                set_executor(e);
            }
        }
    """, imports="import executor_pkg::*;"))


def test_add_executor_takes_a_reference_to_the_parameterized_executor():
    """Annex C: ``solve function void add_executor(ref executor_c<TRAIT> exe);``

    The tree carried ``executor_base_c exe`` instead, behind a ``// TODO:``
    saying the Annex C form did not work.  It does.
    """
    assert_clean(_uses("""
        struct my_trait_s : executor_trait_s { int x; }
        component c {
            executor_group_c<my_trait_s> grp;
            executor_c<my_trait_s>       exe;
            exec init_down {
                grp.add_executor(exe);
            }
        }
    """, imports="import executor_pkg::*;"))


def test_executor_pkg_does_not_import_addr_reg_pkg():
    """Annex C has the dependency one way only.

    ``addr_reg_pkg`` imports ``executor_pkg``; the reverse import the tree
    carried made the two packages mutually dependent.  Asserted by observing
    that an ``addr_reg_pkg`` name is *not* reachable through an
    ``executor_pkg`` wildcard import.
    """
    from ..isolation import assert_rejects
    assert_rejects(_uses("""
        component c {
            addr_trait_s t;
        }
    """, imports="import executor_pkg::*;"), "addr_trait_s")


# ---------------------------------------------------------------------------
# addr_reg_pkg
# ---------------------------------------------------------------------------

def test_region_tag_and_get_tag_resolve():
    assert_clean(_uses("""
        function string f(addr_handle_t h) {
            addr_region_base_s r;
            r.tag = "region";
            return get_tag(h);
        }
    """, imports="import addr_reg_pkg::*;"))


def test_allocation_mode_types_resolve():
    """21.11.  Declared in Pass 1; wired into ``addr_claim_s`` in Pass 2."""
    assert_clean(_uses("""
        struct s {
            rand alloc_base_mode_s   m;
            rand alloc_access_mode_e a;
            rand alloc_share_mode_e  sh;
            rand alloc_skip_mode_e   sk;
            constraint {
                a  in [EXCLUSIVE, SHARED];
                sh in [RANDOM, OVERLAP, SAME_ADDRESS];
                sk in [DONT_SKIP, SKIP];
            }
        }
    """, imports="import addr_reg_pkg::*;"))


def test_mem_access_desc_s_resolves_and_is_extensible():
    """21.13.9.  Empty by design -- the point is that it is extended."""
    assert_clean(_uses("""
        extend struct mem_access_desc_s {
            int priority;
        }
    """, imports="import addr_reg_pkg::*;"))


@pytest.mark.parametrize("call", [
    "bit[64] v = addr_value(h);",
    "bit[64] v = addr_value_solve(h);",
    "bool    b = addr_value_abs(h);",
])
def test_address_value_functions_are_callable(call):
    """``addr_value_solve`` and ``addr_value_abs`` were both missing."""
    assert_clean(_uses("""
        function void f(addr_handle_t h) {
            %s
        }
    """ % call, imports="import addr_reg_pkg::*;"))


@pytest.mark.parametrize("call", [
    "bit[8]  a = read8(h);",
    "bit[16] b = read16(h);",
    "bit[32] c = read32(h);",
    "bit[64] d = read64(h);",
    "write8(h, 8'h1);",
    "write16(h, 16'h1);",
    "write32(h, 32'h1);",
    "write64(h, 64'h1);",
    "read_bytes(h, data, 4);",
    "write_bytes(h, data);",
])
def test_access_functions_still_accept_their_old_call_sites(call):
    """The ``mem_access_desc`` parameter is *defaulted*, hence additive.

    This is the test that makes "Pass 1 breaks no existing source" concrete:
    every one of these calls omits the new trailing argument.
    """
    assert_clean(_uses("""
        function void f(addr_handle_t h) {
            list<bit[8]> data;
            %s
        }
    """ % call, imports="import addr_reg_pkg::*;"))


def test_access_functions_accept_an_explicit_descriptor():
    assert_clean(_uses("""
        function void f(addr_handle_t h) {
            mem_access_desc_s d;
            bit[32] v = read32(h, d);
            write32(h, 32'h1, d);
        }
    """, imports="import addr_reg_pkg::*;"))


def test_make_handle_from_handle_takes_the_sub_parameter():
    """Additive: the third parameter is defaulted, so the two-argument call
    that the tree supported still works."""
    assert_clean(_uses("""
        function void f(addr_handle_t h) {
            addr_handle_t a = make_handle_from_handle(h, 64'h10);
            addr_handle_t b = make_handle_from_handle(h, 64'h10, true);
        }
    """, imports="import addr_reg_pkg::*;"))


@pytest.mark.parametrize("call", [
    "bit[64] v = comp.e.addr_value(h);",
    "bit[64] v = comp.e.addr_value_solve(h);",
    "bool    b = comp.e.addr_value_abs(h);",
    "bit[8]  a = comp.e.read8(h);",
    "bit[16] b = comp.e.read16(h);",
    "bit[32] c = comp.e.read32(h);",
    "bit[64] d = comp.e.read64(h);",
    "comp.e.write8(h, 8'h1);",
    "comp.e.write16(h, 16'h1);",
    "comp.e.write32(h, 32'h1);",
    "comp.e.write64(h, 64'h1);",
    "comp.e.read_bytes(h, data, 4);",
    "comp.e.write_bytes(h, data);",
])
def test_the_access_api_is_available_on_an_executor(call):
    """Annex C's ``extend component executor_base_c`` block.

    This is what lets an access be directed at a specific executor rather
    than at the default one. It was commented out of ``addr_reg_pkg.pss``
    because it could not link: the block lives in ``addr_reg_pkg`` and names
    ``addr_handle_t`` and ``mem_access_desc_s``, which are declared in that
    same package, but an extension body resolved against the *extended*
    type's package (``executor_pkg``) -- known-issues CL-N1.

    Annex C's block deliberately excludes ``read_struct``/``write_struct``,
    so they are not listed here.
    """
    assert_clean(_uses("""
        component c {
            executor_c<> e;
            action a {
                exec body {
                    addr_handle_t h;
                    list<bit[8]>  data;
                    %s
                }
            }
        }
    """ % call, imports="""
        import addr_reg_pkg::*;
        import executor_pkg::*;
    """))


def test_reg_group_get_handle_resolves():
    assert_clean(_uses("""
        component c : reg_group_c {
            function addr_handle_t f() {
                return get_handle();
            }
        }
    """, imports="import addr_reg_pkg::*;"))


# ---------------------------------------------------------------------------
# sync_pkg
# ---------------------------------------------------------------------------

def test_channel_element_parameter_is_named_T():
    """Syntax 133 names it ``T``; the tree called it ``Te``.

    Instantiation is positional, so the rename is invisible to callers -- but
    the name shows up in diagnostics and in the AST, which is what this pins.
    """
    assert_clean(_uses("""
        struct item_s { int v; }
        component c {
            channel_c<item_s, 4> ch;
        }
    """, imports="import sync_pkg::*;"))


def test_channel_target_functions_resolve():
    assert_clean(_uses("""
        struct item_s { int v; }
        component c {
            channel_c<item_s> ch;
            action a {
                exec body {
                    item_s i;
                    comp.ch.put(i);
                    i = comp.ch.get();
                    bool ok = comp.ch.try_put(i);
                    ok = comp.ch.try_get(i);
                }
            }
        }
    """, imports="import sync_pkg::*;"))


# ---------------------------------------------------------------------------
# Pass 2 -- source-breaking corrections
# ---------------------------------------------------------------------------

def test_addr_claim_s_carries_the_alloc_mode_parameter():
    """21.11.  ``ALLOC_MODE`` is defaulted, so the one-argument form still
    works; what changes is that ``alloc_mode`` now exists as a field."""
    assert_clean(_uses("""
        struct my_trait_s : addr_trait_s { int x; }
        struct my_mode_s  : alloc_base_mode_s { }
        component c {
            action a {
                rand addr_claim_s<my_trait_s>            c1;
                rand addr_claim_s<my_trait_s, my_mode_s> c2;
                constraint {
                    c1.alloc_mode.access  == EXCLUSIVE;
                    c2.alloc_mode.sharing == RANDOM;
                }
            }
        }
    """, imports="import addr_reg_pkg::*;"))


def test_transparent_addr_claim_s_forwards_both_parameters():
    assert_clean(_uses("""
        struct my_trait_s : addr_trait_s { int x; }
        struct my_mode_s  : alloc_base_mode_s { }
        component c {
            action a {
                rand transparent_addr_claim_s<my_trait_s>            t1;
                rand transparent_addr_claim_s<my_trait_s, my_mode_s> t2;
                constraint { t1.addr == 64'h0; t2.alloc_mode.access == SHARED; }
            }
        }
    """, imports="import addr_reg_pkg::*;"))


def test_add_nonallocatable_region_takes_an_untraited_region():
    """Annex C writes ``addr_region_s <> r``, not ``addr_region_s<TRAIT> r``:
    a non-allocatable region carries no trait constraint.

    This also pins that the empty argument list specializes to the declared
    defaults, which the plan flagged as needing confirmation rather than
    assumption."""
    assert_clean(_uses("""
        struct my_trait_s : addr_trait_s { int x; }
        component c {
            contiguous_addr_space_c<my_trait_s> aspace;
            exec init_down {
                addr_region_s<my_trait_s> r;
                addr_region_s<>           nr;
                addr_handle_t h1 = aspace.add_region(r);
                addr_handle_t h2 = aspace.add_nonallocatable_region(nr);
            }
        }
    """, imports="import addr_reg_pkg::*;"))


@pytest.mark.parametrize("decl,use", [
    # O2: the core library is Annex C plus `format_string`, nothing else.
    ("std_pkg",      "actor_c<c, a> x;"),
    ("executor_pkg", "executor_group_default_c g;"),
])
def test_a_removed_non_standard_extra_is_gone(decl, use):
    """`actor_c` and `executor_group_default_c` are not in the 3.1 core
    library at all and were removed; see the plan's O2."""
    from ..isolation import assert_rejects
    assert_rejects(_uses("""
        component c { action a { } }
        component holder { %s }
    """ % use, imports="import %s::*;" % decl), "unknown type")


def test_the_channel_actions_are_gone():
    """Syntax 133 declares four target functions and no actions."""
    from ..isolation import assert_rejects
    assert_rejects(_uses("""
        struct item_s { int v; }
        component c {
            channel_c<item_s> ch;
            action a {
                channel_c<item_s>::put_a p;
            }
        }
    """, imports="import sync_pkg::*;"))


def test_format_string_is_kept():
    """The one deliberate departure from Annex C.

    Not a member of `std_pkg` in the standard -- it appears only in Example
    294 -- but retained, marked non-standard, by the O2 decision."""
    assert_clean(_uses("""
        function string f() {
            return format_string("%d", 2);
        }
    """))


# ---------------------------------------------------------------------------
# The four packages together
# ---------------------------------------------------------------------------

def test_all_four_core_packages_import_together():
    """Wildcard-importing all four at once must not collide.

    ``sizeof_s`` is the one that could: it is declared in ``std_pkg`` and
    re-exported through ``addr_reg_pkg``'s import of it, which 21.13.2
    requires to behave "as if they were the same type".
    """
    assert_clean(_uses("""
        struct r_s : packed_s<> { bit[32] f; }
        component c {
            reg_c<r_s> r;
        }
        const int n = sizeof_s<r_s>::nbytes;
    """, imports="""
        import std_pkg::*;
        import executor_pkg::*;
        import addr_reg_pkg::*;
        import sync_pkg::*;
    """))


# ---------------------------------------------------------------------------
# The core library is *not* implicitly visible (CL-S2)
# ---------------------------------------------------------------------------
#
# Clause 21 declares the core library in four packages and gives them no
# special visibility; the only sentence that reads otherwise -- "example code
# may omit importing core library packages for brevity" (21, intro) -- is about
# the document's own examples, not about what a tool shall accept.  Until
# 2026-09-22 this parser made `std_pkg` visible at the root scope, so a model
# that omitted the import parsed here and failed on a conforming tool.
#
# The diagnostic names the package to import rather than claiming the name does
# not exist, because it does exist -- just not where the model looked.

@pytest.mark.parametrize("pkg,body", [
    ("std_pkg",      'component c { exec init_up { print("x"); } }'),
    ("std_pkg",      'component c { function void f() { bit[32] v = urandom(); } }'),
    ("std_pkg",      'struct s : packed_s<> { bit[32] v; }'),
    ("executor_pkg", 'component c { executor_c<int> e; }'),
    ("addr_reg_pkg", 'component c { addr_space_base_c s; }'),
    ("sync_pkg",     'component c { channel_c<int> ch; }'),
])
def test_a_core_library_name_needs_its_import(pkg, body):
    """Without the import the name does not resolve, and the error says which
    import is missing."""
    assert_rejects([("t.pss", body)], "add 'import %s::*;'" % pkg)


@pytest.mark.parametrize("pkg,body", [
    ("std_pkg",      'component c { exec init_up { print("x"); } }'),
    ("std_pkg",      'component c { function void f() { bit[32] v = urandom(); } }'),
    ("std_pkg",      'struct s : packed_s<> { bit[32] v; }'),
    ("executor_pkg", 'component c { executor_c<int> e; }'),
    ("addr_reg_pkg", 'component c { addr_space_base_c s; }'),
    ("sync_pkg",     'component c { channel_c<int> ch; }'),
])
def test_the_same_source_links_once_the_import_is_added(pkg, body):
    """The control: the import is the only thing missing above."""
    assert_clean([("t.pss", "import %s::*;\n%s" % (pkg, body))])


def test_a_standard_annotation_needs_its_import():
    """@doc and @code_doc are std_pkg declarations like any other.

    An unknown annotation is a warning, not an error (7.13 requires tools to
    disregard unrecognized annotations), so this checks the message rather
    than the exit status.
    """
    res = run_isolated([("t.pss", """
        component c {
            @doc {.text = "documented"}
            int a;
        }
    """)])
    assert "add 'import std_pkg::*;'" in res.output, res.describe()


def test_an_ordinary_unknown_name_is_not_blamed_on_a_missing_import():
    """The suggestion is reserved for names that really are core-library ones."""
    res = assert_rejects(
        [("t.pss", "component c { exec init_up { nosuch_fn(1); } }")],
        "unknown identifier 'nosuch_fn'")
    assert "import" not in res.output, res.describe()
