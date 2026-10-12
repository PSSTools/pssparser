"""Every AST definition in ast/*.yaml is documented.

A class, field, enum, flags or value with no description, or an
``Attributes:`` entry naming no field, is listed by
``scripts/ast_doc_coverage.py``; this fails on any. The descriptions are the
AST model reference (docs/ast/).

Skipped without pyastbuilder.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("astbuilder")

ROOT = Path(__file__).resolve().parents[2]


def test_every_ast_definition_is_documented():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "ast_doc_coverage.py"),
                        "--thin", "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
