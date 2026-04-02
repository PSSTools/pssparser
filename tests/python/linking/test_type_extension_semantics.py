from ..test_helpers import assert_parse_ok, get_symbol


def test_component_extension_adds_action():
    root = assert_parse_ok(
        """
        component pss_top {
            action A { }
        }

        extend component pss_top {
            action B { }
        }
        """
    )
    comp = get_symbol(root, "pss_top")
    assert comp is not None
    assert comp.symtabHas("A")
    assert comp.symtabHas("B")


def test_enum_extension_adds_members():
    root = assert_parse_ok(
        """
        enum MyEnum { }

        extend enum MyEnum {
            A,
            B,
            C
        }
        """
    )
    enum_t = get_symbol(root, "MyEnum")
    assert enum_t is not None
    assert len(list(enum_t.children())) == 3
