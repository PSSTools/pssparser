from ..test_helpers import assert_parse_ok


def test_reg_c_field_links():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;

        component my_regs : reg_group_c {
            reg_c<bit[32]> r1;
        }
        """
    )
    assert root is not None


def test_reg_group_c_field_links():
    root = assert_parse_ok(
        """
        import addr_reg_pkg::*;

        component my_regs : reg_group_c {
            reg_c<bit[32]> r1;
            reg_c<bit[32]> r2;
        }

        component pss_top {
            my_regs regs;
        }
        """
    )
    assert root is not None


def test_reg_rw_parameterized_links():
    root = assert_parse_ok(
        """
        import std_pkg::*;
        import addr_reg_pkg::*;

        struct fwperiph_dma_channel_csr : packed_s<> {
            bit[1] en;
        }

        component fwperiph_dma_channel : reg_group_c {
            reg_c<fwperiph_dma_channel_csr,READWRITE,32> CSR;
        }
        """
    )
    assert root is not None
