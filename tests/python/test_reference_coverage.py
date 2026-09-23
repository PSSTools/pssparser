"""Reference-coverage gate (symbol-resolution-plan.md §3, WS0.6).

Recomputes scripts/refcov.py's measurements -- the T-miss slot states, the
bound/unbound counts over the legal corpus, and the schema's reference
fields -- and requires them to equal tests/python/baselines/references.json exactly.

Both directions fail. A slot going from ``reported`` to ``silent``, or a
bound count dropping, is a regression. A slot becoming ``reported`` or an
unbound count dropping is progress, and the baseline is how the plan tracks
it: regenerate it in the same change with

    PYTHONPATH=python python3 scripts/refcov.py baseline
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import refcov  # noqa: E402


@pytest.fixture(scope="module")
def current():
    if not (ROOT / "packages" / "pss-corpus" / "curated").is_dir():
        pytest.skip("pss-corpus is not present; the baseline was taken with it")
    data, _ = refcov.compute()
    return data


def test_reference_coverage_matches_baseline(current):
    baseline = json.loads(refcov.BASELINE.read_text())
    d = refcov.diff(baseline, current)
    assert not d, (
        "reference coverage differs from tests/python/baselines/references.json "
        "(regenerate with `scripts/refcov.py baseline` if deliberate):\n  "
        + "\n  ".join(d))


def test_the_legal_slot_model_is_clean(current):
    """Every slot probe is a one-name edit of this model, so it must link
    cleanly or no slot state means anything."""
    assert current["tmiss"]["00_legal"] == "clean"


def test_no_slot_crashes_or_reports_an_internal_error(current):
    bad = {k: v for k, v in current["tmiss"].items()
           if v in ("crash", "internal", "raw")}
    assert not bad, bad
