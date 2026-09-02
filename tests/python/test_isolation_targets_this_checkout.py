"""``P7-X1``: the out-of-process harness must exercise *this* working tree.

Every out-of-process test -- the whole corpus sweep, every crash-freedom case,
every CLI exit-status case -- runs through :func:`isolation.run_isolated`, which
spawns ``python -m pssparser`` with ``cwd`` set to a temporary directory.  The
suite is normally invoked as ``PYTHONPATH=python pytest ...``: a *relative*
path, which resolves against the repository root in the parent process and
against the temporary directory in the child.  It therefore resolves to nothing
in the child, which falls back to whatever ``pssparser`` the ambient
``sys.path`` provides.

This was not a theoretical hazard.  With a sibling project installed -- an
``easy-install.pth`` naming another checkout's ``packages/pssparser/python``
is the ordinary arrangement here -- the child imported *that* parser.  A
grammar fix in this tree was invisible to the sweep, and a corpus file repaired
against the fix failed with the pre-fix diagnostic.  Nothing errored; the gate
simply stopped being about this repository, and would have stayed that way.

The failure mode is silent by construction, so it needs a test of its own: no
parser behaviour is wrong in either checkout, and the two are similar enough
that results usually agree.  They disagree exactly when this repository has
changed -- which is the only time the sweep matters.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from isolation import (  # noqa: E402
    _REPO_PYTHON, _child_env, _parent_package_root, run_isolated)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _parent_pssparser():
    """Where *this* process imported ``pssparser`` from.

    The assertions below compare against this rather than against
    ``REPO_ROOT/python``, because which copy is under test depends on how the
    suite was invoked: the working tree under ``PYTHONPATH=python``, an
    installed wheel in CI.  Both are legitimate; a child that disagrees with
    its parent is not.
    """
    import pssparser
    return Path(pssparser.__file__).resolve()


def test_the_pinned_path_is_this_repository():
    """The pin is computed from ``__file__``, so a move must not silently miss."""
    assert Path(_REPO_PYTHON) == REPO_ROOT / "python", (
        "isolation._REPO_PYTHON no longer names this repository's python/ "
        "directory (%s); the file was probably moved without updating the "
        "parents[] depth." % _REPO_PYTHON)
    assert (Path(_REPO_PYTHON) / "pssparser" / "__init__.py").is_file(), (
        "%s does not contain an importable pssparser" % _REPO_PYTHON)


def test_the_child_env_puts_the_parents_parser_first():
    """Prepended, not appended: a third-party install must lose, not win."""
    entries = _child_env()["PYTHONPATH"].split(os.pathsep)
    assert entries[0] == _parent_package_root(), (
        "the parser this process imported must come first on the child's "
        "PYTHONPATH, or some other install shadows it; got %r" % (entries,))


def test_the_pin_follows_the_working_tree_when_the_tree_is_under_test():
    """The developer-machine case, asserted where it applies.

    Under ``PYTHONPATH=python`` the pin must be the working tree -- that is the
    P7-X1 guarantee.  Skipped rather than inverted when the suite runs against
    an installed wheel (CI), where the working tree is not importable at all.
    """
    if _parent_pssparser().parent.parent != (REPO_ROOT / "python").resolve():
        import pytest
        pytest.skip("suite is running against an installed pssparser, not the "
                    "working tree; see _parent_package_root()")
    assert _parent_package_root() == _REPO_PYTHON


def test_an_isolated_run_imports_the_same_parser_as_its_parent():
    """The end-to-end assertion, and the one that actually caught this.

    Asks the child where it found ``pssparser``, rather than inferring it from
    the environment -- the environment is what was wrong, so it cannot also be
    the evidence.
    """
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-c",
         "import pssparser, sys; sys.stdout.write(pssparser.__file__)"],
        capture_output=True, text=True, cwd=os.path.dirname(os.devnull) or "/",
        env=_child_env(), timeout=60)
    assert proc.returncode == 0, proc.stderr
    found = Path(proc.stdout.strip()).resolve()
    assert found == _parent_pssparser(), (
        "an isolated child imported a different pssparser (%s) than its parent "
        "(%s). Every out-of-process gate in this suite was testing that copy."
        % (found, _parent_pssparser()))


def test_an_isolated_run_can_import_the_compiled_core():
    """``pssparser.core`` is the extension; without it the CLI dies at startup.

    Distinct from the test above because the failure that blocked v3.1.0 got
    *that* one right and this one wrong: the child imported the intended
    ``pssparser/__init__.py`` and then died on ``import pssparser.core``,
    because the pinned copy was a source tree with no built extension.  The
    package resolving is not the same claim as the package working.
    """
    import subprocess
    proc = subprocess.run(
        [sys.executable, "-c", "import pssparser.core"],
        capture_output=True, text=True, cwd=os.path.dirname(os.devnull) or "/",
        env=_child_env(), timeout=60)
    assert proc.returncode == 0, (
        "an isolated child cannot import the compiled extension, so every "
        "out-of-process test will fail at startup:\n%s" % proc.stderr)


def test_an_isolated_run_sees_a_grammar_change_made_here():
    """A behavioural probe, not a path assertion.

    ``exec file`` in a *component* body (Example 309) is accepted by this tree
    and was rejected before P7-G3.  It is a cheap stand-in for "the child is
    running the parser that was just built": if the child ever reverts to an
    older or foreign copy, this is the shape of failure it will produce.
    """
    res = run_isolated(
        'package p { component C { exec file "f.txt" = "x"; } }',
        args=["--syntax-only"])
    assert res.rc == 0, (
        "an isolated child rejected source this tree accepts in-process, which "
        "means it is not running this tree's parser: %s" % res.describe())
