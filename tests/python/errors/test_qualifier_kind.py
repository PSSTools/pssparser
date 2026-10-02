"""Only a namespace qualifies a name (LRM 18.3; pssc request P1, 2026-09-30).

"The term namespace refers to either a package or a type." A field, a
variable, a function or a symbol is neither, so `tx::send_a` for a component
instance `tx` is not a type name, even though tx's type declares `send_a`.
9.1.3 and Example 47 spell it with the type: `uart_c::write`, not `s1::write`.

pssparser used to exempt this shape on purpose, because a first version of the
completeness gate "broke five working models". Those were pssc fixtures, and
pssc's reading was that the LRM does not allow it. Now each such qualifier is
an error at the qualifier, naming what it is and, where it would be right, the
type to write instead.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import find_markers, parse_collect  # noqa: E402


def _errors(pss):
    _, markers = parse_collect(pss)
    return find_markers(markers, severity="error")


def _one(pss, message, line, col):
    errors = _errors(pss)
    assert len(errors) == 1, errors
    assert message in errors[0]["message"], errors
    assert (errors[0]["line"], errors[0]["col"]) == (line, col), errors
    assert errors[0]["code"] == "PSS002", errors
    assert "pssparser defect" not in errors[0]["message"]


TX = "'tx' is a component instance, not a type or package; did you mean 'tx_c'?"


# --------------------------------------------------------------------------
# 1. The request's two repros

def test_repro_1_traversal():
    _one("""component tx_c { action send_a { } }
component pss_top {
    tx_c tx;
    action A { activity { do tx::send_a; } }
}
""", TX, 4, 30)


def test_repro_2_handles_and_bind():
    """The bind used to report "'i' was left unbound … a pssparser defect"."""
    errors = _errors("""buffer b_s { rand bit[8] v; }
component tx_c { action send_a { output b_s o; } }
component rx_c { action recv_a { input b_s i; } }
component pss_top {
    tx_c tx;
    rx_c rx;
    pool b_s p; bind p *;
    action A {
        activity {
            tx::send_a s;
            rx::recv_a r;
            bind s.o r.i;
        }
    }
}
""")
    assert [(m["line"], m["col"]) for m in errors] == [(10, 13), (11, 13)], errors
    assert TX in errors[0]["message"]
    assert "'rx' is a component instance" in errors[1]["message"]
    assert not any("pssparser defect" in m["message"] for m in errors)


# --------------------------------------------------------------------------
# 2. Every type position

PRE = """component tx_c { action send_a { } struct s2 { int a; } }
component pss_top {
    tx_c tx;
"""


@pytest.mark.parametrize("decl,col", [
    pytest.param("    tx::s2 f;", 5, id="component-field"),
    pytest.param("    action A { rand tx::s2 g; }", 21, id="action-field"),
    pytest.param("    function void f1(tx::s2 x) { }", 22, id="function-parameter"),
    pytest.param("    action B : tx::send_a { }", 16, id="super-type"),
    pytest.param("    typedef tx::s2 t2;", 13, id="typedef"),
    pytest.param("    action A { activity { tx::send_a s; } }", 27, id="activity-handle"),
    pytest.param("    action A { activity { do tx::send_a; } }", 30, id="do"),
    pytest.param("    action A { tx::send_a h; }", 16, id="action-handle-field"),
    pytest.param("    action A { exec body { tx::s2 v; } }", 28, id="exec-local"),
    pytest.param("    pss_top::tx::s2 f;", 14, id="instance-mid-path"),
])
def test_every_type_position(decl, col):
    _one(PRE + decl + "\n}\n", TX, 4, col)


# --------------------------------------------------------------------------
# 3. Every kind of qualifier

@pytest.mark.parametrize("decls,use,message", [
    pytest.param("static const int K = 1;", "K::s2 f;",
                 "'K' is a constant, not a type or package", id="constant"),
    pytest.param("tx_c arr[2];", "arr::s2 f;",
                 "'arr' is an array, not a type or package", id="array"),
    pytest.param("function int fn() { return 1; }", "fn::s2 f;",
                 "'fn' is a function, not a type or package", id="function"),
    pytest.param("action A { } action C { A h; activity { do h::send_a; } }", "",
                 "'h' is an action handle, not a type or package", id="action-handle"),
    pytest.param("action C { exec body { int v; v::s2 w; } }", "",
                 "'v' is a variable, not a type or package", id="variable"),
])
def test_every_qualifier_kind(decls, use, message):
    errors = _errors("component tx_c { action send_a { } struct s2 { int a; } }\n"
                     "component pss_top {\n"
                     f"    {decls}\n"
                     f"    {use}\n"
                     "}\n")
    assert len(errors) == 1, errors
    assert message in errors[0]["message"], errors
    assert "did you mean" not in errors[0]["message"], errors


# --------------------------------------------------------------------------
# 4. The suggestion is offered only when it is right

def test_no_suggestion_when_the_type_lacks_the_name():
    errors = _errors(PRE + "    tx::nosuch f;\n}\n")
    assert len(errors) == 1, errors
    assert errors[0]["message"].startswith(
        "'tx' is a component instance, not a type or package"), errors
    assert "did you mean" not in errors[0]["message"], errors


def test_no_suggestion_for_an_instance_member():
    """`tx_c::g()` would be an error too: g is an instance function."""
    errors = _errors("""component tx_c { function int g() { return 1; } }
component pss_top {
    tx_c tx;
    action A { exec body { int x; x = tx::g(); } }
}
""")
    assert len(errors) == 1, errors
    assert "'tx' is a component instance" in errors[0]["message"], errors
    assert "did you mean" not in errors[0]["message"], errors


# --------------------------------------------------------------------------
# 5. Value positions: static_ref_path (F3)

VAL = """component tx_c {
    static const int N = 3;
    enum m_e { M0, M1 }
    static function int sg() { return 2; }
}
component pss_top {
    tx_c tx;
    action A {
        rand int y;
"""


@pytest.mark.parametrize("stmt,col", [
    pytest.param("constraint y == tx::M0;", 25, id="enum-item"),
    pytest.param("constraint y == tx::N;", 25, id="static-constant"),
    pytest.param("exec body { int x = tx::N; }", 29, id="initializer"),
    pytest.param("exec body { int x; x = tx::sg(); }", 32, id="static-call"),
])
def test_value_positions(stmt, col):
    _one(VAL + "        " + stmt + "\n    }\n}\n", TX, 10, col)


# --------------------------------------------------------------------------
# 6, 7. The legal spellings stay clean

def test_the_type_qualified_forms_are_clean():
    errors = _errors(VAL + """        constraint y == tx_c::M0;
        constraint y == tx_c::N;
        exec body { int x = tx_c::N; x = tx_c::sg(); }
    }
}
""")
    assert not errors, errors


def test_example_47():
    """LRM Example 47: an instance and a type-qualified action side by side."""
    errors = _errors("""component uart_c {
    action write { }
}
component pss_top {
    uart_c s1, s2;
    action entry {
        uart_c::write wr;
        activity { wr; }
    }
}
""")
    assert not errors, errors


def test_an_enum_type_qualifier_keeps_its_message():
    """An enum is a type: `e_t::X` in a type position is still 'unknown type'."""
    errors = _errors("""component pss_top {
    enum e_t { A, B }
    e_t::X f;
}
""")
    assert len(errors) == 1, errors
    assert "not a type or package" not in errors[0]["message"], errors
