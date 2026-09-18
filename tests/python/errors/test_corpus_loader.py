"""Tests for the //! header parser (corpus_loader.py)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from .corpus_loader import CorpusFormatError, parse_case  # noqa: E402


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text)
    return p


def test_parses_all_directives(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id:     PSS020\n"
        "//! at:     3:5-7\n"
        "//! match:  expected ';'\n"
        "//! also:   1:1 \"opened here\"\n"
        "//! also:   2:2 \"and here\"\n"
        "//! count:  2\n"
        "//! severity: warning\n"
        "//! hint:   did you mean\n"
        "//! max-errors: 5\n"
        "struct S { int x }\n"
    ))
    case = parse_case(path)
    assert case.id == "PSS020"
    assert case.at == (3, 5, 7)
    assert case.match == "expected ';'"
    assert not case.match_is_regex
    assert len(case.also) == 2
    assert case.also[0].line == 1 and case.also[0].label == "opened here"
    assert case.count == 2
    assert case.severity == "warning"
    assert case.hint == "did you mean"
    assert case.max_errors == 5
    assert case.xfail is None


def test_regex_match_directive(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id:    PSS020\n"
        "//! match: /expected .*;/\n"
        "x\n"
    ))
    case = parse_case(path)
    assert case.match_is_regex
    assert case.match == "expected .*;"


def test_xfail_directive_carries_reason(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id:    PSS020\n"
        "//! match: expected ';'\n"
        "//! xfail: D1 -- jargon leak\n"
        "x\n"
    ))
    case = parse_case(path)
    assert case.xfail == "D1 -- jargon leak"


def test_unknown_directive_is_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id:    PSS020\n"
        "//! matchh: expected ';'\n"
        "x\n"
    ))
    with pytest.raises(CorpusFormatError):
        parse_case(path)


def test_malformed_at_is_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id: PSS020\n"
        "//! at: not-a-location\n"
        "x\n"
    ))
    with pytest.raises(CorpusFormatError):
        parse_case(path)


def test_also_without_a_label_is_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id: PSS020\n"
        "//! match: x\n"
        "//! also: 1:1\n"
        "x\n"
    ))
    with pytest.raises(CorpusFormatError):
        parse_case(path)


def test_missing_id_is_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! match: expected ';'\n"
        "x\n"
    ))
    with pytest.raises(CorpusFormatError):
        parse_case(path)


def test_missing_at_and_match_is_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! id: PSS020\n"
        "x\n"
    ))
    with pytest.raises(CorpusFormatError):
        parse_case(path)


# -- convergence with the tool-neutral suite (error-suite-plan.md X-2a) ------
#
# The two loaders read the same files.  These tests pin the parts of that
# agreement that a refactor could quietly break: the shared vocabulary, the
# namespacing rule, and -- the one that matters -- that both readers extract
# the *same facts* from every case in the shipped suite corpus.

from pss_errsuite import case as suite_case  # noqa: E402
from .corpus_loader import neutral_view  # noqa: E402

ERROR_SUITE_CASES = (
    Path(__file__).parent.parent.parent.parent / "error-suite" / "cases"
)


def test_neutral_directives_are_accepted(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! case:    SYN-PUNCT-SEMI-01\n"
        "//! class:   syntax.punct\n"
        "//! title:   missing ';'\n"
        "//! expect:  error\n"
        "//! detect:  required\n"
        "//! at:      8:14\n"
        "//! lrm:     B.11\n"
        "//! pss:     3.1\n"
        "//! tags:    struct, field\n"
        "//! fix:     8:     int a;\n"
        "//! cause:   ;\n"
        "//! names:   a\n"
        "struct s {\n    int a\n}\n"
    ))
    case = parse_case(path)
    assert case.case_id == "SYN-PUNCT-SEMI-01"
    assert case.cls == "syntax.punct"
    assert case.expect == "error"
    assert case.detect == "required"
    assert case.lrm == "B.11"
    assert case.tags == ["struct", "field"]
    assert case.fix == [(8, "    int a;")]
    assert case.cause == [";"]
    # `expect:` supplies the severity when the native directive is absent.
    assert case.severity == "error"


def test_our_namespace_sets_the_native_directive(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! case:   X\n"
        "//! class:  syntax.punct\n"
        "//! expect: error\n"
        "//! at:     5:1\n"
        "//! pssparser.id:    PSS020\n"
        "//! pssparser.match: expected ';'\n"
        "//! xfail.pssparser: D1 -- jargon\n"
        "struct S { int x }\n"
    ))
    case = parse_case(path)
    assert case.id == "PSS020"
    assert case.match == "expected ';'"
    assert case.xfail == "D1 -- jargon"


def test_another_tools_directives_are_carried_not_applied(tmp_path):
    """A third party's expectations must not silently become ours -- most
    sharply for `xfail`, where inheriting someone else's known-bad would
    disable one of our assertions."""
    path = _write(tmp_path, "case.pss", (
        "//! case:   X\n"
        "//! class:  syntax.punct\n"
        "//! expect: error\n"
        "//! at:     6:1\n"
        "//! toolb.id:    TB-9\n"
        "//! xfail.toolb: their known-bad\n"
        "struct S { int x }\n"
    ))
    case = parse_case(path)
    assert case.id is None
    assert case.xfail is None
    assert case.other_tools == {"toolb": {"id": "TB-9",
                                          "xfail": "their known-bad"}}


def test_an_unknown_key_in_our_namespace_is_still_an_error(tmp_path):
    path = _write(tmp_path, "case.pss", (
        "//! case:   X\n//! class:  syntax.punct\n//! expect: error\n"
        "//! at:     5:1\n//! pssparser.whatever: x\nstruct S { int x }\n"
    ))
    with pytest.raises(CorpusFormatError, match="unknown directive"):
        parse_case(path)


def test_accept_cases_need_neither_at_nor_match(tmp_path):
    path = _write(tmp_path, "ok.pss", (
        "//! case:   ACC-1\n//! class:  accept.misc\n//! expect: accept\n"
        "struct S { int x; }\n"
    ))
    assert parse_case(path).expect == "accept"


@pytest.mark.parametrize("spec,expected", [
    ("3:5", (3, 5, None)),
    ("3:5-7", (3, 5, 7)),
    ("3:5-3:7", (3, 5, 7)),
])
def test_at_accepts_the_suites_span_spelling(tmp_path, spec, expected):
    path = _write(tmp_path, "case.pss", (
        f"//! id: PSS020\n//! at: {spec}\nstruct S {{ int x }}\n"))
    assert parse_case(path).at == expected


def test_a_multi_line_span_keeps_the_full_extent_but_not_a_same_line_end(
        tmp_path):
    """`at`'s third element is a same-line end column and cannot hold a span
    that crosses lines; `at_end` keeps what was written either way."""
    path = _write(tmp_path, "case.pss", (
        "//! id: PSS020\n//! at: 3:5-4:7\nstruct S { int x }\n"))
    case = parse_case(path)
    assert case.at == (3, 5, None)
    assert case.at_end == (4, 7)


@pytest.mark.skipif(not ERROR_SUITE_CASES.is_dir(),
                    reason="error-suite/ is not present in this tree")
def test_both_loaders_extract_the_same_facts_from_every_suite_case():
    """The convergence property itself.

    If the two readers ever disagree about what a header says, one of the two
    corpora is quietly running different cases than its author thinks -- and
    the disagreement would show up as an inexplicable diff in a run file rather
    than as a failure anywhere near the cause.
    """
    suite_cases = suite_case.collect_cases(ERROR_SUITE_CASES)
    assert suite_cases, "the suite corpus is empty"
    for sc in suite_cases:
        ours = parse_case(sc.path)
        assert neutral_view(ours) == suite_case.neutral_view(sc), sc.name
