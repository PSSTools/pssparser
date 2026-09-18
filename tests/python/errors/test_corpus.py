"""Runs the L1 curated error corpus (tests/python/errors/data/**/*.pss).

Each case's ``//!`` header is an exact assertion against the markers produced
by parsing the file -- see corpus_loader.py and
docs/design/error-testing-strategy.md §4 (L1).
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from test_helpers import parse_collect, _assign_codes, ALL_MARKERS, ALL_MARKER_BATCHES  # noqa: E402
from pssparser import Parser  # noqa: E402

from .corpus_loader import (  # noqa: E402
    CorpusCase, asserts_pssparser, collect_cases,
)

#: Both corpus roots.  `error-suite/cases/` is the tool-neutral suite, which
#: holds the ported L1 cases; `data/` keeps whatever has not been ported (the
#: L3 golden fixtures live there and are excluded by the loader).  One corpus,
#: two readers -- see docs/design/error-suite-design.md §3.4.
ERROR_SUITE_CASES = (
    Path(__file__).parent.parent.parent.parent / "error-suite" / "cases"
)

CASES = collect_cases()
if ERROR_SUITE_CASES.is_dir():
    CASES += collect_cases(ERROR_SUITE_CASES)


def _case_id(case: CorpusCase) -> str:
    try:
        return str(case.path.relative_to(ERROR_SUITE_CASES))
    except ValueError:
        return case.name


def _matches(case: CorpusCase, marker: dict) -> bool:
    if case.match is None:
        return True
    msg = marker.get("message", "")
    if case.match_is_regex:
        return re.search(case.match, msg) is not None
    return case.match in msg


def _parse_multi_collect(case: CorpusCase):
    """S12 only: feed ``case.files`` to the parser together, in order.

    Mirrors ``test_helpers.parse_collect`` (same exception handling, same
    ``ALL_MARKERS``/``ALL_MARKER_BATCHES`` bookkeeping so the global lints in
    ``test_message_lints.py`` see these markers too) but for multiple named
    files instead of one anonymous one. The case file's own content is
    ``case.code`` (already read); companion files (leading-underscore names)
    are read fresh from disk beside it.
    """
    files = []
    for name in case.files:
        if name == case.path.name:
            files.append((name, case.code))
        else:
            files.append((name, (case.path.parent / name).read_text()))

    parser = Parser()
    if case.max_errors is not None:
        parser.set_max_errors(case.max_errors)

    try:
        parser.parses(files)
        parser.link()
    except Exception as e:
        markers = getattr(e, "markers", None)
        if markers is None:
            raise
        coded = _assign_codes(markers)
        ALL_MARKERS.extend(coded)
        ALL_MARKER_BATCHES.append(coded)
        return coded

    coded = _assign_codes(parser.markers)
    ALL_MARKERS.extend(coded)
    ALL_MARKER_BATCHES.append(coded)
    return coded


@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_corpus_case(case: CorpusCase):
    if case.xfail:
        pytest.xfail(case.xfail)

    if case.expect == "accept":
        # A tool-neutral `accept` case asserts silence, which is an assertion
        # about us like any other.
        if case.files is not None:
            markers = _parse_multi_collect(case)
        else:
            _root, markers = parse_collect(case.code, filename=case.path.name)
        errors = [m for m in markers if m.get("severity") == "error"]
        assert not errors, (
            f"{case.name}: expected a clean parse, got "
            f"{[m.get('message') for m in errors]}")
        return

    if not asserts_pssparser(case):
        pytest.skip(
            "tool-neutral case with no pssparser expectation: its `at:` is "
            "where a *good* diagnostic points, which is the error suite's "
            "business, not pytest's (corpus_loader.asserts_pssparser)")

    if case.files is not None:
        markers = _parse_multi_collect(case)
    else:
        _root, markers = parse_collect(
            case.code, filename=case.path.name, max_errors=case.max_errors
        )

    matching = [
        m for m in markers
        if m.get("severity") == case.severity and _matches(case, m)
    ]

    assert matching, (
        f"{case.name}: no {case.severity} marker matched "
        f"match={case.match!r}; got messages="
        f"{[m.get('message') for m in markers]}"
    )

    assert len(matching) == case.count, (
        f"{case.name}: expected {case.count} matching marker(s), got "
        f"{len(matching)}: {[m.get('message') for m in matching]}"
    )

    if case.id is not None:
        for m in matching:
            assert m.get("code") == case.id, (
                f"{case.name}: expected id {case.id!r}, got "
                f"{m.get('code')!r} for message {m.get('message')!r}"
            )

    expected_file = case.at_file if case.at_file is not None else case.path.name
    if case.files is not None:
        first = matching[0]
        assert first.get("file") == expected_file, (
            f"{case.name}: expected primary marker attributed to file "
            f"{expected_file!r}, got {first.get('file')!r}"
        )

    if case.at is not None:
        line, col, col_end = case.at
        first = matching[0]
        assert first.get("line") == line and first.get("col") == col, (
            f"{case.name}: expected primary location {line}:{col}, got "
            f"{first.get('line')}:{first.get('col')}"
        )
        if col_end is not None:
            extent = first.get("extent") or 0
            assert first.get("col", 0) + extent == col_end + 1, (
                f"{case.name}: expected span ending at column {col_end}, "
                f"extent gives {first.get('col')}..{first.get('col', 0) + extent - 1}"
            )

    if case.hint is not None:
        # The hint may be in the message or in a note attached to it: advice
        # that does not fit the one-line message travels as `related` (A9 moved
        # the mustache `{ {` workaround there to stay under the G7 length
        # limit). Either home satisfies "the tool told the user how to fix it".
        first = matching[0]
        where = [first.get("message", "")] + [
            r.get("label", "") for r in first.get("related", [])
        ]
        assert any(case.hint in w for w in where), (
            f"{case.name}: expected hint substring {case.hint!r} in "
            f"{first.get('message')!r} or its notes {where[1:]!r}"
        )

    for expected in case.also:
        first = matching[0]
        related = first.get("related", [])
        assert any(
            r.get("line") == expected.line
            and r.get("col") == expected.col
            and expected.label in r.get("label", "")
            for r in related
        ), (
            f"{case.name}: expected related location {expected.line}:"
            f"{expected.col} {expected.label!r}, got {related}"
        )


@pytest.mark.parametrize(
    "category", [
        "syntax.punct", "syntax.braces", "syntax.names", "syntax.keyword",
        "syntax.scope", "syntax.expr", "syntax.type", "syntax.lex",
        "syntax.stmt", "syntax.reserved", "syntax.recover",
        "syntax.multifile", "syntax.volume", "syntax.template",
        "semantic.compile",
        # `semantic.template` is deliberately absent: both of its cases are
        # xfail on E9-S7-D1 (uncatalogued template-arity messages), which is a
        # known, written-up gap rather than a class nobody has looked at.
    ],
)
def test_category_has_a_non_xfail_case(category):
    """A class that is all-xfail is one nobody has looked at.

    Parametrized over the suite's taxonomy rather than over directory names
    now that the corpus lives in `error-suite/cases/` (design §3.4).
    """
    cases = [c for c in CASES if c.cls == category]
    assert cases, f"no corpus cases found in class {category}"
    assert any(not c.xfail for c in cases), (
        f"every case in {category} is xfail -- add at least one case that "
        f"documents correct current behaviour"
    )
