from pssparser import ParseException, Parser


def _link_ok(code: str):
    p = Parser()
    p.parses([("test.pss", code)])
    return p.link()


def _get_error(code: str):
    try:
        _link_ok(code)
        return None
    except ParseException as e:
        return str(e)


def test_struct_base_type_resolves_locally():
    root = _link_ok(
        """
        struct A { }
        struct B : A { }
        """
    )
    assert root is not None


def test_parameterized_base_type_resolves():
    root = _link_ok(
        """
        struct A<int T> { }
        struct B : A<2> { }
        """
    )
    assert root is not None


def test_imported_base_type_resolves():
    root = _link_ok(
        """
        package p1 {
            struct A { }
        }
        package p3 {
            import p1::*;
            struct B : A { }
        }
        """
    )
    assert root is not None


def test_ambiguous_wildcard_import_reports_resolution_error():
    err = _get_error(
        """
        package p1 {
            struct A { }
        }
        package p2 {
            struct A { }
        }
        package p3 {
            import p1::*;
            import p2::*;
            struct B : A { }
        }
        """
    )
    assert err is not None
    assert "Ambiguous symbol resolution" in err
