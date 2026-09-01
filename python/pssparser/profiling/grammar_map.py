"""Grammar-source lookup: rule name -> line in ``PSSParser.g4``.

The decision-to-*rule* mapping comes from the ATN at runtime (see
``mkProfileSnapshot`` in ``src/ParseProfileInfo.cpp``) and is authoritative.
This module only adds the last hop -- rule to grammar line -- so every row of
a report is a clickable ``src/PSSParser.g4:NNN``.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Dict, Optional


#: A parser-rule declaration.  Parser rules start lowercase; lexer rules start
#: uppercase and never carry decisions, so excluding them costs nothing.
_RULE_DECL = re.compile(r"^\s*(?P<name>[a-z][a-zA-Z_0-9]*)\s*(?:\[[^\]]*\])?\s*:")


def find_grammar(explicit: Optional[str] = None) -> Optional[Path]:
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None
    path = Path(__file__).resolve().parents[3] / "src" / "PSSParser.g4"
    return path if path.is_file() else None


def rule_lines(grammar: Optional[Path]) -> Dict[str, int]:
    """``rule name -> 1-based line of its declaration``.

    A line-oriented scan, not a grammar parse.  It can in principle be fooled
    by a colon inside a multi-line action block; the consequence is one report
    row pointing at the wrong line, which is why nothing but display depends on
    it.  Rules seen twice keep the first line -- ANTLR would reject a genuine
    redefinition anyway, so a second hit means the scan was fooled.
    """
    ret: Dict[str, int] = {}
    if grammar is None:
        return ret
    for lineno, line in enumerate(
            grammar.read_text(encoding="utf-8").splitlines(), start=1):
        m = _RULE_DECL.match(line)
        if m and m.group("name") not in ret:
            ret[m.group("name")] = lineno
    return ret


def grammar_sha(grammar: Optional[Path]) -> str:
    """SHA-256 of the grammar, short form.

    Stamped into every profile.  Two profiles with the same ``grammar_sha``
    must produce identical counters; if they do not, the harness is
    non-deterministic and nothing it reports can be trusted.
    """
    if grammar is None or not grammar.is_file():
        return "unknown"
    return hashlib.sha256(grammar.read_bytes()).hexdigest()[:12]
