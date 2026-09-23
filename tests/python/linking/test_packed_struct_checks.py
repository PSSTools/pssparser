"""The member rules of packed structs (LRM 21.13.1): PSS012 and PSS013.

Before these checks every model in this module linked clean, including the
illegal ones -- see docs/design/packed-struct-checks-plan.md, section 0.

Every rejecting case has a near-miss accepting control beside it, so a check
cannot pass simply by being too broad.
"""
import pytest

from ..test_helpers import parse_collect


def _link(body):
    root, markers = parse_collect("""package p {
    import std_pkg::*;
    import addr_reg_pkg::*;
%s
}
""" % body)
    return root, markers


def _codes(markers):
    return [m.get("code") for m in markers]


def _only(markers, code):
    assert _codes(markers) == [code], "\n".join(
        "%s: %s" % (m.get("code"), m["message"]) for m in markers)
    return markers[0]


# ---------------------------------------------------------------------------
# PSS012: member types
# ---------------------------------------------------------------------------

# (id, declarations, text the message must contain)
_REJECT = [
    ("widthless-enum",
     "enum mode_e {A, B}; struct s : packed_s<> { mode_e f; }",
     "is enum 'mode_e', which has no base type; declare it as 'enum mode_e : bit[N]'"),
    ("string",
     "struct s : packed_s<> { string f; }",
     "is a string, which cannot be packed"),
    ("chandle",
     "struct s : packed_s<> { chandle f; }",
     "is a chandle; use sized_addr_handle_s<SZ> for an address"),
    ("addr_handle_t",
     "struct s : packed_s<> { addr_handle_t f; }",
     "use sized_addr_handle_s<SZ>"),
    ("list",
     "struct s : packed_s<> { list<bit[8]> f; }",
     "is a list; use a fixed-size array"),
    ("map",
     "struct s : packed_s<> { map<bit[8], bit[8]> f; }",
     "is a map"),
    ("set",
     "struct s : packed_s<> { set<bit[8]> f; }",
     "is a set"),
    ("array-of-string",
     "struct s : packed_s<> { string f[4]; }",
     "is an array of a string, which cannot be packed"),
    ("array-of-widthless-enum",
     "enum mode_e {A}; struct s : packed_s<> { array<mode_e, 2> f; }",
     "is an array of enum 'mode_e', which has no base type"),
    ("non-packed-struct",
     "struct q_s { bit[4] a; } struct s : packed_s<> { q_s f; }",
     "is struct 'q_s', which is not packed; derive it from packed_s<>"),
    # R2 / 17.1: a flow object that inherits from a packed struct is not one.
    ("buffer-inheriting-packed",
     "struct pk_s : packed_s<> { bit[4] a; } buffer b_b : pk_s { } "
     "struct s : packed_s<> { b_b f; }",
     "is buffer 'b_b'; a buffer is never packed"),
    # R1: "directly or indirectly".
    ("indirect",
     "struct base_s : packed_s<> { } struct s : base_s { string x; }",
     "field 'x' of packed struct 's' is a string"),
    ("big-endian",
     "struct s : packed_s<BIG_ENDIAN> { string x; }",
     "is a string"),
]

_ACCEPT = [
    ("based-enum",
     "enum mode_e : bit[2] {A, B}; struct s : packed_s<> { mode_e f; }"),
    ("scalars",
     "typedef bit[12] b12_t; "
     "struct s : packed_s<> { bit a; bit[7] b; int c; int[4] d; bool e1; "
     "float32 f; float64 g; b12_t h; bit[4] in [0..9] i; }"),
    ("arrays",
     "enum mode_e : bit[2] {A}; "
     "struct s : packed_s<> { bit[2] a[5]; array<int, 3> b; mode_e c[2]; }"),
    ("nested-packed",
     "struct in_s : packed_s<> { bit[3] a; } struct s : packed_s<> { in_s i; in_s j[2]; }"),
    ("sized-addr-handle",
     "struct s : packed_s<> { sized_addr_handle_s<32> h; }"),
    ("float-storage",
     "struct s : packed_s<> { float32_s f; }"),
    # Q1: static members are not part of the layout.
    ("static-const",
     "struct s : packed_s<> { static const int K = 3; "
     "static const string S = \"x\"; bit[3] a; }"),
    # The same members, but not packed: nothing to check.
    ("not-packed",
     "enum mode_e {A}; struct s { mode_e f; string g; chandle h; list<int> l; }"),
    ("buffer-not-packed",
     "struct pk_s : packed_s<> { bit[4] a; } buffer b_b : pk_s { string x; }"),
]


@pytest.mark.parametrize(
    "decls,expect", [pytest.param(d, e, id=i) for i, d, e in _REJECT])
def test_a_non_packable_member_is_rejected(decls, expect):
    root, markers = _link(decls)
    m = _only(markers, "PSS012")
    assert expect in m["message"]
    assert m["severity"] == "error"
    assert m["line"] > 0


@pytest.mark.parametrize(
    "decls", [pytest.param(d, id=i) for i, d in _ACCEPT])
def test_a_packable_member_is_accepted(decls):
    root, markers = _link(decls)
    assert markers == []
    assert root is not None


def test_the_marker_is_on_the_field_and_points_at_the_enum():
    root, markers = parse_collect(
        "package p {\n"
        "    import std_pkg::*;\n"
        "    enum mode_e {A, B};\n"
        "    struct s : packed_s<> {\n"
        "        bit[2] a;\n"
        "        mode_e f;\n"
        "    }\n"
        "}\n")
    m = _only(markers, "PSS012")
    assert (m["line"], m["col"]) == (6, 9)
    assert [(r["line"], r["label"]) for r in m["related"]] == [(3, "declared here")]


def test_a_nested_culprit_is_reported_once_where_it_is_declared():
    """The inner field is the mistake. The outer field, whose type is a
    perfectly good packed struct, is not reported as well."""
    root, markers = _link(
        "enum mode_e {A}; "
        "struct in_s : packed_s<> { mode_e x; } "
        "struct out_s : packed_s<> { in_s i; in_s j[2]; }")
    m = _only(markers, "PSS012")
    assert "field 'x' of packed struct 'in_s'" in m["message"]


def test_a_type_named_like_packed_s_parameter_is_the_users_type():
    """packed_s is declared `packed_s<endianness_e e>`. Its parameter is not
    visible in a struct derived from it (LRM 10.3), so the user's `e` here is
    the user's enum -- rejected because it has no base type. Before the
    lookup fix it bound to the parameter, and the field was not checked."""
    root, markers = _link("enum e {A}; struct s : packed_s<> { e f; }")
    m = _only(markers, "PSS012")
    assert "is enum 'e', which has no base type" in m["message"]

    root, markers = _link("enum e : bit[2] {A}; struct s : packed_s<> { e f; }")
    assert markers == []


# ---------------------------------------------------------------------------
# Generics: checked per specialization
# ---------------------------------------------------------------------------

_GENERIC = "struct g_s<type T> : packed_s<> { T f; bit[2] pad; }"


def test_an_uninstantiated_packed_generic_is_not_checked():
    root, markers = _link(_GENERIC)
    assert markers == []


def test_a_packable_specialization_is_accepted():
    root, markers = _link(_GENERIC + " struct Top { g_s<bit[4]> a; g_s<bool> b; }")
    assert markers == []


def test_a_non_packable_specialization_is_rejected_once():
    root, markers = _link(
        _GENERIC + " struct Top { g_s<string> a; g_s<string> b; g_s<bit[2]> c; }")
    m = _only(markers, "PSS012")
    assert "field 'f' of packed struct 'g_s' is a string" in m["message"]


def test_two_different_non_packable_arguments_are_both_reported():
    root, markers = _link(
        _GENERIC + " struct Top { g_s<string> a; g_s<chandle> b; }")
    assert _codes(markers) == ["PSS012", "PSS012"]


# ---------------------------------------------------------------------------
# PSS013: type extensions
# ---------------------------------------------------------------------------

def test_an_extension_adding_a_field_is_rejected():
    root, markers = parse_collect(
        "package p {\n"
        "    import std_pkg::*;\n"
        "    struct s : packed_s<> { bit[4] a; }\n"
        "    extend struct s {\n"
        "        bit[4] b;\n"
        "    }\n"
        "}\n")
    m = _only(markers, "PSS013")
    assert m["message"].startswith(
        "type extension of packed struct 's' adds field 'b'")
    assert m["line"] == 5
    assert [(r["line"], r["label"]) for r in m["related"]] == [
        (3, "packed struct declared here")]


def test_an_extension_adding_a_non_packable_field_is_reported_once():
    """The field should not be there at all -- that is the finding. Its type
    is not reported on top of it."""
    root, markers = _link(
        "struct s : packed_s<> { bit[4] a; } extend struct s { string b; }")
    _only(markers, "PSS013")


@pytest.mark.parametrize("ext", [
    pytest.param("constraint { a < 3; }", id="constraint"),
    pytest.param("static const int K = 2;", id="static-const"),
    pytest.param("exec post_solve { }", id="exec"),
])
def test_an_extension_adding_no_field_is_accepted(ext):
    root, markers = _link(
        "struct s : packed_s<> { rand bit[4] a; } extend struct s { %s }" % ext)
    assert markers == []


def test_extending_a_non_packed_struct_with_a_field_is_accepted():
    root, markers = _link("struct s { bit[4] a; } extend struct s { string b; }")
    assert markers == []


def test_an_extension_from_another_package_is_rejected():
    root, markers = parse_collect("""
        package a { import std_pkg::*; struct s : packed_s<> { bit[4] x; } }
        package b { extend struct a::s { bit[2] y; } }
    """)
    m = _only(markers, "PSS013")
    assert "adds field 'y'" in m["message"]


def test_an_extension_of_a_packed_generic_adding_a_field_is_rejected():
    root, markers = _link(
        _GENERIC + " extend struct g_s { bit[1] z; } struct Top { g_s<bit[4]> a; }")
    m = _only(markers, "PSS013")
    assert "packed struct 'g_s' adds field 'z'" in m["message"]


def test_the_sizes_follow_the_same_rules():
    """One predicate: what PSS012 accepts, sizeof_s sizes. (What it rejects
    gets no value -- test_sizeof_values.py covers that, in a model without a
    packed struct, since a model with an error yields no root to inspect.)"""
    from ..template_helpers import sizeof_values
    root, markers = _link(
        "enum good_e : bit[3] {B}; "
        "struct good_s : packed_s<> { good_e f; bool b; } "
        "struct Top { int b = sizeof_s<good_s>::nbits; }")
    assert markers == []
    assert sizeof_values(root)["good_s"] == (4, 1)

    root, markers = _link(
        "enum bad_e {A}; struct bad_s : packed_s<> { bad_e f; } "
        "struct Top { int a = sizeof_s<bad_s>::nbits; }")
    assert _codes(markers) == ["PSS012"]


# ---------------------------------------------------------------------------
# PSS014 / PSS016: register value type and width (21.14.1, 21.14.5)
# ---------------------------------------------------------------------------

def _regs(decls, fields):
    return _link("%s\n    pure component regs_c : reg_group_c { %s }" % (decls, fields))


@pytest.mark.parametrize("decls,fields", [
    pytest.param("struct r_s : packed_s<> { bit[16] a; bit[16] b; }",
                 "reg_c<r_s> r;", id="default-SZ"),
    pytest.param("struct r_s : packed_s<> { bit[16] a; bit[16] b; }",
                 "reg_c<r_s, READWRITE, 32> r;", id="SZ-equals-nbits"),
    pytest.param("struct r_s : packed_s<> { bit[13] a; }",
                 "reg_c<r_s, READWRITE, 32> r;", id="SZ-above-nbits"),
    # Default SZ is 8*nbytes: a 12-bit value type makes a 16-bit register.
    pytest.param("struct r_s : packed_s<> { bit[12] a; }",
                 "reg_c<r_s> r;", id="default-SZ-rounds-to-16"),
    pytest.param("struct r_s : packed_s<> { bit[12] a; }",
                 "reg_c<r_s, READWRITE, 16> r;", id="12-bits-in-16"),
    # Q3: any R whose size can be established.
    pytest.param("", "reg_c<bit[32]> a; reg_c<int[32]> b;", id="scalar-R"),
    pytest.param("enum m_e : bit[8] {A};", "reg_c<m_e> r;", id="based-enum-R"),
])
def test_a_well_formed_register_is_accepted(decls, fields):
    root, markers = _regs(decls, fields)
    assert markers == []


def test_example_360_is_accepted():
    root, markers = _link("""
    struct my_reg0_s : packed_s<> { bit [16] fld0; bit [16] fld1; };
    pure component my_reg0_c : reg_c<my_reg0_s> {}
    struct my_reg1_s : packed_s<> { bit fld0; bit [2] fld1; bit [2] fld2[5]; };
    pure component my_reg1_c : reg_c<my_reg1_s, READWRITE, 32> {}
    pure component regs_c : reg_group_c { my_reg0_c r0; my_reg1_c r1; }
    """)
    assert markers == []


@pytest.mark.parametrize("decls,fields,expect", [
    pytest.param("enum m_e {A};", "reg_c<m_e> r;",
                 "reg_c value type is enum 'm_e', which has no base type",
                 id="widthless-enum-R"),
    pytest.param("", "reg_c<string> r;",
                 "reg_c value type is a string", id="string-R"),
    pytest.param("struct q_s { bit[32] a; }", "reg_c<q_s> r;",
                 "reg_c value type is struct 'q_s', which is not packed",
                 id="non-packed-R"),
    pytest.param("struct r_s : packed_s<> { bit[40] a; }",
                 "reg_c<r_s, READWRITE, 32> r;",
                 "reg_c width SZ = 32 is smaller than its value type 'r_s' "
                 "(40 bits)", id="SZ-below-nbits"),
])
def test_an_ill_formed_register_is_rejected(decls, fields, expect):
    root, markers = _regs(decls, fields)
    m = _only(markers, "PSS014")
    assert expect in m["message"]
    assert m["line"] > 0


def test_a_register_type_is_reported_where_it_is_derived_from():
    """`my_reg_c : reg_c<q_s>` is the use; `my_reg_c r;` is not a second one."""
    root, markers = parse_collect(
        "package p {\n"
        "    import std_pkg::*;\n"
        "    import addr_reg_pkg::*;\n"
        "    struct q_s { bit[32] a; }\n"
        "    pure component my_reg_c : reg_c<q_s> { }\n"
        "    pure component regs_c : reg_group_c { my_reg_c r0; my_reg_c r1; }\n"
        "}\n")
    m = _only(markers, "PSS014")
    assert (m["line"], m["col"]) == (5, 31)
    assert [r["line"] for r in m["related"]] == [4]


def test_a_register_whose_value_type_has_a_bad_member_is_reported_at_the_member():
    root, markers = _regs(
        "enum m_e {A}; struct r_s : packed_s<> { m_e x; }", "reg_c<r_s> r;")
    _only(markers, "PSS012")


@pytest.mark.parametrize("decls,fields,sz", [
    pytest.param("struct r_s : packed_s<> { bit[96] a; }", "reg_c<r_s> r;",
                 96, id="96-bit-default"),
    pytest.param("struct r_s : packed_s<> { bit[8] a; }",
                 "reg_c<r_s, READWRITE, 12> r;", 12, id="explicit-12"),
    pytest.param("struct r_s : packed_s<> { bit[20] a; }", "reg_c<r_s> r;",
                 24, id="20-bit-default-is-24"),
])
def test_a_register_width_without_a_primitive_is_a_warning(decls, fields, sz):
    root, markers = _regs(decls, fields)
    m = _only(markers, "PSS016")
    assert m["severity"] == "warning"
    assert m["message"].startswith(
        "reg_c width SZ = %d has no primitive access function" % sz)
    assert root is not None


def test_a_96_bit_packed_struct_on_its_own_is_fine():
    """The downstream case: a DMA-descriptor-sized packed struct is legal. The
    width only matters when it is a register's value type."""
    root, markers = _link(
        "struct desc_s : packed_s<> { bit[64] addr; bit[32] len; } "
        "struct Top { int n = sizeof_s<desc_s>::nbits; }")
    assert markers == []


# ---------------------------------------------------------------------------
# PSS015: sizeof_s arguments (21.13.2.1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("decls,arg,expect", [
    pytest.param("", "string", "sizeof_s argument is a string, which has no packed size", id="string"),
    pytest.param("", "chandle", "sizeof_s argument is a chandle", id="chandle"),
    pytest.param("enum m_e {A};", "m_e",
                 "sizeof_s argument is enum 'm_e', which has no base type",
                 id="widthless-enum"),
    pytest.param("struct q_s { bit[4] a; }", "q_s",
                 "sizeof_s argument is struct 'q_s', which is not packed",
                 id="non-packed-struct"),
    pytest.param("", "list<bit[8]>", "sizeof_s argument is a list", id="list"),
])
def test_sizeof_of_a_non_packable_type_is_rejected(decls, arg, expect):
    root, markers = _link(
        "%s struct Top { int n = sizeof_s<%s>::nbits; }" % (decls, arg))
    m = _only(markers, "PSS015")
    assert expect in m["message"]


def test_a_qualified_sizeof_is_checked_too():
    root, markers = _link("struct Top { int n = std_pkg::sizeof_s<string>::nbits; }")
    _only(markers, "PSS015")


def test_sizeof_of_a_packed_struct_with_a_bad_member_is_reported_at_the_member():
    root, markers = _link(
        "enum m_e {A}; struct in_s : packed_s<> { m_e x; } "
        "struct Top { int n = sizeof_s<in_s>::nbits; }")
    _only(markers, "PSS012")


def test_sizeof_inside_a_generic_is_checked_per_specialization():
    root, markers = _link(
        "struct g_s<type T> { int n = sizeof_s<T>::nbits; } "
        "struct Top { g_s<bit[4]> a; }")
    assert markers == []
    root, markers = _link(
        "struct g_s<type T> { int n = sizeof_s<T>::nbits; } "
        "struct Top { g_s<string> a; }")
    _only(markers, "PSS015")
