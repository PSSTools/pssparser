"""docs/lint-nodes.rst freshness (rule-authoring-requests-2026-10-10.md B6).

If this fails, the AST (``ast/*.yaml``) or the way the rule checker types a
field has moved on without the docs -- rebuild, run
``python3 scripts/gen_lint_nodes.py`` and commit the result.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_lint_nodes import OUTPUT_PATH, render  # noqa: E402


def test_lint_nodes_rst_is_up_to_date(factory):
    assert OUTPUT_PATH.read_text() == render(), (
        "docs/lint-nodes.rst is stale -- run "
        "`python3 scripts/gen_lint_nodes.py` and commit the result")


def test_the_fields_a_rule_author_needs_are_listed():
    text = OUTPUT_PATH.read_text()
    field = text.split("\n``Field``\n", 1)[1].split("\n.. _lint-node-", 1)[0]
    assert "``FieldAttr`` flags" in field
    assert "Base: :ref:`NamedScopeChild <lint-node-NamedScopeChild>`" in field
    assert "* ``FieldAttr.Rand``" in text
    # A field the checker cannot read is left out.
    assert "``id2idx``" not in text      # RootSymbolScope's map
