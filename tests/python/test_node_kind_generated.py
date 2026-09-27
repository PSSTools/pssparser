"""src/include/pssp/impl/NodeKind.h is generated from the AST headers
(scripts/gen_node_kind.py). An AST class added, removed or re-parented
without regenerating it would misclassify nodes; this keeps it current."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "gen_node_kind.py"


def test_node_kind_header_is_current():
    if not (ROOT / "build" / "include" / "pssp" / "ast" / "IVisitor.h").is_file():
        pytest.skip("the generated AST headers are not built here")
    r = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
