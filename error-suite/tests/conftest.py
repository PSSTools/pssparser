"""Harness test fixtures.

Everything here runs against `tests/fixtures/faketool.py`, never a real PSS
tool, so the whole harness suite passes on a machine with no pssparser build.
The two tests that do need one are marked `needs_pssparser` and skip cleanly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))

FIXTURES = SUITE_ROOT / "tests" / "fixtures"
FIXTURE_CASES = FIXTURES / "cases"
FAKETOOL = FIXTURES / "faketool.py"
TOOLS = SUITE_ROOT / "tools"
CASES = SUITE_ROOT / "cases"


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "needs_pssparser: requires an importable pssparser build")


@pytest.fixture
def suite_root() -> Path:
    return SUITE_ROOT


@pytest.fixture
def fixture_cases() -> Path:
    return FIXTURE_CASES


@pytest.fixture
def corpus() -> Path:
    return CASES


@pytest.fixture
def faketool_descriptor():
    from pss_errsuite.descriptor import load_descriptor
    return load_descriptor(TOOLS / "faketool.toml", SUITE_ROOT)


@pytest.fixture
def faketool_json_descriptor():
    from pss_errsuite.descriptor import load_descriptor
    return load_descriptor(TOOLS / "faketool-json.toml", SUITE_ROOT)


@pytest.fixture
def write_case(tmp_path):
    """Write a case file and return the loaded Case."""
    from pss_errsuite.case import load_case

    def _write(name: str, text: str, root: Path | None = None):
        root = root or tmp_path
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return load_case(path, root)
    return _write


@pytest.fixture
def pssparser_available() -> bool:
    try:
        import pssparser  # noqa: F401
        import pssparser.core  # noqa: F401
    except Exception:
        return False
    return True


@pytest.fixture
def require_pssparser(pssparser_available):
    if not pssparser_available:
        pytest.skip("pssparser is not importable (no build in this tree)")
