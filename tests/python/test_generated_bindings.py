"""
Regression tests for defects in the AST generator (pyastbuilder).

These guard generator behaviour, not parser behaviour. They live here because
pyastbuilder has no working test suite of its own -- its single test module had
bit-rotted to the point of failing at import -- so pssparser's suite is the only
thing standing between a generator regression and a silently degraded AST.

Each test names the defect it pins. All three were found during the PSS 3.1
migration and are recorded in docs/design/pss31-implementation-plan.md.
Generator-source assertions live in test_astbuilder_codegen.py; this module
covers what is observable through a parsed AST.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pssparser import Parser

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []


def _link(code):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    return parser.link()


# ---------------------------------------------------------------------------
# Plural list accessors returned a list of None
# ---------------------------------------------------------------------------
#
# The generated `getXs()` emitted `ret.append(__ep.accept(of._hndl))`, but
# `accept()` returns void -- so every list-of-node property returned
# `[None, None, ...]` while the singular `getX(i)` worked. Silent: the list had
# the right length, so a caller checking `len()` or iterating saw nothing wrong
# until it touched an element.

def test_plural_accessor_returns_nodes_not_none():
    root = _link("struct S { int a; int b; }")

    children = root.getChildren()
    assert children, "root scope reported no children"
    assert all(c is not None for c in children), \
        "getChildren() returned None elements: %r" % (children,)


def test_plural_accessor_agrees_with_singular_accessor():
    """The two accessors must describe the same list."""
    root = _link("struct S { int a; }")

    plural = root.getChildren()
    singular = [root.getChild(i) for i in range(root.numChildren())]

    assert len(plural) == len(singular)
    assert [type(x).__name__ for x in plural] == [type(x).__name__ for x in singular]


def test_plural_accessor_on_a_nested_list_property():
    """Exercise a list property other than the ubiquitous `children`."""
    root = _link("""
    annotation note_s { string text; string owner; }

    component C {
        @note_s {.text = "a", .owner = "b"}
        int a;
    }
    """)

    field = _find(root, lambda n: type(n).__name__ == "Field"
                  and n.numAnnotations() == 1)
    assert field is not None, "no annotated field found"

    params = field.getAnnotation(0).getParameters()
    assert all(p is not None for p in params)
    assert [p.getName().getId() for p in params] == ["text", "owner"]


# ---------------------------------------------------------------------------
# Non-ctor scalar members were left uninitialized
# ---------------------------------------------------------------------------
#
# Generated constructors initialize only the `is_ctor` members, and the ctor
# body assigns only members carrying an explicit `init:` in the YAML. Everything
# else read back whatever was on the heap.
#
# There is no reliable behavioural probe for this. `Annotation.is_standalone` is
# the only non-ctor bool in the schema without an `init:`, and the builder sets
# it on every path, so nothing observable from a parsed AST depends on the
# default. The guarantee is pinned by inspecting generated source instead --
# see test_astbuilder_codegen.py. What is checked here is that the defaulting
# does not clobber a value the builder does set.

def test_non_ctor_bool_set_by_the_builder_is_still_correct():
    root = _link("""
    annotation note_s { string text; }

    component C {
        @note_s {.text = "x"}
        int a;

        @note_s {.text = "standalone"};
    }
    """)

    field = _find(root, lambda n: type(n).__name__ == "Field"
                  and n.numAnnotations() == 1)
    assert field is not None
    assert field.getAnnotation(0).getIs_standalone() is False

    standalone = _find(root, lambda n: type(n).__name__ == "Annotation"
                       and n.getIs_standalone())
    assert standalone is not None, "standalone annotation lost its flag"


# ---------------------------------------------------------------------------
# Floating-point scalar members could not be declared at all
# ---------------------------------------------------------------------------
#
# `TypeKind` covered string, bool and the sized integers only, so `double` in
# ast/*.yaml failed generation with "user-defined type double is not declared".
# That blocked both a numeric field on ExprFloatLiteral and a DataTypeFloat
# node. Covered in depth by test_float_types.py; this asserts the generated
# accessor exists and returns a Python float.

def test_double_member_is_generated_and_returns_a_float():
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", "struct S { int a = 1.5; }")])

    node = _find_pre_link(parser, lambda n:
                          type(n).__name__ == "ExprFloatLiteral")
    assert node is not None, "no ExprFloatLiteral built"

    value = node.getValue()
    assert isinstance(value, float)
    assert value == 1.5


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find(node, pred):
    if pred(node):
        return node
    if hasattr(node, "numChildren"):
        for i in range(node.numChildren()):
            found = _find(node.getChild(i), pred)
            if found is not None:
                return found
    target = getattr(node, "getTarget", None)
    if target is not None:
        t = target()
        if t is not None and t is not node:
            return _find(t, pred)
    return None


def _find_pre_link(parser, pred):
    for scope in parser._files[1:]:
        for child in scope.children():
            for field in child.children():
                if type(field).__name__ != "Field":
                    continue
                init = field.getInit()
                if init is not None and pred(init):
                    return init
    return None
