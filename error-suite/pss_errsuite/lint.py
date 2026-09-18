"""Message lints, tool-agnostic (design §4.4).

These are the G3/G6/G7 lints that already run over pssparser's own markers
(`tests/python/errors/test_message_lints.py`), lifted here so both callers use
one implementation.  Applied to *any* tool's output they are observations, not
failures -- another vendor's jargon is not our business, but it is exactly the
comparison worth seeing.

The jargon list is ANTLR-flavoured because that is what leaks in practice.  A
tool built on something else will leak something else; add it here when it
shows up rather than guessing now.
"""
from __future__ import annotations

import re

JARGON_PHRASES = (
    "mismatched input",
    "no viable alternative",
    "extraneous input",
    "rule stack",
    "recognition error",
)

# An ANTLR "expecting" token set: `{'::', ID, ESCAPED_ID}`.  Anchored to
# "expecting {" rather than searching for any braced list, because an
# unanchored search reads the perfectly clean message "expected '{' before '}'"
# as a token set -- a false positive pssparser's own mutation sweep found.
TOKEN_SET_RE = re.compile(
    r"expecting \{\s*(?:'[^']*'|[A-Z_][A-Z0-9_]*)"
    r"(?:\s*,\s*(?:'[^']*'|[A-Z_][A-Z0-9_]*))*\s*\}"
)

#: A message that is nothing but a token or an upper-case grammar symbol.
BARE_TOKEN_RE = re.compile(r"^\s*(?:'[^']*'|[A-Z_][A-Z0-9_]*)\s*$")

MAX_LENGTH = 120

# Lint identifiers, stable because they end up in run files.
G3_JARGON = "G3-jargon"
G6_NO_CODE = "G6-no-code"
G7_LENGTH = "G7-length"
G7_NEWLINE = "G7-newline"
L_NO_LOCATION = "L-no-location"
L_BARE_TOKEN = "L-bare-token"


def _word_re(name: str) -> re.Pattern:
    return re.compile(r"\b" + re.escape(name) + r"\b")


def jargon_violation(message: str, token_names=()) -> bool:
    """True if *message* leaks a grammar/implementation internal.

    Deliberately does **not** match parser *rule* names: `identifier`,
    `expression`, `declaration` are ordinary English words a good message is
    expected to contain, and matching them produced overwhelming false
    positives.  Lexer token names (`ID`, `ESCAPED_ID`, `TOK_*`) are
    unambiguous -- always upper-case, never legitimate prose -- so callers that
    have a token list may pass it.
    """
    lowered = message.lower()
    if any(phrase in lowered for phrase in JARGON_PHRASES):
        return True
    if TOKEN_SET_RE.search(message):
        return True
    for name in token_names:
        if len(name) > 1 and _word_re(name).search(message):
            return True
    return False


def length_violation(message: str) -> bool:
    return len(message) > MAX_LENGTH


def newline_violation(message: str) -> bool:
    return "\n" in message


def bare_token_violation(message: str) -> bool:
    return bool(BARE_TOKEN_RE.match(message))


def lint_message(message: str, *, has_location: bool = True,
                 has_code: bool = True, token_names=()) -> list[str]:
    out = []
    if jargon_violation(message, token_names):
        out.append(G3_JARGON)
    if length_violation(message):
        out.append(G7_LENGTH)
    if newline_violation(message):
        out.append(G7_NEWLINE)
    if bare_token_violation(message):
        out.append(L_BARE_TOKEN)
    if not has_location:
        out.append(L_NO_LOCATION)
    if not has_code:
        out.append(G6_NO_CODE)
    return out


def lint_diagnostic(diag, token_names=()) -> list[str]:
    return lint_message(diag.message, has_location=diag.has_location,
                        has_code=bool(diag.code), token_names=token_names)
