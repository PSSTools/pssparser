"""Structural guards on the suite itself.

These encode decisions from design §2 that are easy to break by accident and
impossible to notice by eye:

* the harness must stay runnable by someone who has another vendor's tool and
  no pssparser build;
* run and comparison files must never be committed.
"""
from __future__ import annotations

import ast
import subprocess

import pytest


def _module_files(suite_root):
    return sorted((suite_root / "pss_errsuite").rglob("*.py"))


def test_only_the_inprocess_adapter_mentions_pssparser(suite_root):
    """`import pssparser` anywhere at module level would make the suite
    unusable for its primary audience: someone evaluating *their* tool."""
    offenders = []
    for path in _module_files(suite_root):
        if path.name == "inprocess_pssparser.py":
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            if any(n.split(".")[0] == "pssparser" for n in names):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, f"pssparser imported outside the adapter: {offenders}"


def test_the_inprocess_adapter_imports_lazily(suite_root):
    """Even the adapter must not import at module level, or `import
    pss_errsuite.adapters` explodes on a machine without a build."""
    path = suite_root / "pss_errsuite" / "adapters" / "inprocess_pssparser.py"
    tree = ast.parse(path.read_text(), filename=str(path))
    for node in tree.body:                       # top level only
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""]
        else:
            continue
        assert not any(n.split(".")[0] == "pssparser" for n in names), (
            f"module-level pssparser import at line {node.lineno}")

    # …and the module must be importable with pssparser absent.
    import importlib
    assert importlib.import_module(
        "pss_errsuite.adapters.inprocess_pssparser")


def test_the_harness_has_no_third_party_dependencies(suite_root):
    """Stdlib only, so an outsider can run it on a stock interpreter."""
    stdlib_ok = {"pss_errsuite", "conftest"}
    external = set()
    for path in _module_files(suite_root):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                external.update(a.name.split(".")[0] for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                external.add((node.module or "").split(".")[0])
    import sys
    unknown = {m for m in external
               if m and m not in sys.stdlib_module_names
               and m not in stdlib_ok and m != "pssparser"}
    assert not unknown, f"third-party imports in the harness: {sorted(unknown)}"


def test_no_run_file_is_tracked_by_git(suite_root):
    """The distribution rule only holds if it is mechanical: the suite is
    public, the results are not."""
    proc = subprocess.run(
        ["git", "ls-files", "runs/", "compare.json", "compare.md",
         ".rubric-cache.json"],
        cwd=suite_root, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip("not a git checkout")
    assert proc.stdout.strip() == "", (
        f"run/comparison output is tracked: {proc.stdout}")


def test_gitignore_covers_the_output_paths(suite_root):
    text = (suite_root / ".gitignore").read_text()
    for pattern in ("runs/", "compare.", ".rubric-cache.json"):
        assert pattern in text


def test_licence_and_readme_ship_with_the_suite(suite_root):
    assert (suite_root / "LICENSE").is_file()
    readme = (suite_root / "README.md").read_text()
    assert "pss_errsuite run --tool" in readme, "the two-command quickstart"
