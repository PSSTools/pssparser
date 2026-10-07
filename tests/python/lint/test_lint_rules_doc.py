"""docs/lint-rules.rst freshness, and --explain (plan F1.10).

If the freshness test fails, the rule catalogue has moved on without the
docs -- run ``python3 scripts/gen_lint_rules.py`` and commit the result.
"""
import io
import sys
from pathlib import Path

from pssparser.checkers import taxonomy
from pssparser.cli.app import main
from pssparser.lint.catalog import ALL

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from gen_lint_rules import OUTPUT_PATH, render  # noqa: E402


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    old = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = out, err
    try:
        rc = main(argv)
    finally:
        sys.stdout, sys.stderr = old
    return rc, out.getvalue(), err.getvalue()


def test_lint_rules_rst_is_up_to_date():
    assert OUTPUT_PATH.read_text() == render(), (
        "docs/lint-rules.rst is stale -- run "
        "`python3 scripts/gen_lint_rules.py` and commit the result")


def test_every_rule_has_an_anchor_matching_the_doc_url():
    text = OUTPUT_PATH.read_text()
    for md in ALL:
        anchor = taxonomy.doc_url(md.id).rsplit("#", 1)[1]
        assert f".. _{anchor}:" in text, md.id


def test_explain_by_id():
    rc, out, _ = _run(["--explain", "LINT601"])
    assert rc == 0
    assert out.startswith("LINT601 deprecated-braceless-compile-if\n")
    assert "tier:              portability" in out
    assert "docs:              https://" in out


def test_explain_by_old_id_says_so():
    rc, out, _ = _run(["--explain", "PSS104"])
    assert rc == 0
    assert "PSS104 is the old ID of LINT601" in out


def test_explain_a_core_error():
    rc, out, _ = _run(["--explain", "PSS002"])
    assert rc == 0
    assert "default severity:  error" in out


def test_explain_unknown_gives_did_you_mean():
    rc, _, err = _run(["--explain", "unknown-anotation"])
    assert rc == 2
    assert "did you mean 'unknown-annotation'" in err
