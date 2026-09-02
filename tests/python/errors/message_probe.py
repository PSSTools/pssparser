"""Session-wide marker sink + grammar rule-name harvesting, for E-2's global
lints (test_message_lints.py).

Rather than hooking every call site individually, ``test_helpers.parse_collect``
appends every marker it produces to ``test_helpers.ALL_MARKERS``. This module
exposes an accessor for that sink, plus the lexer/parser rule names harvested
from the grammar files -- both are used by the G3 jargon lint to catch a
message that leaked ANTLR internals (a rule name, a token name) instead of
plain English.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Set

sys.path.insert(0, str(Path(__file__).parent.parent))

import test_helpers  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent.parent.parent
PARSER_GRAMMAR = REPO_ROOT / "src" / "PSSParser.g4"
LEXER_GRAMMAR = REPO_ROOT / "src" / "PSSLexer.g4"
ALLOWLIST_PATH = Path(__file__).parent / "lint_allowlist.txt"

_PARSER_RULE_RE = re.compile(r"^([a-z][a-zA-Z0-9_]*)\s*:", re.MULTILINE)
_LEXER_TOKEN_RE = re.compile(r"^([A-Z][A-Z0-9_]*)\s*:", re.MULTILINE)


def all_markers() -> List[dict]:
    """Every marker produced via parse_collect() so far this session."""
    return list(test_helpers.ALL_MARKERS)


def all_batches() -> List[List[dict]]:
    """Marker lists grouped by the parse_collect() call that produced them."""
    return [list(b) for b in test_helpers.ALL_MARKER_BATCHES]


def parser_rule_names() -> Set[str]:
    """Rule names declared in PSSParser.g4 (e.g. 'constraint_expression')."""
    text = PARSER_GRAMMAR.read_text()
    return set(_PARSER_RULE_RE.findall(text))


def lexer_token_names() -> Set[str]:
    """Token names declared in PSSLexer.g4 (e.g. 'TOK_LBRACE', 'ID')."""
    text = LEXER_GRAMMAR.read_text()
    return set(_LEXER_TOKEN_RE.findall(text))


@dataclass
class AllowlistEntry:
    lint: str
    pattern: str
    reason: str
    lineno: int


def load_allowlist() -> List[AllowlistEntry]:
    """Parse lint_allowlist.txt: '<LINT>: <pattern>  # owner//reason' per line."""
    entries: List[AllowlistEntry] = []
    if not ALLOWLIST_PATH.exists():
        return entries
    for lineno, raw in enumerate(ALLOWLIST_PATH.read_text().splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        body, _, reason = line.partition("#")
        lint, sep, pattern = body.partition(":")
        if not sep:
            raise ValueError(
                f"{ALLOWLIST_PATH}:{lineno}: malformed line (expected "
                f"'LINT: pattern  # reason'): {raw!r}"
            )
        entries.append(AllowlistEntry(
            lint=lint.strip(),
            pattern=pattern.strip(),
            reason=reason.strip(),
            lineno=lineno,
        ))
    return entries


def allowed_patterns(lint: str, entries: List[AllowlistEntry]) -> List[str]:
    return [e.pattern for e in entries if e.lint == lint]
