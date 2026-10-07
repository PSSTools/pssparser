"""Run every rule fixture directory under ``tests/lint/`` (plan F1.11).

Each directory is named after the rule it tests and holds ``l*.pss`` cases
with ``// expect:`` comments and ``ok_*.pss`` cases that must stay clean.
See ``pssparser.checkers.testing`` for the format.
"""
from pathlib import Path

import pytest

from pssparser.checkers.testing import check_fixture_dir

LINT_DIR = Path(__file__).resolve().parents[2] / "lint"
DIRS = sorted(p for p in LINT_DIR.iterdir() if p.is_dir())


@pytest.mark.parametrize("directory", DIRS, ids=[d.name for d in DIRS])
def test_rule_fixtures(directory):
    check_fixture_dir(str(directory), rules=[directory.name])
