from ..test_helpers import assert_parse_ok, get_symbol, parse_pss


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


# ===========================================================================
# Name resolution inside a type extension (LRM 17.2.3)
# ===========================================================================
#
# pssparser maintains two views of a model. The *physical* view keeps each
# type definition and each `extend` as the distinct item it was in source;
# the *logical* view presents the type as definition-plus-extensions merged.
# The physical view is the GlobalScope/AST tree, the logical view is the
# symbol tree, and the logical view borrows -- it holds non-owning pointers
# to nodes the physical view owns.
#
# Three defects broke the merge, all now fixed:
#
#   * The `<extend>` symbol scope was not marked synthetic, and
#     TaskBuildSymbolTree::addChild only materializes getChildren() for a
#     synthetic scope. So the scope came out empty and plain fields were
#     never merged at all. Scope-like members (nested types, functions) were
#     pushed by a different overload, which is why they alone worked.
#
#   * TaskResolveFieldRef::visitSymbolScope was an empty stub, so the second
#     element of a package-qualified path -- the `s` of `p::s` -- never
#     resolved and `extend struct p::s` silently dropped its whole body.
#
#   * A merged member kept the getId() it had in the `<extend>` scope, which
#     is the index AstSymbolTableIterator emits as its ChildIdx step, so
#     paths through it landed on whatever occupied that index in the target.
#
# What remains is genuinely a scoping question rather than a merge defect:
# unqualified names in an extension body resolve against the *target's*
# scope stack rather than the package that declares the extension, so the
# declaring package's imports are not visible (LRM 17.2.3).

import pytest


def test_extension_field_is_referenceable():
    """A field introduced by an extension must be reachable by name."""
    parse_pss("""
    package p { struct s_s { bit[4] f; } }
    import p::*;
    component c { }
    extend component c {
        s_s fld;
        target function void go() { fld.f = 1; }
    }
    component pss_top { c c0; }
    """)


def test_extension_local_reaches_its_type_scope():
    """A local in an extension-added function must reach its type's members."""
    parse_pss("""
    package p { struct s_s { bit[4] f; } }
    import p::*;
    component c { }
    extend component c {
        target function void go() { s_s v; v.f = 1; }
    }
    component pss_top { c c0; }
    """)


def test_extension_body_sees_declaring_package_imports():
    """LRM 17.2.3: names in an extension resolve where it is *declared*."""
    parse_pss("""
    package p { struct s_s { bit[4] f; } }
    component c { }
    package q {
        import p::*;
        extend component c {
            target function void go() { s_s v; v.f = 1; }
        }
    }
    component pss_top { import q::*; c c0; }
    """)


def test_same_code_outside_an_extension_works():
    """Control: all three constructs are fine written directly in the type.

    This is what makes the above extension bugs rather than unsupported
    constructs.
    """
    parse_pss("""
    package p { struct s_s { bit[4] f; } }
    import p::*;
    component c {
        s_s fld;
        target function void go() { s_s v; v.f = 1; fld.f = 2; }
    }
    component pss_top { c c0; }
    """)


for _fn in (
    test_extension_body_sees_declaring_package_imports,
):
    _fn = pytest.mark.xfail(
        strict=True,
        reason="phase 3.2: extension body resolves against the target's scope, "
               "not the declaring package (LRM 17.2.3)",
    )(_fn)
    globals()[_fn.__name__] = _fn
