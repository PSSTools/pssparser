"""Generated-file freshness check for docs/markers.rst.

If this fails, the catalogue in core_checker.py has moved on without the
docs -- run ``python3 scripts/gen_marker_docs.py`` and commit the result.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_marker_docs import OUTPUT_PATH, render  # noqa: E402


def test_markers_rst_is_up_to_date():
    committed = OUTPUT_PATH.read_text()
    current = render()
    assert committed == current, (
        "docs/markers.rst is stale -- run "
        "`python3 scripts/gen_marker_docs.py` and commit the result"
    )
