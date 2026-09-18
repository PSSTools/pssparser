"""E-2: global message-quality lints, applied to every marker any test
produced via parse_collect() this session (see message_probe.py).

These tests are reordered to run last (tests/python/conftest.py) since the
marker sink they inspect is only complete once every other test has run.

G3 (jargon), G6 (has-a-code), G7 (length) come straight off the rubric in
docs/design/error-testing-strategy.md. G8 covers two invariants: markers from
one parse are in (file, line, col) order, and re-parsing identical source is
deterministic. Anything a lint would otherwise fail on but hasn't been fixed
yet is recorded in lint_allowlist.txt -- that file is the debt list, and it
must not silently grow stale (see test_allowlist_has_no_stale_entries).
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect  # noqa: E402

from .message_probe import (  # noqa: E402
    all_batches,
    all_markers,
    allowed_patterns,
    lexer_token_names,
    load_allowlist,
)

# The predicates themselves live in the tool-neutral suite
# (``error-suite/pss_errsuite/lint.py``) so that pssparser's markers and
# another vendor's messages are judged by exactly one implementation -- see
# docs/design/error-suite-design.md §4.4. The rationale that used to live here
# (why rule names are not matched, why the token-set regex is anchored to
# "expecting {") moved with the code.
from pss_errsuite.lint import (  # noqa: E402
    JARGON_PHRASES as _JARGON_PHRASES,
    TOKEN_SET_RE as _TOKEN_SET_RE,
    jargon_violation as _g3_violation,
    length_violation as _g7_length_violation,
    newline_violation as _g7_newline_violation,
)


def _allowed(message: str, patterns) -> bool:
    return any(p in message for p in patterns)


def test_g3_no_antlr_jargon_leaks():
    entries = load_allowlist()
    patterns = allowed_patterns("G3", entries)
    token_names = lexer_token_names()

    violations = [
        m for m in all_markers()
        if _g3_violation(m["message"], token_names)
        and not _allowed(m["message"], patterns)
    ]
    assert not violations, (
        "messages leak ANTLR jargon (grammar rule/token names or a raw "
        "expecting-set) and are not in lint_allowlist.txt:\n" +
        "\n".join(f"  {m['message']!r}" for m in violations)
    )


def test_g6_every_marker_has_a_code():
    entries = load_allowlist()
    patterns = allowed_patterns("G6", entries)

    violations = [
        m for m in all_markers()
        if not m.get("code") and not _allowed(m["message"], patterns)
    ]
    assert not violations, (
        "markers with no 'code' and not in lint_allowlist.txt:\n" +
        "\n".join(f"  {m['message']!r}" for m in violations)
    )


def test_g7_message_is_one_short_line():
    entries = load_allowlist()
    patterns = allowed_patterns("G7", entries)

    violations = [
        m for m in all_markers()
        if (_g7_length_violation(m["message"])
            or _g7_newline_violation(m["message"]))
        and not _allowed(m["message"], patterns)
    ]
    assert not violations, (
        "messages over 120 chars or containing a newline, not in "
        "lint_allowlist.txt:\n" +
        "\n".join(f"  {m['message']!r}" for m in violations)
    )


def test_g8_markers_within_a_parse_are_ordered():
    entries = load_allowlist()
    patterns = allowed_patterns("G8", entries)

    for batch in all_batches():
        keys = [(m["file"], m["line"], m["col"]) for m in batch]
        if keys != sorted(keys) and not any(
            _allowed(m["message"], patterns) for m in batch
        ):
            pytest.fail(
                "markers from one parse were not emitted in (file, line, "
                f"col) order: {keys}"
            )


def test_g8_reparse_is_deterministic():
    samples = [
        "struct S { int x }",
        "component { }",
        "rand struct S { };",
        "struct S { int x; ",
    ]
    for src in samples:
        _root1, markers1 = parse_collect(src)
        _root2, markers2 = parse_collect(src)
        assert markers1 == markers2, (
            f"two parses of the same source produced different markers:\n"
            f"  1st: {markers1}\n  2nd: {markers2}"
        )


def test_no_debug_output_leaks_when_a_marker_collector_is_installed(capfd):
    """D3: AstBuilderInt::syntaxError used to fprintf a raw "Error: Syntax
    error: line=... pos=... sym=..." line before creating the marker, so
    every syntax error was reported twice -- once as a structured marker,
    once as unstructured noise. It went to *stdout*, not stderr (the plan's
    original "stderr silence" framing was wrong -- DEBUG_MACROS.h's fallback
    branch is an explicit fprintf(stdout, ...)); capfd is used rather than
    pytest's capsys because that fprintf goes through the C stdio layer, at
    the OS file-descriptor level, which capsys does not intercept.
    """
    capfd.readouterr()  # drop anything buffered from earlier in the session
    parse_collect("struct S { int x }")
    out, err = capfd.readouterr()
    assert out == "", f"unexpected stdout: {out!r}"
    assert err == "", f"unexpected stderr: {err!r}"


def test_allowlist_has_no_stale_entries():
    entries = load_allowlist()
    if not entries:
        pytest.skip("allowlist is empty")

    token_names = lexer_token_names()
    markers = all_markers()

    stale = []
    for entry in entries:
        matching = [m for m in markers if entry.pattern in m["message"]]
        if not matching:
            stale.append(entry)
            continue
        if entry.lint == "G3" and not any(
            _g3_violation(m["message"], token_names) for m in matching
        ):
            stale.append(entry)
        elif entry.lint == "G6" and not any(
            not m.get("code") for m in matching
        ):
            stale.append(entry)
        elif entry.lint == "G7" and not any(
            _g7_length_violation(m["message"])
            or _g7_newline_violation(m["message"]) for m in matching
        ):
            stale.append(entry)

    assert not stale, (
        "lint_allowlist.txt entries no longer matching any current "
        "violation -- delete them:\n" +
        "\n".join(
            f"  line {e.lineno}: {e.lint}: {e.pattern!r}" for e in stale
        )
    )
