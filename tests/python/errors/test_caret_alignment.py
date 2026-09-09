"""The caret-alignment invariant, checked across the whole L1 corpus.

``ast::Location.linepos`` is **1-based** (see ``ast/coretypes.yaml``), and the
marker dicts ``Parser._collectMarkers`` builds carry it through unchanged.  So
for a marker whose message quotes the very name it points at, the source text
under the caret must *be* that name::

    source_line[col-1 : col-1+extent] == quoted_name

This is the regression test for D1 (``docs/design/cli-diagnostics-and-stats.md``
§2): the C++ builder emitted 0-based columns from ``syntaxError`` while every
other producer emitted 1-based ones, and ``_collectMarkers`` applied a single
``+1`` to both -- so the two halves disagreed by one and roughly half the
diagnostics in the tool pointed one character past the token they named.

Rather than an allowlist of messages to skip -- which rots, and whose failure
mode is silently skipping *everything* -- the check calibrates itself:

* If the slice at the caret equals one of the names the message quotes, the
  marker is **verified**.
* If it does not, but the slice one column to the left or right does, the
  marker is **misaligned** -- that is exactly the off-by-one signature, and it
  fails.
* Otherwise the message quotes something that is not at the caret at all
  (``expected ';'``, ``unclosed '{' for component 'C'``) and the marker is
  skipped as **not applicable**.

``test_corpus_has_caret_coverage`` then pins the number of *verified* markers
above a floor, so the suite cannot quietly degrade into skipping every case.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect  # noqa: E402

from .corpus_loader import CorpusCase, collect_cases  # noqa: E402

CASES = [c for c in collect_cases() if not c.xfail]

#: Quoted tokens that are punctuation or token-class jargon rather than source
#: text.  These can coincidentally match a neighbouring slice and manufacture a
#: false "misaligned" verdict, so they never participate in the comparison.
_NOT_A_NAME = re.compile(r"^[^A-Za-z_]*$")

_QUOTED_RE = re.compile(r"'([^']*)'")


def _case_id(case: CorpusCase) -> str:
    return case.name


def _sources(case: CorpusCase) -> dict:
    """Map filename -> source text for every file this case feeds the parser."""
    if case.files is None:
        return {case.path.name: case.code}
    out = {}
    for name in case.files:
        if name == case.path.name:
            out[name] = case.code
        else:
            out[name] = (case.path.parent / name).read_text()
    return out


def _slice_at(text: str, line: int, col: int, extent: int):
    """Return ``extent`` characters at 1-based ``line``/``col``, or None."""
    lines = text.splitlines()
    if line < 1 or line > len(lines):
        return None
    src = lines[line - 1]
    start = col - 1
    if start < 0 or start + extent > len(src):
        return None
    return src[start:start + extent]


def _classify(marker: dict, sources: dict):
    """Return ('verified'|'misaligned'|'n/a', detail)."""
    extent = marker.get("extent") or 0
    col = marker.get("col")
    line = marker.get("line")
    text = sources.get(marker.get("file"))
    if extent <= 0 or not col or not line or text is None:
        return "n/a", None

    names = [n for n in _QUOTED_RE.findall(marker.get("message", ""))
             if n and not _NOT_A_NAME.match(n)]
    if not names:
        return "n/a", None

    here = _slice_at(text, line, col, extent)
    if here is not None and here in names:
        return "verified", here

    for delta in (-1, 1):
        neighbour = _slice_at(text, line, col + delta, extent)
        if neighbour is not None and neighbour in names:
            return "misaligned", (
                f"caret at col {col} covers {here!r}, but the name "
                f"{neighbour!r} that the message quotes sits at col "
                f"{col + delta} -- the column is off by {delta:+d}"
            )

    return "n/a", None


def _markers_for(case: CorpusCase):
    sources = _sources(case)
    if case.files is not None:
        from .test_corpus import _parse_multi_collect
        markers = _parse_multi_collect(case)
    else:
        _root, markers = parse_collect(
            case.code, filename=case.path.name, max_errors=case.max_errors
        )
    return markers, sources


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_caret_lands_on_the_named_token(case: CorpusCase):
    markers, sources = _markers_for(case)

    misaligned = []
    for m in markers:
        verdict, detail = _classify(m, sources)
        if verdict == "misaligned":
            misaligned.append(f"{m.get('message')!r}: {detail}")

    assert not misaligned, (
        f"{case.name}: caret misaligned for "
        f"{len(misaligned)} marker(s):\n  " + "\n  ".join(misaligned)
    )


#: Empirical floor, measured 2026-09-09 after D1 landed.  Raise it when the
#: corpus grows; a *drop* means markers stopped carrying an extent or stopped
#: quoting the name they point at, both of which are regressions in their own
#: right.
MIN_VERIFIED_MARKERS = 50


def test_corpus_has_caret_coverage():
    """The alignment check must actually be checking something.

    Without this, a change that stopped every message quoting its subject --
    or stopped every marker carrying an extent -- would turn the whole of
    ``test_caret_lands_on_the_named_token`` into a no-op that still passes.
    """
    verified = 0
    for case in CASES:
        markers, sources = _markers_for(case)
        for m in markers:
            if _classify(m, sources)[0] == "verified":
                verified += 1

    assert verified >= MIN_VERIFIED_MARKERS, (
        f"only {verified} corpus markers had a caret verified against the "
        f"name they quote (floor is {MIN_VERIFIED_MARKERS}); the alignment "
        f"invariant is no longer being exercised"
    )
