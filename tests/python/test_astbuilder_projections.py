"""pyastbuilder's projections agree with the code generated for ast/*.yaml.

A projection (astbuilder.projection) says how one target API spells each
field: `IExprBin::getLhs()`, `ExprBin.getLhs()`, `ExprBin.lhs`, `node.lhs`.
The AST reference documentation is rendered from those answers
(docs/design/astbuilder-sphinx-plan.md), so they must match what the build
compiles. This generates every backend for pssparser's own schema, as
scripts/astbuilder_snapshot.py does, and checks every field of every class.

Skipped when the installed pyastbuilder predates projections (a PyPI release
older than the checkout in packages/).
"""
from __future__ import annotations

import glob
import subprocess
import sys
from pathlib import Path

import pytest

projection = pytest.importorskip("astbuilder.projection")

from astbuilder.ast import Ast  # noqa: E402
from astbuilder.linker import Linker  # noqa: E402
from astbuilder.parser import Parser  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]

# projection name -> (snapshot subdirectory, projection options)
CASES = {
    "cpp": ("cpp", {"namespace": "pssp::ast"}),
    "python": ("pyext", {"module": "pssparser.ast"}),
    "ts": ("ts", {}),
    "reflect": ("reflect", {}),
}


@pytest.fixture(scope="module")
def model():
    ast = Ast()
    for f in sorted(glob.glob(str(ROOT / "ast" / "*.yaml"))):
        with open(f) as fp:
            Parser(ast).parse(fp)
    Linker().link(ast)
    return ast


@pytest.fixture(scope="module")
def snapshot(tmp_path_factory):
    out = tmp_path_factory.mktemp("astbuilder-snapshot")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "astbuilder_snapshot.py"), str(out)],
                   check=True)
    return out


@pytest.mark.parametrize("name", sorted(CASES))
def test_projection_matches_generated_code(name, model, snapshot):
    subdir, options = CASES[name]
    proj = projection.load_projection(name, model, **options)
    problems = projection.check_generated(model, proj, snapshot / subdir)
    assert problems == [], "\n".join(problems[:20])


def test_every_field_is_reachable(model):
    """Each field is exposed by C++, Python and TypeScript; only maps are
    hidden from reflection."""
    projs = {n: projection.load_projection(n, model, **CASES[n][1]) for n in CASES}
    hidden = []
    for c in model.classes:
        for d in c.data:
            for n, p in projs.items():
                if not p.accessors(c, d):
                    hidden.append((n, c.name, d.name, p.hidden(c, d)))
    assert all(n == "reflect" and "map" in (why or "") for n, _, _, why in hidden), hidden
