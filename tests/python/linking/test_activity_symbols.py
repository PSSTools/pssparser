"""Activity symbols used as if they were actions (LRM 11.7; pssc request Q3).

Example 120 activates a symbol with `a_or_b;`, which parses as an action
handle traversal resolved to the SymbolDeclaration. The same statement form
also admits `with { ... }` and `{.x = ...}`, which mean nothing on a symbol:
a symbol has no fields. pssparser had no action to resolve the names inside
against, left them unbound, and its completeness gate then blamed itself
("'val' was left unbound by pssparser ... a pssparser defect").
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import find_markers, parse_collect  # noqa: E402


def _errors(pss):
    _, markers = parse_collect(pss)
    return find_markers(markers, severity="error")


def _model(activity, symbol_first=True):
    sym = "        symbol s { do A; }\n"
    act = f"        activity {{ {activity} }}\n"
    return ("component pss_top {\n"
            "    action A { rand bit[4] val; }\n"
            "    action T {\n"
            + (sym + act if symbol_first else act + sym) +
            "    }\n"
            "}\n")


@pytest.mark.parametrize("symbol_first", [True, False], ids=["decl-first", "use-first"])
@pytest.mark.parametrize("activity,what,col", [
    pytest.param("s with { val == 1; };", "'with' constraints", 22, id="with"),
    pytest.param("s with { 1 < 2; };", "'with' constraints", 22, id="with-no-names"),
    pytest.param("s {.val = 1};", "initializer list", 20, id="initializer"),
])
def test_a_with_or_initializer_on_a_symbol_is_an_error(activity, what, col, symbol_first):
    errors = _errors(_model(activity, symbol_first))
    assert len(errors) == 1, errors
    m = errors[0]
    assert m["message"] == (
        f"'s' is a symbol, not an action handle; a symbol takes no {what} (11.7)"), m
    assert m["code"] == "PSS018", m
    assert m["line"] == (5 if symbol_first else 4) and m["col"] == col, m
    assert "pssparser defect" not in m["message"]


@pytest.mark.parametrize("activity", [
    pytest.param("s;", id="example-120-form"),
    pytest.param("s();", id="call-form"),
])
def test_activating_a_symbol_is_clean(activity):
    assert not _errors(_model(activity))


def test_a_with_on_a_real_handle_is_still_clean():
    errors = _errors("""component pss_top {
    action A { rand bit[4] val; }
    action T {
        A a1;
        activity { a1 with { val == 1; }; a1 {.val = 2}; }
    }
}
""")
    assert not errors, errors


# --------------------------------------------------------------------------
# Q4: argument kinds and recursion (11.7)

def _syms(symbols, activity):
    return ("component pss_top {\n"
            "    action A { }\n"
            "    action A2 : A { }\n"
            "    action B { }\n"
            "    action T {\n"
            "        A a; A2 a2; B b; A arr[2];\n"
            f"{symbols}\n"
            f"        activity {{ {activity} }}\n"
            "    }\n"
            "}\n")


HANDLE = "        symbol s(A h) { h; }"
VALUE = "        symbol t(int n) { repeat (n) { do A; } }"


@pytest.mark.parametrize("symbols,call,message", [
    pytest.param(HANDLE, "s(3);",
                 "argument 1 of 's' is a value, but parameter 'h' is a handle of action 'A'",
                 id="value-for-a-handle"),
    pytest.param(HANDLE, "s(b);",
                 "argument 1 of 's' is a handle of action 'B', but parameter 'h' is a "
                 "handle of action 'A'", id="wrong-action-type"),
    pytest.param(VALUE, "t(a);",
                 "argument 1 of 't' is an action handle, but parameter 'n' is numeric",
                 id="handle-for-a-value"),
])
def test_a_symbol_argument_of_the_wrong_kind_is_pss006(symbols, call, message):
    errors = _errors(_syms(symbols, call))
    assert [m["message"] for m in errors] == [message], errors
    assert errors[0]["code"] == "PSS006"


@pytest.mark.parametrize("call", ["s(a);", "s(a2);", "s(arr[0]);"],
                         ids=["same-type", "subtype", "array-element"])
def test_a_handle_argument_of_the_right_kind_is_clean(call):
    assert not _errors(_syms(HANDLE, call))


def test_a_value_argument_of_the_right_kind_is_clean():
    assert not _errors(_syms(VALUE, "t(4); t(2 + 2);"))


@pytest.mark.parametrize("symbols,chain,line", [
    pytest.param("        symbol s1(int n) { s2(n); }\n"
                 "        symbol s2(int n) { s1(n); }", "s1 -> s2 -> s1", 8, id="two"),
    pytest.param("        symbol s1 { s2(); }\n"
                 "        symbol s2 { s3(); }\n"
                 "        symbol s3 { s1(); }", "s1 -> s2 -> s3 -> s1", 9, id="three"),
    pytest.param("        symbol s1 { s1; }", "s1 -> s1", 7, id="self-by-example-120-form"),
])
def test_a_symbol_that_activates_itself_is_pss064(symbols, chain, line):
    errors = _errors(_syms(symbols, "s1(1);" if "int n" in symbols else "s1();"))
    assert len(errors) == 1, errors
    assert errors[0]["code"] == "PSS064", errors
    assert errors[0]["message"] == f"symbol 's1' activates itself: {chain} (11.7)", errors
    assert errors[0]["line"] == line, errors


def test_two_cycles_are_two_errors():
    errors = _errors(_syms("        symbol s1 { s1(); }\n"
                           "        symbol s2 { s2(); }", "s1(); s2();"))
    assert [m["code"] for m in errors] == ["PSS064", "PSS064"], errors


def test_a_diamond_is_not_a_cycle():
    assert not _errors(_syms("        symbol d1 { d2(); d3(); }\n"
                             "        symbol d2 { d4(); }\n"
                             "        symbol d3 { d4(); }\n"
                             "        symbol d4 { do A; }", "d1();"))
