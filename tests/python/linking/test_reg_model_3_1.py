"""
PSS 3.1 register-model and address-space features (21.13, 21.14).

Each test is one of the acceptance snippets from the pssparser 3.1
requirements: the register-component hierarchy, path-based offsets, symbolic
register names, masked/field-wise writes, and struct/byte-granular address
access.
"""
from ..test_helpers import assert_parse_ok


def test_reg_sized_c_gives_generic_same_width_access():
    # 21.14.1 Example355: a function that works on any 32-bit register,
    # whatever its field layout.
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            struct CR : packed_s<> {
                bit en; bit[11] pad; bit[4] mode; bit[16] coeff;
            }
            pure component regs_c : reg_group_c {
                reg_c<CR> cr1;
                reg_c<bit[32]> cr2;
            }
            target function void zero_r32(list<ref reg_sized_c<32>> regs) {
                foreach (r : regs) { r.write_val(0); }
            }
        }
        """
    )
    assert root is not None


def test_reg_base_c_get_handle():
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            function bit[64] where(ref reg_base_c r) {
                return addr_value(r.get_handle());
            }
        }
        """
    )
    assert root is not None


def test_get_offset_of_path_and_node_s():
    # 21.14.2 Syntax161
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            pure component g : reg_group_c {
                pure function bit[64] get_offset_of_path(list<node_s> path) {
                    return 0;
                }
            }
        }
        """
    )
    assert root is not None


def test_symbolic_register_names():
    # 21.14.6, condensed from Example365
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            import std_pkg::*;
            struct R1_s : packed_s<> { bit[32] fld; }
            pure component dma_reg_group_c : reg_group_c {
                reg_c<R1_s, READWRITE, 32> reg_a;
                reg_c<R1_s, READWRITE, 32> reg_c_arr[3];
                solve pure function string get_mnemonic_of_instance(string name) {
                    if (name == "reg_a") { return "DMA_REG_A"; }
                    return "";
                }
                solve pure function string get_mnemonic_of_instance_array(
                        string name, int index) {
                    if (name == "reg_c_arr") {
                        return format("DMA_REG_C[%d]", index);
                    }
                    return "";
                }
            }
            component pss_top {
                dma_reg_group_c regs;
                transparent_addr_space_c<> mem;
                exec init_down {
                    transparent_addr_region_s<> mmio;
                    addr_handle_t h;
                    mmio.size = 0x80000;
                    mmio.addr = 0xA0000000;
                    h = mem.add_nonallocatable_region(mmio);
                    regs.set_handle(h);
                    regs.set_mnemonic("");
                    use_symbolic_reg_names(regs, true);
                }
            }
        }
        """
    )
    assert root is not None


def test_masked_and_field_wise_writes():
    # 21.14.1 Example356, condensed
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            struct CR : packed_s<> {
                bit en; bit[11] pad; bit[4] mode; bit[16] coeff;
            }
            pure component regs_c : reg_group_c { reg_c<CR> cr; }
            component dut_c {
                regs_c regs;
                action cfg_a {
                    rand bit[4] mode;
                    rand bit[16] coeff;
                    exec body {
                        comp.regs.cr.write_masked(
                            {.mode=~0, .coeff=~0}, {.mode=mode, .coeff=coeff});
                        comp.regs.cr.write_val_masked(
                            0xFFFFF000, (coeff << 16) | (mode << 12));
                        comp.regs.cr.write_fields({"mode", "coeff"}, {mode, coeff});
                        comp.regs.cr.write_field("en", 1);
                    }
                }
            }
        }
        """
    )
    assert root is not None


def test_struct_and_byte_granular_address_access():
    # 21.13.9
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            struct D : packed_s<> { bit[32] a; }
            component c {
                exec init_down {
                    addr_handle_t h;
                    D d;
                    list<bit[8]> bytes;
                    write_struct(h, d);
                    read_struct(h, d);
                    write_bytes(h, bytes);
                    read_bytes(h, bytes, 4);
                }
            }
        }
        """
    )
    assert root is not None


def test_make_handle_from_claim_takes_sub():
    # 21.13.4.1 Syntax146
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            function void f(addr_claim_base_s claim) {
                addr_handle_t h = make_handle_from_claim(claim, 0, false);
            }
        }
        """
    )
    assert root is not None


def test_sizeof_s_resolves_through_both_packages():
    # 21.13.2: sizeof_s is declared in std_pkg; addr_reg_pkg must still reach it.
    root = assert_parse_ok(
        """
        package t {
            import addr_reg_pkg::*;
            import std_pkg::*;
            struct S : packed_s<> { bit[32] a; }
            const int nbytes_a = std_pkg::sizeof_s<S>::nbytes;
            const int nbytes_b = sizeof_s<S>::nbytes;
        }
        """
    )
    assert root is not None


def test_format_and_format_string():
    root = assert_parse_ok(
        """
        package t {
            import std_pkg::*;
            function void f() {
                string a = format("%d", 1);
                string b = format_string("%d", 2);
                print("hello %d", 3);
                message(LOW, "hi %d", 4);
            }
        }
        """
    )
    assert root is not None
