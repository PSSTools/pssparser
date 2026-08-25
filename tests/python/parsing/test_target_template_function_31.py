'''
Tests for target-template functions -- PSS 3.1 §20.6.

    target C function void do_stw(int a) = """ stw {{a}}, 0 """;

Before P5-C2 this construct parsed, reported nothing, and produced **no AST
node at all** -- the enclosing scope came back without it.  `target_template_
function` was in the grammar and reachable from both `package_body_item` and
`component_body_item`, but had no visitor in the AST builder.

The `{{a}}` mustache is *not* interpreted here.  The template text is kept
verbatim in `data`; scanning it is P5-I1b.  What matters for P5-C2 is that the
node exists and that the prototype's parameters are in a scope, because that
scope is what §20.6 mustache expressions resolve against.

Note this module delimits its PSS sources with single-quoted triple quotes,
since the construct under test is spelled with double-quoted triple quotes.
'''
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import (
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


def _children(scope):
    return [scope.getChild(i) for i in range(scope.numChildren())]


def _find(scope, typename):
    """Depth-1 search for a child of the named AST type."""
    return [c for c in _children(scope) if type(c).__name__ == typename]


# ---------------------------------------------------------------------------
# The node exists at all
# ---------------------------------------------------------------------------

def test_target_template_function_builds_a_node():
    """The defect P5-C2 fixes: the construct used to vanish silently."""
    root, markers = _parse('''
        package p {
            target C function void do_stw(int a) = """ stw {{a}}, 0 """;
        }
    ''')
    assert markers == []

    fn_scope = get_symbol(get_symbol(root, "p"), "do_stw")
    assert fn_scope is not None, "no symbol for the target-template function"

    tmpl = _find(fn_scope, "TargetTemplateFunction")
    assert len(tmpl) == 1, "expected exactly one TargetTemplateFunction node"


def test_target_template_function_in_a_component():
    """Reachable from component_body_item as well as package_body_item.

    Both grammar paths are live; only one of them is usually exercised.
    """
    root, markers = _parse('''
        component c {
            target C function void poke(int addr) = """ *p = {{addr}}; """;
        }
    ''')
    assert markers == []

    fn_scope = get_symbol(get_symbol(root, "c"), "poke")
    assert fn_scope is not None
    assert _find(fn_scope, "TargetTemplateFunction")


# ---------------------------------------------------------------------------
# Field contents
# ---------------------------------------------------------------------------

def test_template_text_is_verbatim():
    """`data` is the text between the quotes, byte for byte.

    Nothing is stripped, unescaped or interpreted -- notably the `{{a}}`, which
    stays raw until P5-I1b scans it.
    """
    root, _ = _parse('''
        package p {
            target C function void f(int a) = """ stw {{a}}, 0 """;
        }
    ''')
    fn = _find(get_symbol(get_symbol(root, "p"), "f"), "TargetTemplateFunction")[0]
    assert fn.getData() == " stw {{a}}, 0 "


def test_language_identifier_is_captured():
    root, _ = _parse('''
        package p {
            target SV function void f() = """nop;""";
        }
    ''')
    fn = _find(get_symbol(get_symbol(root, "p"), "f"), "TargetTemplateFunction")[0]
    assert fn.getLanguage() == "SV"


def test_single_quoted_form_is_accepted():
    """`string_literal` covers both quote forms; only the triple-quoted one is
    a template context, but the single-quoted spelling must still parse."""
    root, _ = _parse('''
        package p {
            target C function int rd() = "return *p;";
        }
    ''')
    fn = _find(get_symbol(get_symbol(root, "p"), "rd"), "TargetTemplateFunction")[0]
    assert fn.getData() == "return *p;"


@pytest.mark.parametrize("src,expected", [
    ('target C static function int rd() = "return *p;";', True),
    ('target C function int rd() = "return *p;";', False),
])
def test_is_static_is_set_on_both_paths(src, expected):
    """Non-ctor bool members are uninitialized by the generated constructors,
    so the *false* case is the one that catches a builder that only assigns
    when the value is true.  Such a bug passes alone and fails in a full run.
    """
    root, _ = _parse("package p { %s }" % src)
    fn = _find(get_symbol(get_symbol(root, "p"), "rd"), "TargetTemplateFunction")[0]
    assert fn.getIs_static() is expected


def test_prototype_is_present_and_named():
    root, _ = _parse('''
        package p {
            target C function void do_stw(int a, int b) = """x""";
        }
    ''')
    fn = _find(get_symbol(get_symbol(root, "p"), "do_stw"), "TargetTemplateFunction")[0]
    proto = fn.getProto()
    assert proto is not None
    assert proto.getName().getId() == "do_stw"
    assert len(proto.getParameters()) == 2


# ---------------------------------------------------------------------------
# Parameter scoping -- what §20.6 mustache resolution will need
# ---------------------------------------------------------------------------

def get_param(fn_scope, name):
    """Look a function parameter up in its scope's `<plist>`.

    That sub-scope is where all four function-scope builders put parameters
    (known-issues P3-X8); before that was made uniform, this path put them in
    the function scope's own children instead.
    """
    if fn_scope is None or fn_scope.getPlist() is None:
        return None
    plist = fn_scope.getPlist()
    for i in range(plist.numChildren()):
        c = plist.getChild(i)
        if c is not None and c.getName().getId() == name:
            return c
    return None


def test_parameters_are_resolvable_in_the_function_scope():
    """The prerequisite for P5-I1c.

    A target-template function has a prototype but no PSS body, so it would
    otherwise take the bare-prototype path.  Without a scope holding the
    parameters, a `{{a}}` in the template has nothing to bind to.
    """
    root, _ = _parse('''
        package p {
            target C function void do_stw(int a, int b) = """ stw {{a}}, {{b}} """;
        }
    ''')
    fn_scope = get_symbol(get_symbol(root, "p"), "do_stw")

    assert get_param(fn_scope, "a") is not None, "parameter 'a' is not in scope"
    assert get_param(fn_scope, "b") is not None, "parameter 'b' is not in scope"


def test_template_node_lives_inside_its_own_function_scope():
    """Placement, not just presence.

    The template body is where the mustaches are; the parameters are in the
    function scope.  The node must sit *inside* that scope for ordinary
    upward name resolution to reach them.
    """
    root, _ = _parse('''
        package p {
            target C function void f(int a) = """{{a}}""";
        }
    ''')
    fn_scope = get_symbol(get_symbol(root, "p"), "f")
    assert _find(fn_scope, "TargetTemplateFunction"), \
        "template node is not a child of its function scope"

    # ...and not left dangling at package level as well.
    pkg = get_symbol(root, "p")
    assert not _find(pkg, "TargetTemplateFunction"), \
        "template node duplicated at package scope"


def test_duplicate_parameter_is_reported():
    """PSS003, with the parameter actually named.

    The general reportDuplicateSymbol path cannot be used here: it resolves the
    name via TaskGetName, and FunctionParamDecl is a ScopeChild rather than a
    NamedScopeChild, so the name comes back empty ("duplicate declaration of
    ''").  Assert the name appears, not merely that something was reported.
    """
    root, markers = _parse('''
        package p {
            target C function void g(int a, int a) = """x""";
        }
    ''')
    dups = [m for m in markers if m.get("code") == "PSS003"]
    assert len(dups) == 1, markers
    assert "'a'" in dups[0]["message"], dups[0]["message"]
    assert dups[0]["line"] > 0, "marker has no usable location"


def test_no_parameters_is_fine():
    root, markers = _parse('''
        package p {
            target C function void f() = """nop();""";
        }
    ''')
    assert markers == []
    fn_scope = get_symbol(get_symbol(root, "p"), "f")
    assert _find(fn_scope, "TargetTemplateFunction")


def test_two_template_functions_coexist():
    root, markers = _parse('''
        package p {
            target C function void f(int a) = """{{a}}""";
            target C function void g(int b) = """{{b}}""";
        }
    ''')
    assert markers == []
    pkg = get_symbol(root, "p")
    assert get_param(get_symbol(pkg, "f"), "a") is not None
    assert get_param(get_symbol(pkg, "g"), "b") is not None
