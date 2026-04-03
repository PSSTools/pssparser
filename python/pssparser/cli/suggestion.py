"""Spellcheck utilities for 'did you mean?' suggestions.

The C++ linker already embeds suggestions in marker messages.  This module
provides:
  - ``extract_suggestion``: pull the suggestion out of a marker message.
  - ``levenshtein`` / ``suggest``: fallback helpers for Python-only checks.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

_DID_YOU_MEAN_RE = re.compile(r"did you mean '([^']+)'\s*\??")


def extract_suggestion(message: str) -> Optional[str]:
    """Return the suggested name from a marker message, or ``None``."""
    m = _DID_YOU_MEAN_RE.search(message)
    return m.group(1) if m else None


def levenshtein(a: str, b: str) -> int:
    """Standard Levenshtein edit distance (consistent with the C++ impl)."""
    m, n = len(a), len(b)
    dp = list(range(n + 1))
    for i in range(1, m + 1):
        prev = dp[0]
        dp[0] = i
        for j in range(1, n + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            tmp = dp[j]
            dp[j] = min(dp[j] + 1, dp[j - 1] + 1, prev + cost)
            prev = tmp
    return dp[n]


def suggest(
    name: str,
    candidates: Iterable[str],
    max_dist: int = 2,
) -> Optional[str]:
    """Return the closest candidate within *max_dist*, or ``None``.

    Tie-breaker: prefer a candidate that matches case-insensitively.
    """
    best: Optional[str] = None
    best_dist = max_dist + 1
    best_case_match = False

    for cand in candidates:
        d = levenshtein(name, cand)
        if d <= 0 or d >= best_dist:
            if d == best_dist and d <= max_dist:
                # tie-break on case-insensitive match
                case_match = name.lower() == cand.lower()
                if case_match and not best_case_match:
                    best = cand
                    best_case_match = True
            continue
        if d <= max_dist:
            best = cand
            best_dist = d
            best_case_match = name.lower() == cand.lower()
    return best
