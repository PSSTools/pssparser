from pssparser import ParseException, Parser


def _link_error(code: str):
    p = Parser()
    try:
        p.parses([("test.pss", code)])
        p.link()
        return None
    except ParseException as e:
        return str(e)


def test_duplicate_action_in_component_extension_reports_error():
    err = _link_error(
        """
        component pss_top {
            action A { }
        }

        extend component pss_top {
            action A { }
            action B { }
        }
        """
    )
    assert err is not None


def test_unknown_enum_extension_reports_error():
    err = _link_error(
        """
        enum MyEnum { }

        extend enum MyEnum2 {
            A,
            B,
            C
        }
        """
    )
    assert err is not None
    assert "MyEnum2" in err


def test_unknown_struct_extension_reports_error():
    err = _link_error(
        """
        struct S { }

        extend struct S2 {
            int i;
        }
        """
    )
    assert err is not None
    assert "S2" in err


def test_instance_field_static_ref_links_cleanly():
    p = Parser()
    p.parses([("test.pss", """
        component pss_top {
            int field;

            action Entry {
                exec post_solve {
                    int i = field;
                }
            }
        }
    """)])
    root = p.link()
    assert root is not None
