"""docs/lint-functions.rst freshness (lint-core-plan.md C3.2).

If this fails, the lint engine's function registry has moved on without the
docs -- rebuild, run ``python3 scripts/gen_lint_functions.py`` and commit the
result.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_lint_functions import OUTPUT_PATH, render  # noqa: E402


def test_lint_functions_rst_is_up_to_date(factory):
    functions = factory._lintTestHooks().cel_functions()["functions"]
    assert OUTPUT_PATH.read_text() == render(functions), (
        "docs/lint-functions.rst is stale -- run "
        "`python3 scripts/gen_lint_functions.py` and commit the result")


def test_profile_exclusions_are_not_documented(factory):
    functions = factory._lintTestHooks().cel_functions()["functions"]
    text = OUTPUT_PATH.read_text()
    for f in functions:
        if f["kind"] != "macro":    # a macro's section names no overload id
            assert (f"``{f['id']}``" in text) == f["in_profile"], f["id"]
