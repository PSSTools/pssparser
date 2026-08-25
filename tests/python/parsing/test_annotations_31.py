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
    assert [ann.getParameter(i).getName().getId() for i in range(2)] == ["desc", "owner"]


def test_standalone_annotation_anchors_to_enclosing_scope():
    pss = DESC_DECL + """
    @desc_s {.desc = "file-level"};

    component C {
    }
    """
    root, markers = _parse(pss)
    assert root is not None
    assert not [m for m in markers if m.severity == "error"]

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
}


@pytest.mark.parametrize("scope", sorted(SCOPE_CASES))
def test_annotation_in_each_scope(scope):
    assert_parse_ok(SCOPE_CASES[scope])


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
    assert_parse_ok_with_warning(pss, marker_id="PSS101")


def test_known_annotation_type_does_not_warn():
    pss = """
    annotation note_s { string text; }

    component C {
        @note_s {.text = "x"}
        int a;
    }
    """
    assert_no_marker(pss, marker_id="PSS101")


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
    component C {
        @%s {.text = "documented"}
        int a;
    }
    """ % name
    assert_no_marker(pss, marker_id="PSS101")


@pytest.mark.parametrize("name", ["doc", "code_doc"])
def test_std_pkg_annotation_field_is_checked(name):
    """Proves the annotation resolved to the std_pkg declaration, not to nothing."""
    pss = """
    component C {
        @%s {.nosuchfield = "x"}
        int a;
    }
    """ % name
    assert_marker(pss, severity="error", text="nosuchfield")


def test_code_doc_on_procedural_stmt():
    """§21.6.1 Example325 applies @code_doc to a statement inside a function."""
    pss = """
    component C {
        function void f() {
            @code_doc {.text = "Zero the target memory word"}
            int a;
        }
    }
    """
    assert_no_marker(pss, marker_id="PSS101")


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
    assert_no_marker(pss, marker_id="PSS101")


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
