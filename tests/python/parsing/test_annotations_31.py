"""
Tests for PSS 3.1 annotation declarations, application, and extensions.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
    assert_parse_ok,
    assert_parse_error,
    assert_marker,
    assert_no_marker,
    assert_parse_ok_with_warning,
    get_symbol,
    parse_collect,
)


# Keeps the owning Parser alive for the duration of a test: AST node wrappers do
# not hold a reference to it, and the C++ nodes are freed when it is collected.
_LIVE_PARSERS = []


def _parse(pss):
    from pssparser import Parser
    p = Parser()
    _LIVE_PARSERS.append(p)
    root, markers = parse_collect(pss, parser=p)
    return root, markers


# ---------------------------------------------------------------------------
# Declaration
# ---------------------------------------------------------------------------

def test_annotation_declaration_basic():
    pss = """
    annotation desc_s {
        string desc;
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "desc_s") is not None


def test_annotation_declaration_with_super_and_params():
    pss = """
    annotation base_s {
        string desc;
    }

    annotation rich_s<int W=1> : base_s {
        static const int width = W;
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "base_s") is not None
    assert get_symbol(root, "rich_s") is not None


def test_extend_annotation_basic():
    pss = """
    annotation desc_s {
        string desc;
    }

    extend annotation desc_s {
        static const int version = 1;
    }
    """
    root = assert_parse_ok(pss)
    assert root is not None


def test_annotation_compile_if_in_body():
    pss = """
    annotation cfg_s {
        compile if (true) {
            string name;
        }
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "cfg_s") is not None


def test_extend_annotation_requires_target():
    pss = """
    extend annotation {
        static const int version = 1;
    }
    """
    assert_parse_error(pss)


# ---------------------------------------------------------------------------
# Application syntax (D1 hard cut-over)
# ---------------------------------------------------------------------------

DESC_DECL = """
    annotation desc_s {
        string desc;
        string owner;
    }
"""


def test_annotation_application_named():
    pss = DESC_DECL + """
    @desc_s {.desc = "block", .owner = "dv"}
    component C {
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "desc_s") is not None
    assert get_symbol(root, "C") is not None


def test_annotation_application_no_params():
    pss = """
    annotation marker_s {
    }

    @marker_s
    component C {
    }
    """
    root = assert_parse_ok(pss)
    assert get_symbol(root, "C") is not None


@pytest.mark.parametrize("application", [
    '@desc_s("block")',
    '@desc_s(desc="block")',
    '@desc_s("block", owner="dv")',
    '@desc_s()',
])
def test_annotation_old_paren_form_rejected(application):
    """D1: the PSS 3.0 parenthesized form is removed outright, not deprecated."""
    pss = DESC_DECL + application + """
    component C {
    }
    """
    assert_parse_error(pss)


def test_annotation_param_requires_leading_dot():
    pss = DESC_DECL + """
    @desc_s {desc = "block"}
    component C {
    }
    """
    assert_parse_error(pss)


# ---------------------------------------------------------------------------
# AST shape
# ---------------------------------------------------------------------------

def test_element_annotation_attaches_to_following_declaration():
    pss = DESC_DECL + """
    @desc_s {.desc = "block", .owner = "dv"}
    component C {
    }
    """
    root, markers = _parse(pss)
    assert root is not None

    comp = _find_child(root, "C")
    assert comp is not None, "component C not found in the AST"
    comp = _unwrap(comp)
    assert comp.numAnnotations() == 1
    ann = comp.getAnnotation(0)
    assert ann.getIs_standalone() is False
    assert ann.numParameters() == 2
    assert [ann.getParameter(i).getName().getId().getId() for i in range(2)] == ["desc", "owner"]


def test_standalone_annotation_anchors_to_enclosing_scope():
    pss = DESC_DECL + """
    @desc_s {.desc = "file-level"};

    component C {
    }
    """
    root, markers = _parse(pss)
    assert root is not None
    assert not [m for m in markers if m["severity"] == "error"]

    ann = _find_standalone_annotation(root)
    assert ann is not None, "standalone annotation is not a child of the scope"
    assert ann.getIs_standalone() is True

    # ...and it must not have been attached to the following component.
    comp = _find_child(root, "C")
    assert comp is not None
    assert _unwrap(comp).numAnnotations() == 0


def test_standalone_annotation_at_end_of_scope_is_not_dangling():
    """The semicolon form has nothing to attach to by design."""
    pss = """
    annotation note_s { string text; }

    component C {
        @note_s {.text = "end"};
    }
    """
    assert_no_marker(pss, marker_id="PSS100")


# ---------------------------------------------------------------------------
# Dangling annotations (PSS100)
# ---------------------------------------------------------------------------

def test_dangling_annotation_is_error():
    """§7.13: error if no subsequent element is present in the scope."""
    pss = """
    annotation note_s { string text; }

    component C {
        int a;
        @note_s {.text = "nothing follows"}
    }
    """
    assert_marker(pss, marker_id="PSS100", severity="error")


def test_annotation_followed_by_element_is_not_dangling():
    pss = """
    annotation note_s { string text; }

    component C {
        @note_s {.text = "attached"}
        int a;
    }
    """
    assert_no_marker(pss, marker_id="PSS100")


# ---------------------------------------------------------------------------
# Placement (P2-A2) -- one case per scope `annotation` was added to
# ---------------------------------------------------------------------------

PREAMBLE = """
    annotation note_s { string text; }
"""

ANN = '@note_s {.text = "x"}'

SCOPE_CASES = {
    "package_body_item": PREAMBLE + "package p { %s struct S {} }" % ANN,
    "struct_body_item": PREAMBLE + "struct S { %s int a; }" % ANN,
    "action_body_item": PREAMBLE + "component C { action A { %s int a; } }" % ANN,
    "component_body_item": PREAMBLE + "component C { %s int a; }" % ANN,
    "activity_stmt": PREAMBLE + (
        "component C { action A {} action B { activity { %s do A; } } }" % ANN),
    "procedural_stmt": PREAMBLE + (
        "component C { function void f() { %s int a; } }" % ANN),
    "override_stmt": PREAMBLE + (
        "component C { action A {} action B : A {} "
        "action X { override { %s type A with B; } } }" % ANN),
    "constraint_body_item": PREAMBLE + (
        "struct S { int a; constraint c { %s a > 0; } }" % ANN),
    "covergroup_body_item": PREAMBLE + (
        "struct S { int a; covergroup cg { %s option.weight = 1; } }" % ANN),
    "monitor_body_item": PREAMBLE + (
        "component C { action A {} monitor M { %s A a; } }" % ANN),
    "monitor_activity_stmt": PREAMBLE + (
        "component C { action A {} monitor N { activity { %s A a; } } }" % ANN),
    "monitor_constraint_body_item": PREAMBLE + (
        "component C { action A {} monitor M { A a; constraint c { %s 1 == 1; } } }" % ANN),
    # PP-4: neither an enum's symbol scope nor an `extend`'s wraps its
    # declaration as `target`, and the global scope had no annotation pass, so
    # each of these was reported as left unbound (PSS042).
    "file_enum": PREAMBLE + "%s enum e { A, B };" % ANN,
    "package_enum": PREAMBLE + "package p { %s enum e { A, B }; }" % ANN,
    "file_extend_enum": PREAMBLE + "enum e { A }; %s extend enum e { B };" % ANN,
    "package_extend_enum": PREAMBLE + (
        "package p { enum e { A }; %s extend enum e { B }; }" % ANN),
    "file_extend_struct": PREAMBLE + "struct S {} %s extend struct S { }" % ANN,
    "package_extend_struct": PREAMBLE + (
        "package p { struct S {} %s extend struct S { } }" % ANN),
    "file_import": PREAMBLE + "package q {} %s import q::*;" % ANN,
    # The symbol tree holds an imported function's scope, not the import
    # statement, so nothing reached the annotation on one outside a type.
    "file_import_function": PREAMBLE + "%s import target function void f();" % ANN,
    "package_import_function": PREAMBLE + (
        "package q { %s import target function void f(); }" % ANN),
    "package_import_function_via_import": PREAMBLE.replace(
        "annotation note_s", "package a_pkg { annotation note_s") + "}" + (
        " package q { import a_pkg::*; %s import target function void f(); }"
        % ANN),
}

# Each of these was resolved, not merely accepted: a field the annotation
# does not declare is an error only once its type is known.
UNBOUND_BEFORE_PP4 = sorted(
    k for k in SCOPE_CASES if k.startswith(("file_", "package_e", "package_i")))


@pytest.mark.parametrize("scope", sorted(SCOPE_CASES))
def test_annotation_in_each_scope(scope):
    assert_parse_ok(SCOPE_CASES[scope])


@pytest.mark.parametrize("scope", UNBOUND_BEFORE_PP4)
def test_annotation_type_resolves_in_each_scope(scope):
    """PP-4: the annotation's type is bound, so its fields are checked."""
    src = SCOPE_CASES[scope].replace(".text", ".nosuchfield")
    assert_marker(src, marker_id="PSS002", text="nosuchfield")
    assert_no_marker(src, marker_id="PSS042")


# ---------------------------------------------------------------------------
# Linker checks
# ---------------------------------------------------------------------------

def test_unknown_annotation_type_warns_and_parse_succeeds():
    """§7.13: "tools shall disregard unrecognized annotations" -- never an error."""
    pss = """
    component C {
        @nonexistent_s {.text = "x"}
        int a;
    }
    """
    assert_parse_ok_with_warning(pss, marker_id="LINT403")


def test_known_annotation_type_does_not_warn():
    pss = """
    annotation note_s { string text; }

    component C {
        @note_s {.text = "x"}
        int a;
    }
    """
    assert_no_marker(pss, marker_id="LINT403")


def test_unknown_annotation_param_is_error():
    pss = """
    annotation note_s { string text; }

    component C {
        @note_s {.nosuchfield = "x"}
        int a;
    }
    """
    assert_marker(pss, severity="error", text="nosuchfield")


def test_inherited_annotation_field_is_accepted():
    """Field lookup must follow the annotation's super chain, not just its own scope."""
    pss = """
    annotation base_s { string desc; }
    annotation rich_s : base_s { string owner; }

    component C {
        @rich_s {.desc = "a", .owner = "b"}
        int a;
    }
    """
    assert_parse_ok(pss)


def test_extend_annotation_field_is_accepted():
    """Closed with P2-A5b, which was never specific to annotations: the
    annotation checker was simply the first thing to report that a type
    extension's fields reached no scope."""
    pss = """
    annotation note_s { string text; }
    extend annotation note_s { string extra; }

    component C {
        @note_s {.extra = "x"}
        int a;
    }
    """
    assert_parse_ok(pss)


def test_non_constant_initializer_rejected():
    pss = """
    annotation note_s { int val; }

    component C {
        int a;
        @note_s {.val = a}
        int b;
    }
    """
    assert_marker(pss, marker_id="PSS102", severity="error")


def test_annotation_declared_outside_package_scope_is_error():
    """§7.13b: annotation types may only be declared at package scope.

    Enforced by the grammar rather than the linker -- `annotation_declaration`
    is reachable only from `package_body_item` -- so this is a syntax error.
    """
    pss = """
    component C {
        annotation note_s { string text; }
    }
    """
    assert_parse_error(pss)


# ---------------------------------------------------------------------------
# Standard annotations (Annex C.1, §21.6)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", ["doc", "code_doc"])
def test_std_pkg_annotation_is_recognized(name):
    pss = """
    import std_pkg::*;
    component C {
        @%s {.text = "documented"}
        int a;
    }
    """ % name
    assert_no_marker(pss, marker_id="LINT403")


@pytest.mark.parametrize("name", ["doc", "code_doc"])
def test_std_pkg_annotation_field_is_checked(name):
    """Proves the annotation resolved to the std_pkg declaration, not to nothing."""
    pss = """
    import std_pkg::*;
    component C {
        @%s {.nosuchfield = "x"}
        int a;
    }
    """ % name
    assert_marker(pss, severity="error", text="nosuchfield")


def test_code_doc_on_procedural_stmt():
    """§21.6.1 Example325 applies @code_doc to a statement inside a function."""
    pss = """
    import std_pkg::*;
    component C {
        function void f() {
            @code_doc {.text = "Zero the target memory word"}
            int a;
        }
    }
    """
    assert_no_marker(pss, marker_id="LINT403")


def test_package_qualified_annotation_type_resolves():
    """Was P2-A5a: `pkg::Type` failed on its second path element."""
    pss = """
    package p {
        annotation note_s { string text; }
    }

    component C {
        @p::note_s {.text = "x"}
        int a;
    }
    """
    assert_no_marker(pss, marker_id="LINT403")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unwrap(node):
    """Linking wraps declarations in a symbol scope; annotations stay on the target."""
    target = getattr(node, "getTarget", None)
    if target is not None:
        t = target()
        if t is not None:
            return t
    return node


def _find_child(scope, name):
    for i in range(scope.numChildren()):
        c = scope.getChild(i)
        try:
            nm = c.getName()
        except AttributeError:
            continue
        if nm is None:
            continue
        if (nm if isinstance(nm, str) else nm.getId()) == name:
            return c
    return None


def _find_standalone_annotation(scope):
    for i in range(scope.numChildren()):
        c = scope.getChild(i)
        if hasattr(c, "getIs_standalone"):
            return c
    return None


# ---------------------------------------------------------------------------
# PP-2: parameter values against their fields (PSS150), repeated and unset
# annotations (LINT409, LINT411)
# ---------------------------------------------------------------------------

TYPED = """
    package p {
        enum e { A, B };
        enum f { C };
        annotation a_s {
            string name = "";
            int    n = 0;
            bool   b = false;
            bit[8] m = 0;
            e      en = e::A;
            int[4] s4 = 0;
        }
        annotation req_s { string name; string header; }
        annotation d_s : req_s { int x = 1; }
    }
    component c {
        import p::*;
        %s int z;
    }
"""

GOOD_VALUES = {
    "all": '@a_s {.name = "x", .n = 3, .b = true, .m = 255, .en = e::B, .s4 = -8}',
    "comparison_to_bool": '@a_s {.b = (3 > 2)}',
    "minus_one_in_bit8": '@a_s {.m = -1}',
    "bitneg_in_bit8": '@a_s {.m = ~0}',
    "int4_as_unsigned": '@a_s {.s4 = 15}',
    "qualified_item": '@a_s {.en = p::e::B}',
}


@pytest.mark.parametrize("case", sorted(GOOD_VALUES))
def test_annotation_parameter_values_that_suit_their_field(case):
    src = TYPED % GOOD_VALUES[case]
    assert_no_marker(src, marker_id="PSS150")
    assert_no_marker(src, severity="error")


BAD_VALUES = {
    "int_for_string": ('@a_s {.name = 5}', "'name' is int, but its field is string"),
    "string_for_int": ('@a_s {.n = "s"}', "'n' is string, but its field is int"),
    "int_for_bool": ('@a_s {.b = 3}', "'b' is int, but its field is bool"),
    "int_for_enum": ('@a_s {.en = 1}', "'en' is int, but its field is enum e"),
    "other_enum": ('@a_s {.en = f::C}', "'en' is enum f, but its field is enum e"),
    "too_wide": ('@a_s {.m = 256}', "'m' is 256, which does not fit in bit[8]"),
    "too_negative": ('@a_s {.m = -129}', "'m' is -129, which does not fit in bit[8]"),
    "int4_too_wide": ('@a_s {.s4 = 16}', "'s4' is 16, which does not fit in int[4]"),
    "duplicate": ('@a_s {.name = "x", .name = "y"}',
                  "'name' is given more than once"),
}


@pytest.mark.parametrize("case", sorted(BAD_VALUES))
def test_annotation_parameter_values_that_do_not_suit_their_field(case):
    ann, text = BAD_VALUES[case]
    assert_marker(TYPED % ann, marker_id="PSS150", severity="error",
                  text=text, count=1)


def test_unset_field_without_default_warns_per_field():
    m = assert_marker(TYPED % '@req_s {.name = "x"}', marker_id="LINT411",
                      severity="warning", text="leaves field 'header' unset",
                      count=1)
    assert m["related"], m


def test_unset_field_of_a_base_annotation_warns():
    src = TYPED % '@d_s {.header = "h"}'
    assert_marker(src, marker_id="LINT411", text="field 'name'", count=1)
    assert_no_marker(src, marker_id="LINT411", text="field 'x'")


def test_field_with_a_default_may_be_left_unset():
    assert_no_marker(TYPED % '@a_s', marker_id="LINT411")


def test_same_annotation_type_twice_warns_once():
    # `a_s` under the import and `p::a_s` are one type.
    m = assert_marker(TYPED % '@a_s {.n = 1} @p::a_s {.n = 2}',
                      marker_id="LINT409", severity="warning", count=1)
    assert m["related"], m


def test_different_annotation_types_do_not_warn():
    assert_no_marker(TYPED % '@a_s @d_s {.name = "a", .header = "h"}',
                     marker_id="LINT409")


@pytest.mark.parametrize("decl", [
    "function void f() {}",
    "struct s {}",
    "enum e2 { X };",
])
def test_same_annotation_type_twice_warns_on_each_kind(decl):
    src = TYPED.replace("%s int z;", "@a_s @a_s " + decl)
    assert_marker(src, marker_id="LINT409", count=1)
