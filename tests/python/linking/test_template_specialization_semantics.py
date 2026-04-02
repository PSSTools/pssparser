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

        struct addr_region_s<struct TRAIT : addr_trait_s = empty_addr_trait_s> {
            TRAIT trait;
        }

        component pss_top {
            addr_region_s<> r1;
        }
        """
    )
    assert root is not None
