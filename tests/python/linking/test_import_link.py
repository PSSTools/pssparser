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


# ---------------------------------------------------------------------------
# Single-symbol imports
#
# `import p::S;` names one symbol.  Every test above uses the wildcard form,
# which is why the non-wildcard branch of `TaskResolveRootRef::searchImport`
# could resolve to nothing for as long as it did: it looked the name up
# *inside* the scope the import path had already resolved to -- searching for
# `S` in `S` -- found nothing, and returned without a marker.  The import
# behaved as though it had not been written, and the failure surfaced later and
# elsewhere, as an unresolved reference.
#
# Found by moving vscode-pss-support onto this parser.  A language server links
# on every keystroke, so it meets the non-wildcard form constantly; a corpus of
# valid, mostly wildcard-importing PSS does not.
# ---------------------------------------------------------------------------

def test_single_symbol_import_resolves_the_symbol_it_names():
    root = _link_ok(
        """
        package p1 {
            struct A { }
        }
        package p3 {
            import p1::A;
            struct B : A { }
        }
        """
    )
    assert root is not None


def test_single_symbol_import_does_not_bring_in_the_rest_of_the_package():
    # The other half of the fix, and the reason it is not simply "treat the
    # non-wildcard form as a wildcard": a repair that resolved the import by
    # opening its parent package would pass the test above while quietly
    # turning every `import p::A;` into `import p::*;`.
    err = _get_error(
        """
        package p1 {
            struct A { }
            struct C { }
        }
        package p3 {
            import p1::A;
            struct B : C { }
        }
        """
    )
    assert err is not None
    assert "C" in err
