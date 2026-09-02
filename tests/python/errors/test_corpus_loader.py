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
