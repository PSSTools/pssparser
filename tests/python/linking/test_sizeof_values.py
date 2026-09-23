"""The values ``sizeof_s<T>`` computes, checked against the spec.

Until this module, no test asserted a ``sizeof_s`` value -- only that a use of
it linked. ``reg_c<R>``'s default width is ``8*sizeof_s<R>::nbytes``, so a wrong
value here silently sizes a register wrong.

Expected values come from the spec wherever it gives one:

- 21.13.2.2 -- ``int``, ``int[4]``, ``bit``, ``bit[33]``, ``array<int,10>``,
  ``{bit[2] kind; int data;}``
- 21.13.1.2 -- Example 344, 30 bits in 4 bytes
- 21.14.1 -- Example 360, ``my_reg1_s`` is 13 bits

and otherwise from the rules in 21.13.1 (see
docs/design/packed-struct-checks-plan.md, section 1). A non-packable argument
(21.13.2.1) has no size: the members are left uncomputed rather than given a
made-up number, and the use is reported (PSS015).
"""
import pytest

from ..test_helpers import parse_collect
from ..template_helpers import sizeof_values


_TYPES = """
package p {
    import std_pkg::*;
    import addr_reg_pkg::*;

    enum plain_e { PA, PB };
    enum based_e : bit[2] { BA, BB };
    typedef bit[12] b12_t;

    struct kd_s : packed_s<> { bit[2] kind; int data; }

    // Example 344
    struct ex344_s : packed_s<LITTLE_ENDIAN> {
        bit[6] A; bit[2] B; bit[9] C; bit[7] D; bit[6] E;
    }

    // Example 360
    struct my_reg1_s : packed_s<> {
        bit     fld0;
        bit [2] fld1;
        bit [2] fld2[5];
    }

    struct base_s : packed_s<> { bit[3] x; }
    struct derived_s : base_s { bit[5] y; }
    struct static_s : packed_s<> { static const int K = 3; bit[4] a; }
    struct nested_s : packed_s<> { kd_s inner; bool b; }
    struct benum_s : packed_s<> { based_e e; bit[6] pad; }
    struct flt_s : packed_s<> { float32 f; float64 d; }
    struct arr_s : packed_s<> { array<bit[4],3> a; }
    struct addr_s : packed_s<> { sized_addr_handle_s<32> h; }

    struct Top {
%s
    }
}
"""


def _sizes(*args):
    body = "\n".join(
        "        int v%d = sizeof_s<%s>::nbits;" % (i, a)
        for i, a in enumerate(args))
    root, markers = parse_collect(_TYPES % body)
    assert root is not None, markers
    return sizeof_values(root), markers


# (argument, description as sizeof_values reports it, nbits, nbytes)
_SPEC = [
    # 21.13.2.2
    ("int",             "int",              32, 4),
    ("int[4]",          "int[4]",           4,  1),
    ("bit",             "bit",              1,  1),
    ("bit[33]",         "bit[33]",          33, 5),
    ("array<int,10>",   None,               320, 40),
    ("kd_s",            "kd_s",             34, 5),
    # Example 344, Example 360
    ("ex344_s",         "ex344_s",          30, 4),
    ("my_reg1_s",       "my_reg1_s",        13, 2),
]

_RULES = [
    ("bool",            "bool",             1,  1),
    ("b12_t",           None,               12, 2),
    ("based_e",         "based_e",          2,  1),
    ("float32",         "float32",          32, 4),
    ("float64",         "float64",          64, 8),
    ("nested_s",        "nested_s",         35, 5),
    ("benum_s",         "benum_s",          8,  1),
    ("flt_s",           "flt_s",            96, 12),
    ("arr_s",           "arr_s",            12, 2),
    ("derived_s",       "derived_s",        8,  1),
    ("static_s",        "static_s",         4,  1),
    # R10: the handle's packed width is SZ, not the width of its chandle.
    ("addr_s",          "addr_s",           32, 4),
]

# Not packable (21.13.2.1): no value.
_NONE = [
    ("plain_e",         "plain_e"),
    ("string",          "string"),
    ("chandle",         "chandle"),
]


# Before Phase 1 of the plan every row below except `int` was wrong (plan
# section 2.2, S1-S8): nbytes truncated, enums and floats and arrays counted
# as 0, inherited fields dropped, static fields counted, and non-packable
# types given a value.

def _param(arg, *rest):
    return pytest.param(arg, *rest, id=arg)


def _lookup(values, arg, desc):
    if desc is not None:
        assert desc in values, "no sizeof_s<%s> specialization in %r" % (
            arg, sorted(values))
        return values[desc]
    # The argument describes differently (a typedef describes as its
    # target, array<> by kind): with one use in the model, take the only
    # specialization the model created.
    assert len(values) == 1, sorted(values)
    return next(iter(values.values()))


@pytest.mark.parametrize(
    "arg,desc,nbits,nbytes",
    [_param(*r) for r in _SPEC + _RULES])
def test_sizeof_value(arg, desc, nbits, nbytes):
    values, _ = _sizes(arg)
    assert _lookup(values, arg, desc) == (nbits, nbytes)


@pytest.mark.parametrize(
    "arg,desc", [_param(*r) for r in _NONE])
def test_sizeof_of_a_non_packable_type_is_rejected(arg, desc):
    """21.13.2.1. Such a specialization is also left without a value -- the
    linker no longer invents one -- but a model with an error yields no root
    to read it from, so the diagnostic is what is asserted here."""
    root, markers = parse_collect(_TYPES % (
        "        int v0 = sizeof_s<%s>::nbits;" % arg))
    assert [m.get("code") for m in markers] == ["PSS015"], markers
    assert markers[0]["message"].startswith("sizeof_s argument is ")


def test_nbytes_is_the_register_width_divided_by_8_rounded_up():
    """R16, stated directly: every computed value obeys it."""
    values, _ = _sizes("bit[1]", "bit[7]", "bit[8]", "bit[9]", "bit[64]",
                       "bit[65]")
    for desc, (nbits, nbytes) in values.items():
        if nbits is None:
            continue
        assert nbytes == (nbits + 7) // 8, (desc, nbits, nbytes)


def test_a_type_declared_after_the_use_is_sized():
    """Declaration order must not matter: the member types of a struct named
    before it is declared are sized all the same, not left incomplete."""
    root, markers = parse_collect("""
        package p {
            import std_pkg::*;
            struct Top { int n = sizeof_s<late_s>::nbits; }
            struct late_s : packed_s<> { bit[2] a; mid_s m; }
            struct mid_s : packed_s<> { bit[5] b; }
        }
    """)
    assert root is not None, markers
    assert sizeof_values(root)["late_s"] == (7, 1)


def test_a_packed_generic_is_sized_per_specialization():
    root, markers = parse_collect("""
        package p {
            import std_pkg::*;
            struct g_s<type T, int N = 3> : packed_s<> { T v; bit[N] w; }
            struct Top {
                int a = sizeof_s<g_s<bit[4]> >::nbits;
                int b = sizeof_s<g_s<bool, 7> >::nbits;
            }
        }
    """)
    assert root is not None, markers
    got = sorted(v for v in sizeof_values(root).values())
    assert got == [(7, 1), (8, 1)]


def test_the_core_float_storage_types_are_sized():
    """float32_s is float_base_s<23,8>: 23 + 8 + 1 bits (21.5)."""
    root, markers = parse_collect("""
        package p {
            import std_pkg::*;
            struct Top {
                int a = sizeof_s<float32_s>::nbits;
                int b = sizeof_s<float64_s>::nbits;
            }
        }
    """)
    assert root is not None, markers
    got = sorted(v for v in sizeof_values(root).values())
    assert got == [(32, 4), (64, 8)]


def test_a_package_qualified_sizeof_is_specialized():
    """`std_pkg::sizeof_s<T>::nbits` used to bind the generic's own member --
    the placeholder -1 -- because only the first element of a static path had
    its template arguments applied."""
    root, markers = parse_collect("""
        package p {
            import std_pkg::*;
            struct k_s : packed_s<> { bit[2] kind; int data; }
            struct Top { int n = std_pkg::sizeof_s<k_s>::nbytes; }
        }
    """)
    assert root is not None, markers
    assert sizeof_values(root) == {"k_s": (34, 5)}
