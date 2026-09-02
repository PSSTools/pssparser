"""Grammar-source lookup: rule name -> line in ``PSSParser.g4``.

The decision-to-*rule* mapping comes from the ATN at runtime (see
``mkProfileSnapshot`` in ``src/ParseProfileInfo.cpp``) and is authoritative.
This module only adds the last hop -- rule to grammar line -- so every row of
a report is a clickable ``src/PSSParser.g4:NNN``.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Optional


#: A parser-rule declaration.  Parser rules start lowercase; lexer rules start
#: uppercase and never carry decisions, so excluding them costs nothing.
_RULE_DECL = re.compile(r"^\s*(?P<name>[a-z][a-zA-Z_0-9]*)\s*(?:\[[^\]]*\])?\s*:")


#: Where the grammar sits relative to a checkout root.
_GRAMMAR_RELPATH = Path("src") / "PSSParser.g4"


def find_grammar(explicit: Optional[str] = None) -> Optional[Path]:
    """Locate ``src/PSSParser.g4``, or ``None`` if this is not a checkout.

    The grammar is a BUILD input: ANTLR consumes it to generate the parser, and
    it is deliberately not shipped in the wheel.  So this can only ever find it
    in a source tree, and the three probes below are three different ways of
    being in one:

    1. ``explicit`` -- ``--grammar`` on ``scripts/profile_grammar.py``.
    2. ``$PSSPARSER_GRAMMAR`` -- the escape hatch for a layout none of the rest
       anticipates.
    3. ``parents[3]`` -- this module at ``<repo>/python/pssparser/profiling/``,
       i.e. the parser is being imported straight out of the checkout.
    4. **cwd and its ancestors** -- the parser is an INSTALLED WHEEL, but the
       tests are being run from the checkout.  That is not an edge case, it is
       how CI runs: a clean venv with the wheel in it, ``pytest tests/python``
       from the repository root.  Probe 3 resolves into site-packages there and
       finds nothing, which left ``grammar_sha`` returning ``"unknown"`` and
       took three profiling tests red on the v3.1.0 tag build.
    """
    if explicit:
        path = Path(explicit)
        return path if path.is_file() else None

    env = os.environ.get("PSSPARSER_GRAMMAR")
    if env:
        path = Path(env)
        return path if path.is_file() else None

    path = Path(__file__).resolve().parents[3] / _GRAMMAR_RELPATH
    if path.is_file():
        return path

    cwd = Path.cwd().resolve()
    for base in (cwd, *cwd.parents):
        candidate = base / _GRAMMAR_RELPATH
        if candidate.is_file():
            return candidate
    return None


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
