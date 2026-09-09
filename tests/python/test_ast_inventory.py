"""Runs ``scripts/check_ast_inventory.py`` as part of the suite.

The script is the enforcement mechanism for phase 6 of
docs/ast-coverage-plan.md: it fails when ``ast/*.yaml`` or ``src/PSSParser.g4``
stops being a truthful description of what the parser produces. Its own module
docstring explains what each of its three checks catches and why nothing else
catches it.

This wrapper exists so the check runs wherever the suite runs, rather than only
in a CI job somebody has to remember to add. It is deliberately thin: the
script is also useful standalone, and ``--list`` is how you triage a finding.
"""
import os
import subprocess
import sys

import pytest

PROJ_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCRIPT = os.path.join(PROJ_DIR, "scripts", "check_ast_inventory.py")
ALLOWLIST = os.path.join(PROJ_DIR, "scripts", "ast_inventory_allowlist.txt")


def _run(*args):
    return subprocess.run(
        [sys.executable, SCRIPT] + list(args),
        cwd=PROJ_DIR, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        universal_newlines=True)


@pytest.mark.skipif(not os.path.exists(SCRIPT), reason="check script not present")
def test_ast_inventory_has_no_new_findings():
    """Every AST class is built, every risky class has a symbol-tree visitor,
    every grammar rule is reachable -- or is allowlisted with a reason."""
    r = _run()
    assert r.returncode == 0, (
        "scripts/check_ast_inventory.py reported a finding.\n\n%s\n"
        "Either fix it, or -- if it is intended -- add an entry with a reason "
        "to scripts/ast_inventory_allowlist.txt. Run the script with --list to "
        "see every finding." % r.stdout)


@pytest.mark.skipif(not os.path.exists(SCRIPT), reason="check script not present")
def test_every_allowlist_entry_carries_a_reason():
    """An exemption without a stated reason is indistinguishable from an
    unexamined one, which is the state this whole check exists to end."""
    for lineno, line in enumerate(open(ALLOWLIST), 1):
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        assert len(parts) == 2 and parts[1].strip(), (
            "%s:%d: allowlist entry has no reason: %r"
            % (os.path.relpath(ALLOWLIST, PROJ_DIR), lineno, line))
