from ..test_helpers import assert_parse_ok


def test_equivalent_specializations_link_cleanly():
    root = assert_parse_ok(
        """
        package p {
            struct Q<type T> {
                rand T v1;
            }
            struct Top {
                Q<int> v1;
                Q<int> v2;
            }
        }
        """
    )
    assert root is not None


def test_specialized_default_value_param_resolves():
    root = assert_parse_ok(
        """
        package p {
            struct sz_t<type T> {
                static const int xz;
            }

            struct Q<type R, int SZ=sz_t<R>::xz> {
                rand R v1;
            }

            struct Top {
                Q<int> v1;
            }
        }
        """
    )
    assert root is not None


def test_sizeof_scalar_template_reference():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;
        import std_pkg::*;

        component pss_top {
            int sz = sizeof_s<int>::nbits;
        }
        """
    )
    assert root is not None


def test_sizeof_packed_struct_template_reference():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;
        import std_pkg::*;
        struct R : packed_s<> {
            bit[8] a;
            bit[8] b;
            bit[8] c;
        }

        component pss_top {
            int sz2 = sizeof_s<R>::nbits;
        }
        """
    )
    assert root is not None


def test_reg_c_template_specialization_links():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;
        import std_pkg::*;

        pure component my_regs : reg_group_c {
            reg_c<int> r1;
        }

        component pss_top {
            my_regs regs;
        }
        """
    )
    assert root is not None


def test_nested_template_specializations_link():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;
        import std_pkg::*;

        struct addr_region_s<struct TRAIT : addr_trait_s = empty_addr_trait_s> {
            TRAIT trait;
        }

        component pss_top {
            addr_region_s<> r1;
        }
        """
    )
    assert root is not None


def test_a_base_types_template_parameter_is_not_visible_in_a_subtype():
    """LRM 10.3: "A template parameter may not be referenced from within
    subtypes that inherit from the template type that originally defined the
    parameter." So `e` in `s` is the package's enum, not b's parameter `e`.

    The lookup used to search the base type's parameter list on its way up
    the super chain, and found the parameter first. Every packed struct
    inherits `packed_s<endianness_e e>`, which is how this surfaced.
    """
    from pssparser.core import resolveSymbolPathRef
    from ..template_helpers import lookup
    root = assert_parse_ok(
        """
        package p {
            struct b<int e = 1> { }
            enum e : bit[3] { A, B };
            struct s : b<> { e f; }
        }
        """
    )
    f = lookup(root, "p::s").getChild(0)
    target = resolveSymbolPathRef(root, f.getType().getType_id().getTarget())
    assert target == lookup(root, "p::e")


def test_a_types_own_template_parameter_is_still_visible():
    """Control for the test above: the fix is scoped to base types.

    Decisive by construction: were `T f` bound to the package's enum `T`,
    which has no base type, the packed-struct check would reject it (PSS012).
    Bound to the parameter, it is `bit[4]` and the model is clean.
    """
    root = assert_parse_ok(
        """
        package p {
            import std_pkg::*;
            enum T { A };
            struct g<type T> : packed_s<> { T f; }
            struct Top { g<bit[4]> x; }
        }
        """
    )
    assert root is not None
