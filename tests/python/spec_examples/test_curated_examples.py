from ..test_helpers import assert_parse_ok


def test_pss30_combined_features_example():
    root = assert_parse_ok(
        """
        component pss_top {
            action A {
                rand int x;

                exec body {
                    randomize x with { x < 50; };
                }
            }

            action B {
                exec body { }
            }

            action my_compound {
                A a1;
                A a2;
                B b1;

                activity {
                    atomic {
                        a1;
                        a2;
                    }
                    b1;
                }
            }
        }
        """
    )
    assert root is not None


def test_yield_in_exec_block_example():
    root = assert_parse_ok(
        """
        component pss_top {
            action A {
                exec body {
                    int x = 0;
                    yield;
                    x = x + 1;
                }
            }
        }
        """
    )
    assert root is not None


def test_platform_qualifier_both_example():
    root = assert_parse_ok(
        """
        component pss_top {
            target function void target_only() { }
            solve function int solve_only() { return 0; }
            target solve function int both_platforms() { return 0; }

            action A {
                exec body {
                    target_only();
                }
            }
        }
        """
    )
    assert root is not None


def test_reactive_control_flow_example():
    root = assert_parse_ok(
        """
        component my_ip_c {
            function int sample_DUT_state();
            import target C function sample_DUT_state;

            action check_state {
                int curr_val;
                exec body {
                    curr_val = comp.sample_DUT_state();
                }
            };

            action A { };
            action B { };

            action my_test {
                check_state cs;
                activity {
                    repeat {
                        cs;
                        if (cs.curr_val % 2 == 0) {
                            do A;
                        } else {
                            do B;
                        }
                    } while (cs.curr_val < 10);
                }
            };
        };
        """
    )
    assert root is not None


def test_target_template_function_implementation_example():
    root = assert_parse_ok(
        '''
        package thread_ops_pkg {
            function void do_stw(bit[32] val, bit[32] vaddr);
        }
        package thread_ops_asm_pkg {
            target ASM function void do_stw(bit[32] val, bit[32] vaddr) = """
 loadi RA {{val}}
 store RA {{vaddr}}
 """;
        }
        '''
    )
    assert root is not None


def test_import_class_example():
    root = assert_parse_ok(
        """
        import class base {
            void base_method();
        }
        import class ext : base {
            void ext_method();
        }
        """
    )
    assert root is not None
