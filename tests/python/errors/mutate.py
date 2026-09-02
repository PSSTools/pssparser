"""E-7: mechanical mutation operators, driven off the real lexer token stream
(``pssparser.tokens.tokenize``) so every mutation lands exactly on a token
boundary -- see docs/design/error-testing-strategy.md §4 L2.

Each operator takes a known-good source string plus one lexer :class:`Token`
(from that source's own ``tokenize()`` call) and returns a mutated source
string, built by slicing the *original* text around the token's
``start``/``stop`` offsets. Every operator's replacement text starts at or
after ``tok.start``, so the prefix ``src[:tok.start]`` is untouched -- which
is what lets :func:`iter_mutants` hand back the token's original
``(line, col)`` as the mutation site and have it still be correct against the
mutated source (see test_mutation_sweep.py's G1 check).

+-------------------+------------------------------------------------+
| Operator          | Injects                                         |
+===================+==================================================+
| delete-token      | omitted ``;``, ``)``, name, keyword             |
| duplicate-token   | doubled punctuation                             |
| swap-adjacent     | transposed tokens                               |
| keyword-for-name  | reserved word where an identifier belongs       |
| punct-substitute  | ``;``->``,``, ``:``->``::``, ``=``->``==``, ``{``->``(`` |
| truncate          | file cut at each token boundary                 |
| drop-close-brace  | brace imbalance at each depth                   |
+-------------------+------------------------------------------------+
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

from pssparser.tokens import Token, TokenStream, tokenize

REPO_ROOT = Path(__file__).parent.parent.parent.parent
LEXER_GRAMMAR = REPO_ROOT / "src" / "PSSLexer.g4"

#: One sample per operator per source file by default (§8's "fixed sample
#: per source file"); --errors-full switches to every candidate.
DEFAULT_SAMPLE = 3

_KEYWORD_RE = re.compile(r"^TOK_[A-Z_0-9]+\s*:\s*'([a-z_][a-z_0-9]*)'\s*;", re.MULTILINE)

_PUNCT_SUBSTITUTIONS = {
    ";": ",",
    ":": "::",
    "=": "==",
    "{": "(",
}


def reserved_keywords() -> List[str]:
    """Keyword literals declared in PSSLexer.g4 (e.g. 'struct', 'return')."""
    text = LEXER_GRAMMAR.read_text()
    return sorted(set(_KEYWORD_RE.findall(text)))


@dataclass(frozen=True)
class Mutant:
    operator: str
    source: str
    site_line: int
    site_col: int
    description: str
    #: text of the token the mutation was anchored on -- lets a consumer
    #: recognize e.g. a brace/paren mutation, which can legitimately desync
    #: recovery for the rest of the file (see test_mutation_sweep.py's G2
    #: nesting-mutation carve-out).
    site_text: str = ""
    #: swap-adjacent only: the *other* token's original (line, col). A swap
    #: disturbs two positions, and which one the parser actually trips on
    #: depends on the surrounding grammar -- G1 accepts either.
    site_line2: int = 0
    site_col2: int = 0


def code_tokens(ts: TokenStream) -> List[Token]:
    """Non-trivia tokens, in source order."""
    return [t for t in ts if not t.is_trivia]


def _sample(items: Sequence, n: int) -> List:
    if n is None or len(items) <= n:
        return list(items)
    if n <= 0:
        return []
    step = len(items) / n
    idxs = sorted({int(i * step) for i in range(n)})
    return [items[i] for i in idxs]


def _splice(src: str, tok: Token, replacement: str) -> str:
    return src[:tok.start] + replacement + src[tok.stop + 1:]


def delete_token(src: str, tok: Token) -> str:
    return _splice(src, tok, "")


def duplicate_token(src: str, tok: Token) -> str:
    return src[:tok.stop + 1] + tok.text + src[tok.stop + 1:]


def swap_adjacent(src: str, tok_a: Token, tok_b: Token) -> str:
    return (src[:tok_a.start] + tok_b.text + src[tok_a.stop + 1:tok_b.start]
            + tok_a.text + src[tok_b.stop + 1:])


def keyword_for_name(src: str, tok: Token, keyword: str) -> str:
    return _splice(src, tok, keyword)


def punct_substitute(src: str, tok: Token, replacement: str) -> str:
    return _splice(src, tok, replacement)


def truncate(src: str, tok: Token) -> str:
    """Cut the file right after *tok* -- everything that follows is gone."""
    return src[:tok.stop + 1]


def drop_close_brace(src: str, tok: Token) -> str:
    return _splice(src, tok, "")


def _is_punct(tok: Token) -> bool:
    return bool(tok.text) and not (tok.text[0].isalnum() or tok.text[0] == "_")


def iter_mutants(name: str, src: str, *, full: bool = False,
                  sample: int = DEFAULT_SAMPLE) -> Iterator[Mutant]:
    """Every mutant §4 L2's seven operators produce for *src*, sampled.

    Deterministic: candidates are taken in source (token) order and, when
    not exhaustive, evenly spaced through the candidate list -- no RNG, so a
    failure reproduces without pinning a seed.
    """
    ts = tokenize(src)
    code = code_tokens(ts)
    keywords = reserved_keywords()

    def take(cands):
        return cands if full else _sample(cands, sample)

    for tok in take(code):
        yield Mutant("delete-token", delete_token(src, tok), tok.line, tok.col,
                      f"{name}: deleted {tok.type_name} {tok.text!r}", tok.text)

    punct = [t for t in code if _is_punct(t)]
    for tok in take(punct):
        yield Mutant("duplicate-token", duplicate_token(src, tok), tok.line, tok.col,
                      f"{name}: duplicated {tok.text!r}", tok.text)

    pairs = list(zip(code, code[1:]))
    for a, b in take(pairs):
        yield Mutant("swap-adjacent", swap_adjacent(src, a, b), a.line, a.col,
                      f"{name}: swapped {a.text!r}/{b.text!r}", a.text + b.text,
                      b.line, b.col)

    ids = [t for t in code if t.type_name == "ID"]
    for tok in take(ids):
        kw = keywords[tok.index % len(keywords)] if keywords else "return"
        yield Mutant("keyword-for-name", keyword_for_name(src, tok, kw), tok.line, tok.col,
                      f"{name}: replaced identifier {tok.text!r} with keyword {kw!r}", tok.text)

    subs = [t for t in code if t.text in _PUNCT_SUBSTITUTIONS]
    for tok in take(subs):
        repl = _PUNCT_SUBSTITUTIONS[tok.text]
        yield Mutant("punct-substitute", punct_substitute(src, tok, repl), tok.line, tok.col,
                      f"{name}: substituted {tok.text!r} -> {repl!r}", tok.text)

    for tok in take(code):
        yield Mutant("truncate", truncate(src, tok), tok.line, tok.col,
                      f"{name}: truncated after {tok.text!r}", tok.text)

    braces = [t for t in code if t.text == "}"]
    for tok in take(braces):
        yield Mutant("drop-close-brace", drop_close_brace(src, tok), tok.line, tok.col,
                      f"{name}: dropped '}}'", tok.text)


#: Token spellings that open/close nesting. A mutation anchored on one of
#: these can legitimately desync recovery for the rest of the file (every
#: subsequent top-level construct fails independently, not as a near-duplicate
#: cascade) -- see test_mutation_sweep.py's G2 nesting-mutation carve-out.
NESTING_TOKENS = frozenset("{}()[]")


def is_nesting_mutation(mutant: "Mutant") -> bool:
    return any(c in NESTING_TOKENS for c in mutant.site_text)


def nearest_code_token_index(tokens: Sequence[Token], line: int, col: int) -> int:
    """Index into *tokens* (non-trivia) closest to (line, col).

    Used to translate a marker's or a mutation site's (line, col) into a
    token-count position, so "within 2 tokens" (G1, G2) can be measured as
    an index distance rather than a character distance. Heuristic, not
    exact -- good enough for an invariant check that never asserts message
    text, since it only needs to be right to within a token or two.
    """
    best_i, best_d = 0, None
    for i, t in enumerate(tokens):
        d = abs(t.line - line) * 1000 + abs(t.col - col)
        if best_d is None or d < best_d:
            best_d, best_i = d, i
    return best_i
