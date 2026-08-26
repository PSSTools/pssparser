"""
Tests for the PSS 3.1 function-declaration platform qualifier (P3-F1) and
`type...` varargs parameters (P3-F2). LRM §4.1/§4.3, Annex B B.5.

::

    function_decl ::= [ platform_qualifier ] [ pure ] [ static ]
                      function function_prototype ;
    platform_qualifier ::= target [ solve ] | solve

`function_decl` had no `platform_qualifier`, which matters beyond syntax:
Annex C declares many core-library functions as `solve function` /
`target function` at package scope, so the 3.1 standard library does not parse
without it. This is a prerequisite for Phase 4.

Two things the qualifier work exposed:

* `FunctionPrototype.is_target` / `is_solve` were hardcoded `false` at every
  call site, so the flags carried no information at all.
* `procedural_function` applied them with an `if`/`else`, so `target solve`
  recorded only `target`. `platform_qualifier` is `target [solve] | solve` --
  the two are not mutually exclusive.

For P3-F2, the `type... args` spelling parsed but the builder's `is_type` and
plain-category arms sat inside an `else if (is_ref)` and were unreachable, so
the parameter was built as a `ParamKind_DataType` with a null type. Annex C uses
`type... args` for `print`, `format`, `message`, `error`, `fatal` and
`file_write`, so every one of those would have been silently mis-typed.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from test_helpers import assert_parse_ok, assert_parse_error  # noqa: E402
from pssparser import Parser  # noqa: E402
from pssparser.ast import FunctionParamDeclKind  # noqa: E402

# AST node wrappers do not keep their owning Parser alive.
_LIVE_PARSERS = []

_KIND_DATATYPE = FunctionParamDeclKind.ParamKind_DataType
_KIND_TYPE = FunctionParamDeclKind.ParamKind_Type
_KIND_REF_MONITOR = FunctionParamDeclKind.ParamKind_RefMonitor
_KIND_NUMERIC = FunctionParamDeclKind.ParamKind_Numeric


def _prototype(code, name="f"):
    parser = Parser()
    _LIVE_PARSERS.append(parser)
    parser.parses([("test.pss", code)])
    assert not parser.markers, [m for m in parser.markers]

    def walk(node, depth=0):
        if node is None or depth > 20 or not hasattr(node, "numChildren"):
            return None
        for i in range(node.numChildren()):
            child = node.getChild(i)
            # A definition or an import wraps the prototype behind getProto()
            # rather than holding it as a child.
            if hasattr(child, "getProto"):
                child = child.getProto()
            if child is None:
                continue
            if type(child).__name__ == "FunctionPrototype" \
                    and child.getName().getId() == name:
                return child
            found = walk(child, depth + 1)
            if found is not None:
                return found
        return None

    for scope in parser._files[1:]:
        found = walk(scope)
        if found is not None:
            return found
    raise AssertionError("no FunctionPrototype %r found" % name)


# ===========================================================================
# P3-F1 -- platform qualifier on function_decl
# ===========================================================================

@pytest.mark.parametrize("decl", [
    "target function void f();",
    "solve function void f();",
    "target solve function void f();",
    "function void f();",
])
def test_qualified_function_decl_parses(decl):
    assert_parse_ok("package p { %s }" % decl)


def test_qualified_function_decl_in_a_component():
    assert_parse_ok("component C { target function void f(); }")


def test_qualifier_combines_with_pure_and_static():
    # Non-void deliberately: LRM 20.2.6 (a) allows `pure` only on a function
    # that returns a value, and that rule is checked.
    assert_parse_ok("package p { target pure static function int f(); }")


def test_qualifier_with_parameters_and_return_type():
    assert_parse_ok("package p { solve function int f(int a, string b); }")


@pytest.mark.parametrize("decl,is_target,is_solve", [
    ("target function void f();", True, False),
    ("solve function void f();", False, True),
    ("target solve function void f();", True, True),
    ("function void f();", False, False),
])
def test_qualifier_is_recorded_on_the_prototype(decl, is_target, is_solve):
    """
    Both flags previously read `false` unconditionally -- they were passed as
    literals at every construction site.
    """
    proto = _prototype("package p { %s }" % decl)
    assert proto.getIs_target() is is_target
    assert proto.getIs_solve() is is_solve


def test_target_solve_records_both_flags():
    """
    Called out separately because `procedural_function` used an if/else here
    and recorded only `target` -- and `target [solve]` is exactly the form that
    distinguishes the two.
    """
    proto = _prototype("package p { target solve function void f(); }")
    assert proto.getIs_target() and proto.getIs_solve()


def test_qualifier_on_a_procedural_function_is_recorded():
    """The same threading applies to the definition form, not only the decl."""
    proto = _prototype("package p { target solve function void f() { } }")
    assert proto.getIs_target() and proto.getIs_solve()


def test_qualifier_on_an_imported_function_is_recorded():
    proto = _prototype("package p { import target function void f(); }")
    assert proto.getIs_target() is True
    assert proto.getIs_solve() is False


@pytest.mark.parametrize("decl", [
    "function target void f();",     # qualifier after `function`
    "target void f();",              # qualifier with no `function`
    "solve target function void f();",  # wrong order: B.5 is `target [solve]`
])
def test_malformed_qualifier_rejected(decl):
    assert_parse_error("package p { %s }" % decl)


# ===========================================================================
# P3-F2 -- `type...` varargs
# ===========================================================================

def test_varargs_type_parameter_parses():
    assert_parse_ok("package p { function void f(string fmt, type... args); }")


def test_varargs_is_the_only_parameter():
    assert_parse_ok("package p { function void f(type... args); }")


def test_varargs_type_parameter_has_the_type_kind():
    """
    The regression. `type... args` used to build a ParamKind_DataType with a
    null type, because the `is_type` arm was unreachable behind
    `else if (is_ref)`.
    """
    proto = _prototype("package p { function void f(string fmt, type... args); }")
    assert proto.numParameters() == 2

    varargs = proto.getParameter(1)
    assert varargs.getName().getId() == "args"
    assert varargs.getKind() == _KIND_TYPE


def test_varargs_type_parameter_has_no_data_type():
    """A category parameter names no concrete type -- the null is meaningful."""
    proto = _prototype("package p { function void f(type... args); }")
    assert proto.getParameter(0).getType() is None


def test_leading_parameters_are_unaffected():
    proto = _prototype("package p { function void f(string fmt, type... args); }")
    fmt = proto.getParameter(0)
    assert fmt.getKind() == _KIND_DATATYPE
    assert fmt.getType() is not None


def test_varargs_plain_category_parameter():
    proto = _prototype("package p { function void f(numeric... args); }")
    assert proto.getParameter(0).getKind() == _KIND_NUMERIC


def test_varargs_ref_category_parameter():
    proto = _prototype("""
    component C { monitor M { } }
    package p { function void f(ref monitor... args); }
    """)
    assert proto.getParameter(0).getKind() == _KIND_REF_MONITOR


def test_varargs_data_type_parameter():
    proto = _prototype("package p { function void f(int... args); }")
    param = proto.getParameter(0)
    assert param.getKind() == _KIND_DATATYPE
    assert param.getType() is not None


def test_annex_c_style_signatures_parse():
    """The signatures P4-L1 depends on."""
    assert_parse_ok("""
    package annex_c_shapes_p {
        function string format(string fmt, type... args);
        target function void print(string fmt, type... args);
        function void message(int level, string fmt, type... args);
        function void error(string fmt, type... args);
        function void fatal(int status, string fmt, type... args);
    }
    """)


@pytest.mark.parametrize("decl", [
    "function void f(type... a, type... b);",   # two varargs
    "function void f(type... a, int b);",       # varargs not last
    "function void f(type...);",                # no parameter name
])
def test_malformed_varargs_rejected(decl):
    assert_parse_error("package p { %s }" % decl)
