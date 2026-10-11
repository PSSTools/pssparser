"""The AST model reference (docs/ast/) builds without a warning.

docs/ast/ is rendered from ast/*.yaml by pyastbuilder's Sphinx support, so the
yaml's ``doc:`` text is reStructuredText: a bare ``*`` or ``|`` in it, or a
``See Also`` name that no longer exists, is a docs-build warning at the yaml
line. The full documentation is not ``-W`` clean (other pages have warnings of
their own), so this builds just docs/ast/ -- with the real ``docs/conf.py``
model configuration and the ``-W`` flag -- in a scratch project.

Skipped without Sphinx, without pyastbuilder's Sphinx support, or without
Graphviz's ``dot``.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("sphinx")
pytest.importorskip("astbuilder.sphinx")

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

CONF = '''
import sys
sys.path.insert(0, %(ext)r)
_ns = {"__file__": %(conf)r}
exec(compile(open(%(conf)r).read(), %(conf)r, "exec"), _ns)
astbuilder_models = _ns["astbuilder_models"]
astbuilder_models["pss"]["yaml"] = [%(yaml)r]
extensions = ["astbuilder.sphinx"]
project = "pssparser AST reference check"
'''


def test_ast_reference_builds_clean(tmp_path):
    if shutil.which("dot") is None:
        pytest.skip("graphviz is not installed")
    src = tmp_path / "src"
    shutil.copytree(DOCS / "ast", src / "ast")
    (src / "conf.py").write_text(CONF % {
        "ext": str(DOCS / "_ext"), "conf": str(DOCS / "conf.py"),
        "yaml": str(ROOT / "ast" / "*.yaml")})
    (src / "index.rst").write_text("Check\n=====\n\n.. toctree::\n\n   ast/index\n")
    # ast/index.rst links to this page of the full documentation.
    (src / "lint-rule-authoring.rst").write_text(":orphan:\n\nRules\n=====\n")
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html",
                        str(src), str(tmp_path / "out")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    page = (tmp_path / "out" / "ast" / "expr.html").read_text()
    assert 'id="astb-class-ExprBin"' in page
