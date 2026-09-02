"""L3: rendered-output goldens (E-8).

L1 (``test_corpus.py``) pins the *marker dict* -- id, location, related
locations as structured data. L3 pins what a user actually sees on a
terminal: the full CLI stdout/stderr for a curated set of cases, captured to
``tests/python/errors/data/golden/<name>.txt``. Small on purpose (see
``docs/design/error-testing-strategy.md`` §4 L3) -- goldens catch formatting
regressions in the *renderer* (``cli/output.py``), not the message catalogue,
which L1 already covers.

Run ``pytest tests/python/errors/test_golden.py --bless-errors`` to
(re)generate the golden files after an intentional rendering change, then
inspect the diff before committing.
"""
from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pytest

from pssparser.cli.commands import cmd_parse

REPO_ROOT = Path(__file__).resolve().parents[3]
GOLDEN_DIR = Path(__file__).parent / "data" / "golden"


@dataclass
class GoldenCase:
    name: str
    source: str  # path relative to REPO_ROOT -- kept relative so the
    # rendered "file:line:col" header is stable across checkouts/machines.
    use_json: bool = False
    max_errors: int = 20
    color: Optional[bool] = False


# Picked to exercise: a plain single diagnostic with no related location; a
# diagnostic *with* a related location (both the component and struct D8
# opener-pointer shapes, plus the short-file EOF-past-end-of-source case,
# where the related note has a location but -- correctly -- no source line to
# show, since nothing exists past EOF); several diagnostics from one parse;
# multi-line source context (error several lines into a nested body); an
# error at the very start of a line; JSON rendering (plain and with a related
# location, to pin that JsonOutput also serialises `related`); a warning
# (not just `error`); the `--max-errors` cap firing (PSS029, several
# diagnostics); a completely clean file (0 errors, exit 0); and forced-color
# output, to pin the ANSI escape sequences.
CASES: List[GoldenCase] = [
    GoldenCase(
        "plain_single_diagnostic",
        "tests/python/errors/data/punct/missing_semicolon_return.pss",
    ),
    GoldenCase(
        "related_location_component",
        "tests/python/errors/data/braces/unclosed_component_opener_pointer.pss",
    ),
    GoldenCase(
        "related_location_struct",
        "tests/python/errors/data/braces/unclosed_struct_opener_pointer.pss",
    ),
    GoldenCase(
        "related_location_eof_short_file",
        "tests/python/errors/data/syntax/unexpected_eof.pss",
    ),
    GoldenCase(
        "multiple_diagnostics_single_line",
        "tests/python/errors/data/names/expected_identifier_after_garbage_token.pss",
    ),
    GoldenCase(
        "keyword_mislabel",
        "tests/python/errors/data/keywords/rand_struct.pss",
    ),
    GoldenCase(
        "missing_identifier_struct",
        "tests/python/errors/data/names/struct_no_name.pss",
    ),
    GoldenCase(
        "missing_brace_component",
        "tests/python/errors/data/punct/missing_open_brace_component.pss",
    ),
    GoldenCase(
        "cascade_suppressed",
        "tests/python/errors/data/punct/cascade_garbage_tokens.pss",
    ),
    GoldenCase(
        "volume_cap_pss029",
        "tests/python/errors/data/volume/max_errors_cap_fires.pss",
        max_errors=3,
    ),
    GoldenCase(
        "json_output_related",
        "tests/python/errors/data/braces/unclosed_component_opener_pointer.pss",
        use_json=True,
    ),
    GoldenCase(
        "json_output_plain",
        "tests/python/errors/data/punct/missing_semicolon_return.pss",
        use_json=True,
    ),
    GoldenCase(
        "warning_diagnostic",
        "tests/python/errors/data/golden/warning_annotation.pss",
    ),
    GoldenCase(
        "clean_file_zero_errors",
        "tests/python/errors/data/golden/clean.pss",
    ),
    GoldenCase(
        "colored_output",
        "tests/python/errors/data/punct/missing_semicolon_return.pss",
        color=True,
    ),
]

assert len({c.name for c in CASES}) == len(CASES), "duplicate golden case name"


def _render(case: GoldenCase, monkeypatch) -> str:
    # chdir to the repo root so `case.source` (already relative to it) is
    # both a valid path to read *and* the exact string that ends up in the
    # rendered "file:line:col" header -- independent of the directory pytest
    # happened to be invoked from.
    monkeypatch.chdir(REPO_ROOT)

    stdout = io.StringIO()
    stderr = io.StringIO()
    exit_code = cmd_parse(
        files=[case.source],
        use_json=case.use_json,
        color=case.color,
        max_errors=case.max_errors,
        stdout=stdout,
        stderr=stderr,
    )
    return (
        f"$ pssparser {case.source} (exit {exit_code})\n"
        f"--- stdout ---\n{stdout.getvalue()}"
        f"--- stderr ---\n{stderr.getvalue()}"
    )


def _golden_path(case: GoldenCase) -> Path:
    return GOLDEN_DIR / f"{case.name}.txt"


@pytest.mark.parametrize("case", CASES, ids=lambda c: c.name)
def test_golden(case: GoldenCase, monkeypatch, bless_errors):
    rendered = _render(case, monkeypatch)
    path = _golden_path(case)

    if bless_errors:
        path.write_text(rendered)
        return

    assert path.exists(), (
        f"missing golden file {path}; run "
        f"'pytest {Path(__file__).relative_to(REPO_ROOT)} --bless-errors' "
        f"to generate it"
    )
    expected = path.read_text()
    assert rendered == expected, (
        f"{case.name}: rendered CLI output no longer matches "
        f"{path.relative_to(REPO_ROOT)} -- re-run with --bless-errors and "
        f"review the diff if this is an intentional rendering change"
    )


def test_no_stray_golden_files():
    """Every .txt under data/golden/ must belong to a case above.

    A golden file with no corresponding case is dead: --bless-errors will
    never touch it again, so it can silently drift from what the renderer
    actually produces.
    """
    expected_names = {f"{c.name}.txt" for c in CASES}
    actual_names = {p.name for p in GOLDEN_DIR.glob("*.txt")}
    stray = actual_names - expected_names
    assert not stray, f"golden .txt files with no matching GoldenCase: {stray}"
