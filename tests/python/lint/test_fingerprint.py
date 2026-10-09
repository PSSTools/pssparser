"""Finding fingerprints (lint-framework-plan F2.3).

A fingerprint hashes a finding's code, its enclosing declaration and the
normalised text it flags -- never its line or column -- so a baseline keeps
recognising it while the file around it is edited.
"""
from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from pssparser import Parser, tokens
from pssparser.lint.declpath import index_for
from pssparser.lint.fingerprint import (Fingerprinter, digest, fingerprint,
                                        normalised_span)

ROOT = Path(__file__).resolve().parents[3]


def _fp(src, line, col, extent=0, code="LINT999"):
    """The fingerprint of a toy finding at *line*:*col* in *src*."""
    p = Parser()
    p.parses([("m.pss", src)])
    fp = Fingerprinter(index_for(p, ["m.pss"]), read=lambda f: src)
    return fp({"code": code, "file": "m.pss", "line": line, "col": col,
               "extent": extent})


def _at(src, needle, extent=None):
    """(line, col, extent) of the first *needle* in *src*, 1-based."""
    off = src.index(needle)
    line = src.count("\n", 0, off) + 1
    col = off - (src.rfind("\n", 0, off) + 1) + 1
    return line, col, len(needle) if extent is None else extent


MODEL = """\
package p {
  struct s {
    rand int a;
    constraint c { a > 1 + 2; }
  }
  struct t {
    rand int a;
    constraint c { a > 1 + 2; }
  }
}
"""


# ---------------------------------------------------------------------------
# The normalised span
# ---------------------------------------------------------------------------

def test_span_is_code_tokens_joined_by_spaces():
    src = "struct s { int  a ; /* c */ int b; }\n"
    line, col, n = _at(src, "int  a ; /* c */ int b")
    assert normalised_span(src, line, col, n) == "int a ; int b"


def test_span_with_no_extent_is_the_token_at_the_column():
    src = "struct s { int a; }\n"
    assert normalised_span(src, 1, 8) == "s"
    assert normalised_span(src, 1, 7) == "s"  # on whitespace: the next token


def test_span_may_cross_lines():
    src = "struct s {\n  int a;\n}\n"
    assert normalised_span(src, 1, 10, 9) == "{ int a"


def test_span_outside_the_file_is_empty():
    assert normalised_span("struct s {}\n", 9, 1) == ""


def test_fingerprint_accepts_a_token_stream():
    src = "struct s { int a; }\n"
    d = {"code": "LINT999", "line": 1, "col": 8, "extent": 1}
    assert fingerprint(d, "s", src) == fingerprint(d, "s", tokens.tokenize(src))
    assert fingerprint(d, "s", src) == digest("LINT999", "s", "s")


# ---------------------------------------------------------------------------
# What a fingerprint is stable under, and what changes it
# ---------------------------------------------------------------------------

def test_stable_when_lines_are_inserted_above():
    before = _fp(MODEL, *_at(MODEL, "a > 1 + 2"))
    edited = "// header\n\n" + MODEL.replace("  struct s {", "\n  struct s {")
    assert _fp(edited, *_at(edited, "a > 1 + 2")) == before


def test_stable_under_whitespace_and_comments_inside_the_span():
    before = _fp(MODEL, *_at(MODEL, "a > 1 + 2"))
    edited = MODEL.replace("a > 1 + 2;", "a  >  1 /* x */\n      + 2;", 1)
    assert _fp(edited, *_at(edited, "a  >  1 /* x */\n      + 2")) == before


def test_changes_when_the_flagged_text_changes():
    before = _fp(MODEL, *_at(MODEL, "a > 1 + 2"))
    edited = MODEL.replace("a > 1 + 2;", "a > 1 + 3;", 1)
    assert _fp(edited, *_at(edited, "a > 1 + 3")) != before


def test_changes_when_the_finding_moves_to_another_declaration():
    first = MODEL.index("a > 1 + 2")
    second = MODEL.index("a > 1 + 2", first + 1)
    line1, col1, n = _at(MODEL, "a > 1 + 2")
    tail = MODEL[second:]
    line2 = MODEL.count("\n", 0, second) + 1
    col2 = second - MODEL.rfind("\n", 0, second)
    assert tail.startswith("a > 1 + 2")
    assert _fp(MODEL, line1, col1, n) != _fp(MODEL, line2, col2, n)


def test_changes_with_the_code():
    loc = _at(MODEL, "a > 1 + 2")
    assert _fp(MODEL, *loc, code="LINT998") != _fp(MODEL, *loc)


def test_no_fingerprint_without_a_code_or_a_location():
    fp = Fingerprinter(None, read=lambda f: "struct s {}\n")
    assert fp({"file": "m.pss", "line": 1, "col": 1}) is None
    assert fp({"code": "LINT999", "file": "m.pss", "line": 0, "col": 0}) is None


def test_unreadable_file_has_no_fingerprint(tmp_path):
    fp = Fingerprinter(None)
    assert fp({"code": "LINT999", "file": str(tmp_path / "gone.pss"),
               "line": 1, "col": 1}) is None


def test_a_diagnostic_span_comes_from_end_col():
    from pssparser.cli.diagnostics import Diagnostic

    src = "struct s { int abc; }\n"
    d = Diagnostic(file="m.pss", line=1, col=16, severity="warning",
                   message="m", code="LINT999", end_col=19)
    fp = Fingerprinter(None, read=lambda f: src)
    assert fp(d) == digest("LINT999", "", "abc")


# ---------------------------------------------------------------------------
# pssfmt (design Q7)
# ---------------------------------------------------------------------------

def _toy_findings(src, name):
    """Fingerprints of a toy rule that flags every identifier."""
    p = Parser()
    p.parses([(name, src)])
    fp = Fingerprinter(index_for(p, [name]), read=lambda f: src)
    found = Counter()
    for t in tokens.tokenize(src).code():
        if t.type_name == "ID":
            found[fp({"code": "LINT999", "file": name, "line": t.line,
                      "col": t.col + 1, "extent": len(t.text)})] += 1
    return found


def _corpus_sample():
    base = ROOT / "packages" / "pss-corpus"
    files = sorted(base.glob("**/*.pss")) if base.is_dir() else []
    # Every eighth file: enough variety, a bounded run time.
    return files[::8]


@pytest.mark.parametrize("path", _corpus_sample(), ids=lambda p: p.name)
def test_stable_under_pssfmt(path):
    pytest.importorskip("pssfmt")
    from pssfmt.cli import run_format
    from pssfmt.style import DEFAULT_STYLE

    src = path.read_text(encoding="utf-8")
    try:
        before = _toy_findings(src, path.name)
    except Exception:
        pytest.skip("does not parse")
    result = run_format(src, DEFAULT_STYLE)
    if not result.ok:
        pytest.skip("pssfmt declined to format the file")
    if result.text == src:
        pytest.skip("pssfmt left the file unchanged")
    assert _toy_findings(result.text, path.name) == before
