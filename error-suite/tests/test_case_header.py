"""Header parsing: every directive, both `at:` grammars, strictness."""
from __future__ import annotations

import pytest

from pss_errsuite.case import CaseFormatError, Span

FULL = """//! case:    SEM-TYPE-ASSIGN-WIDTH-01
//! class:   semantic.type.assign-incompatible
//! title:   string literal assigned to a bit field
//! expect:  error
//! detect:  required
//! at:      14:9-14:26
//! also:    9:5 "declared here"
//! also:    10:5 "and here"
//! count:   2
//! lrm:     8.4.2
//! pss:     3.1
//! tags:    scalar-type, initializer
//! requires: max_errors
//! fix:     14:         b = 8'h20;
//! cause:   assign, string, bit
//! not_cause: undeclared, unknown type
//! names:   b
//! pssparser.id:    PSS0xx
//! pssparser.match: cannot assign
//! xfail.pssparser: D1 -- token-set jargon leaks
package p {
    struct s {
        bit[8] b;
    }
}
"""


def test_every_directive_round_trips(write_case):
    case = write_case("full.pss", FULL)
    assert case.case_id == "SEM-TYPE-ASSIGN-WIDTH-01"
    assert case.cls == "semantic.type.assign-incompatible"
    assert case.expect == "error"
    assert case.detect == "required"
    assert case.at == Span(14, 9, 14, 26)
    assert [(a.line, a.col, a.label) for a in case.also] == [
        (9, 5, "declared here"), (10, 5, "and here")]
    assert case.count == 2
    assert case.lrm == "8.4.2"
    assert case.pss == "3.1"
    assert case.tags == ["scalar-type", "initializer"]
    assert case.requires == ["max_errors"]
    assert case.fix == [(14, "        b = 8'h20;")]
    assert case.cause == ["assign", "string", "bit"]
    assert case.not_cause == ["undeclared", "unknown type"]
    assert case.names == ["b"]
    assert case.tool_opts["pssparser"] == {"id": "PSS0xx",
                                           "match": "cannot assign"}
    assert case.xfail == {"pssparser": "D1 -- token-set jargon leaks"}


@pytest.mark.parametrize("spec,expected", [
    ("14:9", Span(14, 9)),
    ("14:9-26", Span(14, 9, 14, 26)),        # the internal corpus's spelling
    ("14:9-15:3", Span(14, 9, 15, 3)),       # the suite's spelling
])
def test_at_accepts_all_three_spellings(write_case, spec, expected):
    text = (f"//! case:  X\n//! class: syntax.punct\n//! expect: error\n"
            f"//! at:    {spec}\n" + "package p { }\n" * 20)
    assert write_case("at.pss", text).at == expected


def test_unknown_directive_is_an_error(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
            "//! typo:  oops\npackage p { }\n")
    with pytest.raises(CaseFormatError, match="unknown directive 'typo'"):
        write_case("bad.pss", text)


def test_namespaced_directive_for_another_tool_is_ignored(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
            "//! toolb.whatever: fine\npackage p { }\n")
    case = write_case("ns.pss", text)
    assert case.tool_opts["toolb"]["whatever"] == "fine"


def test_a_tool_key_folds_dash_to_underscore(write_case):
    """`pssparser.max-errors:` and `pssparser.max_errors:` are one directive.

    Both spellings are in the corpus, and the runner looks up `max_errors`.
    Until they were folded, every `max-errors` case ran at the tool's default
    cap and measured the cap instead of the tool.
    """
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
            "//! pssparser.max-errors: 3\npackage p { }\n")
    case = write_case("dash.pss", text)
    assert case.tool_opts["pssparser"] == {"max_errors": "3"}


def test_duplicate_non_repeatable_directive_is_an_error(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
            "//! title: a\n//! title: b\npackage p { }\n")
    with pytest.raises(CaseFormatError, match="duplicate directive"):
        write_case("dup.pss", text)


def test_error_case_without_at_is_rejected(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: error\n"
            "package p { }\n")
    with pytest.raises(CaseFormatError, match="requires an 'at:'"):
        write_case("noat.pss", text)


def test_accept_case_with_at_is_rejected(write_case):
    text = ("//! case:  X\n//! class: accept.misc\n//! expect: accept\n"
            "//! at: 4:1\npackage p { }\n")
    with pytest.raises(CaseFormatError, match="must not carry 'at:'"):
        write_case("acceptat.pss", text)


def test_at_beyond_end_of_file_is_rejected(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: error\n"
            "//! at: 99:1\npackage p { }\n")
    with pytest.raises(CaseFormatError, match="outside the file"):
        write_case("far.pss", text)


def test_fix_synthesizes_the_control(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: error\n"
            "//! at: 5:14\n//! fix: 5:     int a;\n"
            "struct s {\n    int a\n}\n")
    case = write_case("fix.pss", text)
    control = case.control_source()
    assert "    int a;\n" in control
    # The header is preserved, so the control's line numbers still line up
    # with the case's -- which is what makes a diagnostic on one comparable to
    # a diagnostic on the other.
    assert control.splitlines()[0] == "//! case:  X"
    assert len(control.splitlines()) == len(case.source.splitlines())


def test_ok_sibling_beats_fix(write_case, tmp_path):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: error\n"
            "//! at: 5:14\n//! fix: 5:     int a;\n"
            "struct s {\n    int a\n}\n")
    case = write_case("both.pss", text)
    (tmp_path / "both.ok.pss").write_text("struct s { int a; }\n")
    assert case.control_source() == "struct s { int a; }\n"


def test_control_overrides_repair_a_companion_too(write_case, tmp_path):
    """A multifile case's defect can live in a file other than the case.

    That is the shape the `syntax.multifile` class exists to measure -- a tool
    has to attribute the diagnostic to the right file -- and a control that
    could only repair the case file itself could not express it: the broken
    companion would still be broken, so every such case would read
    `control_failed`.
    """
    text = ("//! case:  X\n//! class: syntax.multifile\n//! expect: error\n"
            "//! files: _lib.pss, comp.pss\n//! at-file: _lib.pss\n"
            "//! at: 1:14\npackage p { }\n")
    case = write_case("comp.pss", text)
    (tmp_path / "_lib.pss").write_text("struct s {\n    int a\n}\n")

    assert case.control_overrides() is None       # nothing repaired yet
    (tmp_path / "_lib.ok.pss").write_text("struct s {\n    int a;\n}\n")
    assert case.control_overrides() == {"_lib.pss": "struct s {\n    int a;\n}\n"}


def test_control_overrides_combine_both_files(write_case, tmp_path):
    text = ("//! case:  X\n//! class: syntax.multifile\n//! expect: error\n"
            "//! files: two.pss, _other.pss\n//! at: 6:10\n"
            "//! fix: 6:     int a;\n"
            "struct s {\n    int a\n}\n")
    case = write_case("two.pss", text)
    (tmp_path / "_other.pss").write_text("struct t {\n    int b\n}\n")
    (tmp_path / "_other.ok.pss").write_text("struct t {\n    int b;\n}\n")

    overrides = case.control_overrides()
    assert set(overrides) == {"two.pss", "_other.pss"}
    assert "    int a;\n" in overrides["two.pss"]


def test_at_in_a_companion_is_not_bounded_by_this_file(write_case, tmp_path):
    """`at:` counts the header only when it points into this file."""
    text = ("//! case:  X\n//! class: syntax.multifile\n//! expect: error\n"
            "//! files: _big.pss, small.pss\n//! at-file: _big.pss\n"
            "//! at: 400:1\npackage p { }\n")
    case = write_case("small.pss", text)      # 7 lines; `at:` is line 400
    assert case.at.line == 400


def test_files_must_include_the_case_itself(write_case):
    text = ("//! case:  X\n//! class: syntax.multifile\n//! expect: accept\n"
            "//! files: _a.pss, _b.pss\npackage p { }\n")
    with pytest.raises(CaseFormatError, match="must list this file"):
        write_case("mf.pss", text)


def test_header_stops_at_the_first_non_directive_line(write_case):
    text = ("//! case:  X\n//! class: syntax.punct\n//! expect: accept\n"
            "package p { }\n//! title: not a directive down here\n")
    case = write_case("stop.pss", text)
    assert case.title == ""


def test_a_cause_term_can_be_a_literal_comma(write_case):
    r"""A missing-separator case's whole defect is a `,`, and an accurate
    message for it says `','`. Without `\,` the term is unexpressible and the
    accuracy proxy would mark a good message down."""
    case = write_case("c.pss", "//! case:   X\n"
                               "//! class:  syntax.punct\n"
                               "//! expect: error\n"
                               "//! at:     5:1\n"
                               r"//! cause:  \,, argument" "\n"
                               "//! fix:    5: struct S { }\n"
                               "struct S { \n")
    assert case.cause == [",", "argument"]


def test_an_unescaped_comma_still_separates(write_case):
    case = write_case("c.pss", "//! case:   X\n"
                               "//! class:  syntax.punct\n"
                               "//! expect: error\n"
                               "//! at:     5:1\n"
                               "//! cause:  a, b,c\n"
                               "//! fix:    5: struct S { }\n"
                               "struct S { \n")
    assert case.cause == ["a", "b", "c"]
