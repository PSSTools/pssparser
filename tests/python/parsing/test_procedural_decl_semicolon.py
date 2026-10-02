"""A procedural data declaration must end in `;` (pssc request Q1, 2026-10-01).

`procedural_data_declaration` used to leave the `;` off, and the
empty-statement alternative of `procedural_stmt` consumed it instead. So
`int x = 1` followed by `int y = 2;` parsed as two declarations and an empty
statement. That is a legal parse, so no recovery path ran and no marker was
reported. The AST it built was exactly the intended one, so nothing downstream
could tell. Assignments were never affected, because their rule carries the `;`.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import find_markers, parse_collect  # noqa: E402


def _body(stmts, wrap):
    """`stmts` inside the body form named by `wrap`, the first statement on line 4."""
    inner = "\n".join("            " + s for s in stmts)
    if wrap == "exec":
        return ("component pss_top {\n"
                "    action T {\n"
                "        exec body {\n"
                f"{inner}\n"
                "        }\n"
                "    }\n"
                "}\n")
    if wrap == "function":
        return ("package p {\n"
                "    function void f() {\n"
                "        if (1 > 0) {\n"
                f"{inner}\n"
                "        }\n"
                "    }\n"
                "}\n")
    if wrap == "repeat":
        return ("package p {\n"
                "    function void f() {\n"
                "        repeat (2) {\n"
                f"{inner}\n"
                "        }\n"
                "    }\n"
                "}\n")
    raise ValueError(wrap)


#: (statements, the expected message, the marker's line and column).
#: The first statement is on line 4, at column 13.
MISSING = [
    pytest.param(["int x = 1", "int y = 2;"],
                 "expected ';' before 'int'", 5, 13, id="decl-then-decl"),
    pytest.param(["int x = 1", "int y = x;", "y = 3;"],
                 "expected ';' before 'int'", 5, 13, id="decl-then-use"),
    pytest.param(["int x = 1", "x = 2;"],
                 "expected ';' before 'x'", 5, 13, id="decl-then-assign"),
    pytest.param(["int x", "int y;"],
                 "expected ';' after 'x'", 4, 18, id="decl-no-init"),
    pytest.param(["int a = 1, b = 2", "int c;"],
                 "expected ';' before 'int'", 5, 13, id="multi-declarator"),
]


@pytest.mark.parametrize("wrap", ["exec", "function", "repeat"])
@pytest.mark.parametrize("stmts,message,line,col", MISSING)
def test_a_declaration_missing_its_semicolon_is_pss020(stmts, message, line, col, wrap):
    _, markers = parse_collect(_body(stmts, wrap))
    errors = find_markers(markers, severity="error")
    assert len(errors) == 1, errors
    assert errors[0]["code"] == "PSS020", errors
    assert message in errors[0]["message"], errors
    assert (errors[0]["line"], errors[0]["col"]) == (line, col), errors


@pytest.mark.parametrize("stmts", [
    pytest.param(["int x = 1;", "int y = 2;"], id="both-terminated"),
    pytest.param(["int x = 1;;"], id="declaration-then-empty-statement"),
    pytest.param(["int a = 1, b = 2;", "a = b;"], id="multi-declarator"),
])
@pytest.mark.parametrize("wrap", ["exec", "function"])
def test_terminated_declarations_are_clean(stmts, wrap):
    root, markers = parse_collect(_body(stmts, wrap))
    assert root is not None, markers
    assert not find_markers(markers, severity="error"), markers


def test_a_template_declaration_directive_still_parses():
    """`{% int i = 0; %}` parses its directive with the same rule. It used to
    strip the `;` first, because the rule did not include it."""
    pss = ('component pss_top { action T {\n'
           '    exec body C = """{% int i = 0; %}{% i = 1; %}""";\n'
           '} }\n')
    root, markers = parse_collect(pss)
    assert root is not None, markers
    assert not find_markers(markers, severity="error"), markers


def test_a_template_declaration_directive_without_its_semicolon_is_reported():
    pss = ('component pss_top { action T {\n'
           '    exec body C = """{% int i = 0 %}""";\n'
           '} }\n')
    _, markers = parse_collect(pss)
    assert find_markers(markers, severity="error",
                        text="expected ';' after declaration"), markers
