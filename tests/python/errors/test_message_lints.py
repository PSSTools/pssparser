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

_JARGON_PHRASES = [
    "mismatched input",
    "no viable alternative",
    "extraneous input",
]
# An ANTLR "expecting" token set: '{' followed by comma-separated quoted or
# bare-uppercase tokens and '}', e.g. "{'::', ID, ESCAPED_ID}". Anchored to
# "expecting {" (how ANTLR always introduces a raw set) rather than a bare
# "{ ... }" search -- E-7's mutation sweep found a false positive on a
# perfectly clean, already-humanized message, "expected '{' before '}'":
# the quoted '{' and '}' are two *different* single-token literals with
# ordinary English between them ("before"), and an unanchored search reads
# that "before" as if it were one comma-separated element of a set.
_TOKEN_SET_RE = re.compile(
    r"expecting \{\s*(?:'[^']*'|[A-Z_][A-Z0-9_]*)"
    r"(?:\s*,\s*(?:'[^']*'|[A-Z_][A-Z0-9_]*))*\s*\}"
)


def _word_re(name: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(name) + r"\b")


def _g3_violation(message: str, token_names) -> bool:
    """True if *message* leaks an ANTLR/grammar internal.

    Deliberately does NOT word-match parser rule names from PSSParser.g4:
    rule names like ``identifier``, ``expression``, ``declaration`` are
    ordinary English words that a *good* rewritten message is expected to
    contain, so that check produced overwhelming false positives in
    practice (see error-testing-plan.md's E-2 "Landed" note). Lexer token
    names (``ID``, ``ESCAPED_ID``, ``TOK_*``) are unambiguous, since they are
    always upper-case/underscored and never legitimate English prose.
    """
    for phrase in _JARGON_PHRASES:
        if phrase in message:
            return True
    if _TOKEN_SET_RE.search(message):
        return True
    for name in token_names:
        if len(name) > 1 and _word_re(name).search(message):
            return True
    return False


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
        if (len(m["message"]) > 120 or "\n" in m["message"])
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
            len(m["message"]) > 120 or "\n" in m["message"] for m in matching
        ):
            stale.append(entry)

    assert not stale, (
        "lint_allowlist.txt entries no longer matching any current "
        "violation -- delete them:\n" +
        "\n".join(
            f"  line {e.lineno}: {e.lint}: {e.pattern!r}" for e in stale
        )
    )
