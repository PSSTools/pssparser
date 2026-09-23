"""Occurrence-completeness gate (pss-scrambler FR-001; plan S3.2).

Recomputes scripts/occgate.py over the legal corpus and requires it to equal
tests/python/baselines/occurrences.json exactly: every ID token that names
something is reported by pssparser.refs.occurrences(), every occurrence is an
ID token (or a ``{{name}}`` in a template string), and the names the linker
leaves unbound on legal input are exactly the recorded ones.

Both directions fail. A new gap is a regression; a closed one is progress to
record by regenerating the baseline in the same change:

    PYTHONPATH=python python3 scripts/occgate.py baseline
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import occgate  # noqa: E402


def test_occurrences_match_baseline():
    if not (ROOT / "packages" / "pss-corpus" / "curated").is_dir():
        pytest.skip("pss-corpus is not present; the baseline was taken with it")
    now = json.loads(json.dumps(occgate.measure(), sort_keys=True))
    base = json.loads(occgate.BASELINE.read_text())
    diff = ["%s: baseline %s, now %s" % (fn, base["gaps"].get(fn), now["gaps"].get(fn))
            for fn in sorted(set(base["gaps"]) | set(now["gaps"]))
            if base["gaps"].get(fn) != now["gaps"].get(fn)]
    assert base["files"] == now["files"], "corpus size changed"
    assert not diff, (
        "occurrence completeness differs from tests/python/baselines/"
        "occurrences.json (regenerate with `scripts/occgate.py baseline` if "
        "deliberate):\n  " + "\n  ".join(diff))


def test_no_file_crashes():
    base = json.loads(occgate.BASELINE.read_text())
    assert not [fn for fn, g in base["gaps"].items() if g.get("crashed")]
