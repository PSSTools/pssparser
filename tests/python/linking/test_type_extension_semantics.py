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


# ---------------------------------------------------------------------------
# P2-A5b: an extension's fields reach the type it extends
# ---------------------------------------------------------------------------
#
# `TaskApplyTypeExtensions` re-homes an extension's children into the target's
# symbol scope, and `TaskResolveRefs` skips extension bodies on the strength of
# that.  A *field* was never re-homed: the extension's symbol scope is not
# synthetic, so `TaskBuildSymbolTree::addChild` records the name in its symtab
# without pushing the field into its children, and the re-homing walk had
# nothing to find.  So `extend struct S { int b; }` contributed nothing at all.


def test_struct_extension_adds_field():
    root = assert_parse_ok(
        """
        struct S { int a; }
        extend struct S { int b; }
        """
    )
    s = get_symbol(root, "S")
    assert s is not None
    assert s.symtabHas("a"), "the original field is gone"
    assert s.symtabHas("b"), "the extension's field did not reach the type"


def test_extension_field_is_referenceable():
    """Presence in the symtab is not the same as being resolvable."""
    assert_parse_ok(
        """
        struct S { int a; }
        extend struct S { int b; }
        component pss_top {
            S s;
            exec init_up { s.b = 1; }
        }
        """
    )


def test_component_extension_field_is_referenceable():
    assert_parse_ok(
        """
        component C { int a; }
        extend component C { int b; }
        component pss_top {
            C c;
            exec init_up { c.b = 1; }
        }
        """
    )


def test_original_declaration_can_reference_an_extension_field():
    """Extension is not ordered: the type's own constraint sees `b`."""
    assert_parse_ok(
        """
        struct S {
            rand int a;
            constraint c0 { a > b; }
        }
        extend struct S { rand int b; }
        """
    )


def test_unknown_member_is_still_reported():
    """The guard against the fix being 'accept everything'."""
    from ..test_helpers import assert_marker
    assert_marker(
        """
        struct S { int a; }
        extend struct S { int b; }
        component pss_top {
            S s;
            exec init_up { s.nope = 1; }
        }
        """,
        severity="error")


def test_extension_field_colliding_with_an_existing_one_is_reported():
    from ..test_helpers import assert_marker
    assert_marker(
        """
        struct S { int a; }
        extend struct S { int a; }
        """,
        text="conflicts with an existing declaration")


# ---------------------------------------------------------------------------
# An extension target named without qualification, inside its own package
# ---------------------------------------------------------------------------
#
# `TaskApplyTypeExtensions` resolved the target through a freshly built
# ResolveContext, which starts at the root with no scope stack.  So an
# unqualified target resolved only when the type happened to live at the root:
# the ordinary `package p { struct S {...} extend struct S {...} }` reported
# `unknown type 'S'`.  The walk's own iterator is now cloned into the context.


def test_extension_in_declaring_package_resolves_unqualified_target():
    assert_parse_ok(
        """
        package p {
            struct S { int a; }
            extend struct S { int b; }
            function void f(p::S s) { s.b = 1; }
        }
        """
    )


def test_component_extension_in_declaring_package():
    assert_parse_ok(
        """
        package p {
            component C { int a; }
            extend component C { int b; }
        }
        """
    )


def test_enum_extension_in_declaring_package():
    assert_parse_ok(
        """
        package p {
            enum E { A }
            extend enum E { B }
        }
        component pss_top {
            p::E e;
            exec init_up { e = p::E::B; }
        }
        """
    )


def test_extending_a_genuinely_unknown_type_is_still_reported():
    from ..test_helpers import assert_marker
    assert_marker(
        "package p { extend struct Nope { int b; } }",
        text="Nope")


def test_extending_an_unknown_enum_reports_once():
    """It used to report twice -- `TaskResolveRef` and `visitExtendEnum` each
    emitted their own message for the same name."""
    from ..test_helpers import parse_collect
    _, markers = parse_collect("package p { extend enum Nope { B } }")
    errs = [m for m in markers if m["severity"] == "error"]
    assert len(errs) == 1, errs
    assert "Nope" in errs[0]["message"]
