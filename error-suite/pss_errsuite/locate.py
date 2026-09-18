"""Location tolerance.

``--tolerance token:N`` is the default policy, and it needs an actual notion of
"N tokens away".  Measuring in *columns* would make the policy depend on how
long the identifiers in a case happen to be, so a case with a 20-character type
name would be judged more leniently than one with a 2-character name for no
reason at all.  So we lex, crudely.

The lexer is deliberately approximate and PSS-agnostic: identifiers, numbers
(including based literals), strings, comments-as-nothing, and everything else
as single-character punctuation.  It only ever has to *count* tokens between
two positions, never classify them, and any two readings that agree on
tokenization agree on the count.
"""
from __future__ import annotations

import bisect
import re

_TOKEN_RE = re.compile(r"""
      (?P<ws>\s+)
    | (?P<line_comment>//[^\n]*)
    | (?P<block_comment>/\*.*?\*/)
    | (?P<string>"(?:\\.|[^"\\])*")
    | (?P<based>\d+\s*'\s*[bBoOdDhH]\s*[0-9a-fA-F_xXzZ?]+)
    | (?P<number>\d[\w.]*)
    | (?P<ident>[A-Za-z_][A-Za-z0-9_]*)
    | (?P<punct>.)
""", re.VERBOSE | re.DOTALL)

_SKIP = {"ws", "line_comment", "block_comment"}


def token_positions(source: str) -> list[tuple[int, int]]:
    """1-based ``(line, col)`` of every token start, in order."""
    positions: list[tuple[int, int]] = []
    line, col = 1, 1
    for m in _TOKEN_RE.finditer(source):
        kind = m.lastgroup
        text = m.group()
        if kind not in _SKIP:
            positions.append((line, col))
        nl = text.count("\n")
        if nl:
            line += nl
            col = len(text) - text.rfind("\n")
        else:
            col += len(text)
    return positions


def token_distance(source: str, a: tuple[int, int], b: tuple[int, int]) -> int:
    """How many token boundaries separate two positions."""
    positions = token_positions(source)
    ia = bisect.bisect_left(positions, a)
    ib = bisect.bisect_left(positions, b)
    return abs(ia - ib)


class Tolerance:
    """Policy object: parsed once per run and recorded in the run file, so two
    runs are only ever compared under the same policy."""

    def __init__(self, spec: str = "token:2"):
        self.spec = spec
        if spec == "exact":
            self.kind, self.n = "exact", 0
        elif spec == "line":
            self.kind, self.n = "line", 0
        elif spec.startswith("token:"):
            self.kind = "token"
            try:
                self.n = int(spec.split(":", 1)[1])
            except ValueError:
                raise ValueError(
                    f"bad tolerance {spec!r}; expected 'exact', 'line' or "
                    f"'token:N'") from None
        else:
            raise ValueError(
                f"bad tolerance {spec!r}; expected 'exact', 'line' or "
                f"'token:N'")

    def __repr__(self) -> str:
        return f"Tolerance({self.spec!r})"

    def accepts(self, source: str, expected: tuple[int, int],
                actual: tuple[int, int] | None) -> bool:
        if actual is None or actual[0] is None:
            return False
        if self.kind == "exact":
            return tuple(actual) == tuple(expected)
        if self.kind == "line":
            return actual[0] == expected[0]
        if actual[1] is None:
            return actual[0] == expected[0]
        return token_distance(source, tuple(expected), tuple(actual)) <= self.n

    def distance(self, source: str, expected: tuple[int, int],
                 actual: tuple[int, int] | None) -> float:
        """Ranking key for picking the primary diagnostic."""
        if actual is None or actual[0] is None:
            return float("inf")
        if actual[1] is None:
            return abs(actual[0] - expected[0]) * 1000.0
        return float(token_distance(source, tuple(expected), tuple(actual)))
