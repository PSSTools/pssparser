"""`const` function parameters (LRM 20.2.3).

`const` was parsed and then dropped: `FunctionParamDecl` had no field for it,
so nothing downstream could tell `f(const s_t v)` from `f(s_t v)`. It matters
twice over:

* an aggregate parameter is otherwise a handle the callee may write through
  (20.3.2), and a backend has to know which parameters it may pass as a copy;
* an aggregate literal is a constant in the context of the call, and may be
  passed only to a `const` parameter.

Both the package-function and the component-function call paths check the
second (`TaskCheckCallArgs::checkConstArg`).
"""
import sys
from pathlib import Path

import pytest

from ..isolation import assert_clean, assert_rejects

sys.path.insert(0, str(Path(__file__).parent.parent / "parsing"))
from test_ast_node_probes import _find_nodes_deep, _parse_only  # noqa: E402

_DECLS = """
    struct s_t { int a; int b; }
    function int f(const s_t v, s_t w) { return v.a + w.b; }
"""


def test_const_is_recorded_on_the_parameter(parser):
    p = _parse_only(_DECLS, parser)
    params = {d.getName().getId(): d.getIs_const()
              for d in _find_nodes_deep(p, "FunctionParamDecl")}
    assert params == {"v": True, "w": False}


@pytest.mark.parametrize("call", [
    "f({.a = 1, .b = 2}, q)",          # package function
    "comp.g({.a = 1, .b = 2})",        # component function
])
def test_a_literal_may_be_passed_to_a_const_parameter(call):
    assert_clean([("t.pss", _DECLS + """
        component C {
            function int g(const s_t v) { return v.a; }
            action A { exec body { s_t q; int r; r = %s; } }
        }
    """ % call)])


@pytest.mark.parametrize("call,expected", [
    ("f(q, {.a = 1, .b = 2})",
     "argument 2 of 'f' is an aggregate literal, so parameter 'w' must be "
     "declared const (LRM 20.2.3)"),
    ("comp.g({.a = 1, .b = 2})",
     "argument 1 of 'g' is an aggregate literal, so parameter 'w' must be "
     "declared const (LRM 20.2.3)"),
])
def test_a_literal_may_not_be_passed_to_a_non_const_parameter(call, expected):
    assert_rejects([("t.pss", _DECLS + """
        component C {
            function int g(s_t w) { return w.a; }
            action A { exec body { s_t q; int r; r = %s; } }
        }
    """ % call)], expected)


def test_a_core_library_function_takes_a_literal_without_const():
    """`const` exists for native functions only (20.2.3), and the LRM's own
    register example passes literals to `write_fields`, whose parameters are
    not `const`: the rule does not apply to a function without a PSS body."""
    assert_clean([("t.pss", """
        import addr_reg_pkg::*;
        struct cr_s : packed_s<> { bit[2] mode; bit[4] coeff; }
        pure component regs_c : reg_group_c {
            reg_c<cr_s, READWRITE, 32> cr;
        }
        component C {
            regs_c regs;
            action A { exec body {
                comp.regs.cr.write_fields({"mode", "coeff"}, {1, 2});
            } }
        }
    """)])
