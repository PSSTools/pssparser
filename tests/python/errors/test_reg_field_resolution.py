"""Field names in a masked register write are resolved, not carried (21.14.1).

    regs.csr.write_field("ch_en", 1);

`"ch_en"` names a declared field of the register's value type. The string
spelling is forced by the LRM's own signature -- `write_field(string, bit[SZ])`
-- and 21.14.1 restricts it to a string *literal* precisely so a tool can
resolve it at compile time. It is a name, and resolving names is what this
parser does.

Before this, it did not: `write_field("chan_en", 1)`, one letter wrong, linked
clean and went on to write a register bit nobody asked for. That is the failure
mode worth naming, because nothing about it is visible -- no marker, no
unresolved reference, exit status 0, and a device that misbehaves in simulation
for reasons that look like an RTL bug.

What is deliberately *not* decided here is which bits a resolved field occupies:
`packed_s<>` layout is a target representation (backends order it oppositely on
purpose), so the compiler folds the mask. This answers "which field".
"""
import pytest

from pssparser import ParseException

from ..test_helpers import parse_pss


_MODEL = """
package p {
    import std_pkg::*;
    import addr_reg_pkg::*;

    struct inner_s : packed_s<> { rand bit[4] a; rand bit[4] b; }

    struct csr_s : packed_s<> {
        rand bit[1]  ch_en;
        rand bit[3]  prio;
        rand bit[28] rsvd;
    }
    struct agg_s : packed_s<> {
        rand bit[1]  en;
        inner_s      sub;
        rand bit[23] pad;
    }

    pure component csr_r : reg_c<csr_s, READWRITE, 32> {}
    pure component agg_r : reg_c<agg_s, READWRITE, 32> {}
    pure component raw_r : reg_c<bit[32], READWRITE, 32> {}

    pure component grp_c : reg_group_c {
        csr_r                        csr;
        agg_r                        agg;
        raw_r                        raw;
        reg_c<csr_s, READWRITE, 32>  inline_csr;   // no named type in between
    }

    component top_c {
        grp_c regs;
        target function void f() { %s }
    }
}
"""


def link_error(body: str) -> str:
    with pytest.raises(ParseException) as e:
        parse_pss(_MODEL % body)
    return str(e.value)


def link_ok(body: str) -> None:
    parse_pss(_MODEL % body)


# --- the name must resolve -------------------------------------------------

def test_unknown_field_is_rejected_with_a_suggestion():
    msg = link_error('regs.csr.write_field("chan_en", 1);')
    assert "no field 'chan_en' in register value type 'csr_s'" in msg
    assert "did you mean 'ch_en'?" in msg


def test_unknown_field_with_no_near_match_omits_the_suggestion():
    """A suggestion that is not close is worse than none -- it sends the reader
    to the wrong field."""
    msg = link_error('regs.csr.write_field("zzzzzz", 1);')
    assert "no field 'zzzzzz'" in msg
    assert "did you mean" not in msg


def test_the_error_carries_a_source_location():
    """The whole reason this belongs in the front end rather than downstream:
    the parser knows where the call is."""
    assert "test.pss:" in link_error('regs.csr.write_field("nope", 1);')


# --- 21.14.1's restrictions on the name ------------------------------------

def test_name_must_be_a_string_literal():
    """21.14.1(a). This is the restriction that makes compile-time resolution
    possible at all."""
    msg = link_error('string n; regs.csr.write_field(n, 1);')
    assert "must be a string literal" in msg


def test_name_must_not_be_hierarchical():
    """21.14.1(b): top-level fields only."""
    assert "hierarchical reference" in \
        link_error('regs.agg.write_field("sub.a", 1);')


def test_aggregate_field_is_rejected():
    """21.14.1(c): the value written is a bit vector, so a field that is not
    one cannot receive it."""
    msg = link_error('regs.agg.write_field("sub", 1);')
    assert "composite type" in msg
    assert "scalar fields only" in msg


def test_duplicate_names_in_write_fields():
    """21.14.1(d), and it matters more than it looks: the plural form writes
    its fields in ONE read-modify-write, so naming a field twice does not write
    it twice -- one of the two values is silently lost."""
    msg = link_error('regs.csr.write_fields({"prio","prio"}, {1,2});')
    assert "duplicate field name 'prio'" in msg


def test_names_and_values_must_be_the_same_length():
    assert "2 field name(s) but 1 value(s)" in \
        link_error('regs.csr.write_fields({"ch_en","prio"}, {1});')


def test_write_fields_needs_a_list_literal():
    msg = link_error('list<string> l; regs.csr.write_fields(l, {1});')
    assert "list literal" in msg


def test_register_with_a_scalar_value_type_has_no_named_fields():
    assert "not a struct" in link_error('regs.raw.write_field("x", 1);')


# --- the struct-literal spelling is checked too ----------------------------

def test_unknown_field_in_a_write_masked_literal():
    """`write_masked({.nosuch=1}, ...)` names fields just as directly as
    `write_field` does, and linked clean before this."""
    assert "no field 'nosuch'" in \
        link_error('regs.csr.write_masked({.nosuch=1}, {.nosuch=1});')


def test_duplicate_field_in_a_write_masked_literal():
    assert "duplicate field 'prio' in the mask literal" in \
        link_error('regs.csr.write_masked({.prio=7, .prio=1}, {.prio=2});')


# --- and the legal shapes must still link ----------------------------------

@pytest.mark.parametrize("body", [
    'regs.csr.write_field("ch_en", 1);',
    'regs.csr.write_field("prio", 5);',
    'regs.csr.write_fields({"ch_en","prio"}, {1,2});',
    'regs.csr.write_masked({.prio=7}, {.prio=2});',
    'regs.csr.write_val_masked(1, 1);',
    'regs.raw.write_val_masked(1, 1);',
])
def test_legal_shapes_link_clean(body):
    """A false positive here is a device model that stops compiling, so the
    accepting cases are enumerated as carefully as the rejecting ones."""
    link_ok(body)


def test_an_inline_reg_c_resolves_too():
    """`reg_c<csr_s, ...> inline_csr;` puts no named type between the field and
    the register, where `csr_r` puts one. The walk to the value type has to
    handle both, and this is the case that has no super chain to follow."""
    link_ok('regs.inline_csr.write_field("ch_en", 1);')
    assert "no field 'chan_en'" in \
        link_error('regs.inline_csr.write_field("chan_en", 1);')


def test_a_like_named_method_on_a_user_type_is_not_judged():
    """`write_field` is not a reserved word. A user type may have a method of
    that name, and resolving *its* argument against a register's fields would
    be a false positive on someone else's API."""
    parse_pss("""
        package q {
            component thing_c {
                function void write_field(string name, int val);
                function void g() { write_field("anything at all", 1); }
            }
        }
    """)
